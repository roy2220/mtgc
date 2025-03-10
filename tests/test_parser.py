import unittest
from io import StringIO

from src.parser import (
    CaseClause,
    CompositeCondiction,
    ConstantCondiction,
    ElseIfClause,
    IfStatement,
    Parser,
    ReturnStatement,
    SwitchStatement,
    TestCondiction,
)
from src.scanner import Scanner, TokenType


class TestParser(unittest.TestCase):
    def test_get_composite_statement(self):
        scanner = Scanner(
            StringIO(
                """\
switch get(1001) {
case "1":
    if test(1002, "eq", "100") || !test(1003, "gt", "50") {
        return 1
    } else if !true || false && !!true {
        return 2
    } else if (!true || false) && !!true {
        return 2
    } else if false && !!true || !true {
        return 3
    } else if false && !(!true || !true) {
        return 4
    } else {
        switch get(2001) {
        case "yes":
            return 5
        }
        return 6
    }
    return 7
case "2", "3", "4":
    return 8
default:
    return 9
}
return 10
"""
            )
        )

        parser = Parser(scanner)
        statements = parser.get_program()
        self.assertEqual(
            statements,
            [
                SwitchStatement(
                    key=1001,
                    case_clauses=[
                        CaseClause(
                            values=["1"],
                            then=[
                                IfStatement(
                                    condiction=CompositeCondiction(
                                        logical_op=TokenType.LOGICAL_OR,
                                        condiction1=TestCondiction(
                                            key=1002, op="eq", values=["100"]
                                        ),
                                        condiction2=CompositeCondiction(
                                            logical_op=TokenType.LOGICAL_NOT,
                                            condiction1=TestCondiction(
                                                key=1003, op="gt", values=["50"]
                                            ),
                                            condiction2=None,
                                        ),
                                    ),
                                    then=[ReturnStatement(return_value=1)],
                                    else_if_clauses=[
                                        ElseIfClause(
                                            condiction=CompositeCondiction(
                                                logical_op=TokenType.LOGICAL_OR,
                                                condiction1=CompositeCondiction(
                                                    logical_op=TokenType.LOGICAL_NOT,
                                                    condiction1=ConstantCondiction(
                                                        constant=True
                                                    ),
                                                    condiction2=None,
                                                ),
                                                condiction2=CompositeCondiction(
                                                    logical_op=TokenType.LOGICAL_AND,
                                                    condiction1=ConstantCondiction(
                                                        constant=False
                                                    ),
                                                    condiction2=CompositeCondiction(
                                                        logical_op=TokenType.LOGICAL_NOT,
                                                        condiction1=CompositeCondiction(
                                                            logical_op=TokenType.LOGICAL_NOT,
                                                            condiction1=ConstantCondiction(
                                                                constant=True
                                                            ),
                                                            condiction2=None,
                                                        ),
                                                        condiction2=None,
                                                    ),
                                                ),
                                            ),
                                            then=[ReturnStatement(return_value=2)],
                                        ),
                                        ElseIfClause(
                                            condiction=CompositeCondiction(
                                                logical_op=TokenType.LOGICAL_AND,
                                                condiction1=CompositeCondiction(
                                                    logical_op=TokenType.LOGICAL_OR,
                                                    condiction1=CompositeCondiction(
                                                        logical_op=TokenType.LOGICAL_NOT,
                                                        condiction1=ConstantCondiction(
                                                            constant=True
                                                        ),
                                                        condiction2=None,
                                                    ),
                                                    condiction2=ConstantCondiction(
                                                        constant=False
                                                    ),
                                                ),
                                                condiction2=CompositeCondiction(
                                                    logical_op=TokenType.LOGICAL_NOT,
                                                    condiction1=CompositeCondiction(
                                                        logical_op=TokenType.LOGICAL_NOT,
                                                        condiction1=ConstantCondiction(
                                                            constant=True
                                                        ),
                                                        condiction2=None,
                                                    ),
                                                    condiction2=None,
                                                ),
                                            ),
                                            then=[ReturnStatement(return_value=2)],
                                        ),
                                        ElseIfClause(
                                            condiction=CompositeCondiction(
                                                logical_op=TokenType.LOGICAL_OR,
                                                condiction1=CompositeCondiction(
                                                    logical_op=TokenType.LOGICAL_AND,
                                                    condiction1=ConstantCondiction(
                                                        constant=False
                                                    ),
                                                    condiction2=CompositeCondiction(
                                                        logical_op=TokenType.LOGICAL_NOT,
                                                        condiction1=CompositeCondiction(
                                                            logical_op=TokenType.LOGICAL_NOT,
                                                            condiction1=ConstantCondiction(
                                                                constant=True
                                                            ),
                                                            condiction2=None,
                                                        ),
                                                        condiction2=None,
                                                    ),
                                                ),
                                                condiction2=CompositeCondiction(
                                                    logical_op=TokenType.LOGICAL_NOT,
                                                    condiction1=ConstantCondiction(
                                                        constant=True
                                                    ),
                                                    condiction2=None,
                                                ),
                                            ),
                                            then=[ReturnStatement(return_value=3)],
                                        ),
                                        ElseIfClause(
                                            condiction=CompositeCondiction(
                                                logical_op=TokenType.LOGICAL_AND,
                                                condiction1=ConstantCondiction(
                                                    constant=False
                                                ),
                                                condiction2=CompositeCondiction(
                                                    logical_op=TokenType.LOGICAL_NOT,
                                                    condiction1=CompositeCondiction(
                                                        logical_op=TokenType.LOGICAL_OR,
                                                        condiction1=CompositeCondiction(
                                                            logical_op=TokenType.LOGICAL_NOT,
                                                            condiction1=ConstantCondiction(
                                                                constant=True
                                                            ),
                                                            condiction2=None,
                                                        ),
                                                        condiction2=CompositeCondiction(
                                                            logical_op=TokenType.LOGICAL_NOT,
                                                            condiction1=ConstantCondiction(
                                                                constant=True
                                                            ),
                                                            condiction2=None,
                                                        ),
                                                    ),
                                                    condiction2=None,
                                                ),
                                            ),
                                            then=[ReturnStatement(return_value=4)],
                                        ),
                                    ],
                                    else_clause=[
                                        SwitchStatement(
                                            key=2001,
                                            case_clauses=[
                                                CaseClause(
                                                    values=["yes"],
                                                    then=[
                                                        ReturnStatement(return_value=5)
                                                    ],
                                                )
                                            ],
                                            default_case_clause=None,
                                        ),
                                        ReturnStatement(return_value=6),
                                    ],
                                ),
                                ReturnStatement(return_value=7),
                            ],
                        ),
                        CaseClause(
                            values=["2", "3", "4"],
                            then=[ReturnStatement(return_value=8)],
                        ),
                    ],
                    default_case_clause=[ReturnStatement(return_value=9)],
                ),
                ReturnStatement(return_value=10),
            ],
        )


if __name__ == "__main__":
    unittest.main()
