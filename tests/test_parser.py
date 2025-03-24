import tempfile
import unittest
from io import StringIO

from src.parser import (
    CaseClause,
    ComponentDeclaration,
    CompositeCondiction,
    ConstantCondiction,
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
                    f"""
import "{fp.name}"
"""
                    + """\
component DemoInfo as "just demo"
{
    unit Test1 as "Test1"
    {
        switch get("Var_MyKey") {
            case "abc", "efg":
                return transform(`[]`) as "Value1"
            case "xyz":
                return transform(`[]`) as "Value2"
            default:
                return transform(`[]`) as "Value3"
        }
        return transform(`[]`) as "Value4"
    }

    unit Test2 as "Test2"
    {
        if test("Var_1", "eq", "100") ||
           !(test("Var_2", "eq", "200") && test("Var_3", "eq", "300")) {

            return transform(`[]`) as "Value1"
        } else if (test("Var_4", "eq", "400") || test("Var_5", "eq", "500")) && !test("Var_6", "eq", "600") {
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

        self.assertEqual(
            cd,
            ComponentDeclaration(
                source_location=SourceLocation(
                    file_name="<unnamed>",
                    file_offset=27,
                    line_number=3,
                    column_number=1,
                ),
                name="DemoInfo",
                alias="just demo",
                units=[
                    UnitDeclaration(
                        source_location=SourceLocation(
                            file_name="<unnamed>",
                            file_offset=67,
                            line_number=5,
                            column_number=5,
                        ),
                        name="Test1",
                        alias="Test1",
                        program=[
                            SwitchStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    file_offset=103,
                                    line_number=7,
                                    column_number=9,
                                ),
                                key="Var_MyKey",
                                key_index=1200000,
                                case_clauses=[
                                    CaseClause(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=141,
                                            line_number=8,
                                            column_number=13,
                                        ),
                                        values=["abc", "efg"],
                                        then=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=176,
                                                    line_number=9,
                                                    column_number=17,
                                                ),
                                                transform=[],
                                                transform_scenario="Value1",
                                            )
                                        ],
                                        then_link=None,
                                    ),
                                    CaseClause(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=223,
                                            line_number=10,
                                            column_number=13,
                                        ),
                                        values=["xyz"],
                                        then=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=251,
                                                    line_number=11,
                                                    column_number=17,
                                                ),
                                                transform=[],
                                                transform_scenario="Value2",
                                            )
                                        ],
                                        then_link=None,
                                    ),
                                ],
                                default_case_clause=[
                                    ReturnStatement(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=323,
                                            line_number=13,
                                            column_number=17,
                                        ),
                                        transform=[],
                                        transform_scenario="Value3",
                                    )
                                ],
                                default_case_clause_link=None,
                            ),
                            ReturnStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    file_offset=376,
                                    line_number=15,
                                    column_number=9,
                                ),
                                transform=[],
                                transform_scenario="Value4",
                            ),
                        ],
                    ),
                    UnitDeclaration(
                        source_location=SourceLocation(
                            file_name="<unnamed>",
                            file_offset=422,
                            line_number=18,
                            column_number=5,
                        ),
                        name="Test2",
                        alias="Test2",
                        program=[
                            IfStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    file_offset=458,
                                    line_number=20,
                                    column_number=9,
                                ),
                                condiction=CompositeCondiction(
                                    source_location=SourceLocation(
                                        file_name="<unnamed>",
                                        file_offset=481,
                                        line_number=20,
                                        column_number=32,
                                    ),
                                    logical_op_type=OpType.LOGICAL_OR,
                                    condiction1=TestCondiction(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=481,
                                            line_number=20,
                                            column_number=32,
                                        ),
                                        key="Var_1",
                                        key_index=1200001,
                                        op="eq",
                                        values=["100"],
                                        underlying_values=["100"],
                                    ),
                                    condiction2=CompositeCondiction(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=502,
                                            line_number=21,
                                            column_number=12,
                                        ),
                                        logical_op_type=OpType.LOGICAL_NOT,
                                        condiction1=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=524,
                                                line_number=21,
                                                column_number=34,
                                            ),
                                            logical_op_type=OpType.LOGICAL_AND,
                                            condiction1=TestCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=524,
                                                    line_number=21,
                                                    column_number=34,
                                                ),
                                                key="Var_2",
                                                key_index=1200002,
                                                op="eq",
                                                values=["200"],
                                                underlying_values=["200"],
                                            ),
                                            condiction2=TestCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=554,
                                                    line_number=21,
                                                    column_number=64,
                                                ),
                                                key="Var_3",
                                                key_index=1200003,
                                                op="eq",
                                                values=["300"],
                                                underlying_values=["300"],
                                            ),
                                        ),
                                        condiction2=None,
                                    ),
                                ),
                                then=[
                                    ReturnStatement(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=577,
                                            line_number=23,
                                            column_number=13,
                                        ),
                                        transform=[],
                                        transform_scenario="Value1",
                                    )
                                ],
                                else_if_clauses=[
                                    ElseIfClause(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=622,
                                            line_number=24,
                                            column_number=11,
                                        ),
                                        condiction=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=651,
                                                line_number=24,
                                                column_number=40,
                                            ),
                                            logical_op_type=OpType.LOGICAL_AND,
                                            condiction1=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=651,
                                                    line_number=24,
                                                    column_number=40,
                                                ),
                                                logical_op_type=OpType.LOGICAL_OR,
                                                condiction1=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=651,
                                                        line_number=24,
                                                        column_number=40,
                                                    ),
                                                    key="Var_4",
                                                    key_index=1200004,
                                                    op="eq",
                                                    values=["400"],
                                                    underlying_values=["400"],
                                                ),
                                                condiction2=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=681,
                                                        line_number=24,
                                                        column_number=70,
                                                    ),
                                                    key="Var_5",
                                                    key_index=1200005,
                                                    op="eq",
                                                    values=["500"],
                                                    underlying_values=["500"],
                                                ),
                                            ),
                                            condiction2=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=692,
                                                    line_number=24,
                                                    column_number=81,
                                                ),
                                                logical_op_type=OpType.LOGICAL_NOT,
                                                condiction1=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=713,
                                                        line_number=24,
                                                        column_number=102,
                                                    ),
                                                    key="Var_6",
                                                    key_index=1200005,
                                                    op="eq",
                                                    values=["600"],
                                                    underlying_values=["600"],
                                                ),
                                                condiction2=None,
                                            ),
                                        ),
                                        then=[
                                            IfStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=734,
                                                    line_number=25,
                                                    column_number=13,
                                                ),
                                                condiction=ConstantCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=737,
                                                        line_number=25,
                                                        column_number=16,
                                                    ),
                                                    constant=False,
                                                ),
                                                then=[
                                                    ReturnStatement(
                                                        source_location=SourceLocation(
                                                            file_name="<unnamed>",
                                                            file_offset=757,
                                                            line_number=26,
                                                            column_number=13,
                                                        ),
                                                        transform=[],
                                                        transform_scenario="Value2",
                                                    )
                                                ],
                                                else_if_clauses=[],
                                                else_clause=[],
                                                then_link=None,
                                                else_clause_link=None,
                                            )
                                        ],
                                        then_link=None,
                                    )
                                ],
                                else_clause=[
                                    IfStatement(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=835,
                                            line_number=29,
                                            column_number=13,
                                        ),
                                        condiction=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                file_offset=838,
                                                line_number=29,
                                                column_number=16,
                                            ),
                                            logical_op_type=OpType.LOGICAL_OR,
                                            condiction1=ConstantCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=838,
                                                    line_number=29,
                                                    column_number=16,
                                                ),
                                                constant=True,
                                            ),
                                            condiction2=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=846,
                                                    line_number=29,
                                                    column_number=24,
                                                ),
                                                logical_op_type=OpType.LOGICAL_NOT,
                                                condiction1=ConstantCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        file_offset=847,
                                                        line_number=29,
                                                        column_number=25,
                                                    ),
                                                    constant=False,
                                                ),
                                                condiction2=None,
                                            ),
                                        ),
                                        then=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    file_offset=871,
                                                    line_number=30,
                                                    column_number=17,
                                                ),
                                                transform=[],
                                                transform_scenario="Value3",
                                            )
                                        ],
                                        else_if_clauses=[],
                                        else_clause=[],
                                        then_link=None,
                                        else_clause_link=None,
                                    ),
                                    ReturnStatement(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            file_offset=932,
                                            line_number=32,
                                            column_number=13,
                                        ),
                                        transform=[],
                                        transform_scenario="Value2",
                                    ),
                                ],
                                then_link=None,
                                else_clause_link=None,
                            )
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    unittest.main()
