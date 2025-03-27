import enum
import io
import string
from dataclasses import dataclass


@dataclass
class Token:
    type: "TokenType"
    data: str
    source_location: "SourceLocation"


class TokenType(enum.IntEnum):
    NONE = 0

    WHITESPACE = enum.auto()
    COMMENT = enum.auto()  # //...
    OPEN_PAREN = enum.auto()  # (
    CLOSE_PAREN = enum.auto()  # )
    OPEN_BRACE = enum.auto()  # {
    CLOSE_BRACE = enum.auto()  # }
    PLUS = enum.auto()  # +
    COMMA = enum.auto()  # ,
    COLON = enum.auto()  # :
    LOGICAL_NOT = enum.auto()  # !
    LOGICAL_AND = enum.auto()  # &&
    LOGICAL_OR = enum.auto()  # ||
    STRING_LITERAL = enum.auto()  # "..." or `...`

    IMPORT_KEYWORD = enum.auto()  # import
    COMPONENT_KEYWORD = enum.auto()  # component
    UNIT_KEYWORD = enum.auto()  # unit
    RETURN_KEYWORD = enum.auto()  # return
    TRANSFORM_KEYWORD = enum.auto()  # transform
    AS_KEYWORD = enum.auto()  # as
    SWITCH_KEYWORD = enum.auto()  # switch
    GET_KEYWORD = enum.auto()  # get
    CASE_KEYWORD = enum.auto()  # case
    DEFAULT_KEYWORD = enum.auto()  # default
    IF_KEYWORD = enum.auto()  # if
    ELSE_KEYWORD = enum.auto()  # else
    TRUE_KEYWORD = enum.auto()  # true
    FALSE_KEYWORD = enum.auto()  # false
    TEST_KEYWORD = enum.auto()  # test

    IDENTIFIER = enum.auto()

    def __str__(self) -> str:
        return _token_type_2_str[self]


_token_type_2_str: dict[TokenType, str] = {
    TokenType.NONE: "<none>",
    # ----------
    TokenType.WHITESPACE: "<whitespace>",
    TokenType.COMMENT: "<comment>",
    TokenType.OPEN_PAREN: "`(`",
    TokenType.CLOSE_PAREN: "`)`",
    TokenType.OPEN_BRACE: "`{`",
    TokenType.CLOSE_BRACE: "`}`",
    TokenType.PLUS: "`+`",
    TokenType.COMMA: "`,`",
    TokenType.COLON: "`:`",
    TokenType.LOGICAL_NOT: "`!`",
    TokenType.LOGICAL_AND: "`&&`",
    TokenType.LOGICAL_OR: "`||`",
    TokenType.STRING_LITERAL: "<string>",
    # ----------
    TokenType.IMPORT_KEYWORD: "`import`",
    TokenType.COMPONENT_KEYWORD: "`component`",
    TokenType.UNIT_KEYWORD: "`unit`",
    TokenType.RETURN_KEYWORD: "`return`",
    TokenType.TRANSFORM_KEYWORD: "`transform`",
    TokenType.AS_KEYWORD: "`as`",
    TokenType.SWITCH_KEYWORD: '"switch"',
    TokenType.GET_KEYWORD: "`get`",
    TokenType.CASE_KEYWORD: "`case`",
    TokenType.DEFAULT_KEYWORD: "`default`",
    TokenType.IF_KEYWORD: "`if`",
    TokenType.ELSE_KEYWORD: "`else`",
    TokenType.TRUE_KEYWORD: "`true`",
    TokenType.FALSE_KEYWORD: "`false`",
    TokenType.TEST_KEYWORD: "`test`",
    # ----------
    TokenType.IDENTIFIER: "<identifier>",
}
assert len(_token_type_2_str) == TokenType.IDENTIFIER - TokenType.NONE + 1


@dataclass
class SourceLocation:
    file_name: str
    file_offset: int
    line_number: int
    column_number: int


class Scanner:
    __slots__ = (
        "_stream",
        "_file_name",
        "_file_offset",
        "_line_number",
        "_column_number",
        "_buffered_chars",
    )

    def __init__(self, stream: io.TextIOBase) -> None:
        self._stream = stream
        self._file_name = getattr(stream, "name", "<unnamed>")
        self._file_offset = 0
        self._line_number = 1
        self._column_number = 1
        self._buffered_chars: list[str] = []

    def get_token(self) -> Token:
        source_location = self._source_location

        c = self._get_char()
        match c:
            case "(":
                return Token(TokenType.OPEN_PAREN, c, source_location)

            case ")":
                return Token(TokenType.CLOSE_PAREN, c, source_location)

            case "{":
                return Token(TokenType.OPEN_BRACE, c, source_location)

            case "}":
                return Token(TokenType.CLOSE_BRACE, c, source_location)

            case "+":
                return Token(TokenType.PLUS, c, source_location)

            case ",":
                return Token(TokenType.COMMA, c, source_location)

            case ":":
                return Token(TokenType.COLON, c, source_location)

            case "!":
                return Token(TokenType.LOGICAL_NOT, c, source_location)

            case '"':
                return Token(
                    TokenType.STRING_LITERAL,
                    self._get_single_line_string_literal([c]),
                    source_location,
                )

            case "`":
                return Token(
                    TokenType.STRING_LITERAL,
                    self._get_multi_line_string_literal([c]),
                    source_location,
                )

            case _:
                if c in string.whitespace:
                    return Token(
                        TokenType.WHITESPACE,
                        self._get_whitespace([c]),
                        source_location,
                    )

                elif c == "&":
                    c2 = self._peek_char(1)
                    if c2 == "&":
                        self._discard_chars(1)
                        return Token(TokenType.LOGICAL_AND, "&&", source_location)

                elif c == "|":
                    c2 = self._peek_char(1)
                    if c2 == "|":
                        self._discard_chars(1)
                        return Token(TokenType.LOGICAL_OR, "||", source_location)

                elif c == "/":
                    c2 = self._peek_char(1)
                    if c2 == "/":
                        return Token(
                            TokenType.COMMENT,
                            self._get_comment([c, c2]),
                            source_location,
                        )

                elif c in _first_identifier_letters:
                    token_data, token_type = self._get_identifier_or_keyword([c])
                    if token_type is not TokenType.NONE:
                        return Token(
                            token_type,
                            token_data,
                            source_location,
                        )

        raise UnexpectedCharError(source_location, c)

    @property
    def _source_location(self) -> SourceLocation:
        return SourceLocation(
            file_name=self._file_name,
            file_offset=self._file_offset,
            line_number=self._line_number,
            column_number=self._column_number,
        )

    def _do_get_char(self) -> str:
        c = self._stream.read(1)
        if c == "":
            raise EndOfFileError(self._source_location)
        return c

    def _peek_char(self, pos: int) -> str:
        assert pos >= 1

        while True:
            if len(self._buffered_chars) >= pos:
                return self._buffered_chars[pos - 1]

            try:
                c = self._do_get_char()
            except EndOfFileError:
                return _dummy_char

            self._buffered_chars.append(c)

    def _get_char(self) -> str:
        if len(self._buffered_chars) >= 1:
            c = self._buffered_chars.pop(0)
        else:
            c = self._do_get_char()

        self._file_offset += 1

        if c == "\n":
            self._line_number += 1
            self._column_number = 1
        else:
            self._column_number += 1
        return c

    def _discard_chars(self, number_of_chars: int) -> None:
        assert number_of_chars >= 1

        for _ in range(number_of_chars):
            self._get_char()

    def _get_single_line_string_literal(self, chars: list[str]) -> str:
        c1 = _dummy_char

        while True:
            c2 = self._get_char()
            if c2 == "\n":
                raise UnexpectedCharError(self._source_location, c2, '"')

            chars.append(c2)
            if c1 != "\\" and c2 == '"':
                return "".join(chars)

            c1 = c2

    def _get_multi_line_string_literal(self, chars: list[str]) -> str:
        while True:
            c = self._get_char()
            chars.append(c)
            if c == "`":
                return "".join(chars)

    def _get_whitespace(self, chars: list[str]) -> str:
        while True:
            c = self._peek_char(1)
            if c not in string.whitespace:
                return "".join(chars)

            self._discard_chars(1)
            chars.append(c)

    def _get_identifier_or_keyword(self, chars: list[str]) -> tuple[str, TokenType]:
        while True:
            c = self._peek_char(1)
            if c not in _following_identifier_letters:
                token_data = "".join(chars)
                token_type = _keyword_2_token_type.get(token_data, TokenType.IDENTIFIER)
                return token_data, token_type

            self._discard_chars(1)
            chars.append(c)

    def _get_comment(self, chars: list[str]) -> str:
        while True:
            c = self._get_char()
            chars.append(c)
            if c == "\n":
                return "".join(chars)


_dummy_char = chr(0)

_first_identifier_letters = set(
    [chr(b) for b in range(ord("a"), ord("z") + 1)]
    + [chr(b) for b in range(ord("A"), ord("Z") + 1)]
    + ["_"]
)

_following_identifier_letters = set(
    [chr(b) for b in range(ord("a"), ord("z") + 1)]
    + [chr(b) for b in range(ord("A"), ord("Z") + 1)]
    + [chr(b) for b in range(ord("0"), ord("9") + 1)]
    + ["_"]
)

_keyword_2_token_type = {
    "import": TokenType.IMPORT_KEYWORD,
    "component": TokenType.COMPONENT_KEYWORD,
    "unit": TokenType.UNIT_KEYWORD,
    "return": TokenType.RETURN_KEYWORD,
    "transform": TokenType.TRANSFORM_KEYWORD,
    "as": TokenType.AS_KEYWORD,
    "switch": TokenType.SWITCH_KEYWORD,
    "get": TokenType.GET_KEYWORD,
    "case": TokenType.CASE_KEYWORD,
    "default": TokenType.DEFAULT_KEYWORD,
    "if": TokenType.IF_KEYWORD,
    "else": TokenType.ELSE_KEYWORD,
    "true": TokenType.TRUE_KEYWORD,
    "false": TokenType.FALSE_KEYWORD,
    "test": TokenType.TEST_KEYWORD,
}


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        super().__init__(
            f"{source_location.file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )


class EndOfFileError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "end of file")


class UnexpectedCharError(Error):
    def __init__(
        self,
        source_location: SourceLocation,
        char: str,
        expected_char: str | None = None,
    ) -> None:
        description = f"unexpected char {repr(char)}"
        if expected_char is not None:
            description += f", expected {repr(expected_char)}"
        super().__init__(source_location, description)
