import tempfile
import unittest
from io import StringIO

from src.parser import (
    CaseClause,
    ComponentDeclaration,
    CompositeCondiction,
    ConstantCondiction,
    DefaultCaseClause,
    ElseClause,
    ElseIfClause,
    IfStatement,
    OpType,
    Parser,
    ReturnStatement,
    SwitchStatement,
    TestCondiction,
    UnitDeclaration,
)
from src.scanner import Scanner, SourceLocation


class TestParser(unittest.TestCase):
    def test_get_composite_statement(self):
        with tempfile.NamedTemporaryFile(delete_on_close=True) as fp:
            fp.write(
                """\
[
  { "Idx": 1200000, "Key": "Var_MyKey" },
  { "Idx": 1200001, "Key": "Var_1" },
  { "Idx": 1200002, "Key": "Var_2" },
  { "Idx": 1200003, "Key": "Var_3" },
  { "Idx": 1200004, "Key": "Var_4" },
  { "Idx": 1200005, "Key": "Var_5" },
  { "Idx": 1200005, "Key": "Var_6" }
]
""".encode()
            )
            fp.flush()

            scanner = Scanner(
                StringIO(
                    f'import "{fp.name}"\n'
                    + """\
component DemoInfo as "just demo"
{
    unit Test1 as "Test1"
    {
        switch get("Var_MyKey") {
            case "abc" as "tag1", "efg" as "tag2":
                return transform(`[]`) as "Value1"
            case "xyz" as "tag3":
                return transform(`[]`) as "Value2"
            default:
                return transform(`[]`) as "Value3"
        }
        return transform(`[]`) as "Value4"
    }

    unit Test2 as "Test2"
    {
        if test("Var_1", "eq", "100") as "tag4" ||
           !(test("Var_2", "eq", "200") as "tag9" && test("Var_3", "eq", "300") as "tag5") {

            return transform(`[]`) as "Value1"
        } else if (test("Var_4", "eq", "400") as "tag6" || test("Var_5", "eq", "500") as "tag7") && !test("Var_6", "eq", "600") as "tag8" {
            if false {
            return transform(`[]`) as "Value2"
            }
        } else {
            if true || !false {
                return transform(`[]`) as "Value3"
            }
            return transform(`[]`) as "Value2"
        }
    }
}
"""
                )
            )

            parser = Parser(scanner)
            cd = parser.get_component_declaration()

        print(cd)
        self.assertEqual(
            cd,
            ComponentDeclaration(
                source_location=SourceLocation(
                    file_name="<unnamed>",
                    file_offset=26,
                    line_number=2,
                    column_number=1,
                ),
                name="DemoInfo",
                alias="just demo",
                units=[
                    UnitDeclaration(
                        source_location=SourceLocation(
                            file_name="<unnamed>",
                            file_offset=66,
                            line_number=4,
                            column_number=5,
                        ),
                        name="Test1",
                        alias="Test1",
                        program=[
                            SwitchStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    file_offset=102,
                                    line_number=6,
                                    column_number=9,
                                ),
                                key="Var_MyKey",
                                key_index=1200000,
                                case_clauses=[
                                    CaseClause(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=140,
                                            line_number=7,
                                            column_number=13,
                                        ),
                                        values_and_facts=[
                                            ("abc", "tag1"),
                                            ("efg", "tag2"),
                                        ],
                                        body=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=195,
                                                    line_number=8,
                                                    column_number=17,
                                                ),
                                                transform=[],
                                                transform_annotation="Value1",
                                            )
                                        ],
                                        body_link=None,
                                    ),
                                    CaseClause(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=242,
                                            line_number=9,
                                            column_number=13,
                                        ),
                                        values_and_facts=[("xyz", "tag3")],
                                        body=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=280,
                                                    line_number=10,
                                                    column_number=17,
                                                ),
                                                transform=[],
                                                transform_annotation="Value2",
                                            )
                                        ],
                                        body_link=None,
                                    ),
                                ],
                                default_case_clause=DefaultCaseClause(
                                    source_location=SourceLocation(
                                        file_name="<unnamed>",
                                        file_offset=327,
                                        line_number=11,
                                        column_number=13,
                                    ),
                                    body=[
                                        ReturnStatement(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=352,
                                                line_number=12,
                                                column_number=17,
                                            ),
                                            transform=[],
                                            transform_annotation="Value3",
                                        )
                                    ],
                                    body_link=None,
                                ),
                            ),
                            ReturnStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    file_offset=405,
                                    line_number=14,
                                    column_number=9,
                                ),
                                transform=[],
                                transform_annotation="Value4",
                            ),
                        ],
                    ),
                    UnitDeclaration(
                        source_location=SourceLocation(
                            file_name="<unnamed>",
                            file_offset=451,
                            line_number=17,
                            column_number=5,
                        ),
                        name="Test2",
                        alias="Test2",
                        program=[
                            IfStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    file_offset=487,
                                    line_number=19,
                                    column_number=9,
                                ),
                                condiction=CompositeCondiction(
                                    source_location=SourceLocation(
                                        file_name="<unnamed>",
                                        file_offset=510,
                                        line_number=19,
                                        column_number=32,
                                    ),
                                    logical_op_type=OpType.LOGICAL_OR,
                                    condiction1=TestCondiction(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=510,
                                            line_number=19,
                                            column_number=32,
                                        ),
                                        key="Var_1",
                                        key_index=1200001,
                                        op="eq",
                                        values=["100"],
                                        underlying_values=["100"],
                                        fact="tag4",
                                    ),
                                    condiction2=CompositeCondiction(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=541,
                                            line_number=20,
                                            column_number=12,
                                        ),
                                        logical_op_type=OpType.LOGICAL_NOT,
                                        condiction1=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=563,
                                                line_number=20,
                                                column_number=34,
                                            ),
                                            logical_op_type=OpType.LOGICAL_AND,
                                            condiction1=TestCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=563,
                                                    line_number=20,
                                                    column_number=34,
                                                ),
                                                key="Var_2",
                                                key_index=1200002,
                                                op="eq",
                                                values=["200"],
                                                underlying_values=["200"],
                                                fact="tag9",
                                            ),
                                            condiction2=TestCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=603,
                                                    line_number=20,
                                                    column_number=74,
                                                ),
                                                key="Var_3",
                                                key_index=1200003,
                                                op="eq",
                                                values=["300"],
                                                underlying_values=["300"],
                                                fact="tag5",
                                            ),
                                        ),
                                        condiction2=None,
                                    ),
                                ),
                                body=[
                                    ReturnStatement(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=636,
                                            line_number=22,
                                            column_number=13,
                                        ),
                                        transform=[],
                                        transform_annotation="Value1",
                                    )
                                ],
                                else_if_clauses=[
                                    ElseIfClause(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=681,
                                            line_number=23,
                                            column_number=11,
                                        ),
                                        condiction=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=710,
                                                line_number=23,
                                                column_number=40,
                                            ),
                                            logical_op_type=OpType.LOGICAL_AND,
                                            condiction1=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=710,
                                                    line_number=23,
                                                    column_number=40,
                                                ),
                                                logical_op_type=OpType.LOGICAL_OR,
                                                condiction1=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=710,
                                                        line_number=23,
                                                        column_number=40,
                                                    ),
                                                    key="Var_4",
                                                    key_index=1200004,
                                                    op="eq",
                                                    values=["400"],
                                                    underlying_values=["400"],
                                                    fact="tag6",
                                                ),
                                                condiction2=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=750,
                                                        line_number=23,
                                                        column_number=80,
                                                    ),
                                                    key="Var_5",
                                                    key_index=1200005,
                                                    op="eq",
                                                    values=["500"],
                                                    underlying_values=["500"],
                                                    fact="tag7",
                                                ),
                                            ),
                                            condiction2=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=771,
                                                    line_number=23,
                                                    column_number=101,
                                                ),
                                                logical_op_type=OpType.LOGICAL_NOT,
                                                condiction1=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=792,
                                                        line_number=23,
                                                        column_number=122,
                                                    ),
                                                    key="Var_6",
                                                    key_index=1200005,
                                                    op="eq",
                                                    values=["600"],
                                                    underlying_values=["600"],
                                                    fact="tag8",
                                                ),
                                                condiction2=None,
                                            ),
                                        ),
                                        body=[
                                            IfStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=823,
                                                    line_number=24,
                                                    column_number=13,
                                                ),
                                                condiction=ConstantCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=826,
                                                        line_number=24,
                                                        column_number=16,
                                                    ),
                                                    constant=False,
                                                ),
                                                body=[
                                                    ReturnStatement(
                                                        source_location=SourceLocation(
                                                            file_name="<unnamed>",
                                                            file_offset=846,
                                                            line_number=25,
                                                            column_number=13,
                                                        ),
                                                        transform=[],
                                                        transform_annotation="Value2",
                                                    )
                                                ],
                                                else_if_clauses=[],
                                                else_clause=ElseClause(
                                                    source_location=None,
                                                    body=[],
                                                    body_link=None,
                                                ),
                                                body_link=None,
                                            )
                                        ],
                                        body_link=None,
                                    )
                                ],
                                else_clause=ElseClause(
                                    source_location=SourceLocation(
                                        file_name="<unnamed>",
                                        file_offset=905,
                                        line_number=27,
                                        column_number=11,
                                    ),
                                    body=[
                                        IfStatement(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=924,
                                                line_number=28,
                                                column_number=13,
                                            ),
                                            condiction=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=927,
                                                    line_number=28,
                                                    column_number=16,
                                                ),
                                                logical_op_type=OpType.LOGICAL_OR,
                                                condiction1=ConstantCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=927,
                                                        line_number=28,
                                                        column_number=16,
                                                    ),
                                                    constant=True,
                                                ),
                                                condiction2=CompositeCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=935,
                                                        line_number=28,
                                                        column_number=24,
                                                    ),
                                                    logical_op_type=OpType.LOGICAL_NOT,
                                                    condiction1=ConstantCondiction(
                                                        source_location=SourceLocation(
                                                            file_name="<unnamed>",
                                                            file_offset=936,
                                                            line_number=28,
                                                            column_number=25,
                                                        ),
                                                        constant=False,
                                                    ),
                                                    condiction2=None,
                                                ),
                                            ),
                                            body=[
                                                ReturnStatement(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=960,
                                                        line_number=29,
                                                        column_number=17,
                                                    ),
                                                    transform=[],
                                                    transform_annotation="Value3",
                                                )
                                            ],
                                            else_if_clauses=[],
                                            else_clause=ElseClause(
                                                source_location=None,
                                                body=[],
                                                body_link=None,
                                            ),
                                            body_link=None,
                                        ),
                                        ReturnStatement(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=1021,
                                                line_number=31,
                                                column_number=13,
                                            ),
                                            transform=[],
                                            transform_annotation="Value2",
                                        ),
                                    ],
                                    body_link=None,
                                ),
                                body_link=None,
                            )
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    unittest.main()
