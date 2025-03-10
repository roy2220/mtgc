import unittest
from io import StringIO

from src.scanner import EndOfFileError, Scanner, SourceLocation, Token, TokenType


class TestScanner(unittest.TestCase):
    def test_get_token(self):
        scanner = Scanner(
            StringIO(
                """\
component NormalPostbackInfo as "回传信息规整"
{
    unit MmpNameInfo as "MMP名信息"
    {
        switch get("RawPostbackInfo_ThreeType") {
        case "kochava", "min_kochava":
            return transform(`TODO Kochava`) as "Kochava MMP"
        default:
            return transform(`TODO` + " other") as "其他MMP"
        }
    }

    unit AttributeTypeInfo as "归因类型信息"
    {
        if test("NormalPostbackInfo_MmpNameInfo_Value", "eq", "Kochava") {

            if test("RawPostbackInfo_HasAttribuType", "eq", "true")
               && test("RawPostbackInfo_AttribuType", "eq", "") {

                return transform(`TODO 0`) as "非mtg归因 - kochava"
            }
        }

        if test("RawPostbackInfo_AttribuType", "eq", "0") {
                return transform(`TODO 0`) as "非mtg归因 - 其他"
        }

        return transform(`TODO 1`) as "mtg归因"
    }
}
"""
            )
        )

        tokens = []
        while True:
            try:
                t = scanner.get_token()
            except EndOfFileError:
                break
            tokens.append(t)

        self.assertEqual(
            tokens,
            [
                Token(
                    type=TokenType.COMPONENT_KEYWORD,
                    data="component",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=1
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=10
                    ),
                ),
                Token(
                    type=TokenType.IDENTIFIER,
                    data="NormalPostbackInfo",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=11
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=29
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=30
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=32
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"回传信息规整"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=33
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=1, column_number=41
                    ),
                ),
                Token(
                    type=TokenType.OPEN_BRACE,
                    data="{",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=2, column_number=1
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n    ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=2, column_number=2
                    ),
                ),
                Token(
                    type=TokenType.UNIT_KEYWORD,
                    data="unit",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=5
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.IDENTIFIER,
                    data="MmpNameInfo",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=10
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=21
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=22
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=24
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"MMP名信息"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=25
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n    ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=3, column_number=33
                    ),
                ),
                Token(
                    type=TokenType.OPEN_BRACE,
                    data="{",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=4, column_number=5
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=4, column_number=6
                    ),
                ),
                Token(
                    type=TokenType.SWITCH_KEYWORD,
                    data="switch",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=15
                    ),
                ),
                Token(
                    type=TokenType.GET_KEYWORD,
                    data="get",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=16
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=19
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"RawPostbackInfo_ThreeType"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=20
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=47
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=48
                    ),
                ),
                Token(
                    type=TokenType.OPEN_BRACE,
                    data="{",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=49
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=5, column_number=50
                    ),
                ),
                Token(
                    type=TokenType.CASE_KEYWORD,
                    data="case",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=13
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"kochava"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=14
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=23
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=24
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"min_kochava"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=25
                    ),
                ),
                Token(
                    type=TokenType.COLON,
                    data=":",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=38
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n            ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=6, column_number=39
                    ),
                ),
                Token(
                    type=TokenType.RETURN_KEYWORD,
                    data="return",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=13
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=19
                    ),
                ),
                Token(
                    type=TokenType.TRANSFORM_KEYWORD,
                    data="transform",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=20
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=29
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data="`TODO Kochava`",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=30
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=44
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=45
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=46
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=48
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"Kochava MMP"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=49
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=7, column_number=62
                    ),
                ),
                Token(
                    type=TokenType.DEFAULT_KEYWORD,
                    data="default",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=8, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.COLON,
                    data=":",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=8, column_number=16
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n            ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=8, column_number=17
                    ),
                ),
                Token(
                    type=TokenType.RETURN_KEYWORD,
                    data="return",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=13
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=19
                    ),
                ),
                Token(
                    type=TokenType.TRANSFORM_KEYWORD,
                    data="transform",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=20
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=29
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data="`TODO`",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=30
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=36
                    ),
                ),
                Token(
                    type=TokenType.PLUS,
                    data="+",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=37
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=38
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='" other"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=39
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=47
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=48
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=49
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=51
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"其他MMP"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=52
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=9, column_number=59
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_BRACE,
                    data="}",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=10, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n    ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=10, column_number=10
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_BRACE,
                    data="}",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=11, column_number=5
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n\n    ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=11, column_number=6
                    ),
                ),
                Token(
                    type=TokenType.UNIT_KEYWORD,
                    data="unit",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=5
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.IDENTIFIER,
                    data="AttributeTypeInfo",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=10
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=27
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=28
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=30
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"归因类型信息"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=31
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n    ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=13, column_number=39
                    ),
                ),
                Token(
                    type=TokenType.OPEN_BRACE,
                    data="{",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=14, column_number=5
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=14, column_number=6
                    ),
                ),
                Token(
                    type=TokenType.IF_KEYWORD,
                    data="if",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=11
                    ),
                ),
                Token(
                    type=TokenType.TEST_KEYWORD,
                    data="test",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=12
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=16
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"NormalPostbackInfo_MmpNameInfo_Value"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=17
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=55
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=56
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"eq"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=57
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=61
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=62
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"Kochava"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=63
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=72
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=73
                    ),
                ),
                Token(
                    type=TokenType.OPEN_BRACE,
                    data="{",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=74
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n\n            ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=15, column_number=75
                    ),
                ),
                Token(
                    type=TokenType.IF_KEYWORD,
                    data="if",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=13
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=15
                    ),
                ),
                Token(
                    type=TokenType.TEST_KEYWORD,
                    data="test",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=16
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=20
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"RawPostbackInfo_HasAttribuType"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=21
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=53
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=54
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"eq"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=55
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=59
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=60
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"true"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=61
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=67
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n               ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=17, column_number=68
                    ),
                ),
                Token(
                    type=TokenType.LOGICAL_AND,
                    data="&&",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=16
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=18
                    ),
                ),
                Token(
                    type=TokenType.TEST_KEYWORD,
                    data="test",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=19
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=23
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"RawPostbackInfo_AttribuType"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=24
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=53
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=54
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"eq"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=55
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=59
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=60
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='""',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=61
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=63
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=64
                    ),
                ),
                Token(
                    type=TokenType.OPEN_BRACE,
                    data="{",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=65
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n\n                ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=18, column_number=66
                    ),
                ),
                Token(
                    type=TokenType.RETURN_KEYWORD,
                    data="return",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=17
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=23
                    ),
                ),
                Token(
                    type=TokenType.TRANSFORM_KEYWORD,
                    data="transform",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=24
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=33
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data="`TODO 0`",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=34
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=42
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=43
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=44
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=46
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"非mtg归因 - kochava"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=47
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n            ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=20, column_number=65
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_BRACE,
                    data="}",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=21, column_number=13
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=21, column_number=14
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_BRACE,
                    data="}",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=22, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=22, column_number=10
                    ),
                ),
                Token(
                    type=TokenType.IF_KEYWORD,
                    data="if",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=11
                    ),
                ),
                Token(
                    type=TokenType.TEST_KEYWORD,
                    data="test",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=12
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=16
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"RawPostbackInfo_AttribuType"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=17
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=46
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=47
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"eq"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=48
                    ),
                ),
                Token(
                    type=TokenType.COMMA,
                    data=",",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=52
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=53
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"0"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=54
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=57
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=58
                    ),
                ),
                Token(
                    type=TokenType.OPEN_BRACE,
                    data="{",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=59
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n                ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=24, column_number=60
                    ),
                ),
                Token(
                    type=TokenType.RETURN_KEYWORD,
                    data="return",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=17
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=23
                    ),
                ),
                Token(
                    type=TokenType.TRANSFORM_KEYWORD,
                    data="transform",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=24
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=33
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data="`TODO 0`",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=34
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=42
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=43
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=44
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=46
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"非mtg归因 - 其他"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=47
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=25, column_number=60
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_BRACE,
                    data="}",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=26, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n\n        ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=26, column_number=10
                    ),
                ),
                Token(
                    type=TokenType.RETURN_KEYWORD,
                    data="return",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=9
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=15
                    ),
                ),
                Token(
                    type=TokenType.TRANSFORM_KEYWORD,
                    data="transform",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=16
                    ),
                ),
                Token(
                    type=TokenType.OPEN_PAREN,
                    data="(",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=25
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data="`TODO 1`",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=26
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_PAREN,
                    data=")",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=34
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=35
                    ),
                ),
                Token(
                    type=TokenType.AS_KEYWORD,
                    data="as",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=36
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data=" ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=38
                    ),
                ),
                Token(
                    type=TokenType.STRING_LITERAL,
                    data='"mtg归因"',
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=39
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n    ",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=28, column_number=46
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_BRACE,
                    data="}",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=29, column_number=5
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=29, column_number=6
                    ),
                ),
                Token(
                    type=TokenType.CLOSE_BRACE,
                    data="}",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=30, column_number=1
                    ),
                ),
                Token(
                    type=TokenType.WHITESPACE,
                    data="\n",
                    source_location=SourceLocation(
                        file_name="<unnamed>", line_number=30, column_number=2
                    ),
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
