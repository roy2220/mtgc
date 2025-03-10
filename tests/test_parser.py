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
        scanner = Scanner(
            StringIO(
                """\
component DemoInfo as "just demo"
{
    unit Test1 as "Test1"
    {
        switch get("Var_MyKey") {
            case "abc", "efg":
                return transform(`{"value": 1}`) as "Value1"
            case "xyz":
                return transform(`{"value": 2}`) as "Value2"
            default:
                return transform(`{"value": 3}`) as "Value3"
        }
        return transform(`{"value": 4}`) as "Value4"
    }

    unit Test2 as "Test2"
    {
        if test("Var_1", "eq", "100") ||
           !(test("Var_2", "eq", "200") && test("Var_3", "eq", "300")) {

            return transform(`{"value": 11}`) as "Value1"
        } else if (test("Var_4", "eq", "400") || test("Var_5", "eq", "500")) && !test("Var_6", "eq", "600") {
            if false {
            return transform(`{"value": 22}`) as "Value2"
            }
        } else {
            if true || !false {
                return transform(`{"value": 33}`) as "Value3"
            }
            return transform(`{}`) as "Value2"
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
                    file_name="<unnamed>", line_number=1, column_number=1
                ),
                name="DemoInfo",
                alias="just demo",
                units=[
                    UnitDeclaration(
                        source_location=SourceLocation(
                            file_name="<unnamed>", line_number=3, column_number=5
                        ),
                        name="Test1",
                        alias="Test1",
                        program=[
                            SwitchStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    line_number=5,
                                    column_number=9,
                                ),
                                key="Var_MyKey",
                                case_clauses=[
                                    CaseClause(
                                        values=["abc", "efg"],
                                        then=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=7,
                                                    column_number=17,
                                                ),
                                                transform_literal='{"value": 1}',
                                                transform_scenario="Value1",
                                            )
                                        ],
                                        then_link=None,
                                    ),
                                    CaseClause(
                                        values=["xyz"],
                                        then=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=9,
                                                    column_number=17,
                                                ),
                                                transform_literal='{"value": 2}',
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
                                            line_number=11,
                                            column_number=17,
                                        ),
                                        transform_literal='{"value": 3}',
                                        transform_scenario="Value3",
                                    )
                                ],
                                default_case_clause_link=None,
                            ),
                            ReturnStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    line_number=13,
                                    column_number=9,
                                ),
                                transform_literal='{"value": 4}',
                                transform_scenario="Value4",
                            ),
                        ],
                    ),
                    UnitDeclaration(
                        source_location=SourceLocation(
                            file_name="<unnamed>", line_number=16, column_number=5
                        ),
                        name="Test2",
                        alias="Test2",
                        program=[
                            IfStatement(
                                source_location=SourceLocation(
                                    file_name="<unnamed>",
                                    line_number=18,
                                    column_number=9,
                                ),
                                condiction=CompositeCondiction(
                                    source_location=SourceLocation(
                                        file_name="<unnamed>",
                                        line_number=18,
                                        column_number=12,
                                    ),
                                    logical_op_type=OpType.LOGICAL_OR,
                                    condiction1=TestCondiction(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            line_number=18,
                                            column_number=12,
                                        ),
                                        key="Var_1",
                                        op="eq",
                                        values=["100"],
                                    ),
                                    condiction2=CompositeCondiction(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            line_number=19,
                                            column_number=12,
                                        ),
                                        logical_op_type=OpType.LOGICAL_NOT,
                                        condiction1=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                line_number=19,
                                                column_number=14,
                                            ),
                                            logical_op_type=OpType.LOGICAL_AND,
                                            condiction1=TestCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=19,
                                                    column_number=14,
                                                ),
                                                key="Var_2",
                                                op="eq",
                                                values=["200"],
                                            ),
                                            condiction2=TestCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=19,
                                                    column_number=44,
                                                ),
                                                key="Var_3",
                                                op="eq",
                                                values=["300"],
                                            ),
                                        ),
                                        condiction2=None,
                                    ),
                                ),
                                then=[
                                    ReturnStatement(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            line_number=21,
                                            column_number=13,
                                        ),
                                        transform_literal='{"value": 11}',
                                        transform_scenario="Value1",
                                    )
                                ],
                                else_if_clauses=[
                                    ElseIfClause(
                                        condiction=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                line_number=22,
                                                column_number=20,
                                            ),
                                            logical_op_type=OpType.LOGICAL_AND,
                                            condiction1=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=22,
                                                    column_number=20,
                                                ),
                                                logical_op_type=OpType.LOGICAL_OR,
                                                condiction1=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        line_number=22,
                                                        column_number=20,
                                                    ),
                                                    key="Var_4",
                                                    op="eq",
                                                    values=["400"],
                                                ),
                                                condiction2=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        line_number=22,
                                                        column_number=50,
                                                    ),
                                                    key="Var_5",
                                                    op="eq",
                                                    values=["500"],
                                                ),
                                            ),
                                            condiction2=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=22,
                                                    column_number=81,
                                                ),
                                                logical_op_type=OpType.LOGICAL_NOT,
                                                condiction1=TestCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        line_number=22,
                                                        column_number=82,
                                                    ),
                                                    key="Var_6",
                                                    op="eq",
                                                    values=["600"],
                                                ),
                                                condiction2=None,
                                            ),
                                        ),
                                        then=[
                                            ReturnStatement(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=24,
                                                    column_number=13,
                                                ),
                                                transform_literal='{"value": 22}',
                                                transform_scenario="Value2",
                                            )
                                        ],
                                        then_link=None,
                                    )
                                ],
                                else_clause=[
                                    IfStatement(
                                        source_location=SourceLocation(
                                            file_name="<unnamed>",
                                            line_number=26,
                                            column_number=13,
                                        ),
                                        condiction=CompositeCondiction(
                                            source_location=SourceLocation(
                                                file_name="<unnamed>",
                                                line_number=26,
                                                column_number=16,
                                            ),
                                            logical_op_type=OpType.LOGICAL_OR,
                                            condiction1=ConstantCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=26,
                                                    column_number=16,
                                                ),
                                                constant=True,
                                            ),
                                            condiction2=CompositeCondiction(
                                                source_location=SourceLocation(
                                                    file_name="<unnamed>",
                                                    line_number=26,
                                                    column_number=24,
                                                ),
                                                logical_op_type=OpType.LOGICAL_NOT,
                                                condiction1=ConstantCondiction(
                                                    source_location=SourceLocation(
                                                        file_name="<unnamed>",
                                                        line_number=26,
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
                                                    line_number=27,
                                                    column_number=17,
                                                ),
                                                transform_literal='{"value": 33}',
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
                                            line_number=29,
                                            column_number=13,
                                        ),
                                        transform_literal="{}",
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
