import enum
import io
from dataclasses import dataclass

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
    statements: list["Statement"]


type Statement = "ReturnStatement | IfStatement | SwitchStatement"


@dataclass
class ReturnStatement:
    source_location: SourceLocation
    transform_literal: str
    transform_scenario: str

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_return_statement(self)


@dataclass
class IfStatement:
    source_location: SourceLocation
    condiction: "Condiction"
    then: list[Statement]
    else_if_clauses: list["ElseIfClause"]
    else_clause: list[Statement]

    # for analysis
    then_link: Statement | None = None
    else_clause_link: Statement | None = None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_if_statement(self)


@dataclass
class ElseIfClause:
    condiction: "Condiction"
    then: list[Statement]

    # for analysis
    then_link: Statement | None = None


@dataclass
class SwitchStatement:
    source_location: SourceLocation
    key: str
    case_clauses: list["CaseClause"]
    default_case_clause: list[Statement]

    # for analysis
    default_case_clause_link: Statement | None = None

    def accept_visit(self, visitor: "Visitor") -> None:
        visitor.visit_switch_statement(self)


@dataclass
class CaseClause:
    values: list[str]
    then: list[Statement]

    # for analysis
    then_link: Statement | None = None


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
    op: str
    values: list[str]

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
    __slots__ = (
        "_scanner",
        "_buffered_tokens",
    )

    def __init__(self, scanner: Scanner) -> None:
        self._scanner = scanner
        self._buffered_tokens: list[Token] = []

    def get_program(self) -> list[Statement]:
        statements = self._get_statements()
        t = self._peek_token(1)
        if t.type != TokenType.NONE:
            raise UnexpectedTokenError(t)
        return statements

    def _do_get_token(self) -> Token:
        while True:
            t = self._scanner.get_token()
            if t.type != TokenType.WHITESPACE:
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
        component_name = self._get_string()
        self._get_expected_token(TokenType.AS_KEYWORD)
        component_alias = self._get_string()
        self._get_expected_token(TokenType.OPEN_BRACE)
        unit_declarations = self._get_unit_declarations()
        return ComponentDeclaration(
            source_location, component_name, component_alias, unit_declarations
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
        unit_name = self._get_string()
        self._get_expected_token(TokenType.AS_KEYWORD)
        unit_alias = self._get_string()
        self._get_expected_token(TokenType.OPEN_BRACE)
        statements = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return UnitDeclaration(source_location, unit_name, unit_alias, statements)

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
        transform_literal = self._get_string()
        self._get_expected_token(TokenType.AS_KEYWORD)
        transform_scenario = self._get_string()
        return ReturnStatement(source_location, transform_literal, transform_scenario)

    def _get_switch_statement(self) -> SwitchStatement:
        source_location = self._get_expected_token(
            TokenType.SWITCH_KEYWORD
        ).source_location
        self._get_expected_token(TokenType.GET_KEYWORD)
        self._get_expected_token(TokenType.OPEN_PAREN)
        key = self._get_string()
        self._get_expected_token(TokenType.CLOSE_PAREN)
        self._get_expected_token(TokenType.OPEN_BRACE)

        case_clause = self._get_case_clause()
        case_clauses: list[CaseClause] = [case_clause]
        while self._peek_token(1).type == TokenType.CASE_KEYWORD:
            case_clause = self._get_case_clause()
            case_clauses.append(case_clause)

        default_case_clause: list[Statement] = []
        if self._peek_token(1).type == TokenType.DEFAULT_KEYWORD:
            self._discard_tokens(1)
            self._get_expected_token(TokenType.COLON)
            default_case_clause = self._get_statements()

        self._get_expected_token(TokenType.CLOSE_BRACE)

        return SwitchStatement(source_location, key, case_clauses, default_case_clause)

    def _get_case_clause(self) -> CaseClause:
        self._get_expected_token(TokenType.CASE_KEYWORD)

        values: list[str] = []

        while True:
            values.append(self._get_string())

            if self._peek_token(1).type != TokenType.COMMA:
                break

            self._discard_tokens(1)

        self._get_expected_token(TokenType.COLON)

        then = self._get_statements()
        return CaseClause(values, then)

    def _get_if_statement(self) -> IfStatement:
        source_location = self._get_expected_token(TokenType.IF_KEYWORD).source_location
        condiction = self._get_condiction(0)
        self._get_expected_token(TokenType.OPEN_BRACE)
        then = self._get_statements()
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

        else_clause: list[Statement] = []
        if self._peek_token(1).type == TokenType.ELSE_KEYWORD:
            self._discard_tokens(1)
            self._get_expected_token(TokenType.OPEN_BRACE)
            else_clause = self._get_statements()
            self._get_expected_token(TokenType.CLOSE_BRACE)

        return IfStatement(
            source_location, condiction, then, else_if_clauses, else_clause
        )

    def _get_else_if_clause(self) -> ElseIfClause:
        self._get_expected_token(TokenType.ELSE_KEYWORD)
        self._get_expected_token(TokenType.IF_KEYWORD)
        condiction = self._get_condiction(0)
        self._get_expected_token(TokenType.OPEN_BRACE)
        then = self._get_statements()
        self._get_expected_token(TokenType.CLOSE_BRACE)
        return ElseIfClause(condiction, then)

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
        key = self._get_string()
        self._get_expected_token(TokenType.COMMA)
        op = self._get_string()
        values: list[str] = []

        while True:
            t = self._peek_token(1)
            if t.type != TokenType.COMMA:
                break

            self._discard_tokens(1)
            values.append(self._get_string())

        self._get_expected_token(TokenType.CLOSE_PAREN)
        return TestCondiction(source_location, key, op, values)

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


_dummy_token = Token(TokenType.NONE, "", SourceLocation("", 0, 0))


_token_type_2_binary_op_type: dict[TokenType, OpType] = {
    TokenType.LOGICAL_OR: OpType.LOGICAL_OR,
    TokenType.LOGICAL_AND: OpType.LOGICAL_AND,
}

_binary_op_type_2_precedence: dict[OpType, int] = {
    OpType.LOGICAL_OR: 1,
    OpType.LOGICAL_AND: 2,
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
                    raise InvalidStringLiteral(t)

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


class InvalidStringLiteral(Error):
    def __init__(self, token: Token) -> None:
        super().__init__(
            token.source_location, f"invalid string literal {repr(token.data)}"
        )
