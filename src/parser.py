import enum
import io
import json
import os
from dataclasses import dataclass

import jsonschema

from .scanner import EndOfFileError, Scanner, SourceLocation, Token, TokenType


@dataclass
class ComponentDeclaration:
    source_location: SourceLocation
    name: str
    alias: str
    units: list["UnitDeclaration"]


@dataclass
class UnitDeclaration:
    source_location: SourceLocation
    name: str
    alias: str
    program: list["Statement"]


type Statement = "ReturnStatement | IfStatement | SwitchStatement"


@dataclass
class ReturnStatement:
    source_location: SourceLocation
    transform: list[dict]
    transform_annotation: str

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_return_statement(self)


@dataclass
class IfStatement:
    source_location: SourceLocation
    condiction: "Condiction"
    body: list[Statement]
    else_if_clauses: list["ElseIfClause"]
    else_clause: "ElseClause"

    # for analysis
    body_link: Statement | None = None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_if_statement(self)


@dataclass
class ElseIfClause:
    source_location: SourceLocation
    condiction: "Condiction"
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


@dataclass
class ElseClause:
    # if source_location is None, no ElseClause present
    source_location: SourceLocation | None
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


@dataclass
class SwitchStatement:
    source_location: SourceLocation
    key: str
    key_index: int
    case_clauses: list["CaseClause"]
    default_case_clause: "DefaultCaseClause"

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_switch_statement(self)


@dataclass
class CaseClause:
    source_location: SourceLocation
    values_and_facts: list[tuple[str, str]]
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


@dataclass
class DefaultCaseClause:
    # if source_location is None, no DefaultCaseClause present
    source_location: SourceLocation | None
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


type Condiction = "ConstantCondiction | TestCondiction | CompositeCondiction"


@dataclass
class ConstantCondiction:
    source_location: SourceLocation
    constant: bool

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_constant_condiction(self)


@dataclass
class TestCondiction:
    source_location: SourceLocation
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_test_condiction(self)


@dataclass
class CompositeCondiction:
    source_location: SourceLocation
    logical_op_type: "OpType"
    condiction1: Condiction
    condiction2: Condiction | None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_composite_condiction(self)


class OpType(enum.IntEnum):
    LOGICAL_NOT = enum.auto()
    LOGICAL_OR = enum.auto()
    LOGICAL_AND = enum.auto()


class Visitor:
    def visit_return_statement(self, return_statement: ReturnStatement) -> None:
        raise NotImplementedError()

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        raise NotImplementedError()

    def visit_switch_statement(self, switch_statement: SwitchStatement) -> None:
        raise NotImplementedError()

    def visit_constant_condiction(
        self, constant_condiction: ConstantCondiction
    ) -> None:
        raise NotImplementedError()

    def visit_test_condiction(self, test_condiction: TestCondiction) -> None:
        raise NotImplementedError()

    def visit_composite_condiction(
        self, composite_condiction: CompositeCondiction
    ) -> None:
        raise NotImplementedError()


class Parser:
    __slots__ = ("_scanner", "_buffered_tokens", "_key_2_index")

    def __init__(self, scanner: Scanner) -> None:
        self._scanner = scanner
        self._buffered_tokens: list[Token] = []
        self._key_2_index: dict[str, int] = {}

    def get_component_declaration(self) -> ComponentDeclaration:
        self._import_files()

        component_declaration = self._get_component_declaration()
        t = self._peek_token(1)
        if t.type != TokenType.NONE:
            raise UnexpectedTokenError(t)
        return component_declaration

    def _import_files(self):
        while self._peek_token(1).type == TokenType.IMPORT_KEYWORD:
            self._import_file()

    def _import_file(self):
        current_file_name = self._get_expected_token(
            TokenType.IMPORT_KEYWORD
        ).source_location.file_name
        file_name, source_location = self._get_string_with_source_location()

        if current_file_name != "<unnamed>":
            current_dir_name = os.path.dirname(current_file_name)
            file_name = os.path.join(current_dir_name, file_name)

        try:
            with open(file_name, "r") as f:
                key_index_info_list = json.load(f)

            jsonschema.validate(key_index_info_list, _key_index_info_list_schema)

            for key_index_info in key_index_info_list:
                key = key_index_info["Key"]
                key_index = key_index_info["Idx"]

                self._key_2_index[key] = key_index

        except Exception as e:
            raise ImportFailureError(source_location, file_name, e)

    def _do_get_token(self) -> Token:
        while True:
            t = self._scanner.get_token()
            if t.type not in (TokenType.WHITESPACE, TokenType.COMMENT):
                return t

    def _peek_token(self, pos: int) -> Token:
        assert pos >= 1

        while True:
            if len(self._buffered_tokens) >= pos:
                return self._buffered_tokens[pos - 1]

            try:
                t = self._do_get_token()
            except EndOfFileError:
                return _dummy_token

            self._buffered_tokens.append(t)

    def _get_token(self) -> Token:
        if len(self._buffered_tokens) >= 1:
            return self._buffered_tokens.pop(0)
        else:
            return self._do_get_token()

    def _discard_tokens(self, number_of_tokens: int) -> None:
        assert number_of_tokens >= 1

        for _ in range(number_of_tokens):
            self._get_token()

    def _get_expected_token(self, expected_token_type: TokenType) -> Token:
        t = self._get_token()
        if t.type != expected_token_type:
            raise UnexpectedTokenError(t, expected_token_type)
        return t

    def _get_component_declaration(self) -> ComponentDeclaration:
        source_location = self._get_expected_token(
            TokenType.COMPONENT_KEYWORD
        ).source_location
        component_name = self._get_identifier()
        self._get_expected_token(TokenType.AS_KEYWORD)
        component_alias = self._get_string()
        self._get_expected_token(TokenType.OPEN_BRACE)
        unit_declarations = self._get_unit_declarations()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return ComponentDeclaration(
            source_location,
            component_name,
            component_alias,
            unit_declarations,
        )

    def _get_unit_declarations(self) -> list[UnitDeclaration]:
        unit_declarations: list[UnitDeclaration] = []
        while self._peek_token(1).type == TokenType.UNIT_KEYWORD:
            unit_declaration = self._get_unit_declaration()
            unit_declarations.append(unit_declaration)
        return unit_declarations

    def _get_unit_declaration(self) -> UnitDeclaration:
        source_location = self._get_expected_token(
            TokenType.UNIT_KEYWORD
        ).source_location
        unit_name = self._get_identifier()
        self._get_expected_token(TokenType.AS_KEYWORD)
        unit_alias = self._get_string()
        self._get_expected_token(TokenType.OPEN_BRACE)
        program = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return UnitDeclaration(source_location, unit_name, unit_alias, program)

    def _get_statements(self) -> list[Statement]:
        statements: list[Statement] = []
        while True:
            t = self._peek_token(1)
            match t.type:
                case TokenType.RETURN_KEYWORD:
                    statements.append(self._get_return_statement())
                case TokenType.SWITCH_KEYWORD:
                    statements.append(self._get_switch_statement())
                case TokenType.IF_KEYWORD:
                    statements.append(self._get_if_statement())
                case _:
                    return statements

    def _get_return_statement(self) -> ReturnStatement:
        source_location = self._get_expected_token(
            TokenType.RETURN_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.TRANSFORM_KEYWORD)
        self._get_expected_token(TokenType.OPEN_PAREN)
        transform = self._get_transform()
        self._get_expected_token(TokenType.CLOSE_PAREN)
        self._get_expected_token(TokenType.AS_KEYWORD)
        transform_annotation = self._get_string()
        return ReturnStatement(source_location, transform, transform_annotation)

    def _get_transform(self) -> list[dict]:
        transform_literal, source_location = self._get_string_with_source_location()

        try:
            transform = json.loads(transform_literal)
        except Exception:
            raise InvalidTransformLiteralError(
                source_location, transform_literal, "not a JSON"
            )

        try:
            jsonschema.validate(transform, _transform_schema)
        except Exception as e:
            raise InvalidTransformLiteralError(
                source_location, transform_literal, str(e)
            )

        for transform_item in transform:
            key = transform_item["to"]
            key_index = self._key_2_index.get(key)
            if key_index is None:
                raise UnknownKeyError(source_location, key)
            transform_item["underlying_to"] = key_index

            for operator in transform_item["operators"]:
                from1 = operator.get("from")
                if from1 is not None:
                    underlying_from: list[int] = []
                    for key in from1:
                        key_index = self._key_2_index.get(key)
                        if key_index is None:
                            raise UnknownKeyError(source_location, key)
                        underlying_from.append(int(key_index))
                    operator["underlying_from"] = underlying_from

                op_type = operator.get("op_type")
                if op_type is not None:
                    match op_type:
                        case "any":
                            underlying_op_type = 0
                        case "bool":
                            underlying_op_type = 1
                        case "int":
                            underlying_op_type = 2
                        case "string":
                            underlying_op_type = 3
                        case "float":
                            underlying_op_type = 4
                        case _:
                            underlying_op_type = self._key_2_index.get(op_type)
                            if underlying_op_type is None:
                                raise UnknownKeyError(source_location, op_type)
                    operator["underlying_op_type"] = underlying_op_type

        return transform

    def _get_switch_statement(self) -> SwitchStatement:
        source_location = self._get_expected_token(
            TokenType.SWITCH_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.GET_KEYWORD)
        self._get_expected_token(TokenType.OPEN_PAREN)
        key, key_index = self._get_key()
        self._get_expected_token(TokenType.CLOSE_PAREN)
        self._get_expected_token(TokenType.OPEN_BRACE)

        case_clause = self._get_case_clause()
        case_clauses: list[CaseClause] = [case_clause]
        while self._peek_token(1).type == TokenType.CASE_KEYWORD:
            case_clause = self._get_case_clause()
            case_clauses.append(case_clause)

        default_case_clause = self._maybe_get_default_case_clause()
        self._get_expected_token(TokenType.CLOSE_BRACE)

        return SwitchStatement(
            source_location, key, key_index, case_clauses, default_case_clause
        )

    def _get_case_clause(self) -> CaseClause:
        source_location = self._get_expected_token(
            TokenType.CASE_KEYWORD
        ).source_location
        values_and_facts: list[tuple[str, str]] = []

        while True:
            value = self._get_string()
            self._get_expected_token(TokenType.AS_KEYWORD)
            fact = self._get_string()
            values_and_facts.append((value, fact))

            if self._peek_token(1).type != TokenType.COMMA:
                break

            self._discard_tokens(1)

        self._get_expected_token(TokenType.COLON)

        body = self._get_statements()
        return CaseClause(source_location, values_and_facts, body)

    def _maybe_get_default_case_clause(self) -> DefaultCaseClause:
        t = self._peek_token(1)
        if t.type != TokenType.DEFAULT_KEYWORD:
            return DefaultCaseClause(None, [])

        source_location = t.source_location
        self._discard_tokens(1)
        self._get_expected_token(TokenType.COLON)
        body = self._get_statements()
        return DefaultCaseClause(source_location, body)

    def _get_if_statement(self) -> IfStatement:
        source_location = self._get_expected_token(TokenType.IF_KEYWORD).source_location
        condiction = self._get_condiction(0)
        self._get_expected_token(TokenType.OPEN_BRACE)
        body = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)

        else_if_clauses: list[ElseIfClause] = []
        while (
            self._peek_token(1).type,
            self._peek_token(2).type,
        ) == (
            TokenType.ELSE_KEYWORD,
            TokenType.IF_KEYWORD,
        ):
            else_if_clause = self._get_else_if_clause()
            else_if_clauses.append(else_if_clause)

        else_clause = self._maybe_get_else_clause()

        return IfStatement(
            source_location, condiction, body, else_if_clauses, else_clause
        )

    def _get_else_if_clause(self) -> ElseIfClause:
        source_location = self._get_expected_token(
            TokenType.ELSE_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.IF_KEYWORD)
        condiction = self._get_condiction(0)
        self._get_expected_token(TokenType.OPEN_BRACE)
        body = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return ElseIfClause(source_location, condiction, body)

    def _maybe_get_else_clause(self) -> ElseClause:
        t = self._peek_token(1)
        if t.type != TokenType.ELSE_KEYWORD:
            return ElseClause(None, [])

        source_location = t.source_location
        self._discard_tokens(1)
        self._get_expected_token(TokenType.OPEN_BRACE)
        body = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return ElseClause(source_location, body)

    def _get_condiction(self, min_binary_op_precedence: int | None) -> Condiction:
        t = self._peek_token(1)
        if t.type == TokenType.OPEN_PAREN:
            self._discard_tokens(1)
            condiction = self._get_condiction(0)
            self._get_expected_token(TokenType.CLOSE_PAREN)
        elif t.type == TokenType.LOGICAL_NOT:
            self._discard_tokens(1)
            condiction = CompositeCondiction(
                t.source_location, OpType.LOGICAL_NOT, self._get_condiction(None), None
            )
        else:
            condiction = self._get_basic_condiction()

        if min_binary_op_precedence is None:
            # binary op is not allowed
            return condiction

        while (
            binary_op_type := _token_type_2_binary_op_type.get(self._peek_token(1).type)
        ) is not None:
            binary_op_precedence = _binary_op_type_2_precedence[binary_op_type]
            if binary_op_precedence < min_binary_op_precedence:
                break

            self._discard_tokens(1)
            condiction = CompositeCondiction(
                condiction.source_location,
                binary_op_type,
                condiction,
                self._get_condiction(binary_op_precedence + 1),
            )

        return condiction

    def _get_basic_condiction(self) -> ConstantCondiction | TestCondiction:
        t = self._peek_token(1)
        match t.type:
            case TokenType.TRUE_KEYWORD | TokenType.FALSE_KEYWORD:
                self._discard_tokens(1)
                return ConstantCondiction(
                    t.source_location, t.type == TokenType.TRUE_KEYWORD
                )
            case TokenType.TEST_KEYWORD:
                return self._get_test_condiction()
            case _:
                raise UnexpectedTokenError(t)

    def _get_test_condiction(self) -> TestCondiction:
        source_location = self._get_expected_token(
            TokenType.TEST_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.OPEN_PAREN)
        key, key_index = self._get_key()
        self._get_expected_token(TokenType.COMMA)
        op = self._get_string()
        is_v_op = op.startswith("v_")
        values: list[str] = []
        if is_v_op:
            underlying_values: list[str] = []
        else:
            underlying_values = values

        while True:
            t = self._peek_token(1)
            if t.type != TokenType.COMMA:
                break

            self._discard_tokens(1)
            value, source_location = self._get_string_with_source_location()
            values.append(value)

            if is_v_op:
                key_index = self._key_2_index.get(value)
                if key_index is None:
                    raise UnknownKeyError(source_location, value)
                underlying_values.append(str(key_index))

        self._get_expected_token(TokenType.CLOSE_PAREN)
        self._get_expected_token(TokenType.AS_KEYWORD)
        fact = self._get_string()

        return TestCondiction(
            source_location, key, key_index, op, values, underlying_values, fact
        )

    def _get_identifier(self) -> str:
        return self._get_expected_token(TokenType.IDENTIFIER).data

    def _get_string(self) -> str:
        return self._get_string_with_source_location()[0]

    def _get_string_with_source_location(self) -> tuple[str, SourceLocation]:
        t = self._get_expected_token(TokenType.STRING_LITERAL)
        source_location = t.source_location
        buffer = io.StringIO()

        while True:
            match t.data[0]:
                case '"':
                    _evaluate_single_line_string_literal(t, buffer)

                case "`":
                    buffer.write(t.data[1:-1])

                case _:
                    assert False

            t = self._peek_token(1)
            if t.type != TokenType.PLUS:
                break

            self._discard_tokens(1)
            t = self._get_expected_token(TokenType.STRING_LITERAL)

        return buffer.getvalue(), source_location

    def _get_key(self) -> tuple[str, int]:
        key, source_location = self._get_string_with_source_location()
        key_index = self._key_2_index.get(key)
        if key_index is None:
            raise UnknownKeyError(source_location, key)
        return key, key_index


_dummy_token = Token(TokenType.NONE, "", SourceLocation("", 0, 0, 0))


_token_type_2_binary_op_type: dict[TokenType, OpType] = {
    TokenType.LOGICAL_OR: OpType.LOGICAL_OR,
    TokenType.LOGICAL_AND: OpType.LOGICAL_AND,
}

_binary_op_type_2_precedence: dict[OpType, int] = {
    OpType.LOGICAL_OR: 1,
    OpType.LOGICAL_AND: 2,
}

_key_index_info_list_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Idx": {"type": "integer"},
            "Key": {"type": "string", "minLength": 1},
        },
        "required": ["Idx", "Key"],
    },
}

_transform_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "minLength": 1},
            "operators": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "from": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                        },
                        "op": {"type": "string", "minLength": 1},
                        "values": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                        },
                        "op_type": {"type": "string"},
                    },
                    "required": ["op"],
                },
            },
        },
        "required": ["to"],
    },
}


def _evaluate_single_line_string_literal(t: Token, buffer: io.StringIO):
    i = 1
    j = len(t.data) - 1

    while i < j:
        c = t.data[i]
        i += 1

        if c == "\\":
            c = t.data[i]
            i += 1

            match c:
                case "\\":
                    pass
                case '"':
                    c = '"'
                case _:
                    raise InvalidStringLiteralError(t)

        buffer.write(c)


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        super().__init__(
            f"{source_location.file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )


class UnexpectedTokenError(Error):
    def __init__(
        self, unexpected_token: Token, expected_token_type: TokenType | None = None
    ) -> None:
        description = f"unexpected token {repr(unexpected_token.data)}"
        if expected_token_type is not None:
            description += f", {str(expected_token_type)} is expected"
        super().__init__(unexpected_token.source_location, description)


class ImportFailureError(Error):
    def __init__(
        self, source_location: SourceLocation, file_name: str, e: Exception
    ) -> None:
        super().__init__(source_location, f"failed to import {repr(file_name)}, {e}")


class UnknownKeyError(Error):
    def __init__(self, source_location: SourceLocation, key: str) -> None:
        super().__init__(source_location, f"unknown key {repr(key)}")


class InvalidStringLiteralError(Error):
    def __init__(self, token: Token) -> None:
        super().__init__(
            token.source_location, f"invalid string literal {repr(token.data)}"
        )


class InvalidTransformLiteralError(Error):
    def __init__(
        self, source_location: SourceLocation, transform_literal: str, description: str
    ) -> None:
        super().__init__(
            source_location,
            f"invalid transform literal {repr(transform_literal)}, {description}",
        )
