import ast
import enum
import inspect
from dataclasses import dataclass


@dataclass(kw_only=True)
class SourceLocation:
    file_name: str
    line_number: int
    column_number: int

    def __repr__(self) -> str:
        return f"{self.file_name}:{self.line_number}:{self.column_number}"


@dataclass(kw_only=True)
class Pipeline:
    source_location: SourceLocation
    component_name: str
    nodes: list["Node"]


@dataclass(kw_only=True)
class Node:
    source_location: SourceLocation
    node_name: str
    is_first: bool
    bound_component_name: str | None
    body: list["Statement"]


@dataclass(kw_only=True)
class MatchTransform:
    source_location: SourceLocation
    component_name: str
    business_units: list["BusinessUnit"]


@dataclass(kw_only=True)
class BusinessUnit:
    source_location: SourceLocation
    business_unit: str
    body: list["Statement"]


type Statement = "ReturnStatement | IfStatement"


@dataclass(kw_only=True)
class ReturnStatement:
    source_location: SourceLocation
    next: "Next"  # for Node
    set: "Set"  # for MatchTransform


@dataclass(kw_only=True)
class Next:
    # if source_location is None, no Next present
    source_location: SourceLocation | None
    next_node_name: str | None


@dataclass(kw_only=True)
class Set:
    # if source_location is None, no Set present
    source_location: SourceLocation | None
    business_scenario: str
    key_and_expr_pairs: list[tuple[str, str]]


@dataclass(kw_only=True)
class IfStatement:
    source_location: SourceLocation
    condition: "Condition"
    body: list[Statement]
    else_clause: "ElseClause"


@dataclass(kw_only=True)
class ElseClause:
    # if source_location is None, no ElseClause present
    source_location: SourceLocation | None
    body: list[Statement]


type Condition = "TestCondition | CompositeCondition"


@dataclass(kw_only=True)
class TestCondition:
    source_location: SourceLocation
    key: str
    op: str
    values: list[bool | int | float | str]


@dataclass(kw_only=True)
class CompositeCondition:
    source_location: SourceLocation
    logical_op_type: "LogicalOpType"
    condition_1: Condition
    condition_2: Condition | None


class LogicalOpType(enum.IntEnum):
    LOGICAL_NOT = enum.auto()
    LOGICAL_OR = enum.auto()
    LOGICAL_AND = enum.auto()


class Parser:
    def __init__(self) -> None:
        self._target_type: str = ""
        self._file_name: str = ""
        self._first_line_number: int = 0

    def get_pipeline(self, class1: type) -> Pipeline:
        self._target_type = "PIPELINE"
        self._file_name = inspect.getfile(class1)
        lines, self._first_line_number = inspect.getsourcelines(class1)
        module = ast.parse("".join(lines), filename=self._file_name)

        class_def = module.body[0]
        assert isinstance(class_def, ast.ClassDef), self._get_source_location(class_def)
        assert len(class_def.decorator_list) == 1, self._get_source_location(class_def)
        call = class_def.decorator_list[0]
        assert isinstance(call, ast.Call), self._get_source_location(call)
        attribute = call.func
        assert isinstance(attribute, ast.Attribute), self._get_source_location(
            attribute
        )
        assert attribute.attr == "TABLE_PIPELINE", self._get_source_location(attribute)
        assert len(call.args) == 1, self._get_source_location(call)
        constant = call.args[0]
        assert isinstance(constant, ast.Constant), self._get_source_location(constant)
        assert isinstance(constant.value, str), self._get_source_location(constant)

        component_name = constant.value

        return Pipeline(
            source_location=self._get_source_location(class_def),
            component_name=component_name,
            nodes=self._get_nodes(class_def.body),
        )

    def get_match_transform(self, class1: type) -> MatchTransform:
        self._target_type = "MATCH_TRANSFORM"
        self._file_name = inspect.getfile(class1)
        lines, self._first_line_number = inspect.getsourcelines(class1)
        module = ast.parse("".join(lines), filename=self._file_name)

        class_def = module.body[0]
        assert isinstance(class_def, ast.ClassDef), self._get_source_location(class_def)
        assert len(class_def.decorator_list) == 1, self._get_source_location(class_def)
        call = class_def.decorator_list[0]
        assert isinstance(call, ast.Call), self._get_source_location(call)
        attribute = call.func
        assert isinstance(attribute, ast.Attribute), self._get_source_location(
            attribute
        )
        assert attribute.attr == "TABLE_MATCH_TRANSFORM", self._get_source_location(
            attribute
        )
        assert len(call.args) == 1, self._get_source_location(call)
        constant = call.args[0]
        assert isinstance(constant, ast.Constant), self._get_source_location(constant)
        assert isinstance(constant.value, str), self._get_source_location(constant)

        component_name = constant.value

        return MatchTransform(
            source_location=self._get_source_location(class_def),
            component_name=component_name,
            business_units=self._get_business_units(class_def.body),
        )

    def _get_nodes(self, class_body: list[ast.stmt]) -> list[Node]:
        nodes: list[Node] = []

        for function_def in class_body:
            assert isinstance(function_def, ast.FunctionDef), self._get_source_location(
                function_def
            )
            assert len(function_def.decorator_list) == 1, self._get_source_location(
                function_def
            )
            call = function_def.decorator_list[0]
            assert isinstance(call, ast.Call), self._get_source_location(call)
            attribute = call.func
            assert isinstance(attribute, ast.Attribute), self._get_source_location(
                attribute
            )
            assert attribute.attr in ("FIRST_NODE", "NODE"), self._get_source_location(
                attribute
            )
            if attribute.attr == "FIRST_NODE":
                assert len(call.args) == 0, self._get_source_location(call)

                is_first = True
                bound_component_name = None
            elif attribute.attr == "NODE":
                assert len(call.args) == 1, self._get_source_location(call)
                constant = call.args[0]
                assert isinstance(constant, ast.Constant), self._get_source_location(
                    constant
                )
                assert isinstance(constant.value, str), self._get_source_location(
                    constant
                )

                is_first = False
                bound_component_name = constant.value
            else:
                assert False

            nodes.append(
                Node(
                    source_location=self._get_source_location(function_def),
                    node_name=function_def.name,
                    is_first=is_first,
                    bound_component_name=bound_component_name,
                    body=self._get_body(function_def.body),
                ),
            )

        return nodes

    def _get_business_units(self, class_body: list[ast.stmt]) -> list[BusinessUnit]:
        business_units: list[BusinessUnit] = []

        for function_def in class_body:
            assert isinstance(function_def, ast.FunctionDef), self._get_source_location(
                function_def
            )
            assert len(function_def.decorator_list) == 1, self._get_source_location(
                function_def
            )
            call = function_def.decorator_list[0]
            assert isinstance(call, ast.Call), self._get_source_location(call)
            attribute = call.func
            assert isinstance(attribute, ast.Attribute), self._get_source_location(
                attribute
            )
            assert attribute.attr == "BUSINESS_UNIT", self._get_source_location(
                attribute
            )
            assert len(call.args) == 1, self._get_source_location(call)
            constant = call.args[0]
            assert isinstance(constant, ast.Constant), self._get_source_location(
                constant
            )
            assert isinstance(constant.value, str), self._get_source_location(constant)

            business_unit = constant.value

            business_units.append(
                BusinessUnit(
                    source_location=self._get_source_location(function_def),
                    business_unit=business_unit,
                    body=self._get_body(function_def.body),
                ),
            )

        return business_units

    def _get_body(self, stmts: list[ast.stmt]) -> list[Statement]:
        body: list[Statement] = []

        for stmt in stmts:
            assert isinstance(stmt, (ast.Return, ast.If)), self._get_source_location(
                stmt
            )
            if isinstance(stmt, ast.Return):
                body.append(self._get_return_statement(stmt))
            elif isinstance(stmt, ast.If):
                body.append(self._get_if_statement(stmt))
            else:
                assert False

        return body

    def _get_return_statement(self, return1: ast.Return) -> ReturnStatement:
        assert return1.value is not None, self._get_source_location(return1)
        if self._target_type == "PIPELINE":
            return ReturnStatement(
                source_location=self._get_source_location(return1),
                next=self._get_next(return1.value),
                set=Set(
                    source_location=None, business_scenario="", key_and_expr_pairs=[]
                ),
            )
        elif self._target_type == "MATCH_TRANSFORM":
            return ReturnStatement(
                source_location=self._get_source_location(return1),
                next=Next(source_location=None, next_node_name=""),
                set=self._get_set(return1.value),
            )
        else:
            assert False

    def _get_next(self, return_value: ast.expr) -> Next:
        call = return_value
        assert isinstance(call, ast.Call), self._get_source_location(call)
        attribute = call.func
        assert isinstance(attribute, ast.Attribute), self._get_source_location(
            attribute
        )
        assert attribute.attr == "Next", self._get_source_location(attribute)
        assert len(call.args) == 1, self._get_source_location(call)
        assert isinstance(
            call.args[0], (ast.Constant, ast.Attribute)
        ), self._get_source_location(call.args[0])
        if isinstance(call.args[0], ast.Constant):
            constant = call.args[0]
            assert constant.value is None, self._get_source_location(constant)
            next_node_name = None
        elif isinstance(call.args[0], ast.Attribute):
            attribute = call.args[0]
            next_node_name = attribute.attr
        else:
            assert False

        return Next(
            source_location=self._get_source_location(call),
            next_node_name=next_node_name,
        )

    def _get_set(self, return_value: ast.expr) -> Set:
        call = return_value
        assert isinstance(call, ast.Call), self._get_source_location(call)
        attribute = call.func
        assert isinstance(attribute, ast.Attribute), self._get_source_location(
            attribute
        )
        assert attribute.attr == "Set", self._get_source_location(attribute)
        assert len(call.args) == 2, self._get_source_location(call)
        constant = call.args[0]
        assert isinstance(constant, ast.Constant), self._get_source_location(constant)
        assert isinstance(constant.value, str), self._get_source_location(constant)

        business_scenario = constant.value

        list1 = call.args[1]
        assert isinstance(list1, ast.List), self._get_source_location(list1)

        key_and_expr_pairs: list[tuple[str, str]] = []

        for tuple1 in list1.elts:
            assert isinstance(tuple1, ast.Tuple), self._get_source_location(tuple1)
            assert len(tuple1.elts) == 2, self._get_source_location(tuple1)
            constant = tuple1.elts[0]
            assert isinstance(constant, ast.Constant), self._get_source_location(
                constant
            )
            assert isinstance(constant.value, str), self._get_source_location(constant)

            key = constant.value

            constant = tuple1.elts[1]
            assert isinstance(constant, ast.Constant), self._get_source_location(
                constant
            )
            assert isinstance(constant.value, str), self._get_source_location(constant)

            expr = constant.value
            key_and_expr_pairs.append((key, expr))

        return Set(
            source_location=self._get_source_location(call),
            business_scenario=business_scenario,
            key_and_expr_pairs=key_and_expr_pairs,
        )

    def _get_if_statement(self, if1: ast.If) -> IfStatement:
        condition = self._get_condition(if1.test)
        body = self._get_body(if1.body)
        if len(if1.orelse) == 0:
            else_clause = ElseClause(source_location=None, body=[])
        else:
            else_clause = ElseClause(
                source_location=self._get_source_location(if1.orelse[0]),
                body=self._get_body(if1.orelse),
            )
        return IfStatement(
            source_location=self._get_source_location(if1),
            condition=condition,
            body=body,
            else_clause=else_clause,
        )

    def _get_condition(self, test: ast.expr) -> Condition:
        assert isinstance(
            test, (ast.Call, ast.UnaryOp, ast.BoolOp)
        ), self._get_source_location(test)

        if isinstance(test, ast.Call):
            return self._get_test_condition(test)
        if isinstance(test, ast.UnaryOp):
            assert isinstance(test.op, ast.Not), self._get_source_location(test)
            return CompositeCondition(
                source_location=self._get_source_location(test),
                logical_op_type=LogicalOpType.LOGICAL_NOT,
                condition_1=self._get_condition(test.operand),
                condition_2=None,
            )
        if isinstance(test, ast.BoolOp):
            assert isinstance(test.op, (ast.Or, ast.And)), self._get_source_location(
                test
            )
            assert len(test.values) == 2, self._get_source_location(test)
            if isinstance(test.op, ast.Or):
                return CompositeCondition(
                    source_location=self._get_source_location(test),
                    logical_op_type=LogicalOpType.LOGICAL_OR,
                    condition_1=self._get_condition(test.values[0]),
                    condition_2=self._get_condition(test.values[1]),
                )
            elif isinstance(test.op, ast.And):
                return CompositeCondition(
                    source_location=self._get_source_location(test),
                    logical_op_type=LogicalOpType.LOGICAL_AND,
                    condition_1=self._get_condition(test.values[0]),
                    condition_2=self._get_condition(test.values[1]),
                )
            else:
                assert False
        else:
            assert False

    def _get_test_condition(self, call: ast.Call) -> TestCondition:
        attribute = call.func
        assert isinstance(attribute, ast.Attribute), self._get_source_location(
            attribute
        )
        assert attribute.attr == "Test", self._get_source_location(attribute)
        assert len(call.args) == 3, self._get_source_location(call)
        constant = call.args[0]
        assert isinstance(constant, ast.Constant), self._get_source_location(constant)
        assert isinstance(constant.value, str), self._get_source_location(constant)

        key = constant.value

        constant = call.args[1]
        assert isinstance(constant, ast.Constant), self._get_source_location(constant)
        assert isinstance(constant.value, str), self._get_source_location(constant)

        op = constant.value

        if isinstance(call.args[2], ast.List):
            list1 = call.args[2]
            values = []

            for constant in list1.elts:
                assert isinstance(constant, ast.Constant), self._get_source_location(
                    constant
                )
                assert isinstance(
                    constant.value, (bool, int, float, str)
                ), self._get_source_location(constant)

                values.append(constant.value)
        else:
            constant = call.args[2]
            assert isinstance(constant, ast.Constant), self._get_source_location(
                constant
            )
            assert isinstance(
                constant.value, (bool, int, float, str)
            ), self._get_source_location(constant)

            values = [constant.value]

        return TestCondition(
            source_location=self._get_source_location(call),
            key=key,
            op=op,
            values=values,
        )

    def _get_source_location(self, x: ast.AST) -> SourceLocation:
        return SourceLocation(
            file_name=self._file_name,
            line_number=self._first_line_number + x.lineno - 1,  # type: ignore
            column_number=x.col_offset,  # type: ignore
        )
