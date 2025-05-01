import enum
import io
import json
import os
import re
from dataclasses import dataclass
from typing import Any

import jsonschema
from gjson import GJSON
from gjson.exceptions import GJSONParseError

from .scanner import EndOfFileError, Scanner, SourceLocation, Token, TokenType


class KeyRegistry:
    __slots__ = (
        "_loaded_key_file_names",
        "_key_2_index",
    )

    def __init__(self) -> None:
        self._loaded_key_file_names: set[str] = set()
        self._key_2_index: dict[str, int] = {}

    def load_keys_from_file(self, key_file_name: str) -> None:
        if key_file_name in self._loaded_key_file_names:
            return

        with open(key_file_name, "r") as f:
            key_info_list = json.load(f)

        jsonschema.validate(key_info_list, _key_info_list_schema)

        for key_info in key_info_list:
            key = key_info["Key"]
            key_index = key_info["Idx"]
            self._key_2_index[key] = key_index

        self._loaded_key_file_names.add(key_file_name)

    def lookup_key(self, key: str) -> int | None:
        return self._key_2_index.get(key)


@dataclass(kw_only=True)
class ComponentDeclaration:
    source_location: SourceLocation
    name: str
    alias: str
    bundles: list["BundleDeclaration"]


@dataclass(kw_only=True)
class BundleDeclaration:
    source_location: SourceLocation
    name: str
    units: list["UnitDeclaration"]


@dataclass(kw_only=True)
class UnitDeclaration:
    source_location: SourceLocation
    name: str
    alias: str
    default_transform_list: list["Transform"]
    program: list["Statement"]


type Statement = "ReturnStatement | GotoStatement | IfStatement | SwitchStatement"


@dataclass(kw_only=True)
class Label:
    source_location: SourceLocation
    name: str


@dataclass(kw_only=True)
class ReturnStatement:
    source_location: SourceLocation
    transform_list: list["Transform"]
    label: Label | None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_return_statement(self)


@dataclass(kw_only=True)
class GotoStatement:
    source_location: SourceLocation
    label_name: str

    # for analysis
    return_statement: ReturnStatement | None = None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_goto_statement(self)


@dataclass(kw_only=True)
class Transform:
    source_location: SourceLocation
    spec: dict
    annotation: str


@dataclass(kw_only=True)
class IfStatement:
    source_location: SourceLocation
    condition: "Condiction"
    body: list[Statement]
    else_if_clauses: list["ElseIfClause"]
    else_clause: "ElseClause"

    # for analysis
    body_link: Statement | None = None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_if_statement(self)


@dataclass(kw_only=True)
class ElseIfClause:
    source_location: SourceLocation
    condition: "Condiction"
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


@dataclass(kw_only=True)
class ElseClause:
    # if source_location is None, no ElseClause present
    source_location: SourceLocation | None
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


@dataclass(kw_only=True)
class SwitchStatement:
    source_location: SourceLocation
    key: str
    key_index: int
    case_clauses: list["CaseClause"]
    default_case_clause: "DefaultCaseClause"

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_switch_statement(self)


@dataclass(kw_only=True)
class CaseClause:
    source_location: SourceLocation
    case_values: list["CaseValue"]
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


@dataclass(kw_only=True)
class CaseValue:
    source_location: SourceLocation
    value: str
    fact: str


@dataclass(kw_only=True)
class DefaultCaseClause:
    # if source_location is None, no DefaultCaseClause present
    source_location: SourceLocation | None
    body: list[Statement]

    # for analysis
    body_link: Statement | None = None


type Condiction = "ConstantCondiction | TestCondiction | CompositeCondiction"


@dataclass(kw_only=True)
class ConstantCondiction:
    source_location: SourceLocation
    constant: bool

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_constant_condition(self)


@dataclass(kw_only=True)
class TestCondiction:
    source_location: SourceLocation
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_test_condition(self)


@dataclass(kw_only=True)
class CompositeCondiction:
    source_location: SourceLocation
    logical_op_type: "OpType"
    condition_1: Condiction
    condition_2: Condiction | None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_composite_condition(self)


class OpType(enum.IntEnum):
    LOGICAL_NOT = enum.auto()
    LOGICAL_OR = enum.auto()
    LOGICAL_AND = enum.auto()


class Visitor:
    def visit_return_statement(self, return_statement: ReturnStatement) -> None:
        raise NotImplementedError()

    def visit_goto_statement(self, goto_statement: GotoStatement) -> None:
        raise NotImplementedError()

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        raise NotImplementedError()

    def visit_switch_statement(self, switch_statement: SwitchStatement) -> None:
        raise NotImplementedError()

    def visit_constant_condition(self, constant_condition: ConstantCondiction) -> None:
        raise NotImplementedError()

    def visit_test_condition(self, test_condition: TestCondiction) -> None:
        raise NotImplementedError()

    def visit_composite_condition(
        self, composite_condition: CompositeCondiction
    ) -> None:
        raise NotImplementedError()


class Parser:
    __slots__ = (
        "_scanner",
        "_buffered_tokens",
        "_key_registry",
    )

    def __init__(self, scanner: Scanner, key_registry: KeyRegistry) -> None:
        self._scanner = scanner
        self._key_registry = key_registry
        self._buffered_tokens: list[Token] = []

    def get_component_declaration(self) -> ComponentDeclaration:
        self._import_files()

        component_declaration = self._get_component_declaration()
        t = self._peek_token(1)
        if t.type != TokenType.NONE:
            raise UnexpectedTokenError(t)
        return component_declaration

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
        component_alias = ""
        if self._peek_token(1).type == TokenType.AS_KEYWORD:
            self._discard_tokens(1)
            component_alias = self._get_string()

        self._import_files()

        bundle_declarations = self._get_bundle_declarations()
        return ComponentDeclaration(
            source_location=source_location,
            name=component_name,
            alias=component_alias,
            bundles=bundle_declarations,
        )

    def _import_files(self):
        while self._peek_token(1).type == TokenType.IMPORT_KEYWORD:
            self._import_file()

    def _import_file(self):
        current_file_name = self._get_expected_token(
            TokenType.IMPORT_KEYWORD
        ).source_location.file_name
        key_file_name, source_location = self._get_string_with_source_location()

        if current_file_name != "<unnamed>":
            current_dir_name = os.path.dirname(current_file_name)
            key_file_name = os.path.join(current_dir_name, key_file_name)

        try:
            self._key_registry.load_keys_from_file(key_file_name)
        except Exception as e:
            raise ImportFailureError(source_location, key_file_name, e)

    def _get_bundle_declarations(self) -> list[BundleDeclaration]:
        bundle_declarations: list[BundleDeclaration] = []
        while self._peek_token(1).type == TokenType.BUNDLE_KEYWORD:
            bundle_declaration = self._get_bundle_declaration()
            bundle_declarations.append(bundle_declaration)
        return bundle_declarations

    def _get_bundle_declaration(self) -> BundleDeclaration:
        source_location = self._get_expected_token(
            TokenType.BUNDLE_KEYWORD
        ).source_location
        bundle_name = self._get_identifier()
        self._get_expected_token(TokenType.OPEN_BRACE)
        unit_declarations = self._get_unit_declarations()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return BundleDeclaration(
            source_location=source_location, name=bundle_name, units=unit_declarations
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
        unit_alias = ""
        if self._peek_token(1).type == TokenType.AS_KEYWORD:
            self._discard_tokens(1)
            unit_alias = self._get_string()
        default_transform_list = self._maybe_get_default_transform_list()
        self._get_expected_token(TokenType.OPEN_BRACE)
        program = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return UnitDeclaration(
            source_location=source_location,
            name=unit_name,
            alias=unit_alias,
            default_transform_list=default_transform_list,
            program=program,
        )

    def _maybe_get_default_transform_list(self) -> list[Transform]:
        if self._peek_token(1).type == TokenType.DEFAULT_KEYWORD:
            self._discard_tokens(1)
            return self._get_transform_list()
        return []

    def _get_transform_list(self) -> list[Transform]:
        if self._peek_token(1).type != TokenType.TRANSFORM_KEYWORD:
            return []

        transform_list: list[Transform] = []

        while True:
            transform = self._get_transform()
            transform_list.append(transform)

            if self._peek_token(1).type != TokenType.COMMA:
                break

            self._discard_tokens(1)

        return transform_list

    def _get_transform(self) -> Transform:
        source_location = self._get_expected_token(
            TokenType.TRANSFORM_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.OPEN_PAREN)
        transform_spec = self._get_transform_spec()
        self._get_expected_token(TokenType.CLOSE_PAREN)
        self._get_expected_token(TokenType.AS_KEYWORD)
        transform_annotation = _render_string_template(
            *self._get_string_with_source_location(), transform_spec
        )
        return Transform(
            source_location=source_location,
            spec=transform_spec,
            annotation=transform_annotation,
        )

    def _get_transform_spec(self) -> dict:
        transform_literal, source_location = self._get_string_with_source_location()

        try:
            transform_spec = json.loads(transform_literal)
        except Exception:
            raise InvalidTransformLiteralError(
                source_location, transform_literal, "not a JSON"
            )

        try:
            jsonschema.validate(transform_spec, _transform_schema)
        except Exception as e:
            raise InvalidTransformLiteralError(
                source_location, transform_literal, str(e)
            )

        key = transform_spec["to"]
        key_index = self._key_registry.lookup_key(key)
        if key_index is None:
            raise UnknownKeyError(source_location, key)
        transform_spec["underlying_to"] = key_index

        for operator in transform_spec["operators"]:
            if operator["op"] == "expr":
                values = operator.get("values")
                if values is not None and len(values) >= 1:
                    underlying_values = values.copy()
                    expr_keys: list[str] = []
                    parts = re.split(
                        r"(^|[^a-zA-Z0-9_])(GetFunc(?:Int|Float))(\()([^\)]+)(\))",
                        underlying_values[0],
                        flags=re.MULTILINE,
                    )
                    i = 0
                    last_part = ""
                    while i < len(parts):
                        if parts[i] == "(" and last_part in (
                            "GetFunc",
                            "GetFuncInt",
                            "GetFuncFloat",
                        ):
                            i += 1
                            key = parts[i]
                            key_index = self._key_registry.lookup_key(key)
                            if key_index is None:
                                raise UnknownKeyError(source_location, key)
                            parts[i] = str(key_index)
                            expr_keys.append(key)
                        last_part = parts[i]
                        i += 1
                    underlying_values[0] = "".join(parts)
                    operator["underlying_values"] = underlying_values
                    operator["expr_keys"] = expr_keys

            from1 = operator.get("from")
            if from1 is not None:
                underlying_from: list[int] = []
                for key in from1:
                    key_index = self._key_registry.lookup_key(key)
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
                        underlying_op_type = self._key_registry.lookup_key(op_type)
                        if underlying_op_type is None:
                            raise UnknownKeyError(source_location, op_type)
                operator["underlying_op_type"] = underlying_op_type

        return transform_spec

    def _get_statements(self) -> list[Statement]:
        statements: list[Statement] = []
        while True:
            label = self._maybe_get_label()
            t = self._peek_token(1)
            match t.type:
                case TokenType.RETURN_KEYWORD:
                    statement = self._get_return_statement(label)
                case TokenType.GOTO_KEYWORD:
                    statement = self._get_goto_statement()
                case TokenType.SWITCH_KEYWORD:
                    statement = self._get_switch_statement()
                case TokenType.IF_KEYWORD:
                    statement = self._get_if_statement()
                case _:
                    return statements
            statements.append(statement)

    def _maybe_get_label(self) -> Label | None:
        t1 = self._peek_token(1)
        t2 = self._peek_token(2)
        if (t1.type, t2.type) != (TokenType.IDENTIFIER, TokenType.COLON):
            return None
        self._discard_tokens(2)
        source_location, label_name = t1.source_location, t1.data
        label = Label(source_location=source_location, name=label_name)
        if self._peek_token(1).type != TokenType.RETURN_KEYWORD:
            raise InvalidLabelPositionError(label)
        return label

    def _get_return_statement(self, label: Label | None) -> ReturnStatement:
        source_location = self._get_expected_token(
            TokenType.RETURN_KEYWORD
        ).source_location
        transform_list = self._get_transform_list()
        return ReturnStatement(
            source_location=source_location, transform_list=transform_list, label=label
        )

    def _get_goto_statement(self) -> GotoStatement:
        source_location = self._get_expected_token(
            TokenType.GOTO_KEYWORD
        ).source_location
        label_name = self._get_identifier()
        return GotoStatement(
            source_location=source_location,
            label_name=label_name,
        )

    def _get_switch_statement(self) -> SwitchStatement:
        source_location = self._get_expected_token(
            TokenType.SWITCH_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.GET_KEYWORD)
        self._get_expected_token(TokenType.OPEN_PAREN)
        key, key_index = self._get_key()
        self._get_expected_token(TokenType.CLOSE_PAREN)
        self._get_expected_token(TokenType.OPEN_BRACE)

        case_clause = self._get_case_clause(key)
        case_clauses: list[CaseClause] = [case_clause]
        while self._peek_token(1).type == TokenType.CASE_KEYWORD:
            case_clause = self._get_case_clause(key)
            case_clauses.append(case_clause)

        default_case_clause = self._maybe_get_default_case_clause()
        self._get_expected_token(TokenType.CLOSE_BRACE)

        return SwitchStatement(
            source_location=source_location,
            key=key,
            key_index=key_index,
            case_clauses=case_clauses,
            default_case_clause=default_case_clause,
        )

    def _get_case_clause(self, key: str) -> CaseClause:
        source_location = self._get_expected_token(
            TokenType.CASE_KEYWORD
        ).source_location
        case_values: list[CaseValue] = []

        while True:
            case_value = self._get_case_value(key)
            case_values.append(case_value)

            if self._peek_token(1).type != TokenType.COMMA:
                break

            self._discard_tokens(1)

        self._get_expected_token(TokenType.COLON)

        body = self._get_statements()
        return CaseClause(
            source_location=source_location, case_values=case_values, body=body
        )

    def _get_case_value(self, key) -> CaseValue:
        value, source_location = self._get_string_with_source_location()
        self._get_expected_token(TokenType.AS_KEYWORD)
        fact = _render_string_template(
            *self._get_string_with_source_location(),
            {"key": key, "op": "eq", "values": [value]},
        )
        return CaseValue(source_location=source_location, value=value, fact=fact)

    def _maybe_get_default_case_clause(self) -> DefaultCaseClause:
        t = self._peek_token(1)
        if t.type != TokenType.DEFAULT_KEYWORD:
            return DefaultCaseClause(source_location=None, body=[])

        source_location = t.source_location
        self._discard_tokens(1)
        self._get_expected_token(TokenType.COLON)
        body = self._get_statements()
        return DefaultCaseClause(source_location=source_location, body=body)

    def _get_if_statement(self) -> IfStatement:
        source_location = self._get_expected_token(TokenType.IF_KEYWORD).source_location
        condition = self._get_condition(0)
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
            source_location=source_location,
            condition=condition,
            body=body,
            else_if_clauses=else_if_clauses,
            else_clause=else_clause,
        )

    def _get_else_if_clause(self) -> ElseIfClause:
        source_location = self._get_expected_token(
            TokenType.ELSE_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.IF_KEYWORD)
        condition = self._get_condition(0)
        self._get_expected_token(TokenType.OPEN_BRACE)
        body = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return ElseIfClause(
            source_location=source_location, condition=condition, body=body
        )

    def _maybe_get_else_clause(self) -> ElseClause:
        t = self._peek_token(1)
        if t.type != TokenType.ELSE_KEYWORD:
            return ElseClause(source_location=None, body=[])

        source_location = t.source_location
        self._discard_tokens(1)
        self._get_expected_token(TokenType.OPEN_BRACE)
        body = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return ElseClause(source_location=source_location, body=body)

    def _get_condition(self, min_binary_op_precedence: int | None) -> Condiction:
        t = self._peek_token(1)
        if t.type == TokenType.OPEN_PAREN:
            self._discard_tokens(1)
            condition = self._get_condition(0)
            self._get_expected_token(TokenType.CLOSE_PAREN)
        elif t.type == TokenType.LOGICAL_NOT:
            self._discard_tokens(1)
            condition = CompositeCondiction(
                source_location=t.source_location,
                logical_op_type=OpType.LOGICAL_NOT,
                condition_1=self._get_condition(None),
                condition_2=None,
            )
        else:
            condition = self._get_basic_condition()

        if min_binary_op_precedence is None:
            # binary op is not allowed
            return condition

        while (
            binary_op_type := _token_type_2_binary_op_type.get(self._peek_token(1).type)
        ) is not None:
            binary_op_precedence = _binary_op_type_2_precedence[binary_op_type]
            if binary_op_precedence < min_binary_op_precedence:
                break

            self._discard_tokens(1)
            condition = CompositeCondiction(
                source_location=condition.source_location,
                logical_op_type=binary_op_type,
                condition_1=condition,
                condition_2=self._get_condition(binary_op_precedence + 1),
            )

        return condition

    def _get_basic_condition(self) -> ConstantCondiction | TestCondiction:
        t = self._peek_token(1)
        match t.type:
            case TokenType.TRUE_KEYWORD | TokenType.FALSE_KEYWORD:
                self._discard_tokens(1)
                return ConstantCondiction(
                    source_location=t.source_location,
                    constant=t.type == TokenType.TRUE_KEYWORD,
                )
            case TokenType.TEST_KEYWORD:
                return self._get_test_condition()
            case _:
                raise UnexpectedTokenError(t)

    def _get_test_condition(self) -> TestCondiction:
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
                key_index = self._key_registry.lookup_key(value)
                if key_index is None:
                    raise UnknownKeyError(source_location, value)
                underlying_values.append(str(key_index))

        self._get_expected_token(TokenType.CLOSE_PAREN)
        self._get_expected_token(TokenType.AS_KEYWORD)
        fact = _render_string_template(
            *self._get_string_with_source_location(),
            {"key": key, "op": op, "values": values},
        )

        return TestCondiction(
            source_location=source_location,
            key=key,
            key_index=key_index,
            op=op,
            values=values,
            underlying_values=underlying_values,
            fact=fact,
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
        key_index = self._key_registry.lookup_key(key)
        if key_index is None:
            raise UnknownKeyError(source_location, key)
        return key, key_index


_key_info_list_schema = {
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


_dummy_token = Token(
    type=TokenType.NONE,
    data="",
    source_location=SourceLocation(
        file_name="", file_offset=-1, line_number=0, column_number=0
    ),
)


_token_type_2_binary_op_type: dict[TokenType, OpType] = {
    TokenType.LOGICAL_OR: OpType.LOGICAL_OR,
    TokenType.LOGICAL_AND: OpType.LOGICAL_AND,
}

_binary_op_type_2_precedence: dict[OpType, int] = {
    OpType.LOGICAL_OR: 1,
    OpType.LOGICAL_AND: 2,
}

_transform_schema = {
    "type": "object",
    "properties": {
        "to": {"type": "string", "minLength": 1},
        "operators": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {
                        "oneOf": [
                            {
                                "type": "array",
                                "items": {"type": "string", "minLength": 1},
                                "minItems": 1,
                            },
                            {
                                "type": "null",
                            },
                        ]
                    },
                    "op": {"type": "string", "minLength": 1},
                    "values": {
                        "oneOf": [
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                            {
                                "type": "null",
                            },
                        ]
                    },
                    "op_type": {"type": "string"},
                },
                "required": ["op"],
            },
        },
    },
    "required": ["to"],
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


_string_template_query_pattern = re.compile(
    r"""
    (?:
        \$\$
    )
    |
    (?:
        \$\(
        (
            (?:
                (?:
                    \\\)
                )
                |
                [^\)]
            )+
        )
        (
            \)
        )?
    )
    """.replace(
        " ", ""
    ).replace(
        "\n", ""
    )
)


def _render_string_template(
    string_template: str, source_location: SourceLocation, mapping: dict
) -> str:
    def do_query(match: re.Match[str]) -> str:
        if match.group(0) == "$$":
            return "$"

        query = match.group(1).replace(r"\)", ")")
        closing_parentheses = match.group(2)
        if closing_parentheses is None:
            raise InvalidStringTemplateError(
                source_location, string_template, "missing ')'"
            )

        gjson_obj = GJSON(mapping)
        gjson_obj.register_modifier("slice", _slice_gjson_modifier)
        try:
            value = gjson_obj.get(query)
        except GJSONParseError as e:
            raise InvalidStringTemplateError(source_location, string_template, str(e))
        return _convert_obj_to_text(value)

    return _string_template_query_pattern.sub(do_query, string_template)


def _slice_gjson_modifier(options: dict[str, Any], obj: Any, last: bool) -> Any:
    if not isinstance(obj, list):
        return None
    start = options.get("start")
    if start is None:
        start = 0
    else:
        if not isinstance(start, int) or start < 0:
            return None
    end = options.get("end")
    n = len(obj)
    if end is None:
        end = n
    else:
        if not isinstance(end, int) or end < 0:
            return None
        if end > n:
            end = n
    if start >= end:
        return []
    return obj[start:end]


def _convert_obj_to_text(obj: Any) -> str:
    if isinstance(obj, str):
        if obj == "":
            return '""'
        return obj

    elif isinstance(obj, list):
        if all(isinstance(x, str) for x in obj):
            return "／".join('""' if x == "" else x for x in obj)

    return json.dumps(obj, ensure_ascii=False)


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


class InvalidStringTemplateError(Error):
    def __init__(
        self, source_location: SourceLocation, string_template: str, description: str
    ) -> None:
        super().__init__(
            source_location,
            f"invalid transform literal {repr(string_template)}, {description}",
        )


class InvalidLabelPositionError(Error):
    def __init__(self, label: Label) -> None:
        super().__init__(
            label.source_location, f"label must be followed by a return statement"
        )
