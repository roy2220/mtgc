import dataclasses
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import sympy
from sympy.logic import boolalg

from .parser import (
    CaseClause,
    ComponentDeclaration,
    CompositeCondiction,
    ConstantCondiction,
    IfStatement,
    OpType,
    ReturnStatement,
    Statement,
    SwitchStatement,
    TestCondiction,
    UnitDeclaration,
    Visitor,
)
from .scanner import SourceLocation


@dataclass
class Component:
    name: str
    alias: str
    units: list["Unit"]


@dataclass
class Unit:
    name: str
    alias: str
    return_points: list["ReturnPoint"]


@dataclass
class ReturnPoint:
    or_expr: "OrExpr"
    file_offset: int
    transform: dict
    transform_annotation: str


@dataclass
class OrExpr:
    and_exprs: list["AndExpr"]


@dataclass
class AndExpr:
    test_exprs: list["TestExpr"]


@dataclass
class TestExpr:
    is_positive: bool
    symbol_id: int
    file_offset: int
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str

    reverse_op: str
    number_of_subkeys: int

    def virtual_key(self) -> Iterator[str]:
        yield self.key
        for i in range(0, self.number_of_subkeys):
            yield self.values[i]

    def real_values(self) -> Iterator[str]:
        for i in range(self.number_of_subkeys, len(self.values)):
            yield self.values[i]


class Analyzer:
    __slots__ = (
        "_component_declaration",
        "_reduce_return_points",
    )

    def __init__(
        self,
        component_declaration: ComponentDeclaration,
        reduce_return_points: bool = True,
    ) -> None:
        self._component_declaration = component_declaration
        self._reduce_return_points = reduce_return_points

    def get_component(self) -> Component:
        return Component(
            self._component_declaration.name,
            self._component_declaration.alias,
            self._get_units(),
        )

    def _get_units(self) -> list[Unit]:
        units: list[Unit] = []
        unit_names: set[str] = set()

        for unit_declaration in self._component_declaration.units:
            if unit_declaration.name in unit_names:
                raise DuplicateUnitNameError(unit_declaration)
            unit_names.add(unit_declaration.name)

            units.append(
                Unit(
                    unit_declaration.name,
                    unit_declaration.alias,
                    self._get_return_points(unit_declaration),
                )
            )

        return units

    def _get_return_points(
        self, unit_declaration: UnitDeclaration
    ) -> list[ReturnPoint]:
        p1_analyzer = _P1Analyzer(unit_declaration)
        p2_analyzer = _P2Analyzer(p1_analyzer.get_program_link())
        p3_analyzer = _P3Analyzer(p2_analyzer.get_return_points())
        return p3_analyzer.simplify_return_points(self._reduce_return_points)


class _P1Analyzer(Visitor):
    __slots__ = (
        "_unit_declaration",
        "_link_setter_stack",
    )

    def __init__(self, unit_declaration: UnitDeclaration) -> None:
        self._unit_declaration = unit_declaration
        self._link_setter_stack: list[Callable[[Statement], None]] = []

    def get_program_link(self) -> Statement:
        program_link = None

        def set_link(s: Statement) -> None:
            nonlocal program_link
            program_link = s

        self._link_setter_stack.append(set_link)
        self._visit_block(self._unit_declaration.program)

        if len(self._link_setter_stack) >= 1:
            raise MissingReturnStatementError(self._unit_declaration.source_location)

        assert program_link is not None
        return program_link

    def _visit_block(self, statements: list[Statement]) -> None:
        first_link_setter_index = len(self._link_setter_stack) - 1

        for statement in statements:
            for link_setter in self._link_setter_stack[first_link_setter_index:]:
                link_setter(statement)
            del self._link_setter_stack[first_link_setter_index:]

            if isinstance(statement, ReturnStatement):
                break

            statement.accept_visit(self)

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        def set_link_1(s: Statement) -> None:
            if_statement.body_link = s

        self._link_setter_stack.append(set_link_1)
        self._visit_block(if_statement.body)

        for else_if_clause in if_statement.else_if_clauses:

            def set_link_2(s: Statement) -> None:
                else_if_clause.body_link = s

            self._link_setter_stack.append(set_link_2)
            self._visit_block(else_if_clause.body)

        def set_link_3(s: Statement) -> None:
            if_statement.else_clause.body_link = s

        self._link_setter_stack.append(set_link_3)
        self._visit_block(if_statement.else_clause.body)

    def visit_switch_statement(self, switch_statement: SwitchStatement) -> None:
        for case_clause in switch_statement.case_clauses:

            def set_link_1(s: Statement) -> None:
                case_clause.body_link = s

            self._link_setter_stack.append(set_link_1)
            self._visit_block(case_clause.body)

        def set_link_2(s: Statement) -> None:
            switch_statement.default_case_clause.body_link = s

        self._link_setter_stack.append(set_link_2)
        self._visit_block(switch_statement.default_case_clause.body)


@dataclass
class _P2ReturnPoints:
    file_offset_2_item: dict[int, "_P2ReturnPoint"]
    symbol_id_2_test_args: dict[int, "_TestArgs"]


@dataclass
class _P2ReturnPoint:
    file_offset: int
    transform: dict
    transform_annotation: str
    condiction: boolalg.Boolean


@dataclass
class _TestArgs:
    file_offset: int
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str

    reverse_op: str
    number_of_subkeys: int


class _P2Analyzer(Visitor):
    __slots__ = (
        "_program_link",
        "_symbols",
        "_condiction_stack",
        "_return_points",
    )

    def __init__(self, program_link: Statement) -> None:
        self._program_link = program_link
        self._symbols: dict[tuple[str, ...], sympy.Symbol] = {}
        self._condiction_stack: list[boolalg.Boolean] = []
        self._return_points = _P2ReturnPoints({}, {})

    def get_return_points(self) -> _P2ReturnPoints:
        if self._program_link is not None:
            self._program_link.accept_visit(self)

        return self._return_points

    def _get_or_new_symbol(self, test_args: _TestArgs) -> boolalg.Boolean:
        symbol_key = (test_args.op, test_args.key, *test_args.values)
        symbol = self._symbols.get(symbol_key)
        if symbol is None:
            reverse_symbol_key = (
                test_args.reverse_op,
                test_args.key,
                *test_args.values,
            )
            reverse_symbol = self._symbols.get(reverse_symbol_key)
            if reverse_symbol is not None:
                return boolalg.Not(reverse_symbol)

            symbol_id = len(self._symbols)
            symbol = sympy.Symbol(str(symbol_id))
            self._symbols[symbol_key] = symbol
            self._return_points.symbol_id_2_test_args[symbol_id] = test_args
        return symbol

    def visit_return_statement(self, return_statement: ReturnStatement) -> None:
        if len(self._condiction_stack) == 0:
            condiction = sympy.true
        else:
            condiction = self._condiction_stack[0]
            for i in range(1, len(self._condiction_stack)):
                condiction = boolalg.And(condiction, self._condiction_stack[i])

        file_offset = return_statement.source_location.file_offset
        return_point = self._return_points.file_offset_2_item.get(file_offset)
        if return_point is None:
            return_point = _P2ReturnPoint(
                file_offset,
                return_statement.transform,
                return_statement.transform_annotation,
                condiction,
            )
            self._return_points.file_offset_2_item[file_offset] = return_point
        else:
            condiction = boolalg.Or(return_point.condiction, condiction)
            self._return_points.file_offset_2_item[file_offset] = dataclasses.replace(
                return_point, condiction=condiction
            )

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        if_statement.condiction.accept_visit(self)

        if (s := if_statement.body_link) is not None:
            s.accept_visit(self)

        other_condiction = boolalg.Not(self._condiction_stack.pop())

        for else_if_clause in if_statement.else_if_clauses:
            else_if_clause.condiction.accept_visit(self)

            self._condiction_stack[-1] = boolalg.And(
                other_condiction, self._condiction_stack[-1]
            )

            if (s := else_if_clause.body_link) is not None:
                s.accept_visit(self)

            other_condiction = boolalg.And(
                other_condiction, boolalg.Not(self._condiction_stack.pop())
            )

        self._condiction_stack.append(other_condiction)

        if (s := if_statement.else_clause.body_link) is not None:
            s.accept_visit(self)

        del self._condiction_stack[-1]

    def visit_switch_statement(self, switch_statement: SwitchStatement) -> None:
        case_values: set[str] = set()
        other_condiction = None

        for case_clause in switch_statement.case_clauses:
            condiction = None
            for i, (case_value, fact) in enumerate(case_clause.values_and_facts):
                if case_value in case_values:
                    raise DuplicateCaseValueError(case_clause, i)
                case_values.add(case_value)

                test_op_info = _test_op_infos["in"]
                test_args = _TestArgs(
                    switch_statement.source_location.file_offset,
                    switch_statement.key,
                    switch_statement.key_index,
                    test_op_info.op,
                    [case_value],
                    [case_value],
                    fact,
                    test_op_info.reverse_op,
                    test_op_info.number_of_subkeys,
                )
                if condiction is None:
                    condiction = self._get_or_new_symbol(test_args)
                else:
                    condiction = boolalg.Or(
                        condiction, self._get_or_new_symbol(test_args)
                    )
            assert condiction is not None
            self._condiction_stack.append(condiction)

            if (s := case_clause.body_link) is not None:
                s.accept_visit(self)

            del self._condiction_stack[-1]

            if other_condiction is None:
                other_condiction = boolalg.Not(condiction)
            else:
                other_condiction = boolalg.And(
                    other_condiction, boolalg.Not(condiction)
                )

        assert other_condiction is not None
        self._condiction_stack.append(other_condiction)

        if (s := switch_statement.default_case_clause.body_link) is not None:
            s.accept_visit(self)

        del self._condiction_stack[-1]

    def visit_constant_condiction(
        self, constant_condiction: ConstantCondiction
    ) -> None:
        if constant_condiction.constant:
            self._condiction_stack.append(sympy.true)
        else:
            self._condiction_stack.append(sympy.false)

    def visit_test_condiction(self, test_condiction: TestCondiction) -> None:
        test_op_info = _test_op_infos.get(test_condiction.op)
        if test_op_info is None:
            raise UnknownTestOpError(
                test_condiction.source_location, test_condiction.op
            )

        if len(test_condiction.values) < test_op_info.min_number_of_values:
            raise MoreTestOpValuesRequiredError(
                test_condiction.source_location, test_op_info
            )

        if test_op_info.alternative_op is not None:
            test_op_info = _test_op_infos[test_op_info.alternative_op]

        test_args = _TestArgs(
            test_condiction.source_location.file_offset,
            test_condiction.key,
            test_condiction.key_index,
            test_op_info.op,
            test_condiction.values,
            test_condiction.underlying_values,
            test_condiction.fact,
            test_op_info.reverse_op,
            test_op_info.number_of_subkeys,
        )
        self._condiction_stack.append(self._get_or_new_symbol(test_args))

    def visit_composite_condiction(
        self, composite_condiction: CompositeCondiction
    ) -> None:
        match composite_condiction.logical_op_type:
            case OpType.LOGICAL_NOT:
                composite_condiction.condiction1.accept_visit(self)
                self._condiction_stack[-1] = boolalg.Not(self._condiction_stack[-1])

            case OpType.LOGICAL_OR:
                composite_condiction.condiction1.accept_visit(self)
                assert composite_condiction.condiction2 is not None
                composite_condiction.condiction2.accept_visit(self)

                condiction = self._condiction_stack.pop()
                self._condiction_stack[-1] = boolalg.Or(
                    self._condiction_stack[-1], condiction
                )

            case OpType.LOGICAL_AND:
                composite_condiction.condiction1.accept_visit(self)
                assert composite_condiction.condiction2 is not None
                composite_condiction.condiction2.accept_visit(self)

                condiction = self._condiction_stack.pop()
                self._condiction_stack[-1] = boolalg.And(
                    self._condiction_stack[-1], condiction
                )

            case _:
                assert False


class _P3Analyzer:
    __slots__ = ("_raw_return_points",)

    def __init__(self, raw_return_points: _P2ReturnPoints) -> None:
        self._raw_return_points = raw_return_points

    def simplify_return_points(self, reduce_return_points: bool) -> list[ReturnPoint]:
        return_points: list[ReturnPoint] = []

        for raw_return_point in self._raw_return_points.file_offset_2_item.values():
            condiction = self._simplify_condiction(raw_return_point.condiction)
            if condiction is sympy.false:
                continue

            if condiction is sympy.true:
                or_expr = OrExpr([AndExpr([])])
            else:
                or_expr = self._make_or_expr(condiction)
            return_points.append(
                ReturnPoint(
                    or_expr,
                    raw_return_point.file_offset,
                    raw_return_point.transform,
                    raw_return_point.transform_annotation,
                )
            )

        return_points.sort(key=lambda x: x.file_offset)
        if not reduce_return_points:
            return return_points

        return self._reduce_return_points(return_points)

    def _simplify_condiction(self, condiction: boolalg.Boolean) -> boolalg.Boolean:
        return boolalg.to_dnf(condiction, False, False)

    def _make_or_expr(self, condiction: boolalg.Boolean) -> OrExpr:
        if condiction.func is not boolalg.Or:
            return OrExpr([self._make_and_expr(condiction)])  # type: ignore

        and_exprs: list[AndExpr] = []
        for condiction2 in condiction.args:
            and_exprs.append(self._make_and_expr(condiction2))  # type: ignore

        def file_offsets(and_expr: AndExpr) -> Iterator[int]:
            for test_expr in and_expr.test_exprs:
                yield test_expr.file_offset

        and_exprs.sort(key=lambda x: tuple(file_offsets(x)))
        return OrExpr(and_exprs)

    def _make_and_expr(self, condiction: boolalg.Boolean) -> AndExpr:
        if condiction.func is not boolalg.And:
            return AndExpr([self._make_test_expr(condiction)])  # type: ignore

        test_exprs: list[TestExpr] = []
        for condiction2 in condiction.args:
            test_exprs.append(self._make_test_expr(condiction2))  # type: ignore

        test_exprs.sort(key=lambda x: x.file_offset)
        return AndExpr(test_exprs)

    def _make_test_expr(self, condiction: boolalg.Boolean) -> TestExpr:
        is_positive = True
        if condiction.func is boolalg.Not:
            is_positive = False
            condiction = condiction.args[0]  # type: ignore

        assert condiction.func is sympy.Symbol
        symbol_id = int(condiction.name)  # type: ignore
        test_args = self._raw_return_points.symbol_id_2_test_args[symbol_id]
        return TestExpr(
            is_positive,
            symbol_id,
            test_args.file_offset,
            test_args.key,
            test_args.key_index,
            test_args.op,
            test_args.values,
            test_args.underlying_values,
            test_args.fact,
            test_args.reverse_op,
            test_args.number_of_subkeys,
        )

    @classmethod
    def _reduce_return_points(
        cls, return_points: list[ReturnPoint]
    ) -> list[ReturnPoint]:
        small_return_point: list[ReturnPoint] = []

        for return_point in return_points:
            or_expr = cls._reduce_or_expr(return_point.or_expr)
            if or_expr is None:
                continue

            new_return_point = dataclasses.replace(return_point, or_expr=or_expr)
            small_return_point.append(new_return_point)

        return small_return_point

    @classmethod
    def _reduce_or_expr(cls, or_expr: OrExpr) -> OrExpr | None:
        and_exprs = cls._reduce_and_exprs(or_expr.and_exprs)
        if and_exprs is None:
            return None

        new_or_expr = dataclasses.replace(or_expr, and_exprs=and_exprs)
        return new_or_expr

    @classmethod
    def _reduce_and_exprs(cls, and_exprs: list[AndExpr]) -> list[AndExpr] | None:
        small_and_exprs: list[AndExpr] = []

        for and_expr in and_exprs:
            test_exprs = cls._reduce_test_exprs(and_expr.test_exprs)
            if test_exprs is None:
                continue

            new_and_expr = dataclasses.replace(and_expr, test_exprs=test_exprs)
            if new_and_expr in small_and_exprs:
                continue

            small_and_exprs.append(new_and_expr)

        if len(small_and_exprs) == 0:
            return None

        return small_and_exprs

    @classmethod
    def _reduce_test_exprs(cls, test_exprs: list[TestExpr]) -> list[TestExpr] | None:
        small_test_exprs = dict(enumerate(test_exprs))

        for i, test_expr_x in enumerate(test_exprs):
            if i not in small_test_exprs.keys():
                continue

            distinct_x_values = None
            if (test_expr_x.is_positive, test_expr_x.op) in (
                (True, "in"),
                (False, "nin"),
                (True, "len_eq"),
                (False, "len_neq"),
                (True, "num_eq"),
                (False, "num_neq"),
                (True, "x/map_value_in"),
                (False, "x/map_value_nin"),
                (True, "x/map_value_len_eq"),
                (False, "x/map_value_len_neq"),
                (True, "x/map_value_num_eq"),
                (False, "x/map_value_num_neq"),
            ):
                distinct_x_values = set(test_expr_x.real_values())

            for j, test_expr_y in enumerate(test_exprs):
                if j == i or j not in small_test_exprs.keys():
                    continue

                if test_expr_y.symbol_id == test_expr_x.symbol_id:
                    if test_expr_y.is_positive == test_expr_x.is_positive:
                        # remove duplicate
                        small_test_exprs.pop(j)
                        continue
                    else:
                        # conflict
                        return None

                if (
                    distinct_x_values is not None
                    and test_expr_y.op in (test_expr_x.op, test_expr_x.reverse_op)
                    and tuple(test_expr_y.virtual_key())
                    == tuple(test_expr_x.virtual_key())
                ):
                    if (test_expr_y.is_positive, test_expr_y.op) in (
                        (
                            test_expr_x.is_positive,
                            test_expr_x.op,
                        ),
                        (
                            not test_expr_x.is_positive,
                            test_expr_x.reverse_op,
                        ),
                    ):
                        if distinct_x_values.issuperset(test_expr_y.real_values()):
                            # remove duplicate
                            small_test_exprs.pop(j)
                            continue
                        elif distinct_x_values.isdisjoint(test_expr_y.real_values()):
                            # conflict
                            return None
                    else:
                        if distinct_x_values.issubset(test_expr_y.real_values()):
                            # conflict
                            return None
                        elif distinct_x_values.isdisjoint(test_expr_y.real_values()):
                            # remove unused
                            small_test_exprs.pop(j)
                            continue

        return list(small_test_exprs.values())


@dataclass
class _TestOpInfo:
    op: str
    reverse_op: str
    alternative_op: str | None
    min_number_of_values: int
    number_of_subkeys: int


_test_op_infos: dict[str, _TestOpInfo] = {
    "in": _TestOpInfo("in", "nin", None, 1, 0),
    "nin": _TestOpInfo("nin", "in", None, 1, 0),
    "eq": _TestOpInfo("eq", "neq", "in", 1, 0),
    "neq": _TestOpInfo("neq", "eq", "nin", 1, 0),
    "gt": _TestOpInfo("gt", "lte", None, 1, 0),
    "lte": _TestOpInfo("lte", "gt", None, 1, 0),
    "lt": _TestOpInfo("lt", "gte", None, 1, 0),
    "gte": _TestOpInfo("gte", "lt", None, 1, 0),
    "len_eq": _TestOpInfo("len_eq", "len_neq", None, 1, 0),
    "len_neq": _TestOpInfo("len_neq", "len_eq", None, 1, 0),
    "len_gt": _TestOpInfo("len_gt", "len_lte", None, 1, 0),
    "len_lte": _TestOpInfo("len_lte", "len_gt", None, 1, 0),
    "len_lt": _TestOpInfo("len_lt", "len_gte", None, 1, 0),
    "len_gte": _TestOpInfo("len_gte", "len_lt", None, 1, 0),
    "num_eq": _TestOpInfo("num_eq", "num_neq", None, 1, 0),
    "num_neq": _TestOpInfo("num_neq", "num_eq", None, 1, 0),
    "num_gt": _TestOpInfo("num_gt", "num_lte", None, 1, 0),
    "num_lte": _TestOpInfo("num_lte", "num_gt", None, 1, 0),
    "num_lt": _TestOpInfo("num_lt", "num_gte", None, 1, 0),
    "num_gte": _TestOpInfo("num_gte", "num_lt", None, 1, 0),
    # ----------
    "v_in": _TestOpInfo("v_in", "v_nin", None, 1, 0),
    "v_nin": _TestOpInfo("v_nin", "v_in", None, 1, 0),
    "v_eq": _TestOpInfo("v_eq", "v_neq", "v_in", 1, 0),
    "v_neq": _TestOpInfo("v_neq", "v_eq", "v_nin", 1, 0),
    "v_gt": _TestOpInfo("v_gt", "v_lte", None, 1, 0),
    "v_lte": _TestOpInfo("v_lte", "v_gt", None, 1, 0),
    "v_lt": _TestOpInfo("v_lt", "v_gte", None, 1, 0),
    "v_gte": _TestOpInfo("v_gte", "v_lt", None, 1, 0),
    "v_len_eq": _TestOpInfo("v_len_eq", "v_len_neq", None, 1, 0),
    "v_len_neq": _TestOpInfo("v_len_neq", "v_len_eq", None, 1, 0),
    "v_len_gt": _TestOpInfo("v_len_gt", "v_len_lte", None, 1, 0),
    "v_len_lte": _TestOpInfo("v_len_lte", "v_len_gt", None, 1, 0),
    "v_len_lt": _TestOpInfo("v_len_lt", "v_len_gte", None, 1, 0),
    "v_len_gte": _TestOpInfo("v_len_gte", "v_len_lt", None, 1, 0),
    "v_num_eq": _TestOpInfo("v_num_eq", "v_num_neq", None, 1, 0),
    "v_num_neq": _TestOpInfo("v_num_neq", "v_num_eq", None, 1, 0),
    "v_num_gt": _TestOpInfo("v_num_gt", "v_num_lte", None, 1, 0),
    "v_num_lte": _TestOpInfo("v_num_lte", "v_num_gt", None, 1, 0),
    "v_num_lt": _TestOpInfo("v_num_lt", "v_num_gte", None, 1, 0),
    "v_num_gte": _TestOpInfo("v_num_gte", "v_num_lt", None, 1, 0),
    # ----------
    "x/map_value_in": _TestOpInfo("x/map_value_in", "x/map_value_nin", None, 2, 1),
    "x/map_value_nin": _TestOpInfo("x/map_value_nin", "x/map_value_in", None, 2, 1),
    "x/map_value_eq": _TestOpInfo(
        "x/map_value_eq", "x/map_value_neq", "x/map_value_in", 2, 1
    ),
    "x/map_value_neq": _TestOpInfo(
        "x/map_value_neq", "x/map_value_eq", "x/map_value_nin", 2, 1
    ),
    "x/map_value_gt": _TestOpInfo("x/map_value_gt", "x/map_value_lte", None, 2, 1),
    "x/map_value_lte": _TestOpInfo("x/map_value_lte", "x/map_value_gt", None, 2, 1),
    "x/map_value_lt": _TestOpInfo("x/map_value_lt", "x/map_value_gte", None, 2, 1),
    "x/map_value_gte": _TestOpInfo("x/map_value_gte", "x/map_value_lt", None, 2, 1),
    "x/map_value_len_eq": _TestOpInfo(
        "x/map_value_len_eq", "x/map_value_len_neq", None, 2, 1
    ),
    "x/map_value_len_neq": _TestOpInfo(
        "x/map_value_len_neq", "x/map_value_len_eq", None, 2, 1
    ),
    "x/map_value_len_gt": _TestOpInfo(
        "x/map_value_len_gt", "x/map_value_len_lte", None, 2, 1
    ),
    "x/map_value_len_lte": _TestOpInfo(
        "x/map_value_len_lte", "x/map_value_len_gt", None, 2, 1
    ),
    "x/map_value_len_lt": _TestOpInfo(
        "x/map_value_len_lt", "x/map_value_len_gte", None, 2, 1
    ),
    "x/map_value_len_gte": _TestOpInfo(
        "x/map_value_len_gte", "x/map_value_len_lt", None, 2, 1
    ),
    "x/map_value_num_eq": _TestOpInfo(
        "x/map_value_num_eq", "x/map_value_num_neq", None, 2, 1
    ),
    "x/map_value_num_neq": _TestOpInfo(
        "x/map_value_num_neq", "x/map_value_num_eq", None, 2, 1
    ),
    "x/map_value_num_gt": _TestOpInfo(
        "x/map_value_num_gt", "x/map_value_num_lte", None, 2, 1
    ),
    "x/map_value_num_lte": _TestOpInfo(
        "x/map_value_num_lte", "x/map_value_num_gt", None, 2, 1
    ),
    "x/map_value_num_lt": _TestOpInfo(
        "x/map_value_num_lt", "x/map_value_num_gte", None, 2, 1
    ),
    "x/map_value_num_gte": _TestOpInfo(
        "x/map_value_num_gte", "x/map_value_num_lt", None, 2, 1
    ),
}


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        super().__init__(
            f"{source_location.file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )


class DuplicateCaseValueError(Error):
    def __init__(self, case_clause: CaseClause, case_value_index: int) -> None:
        super().__init__(
            case_clause.source_location,
            f"duplicate case value: {repr(case_clause.values_and_facts[case_value_index][0])}",
        )


class DuplicateUnitNameError(Error):
    def __init__(self, unit_declaration: UnitDeclaration) -> None:
        super().__init__(
            unit_declaration.source_location,
            f"duplicate unit name: {repr(unit_declaration.name)}",
        )


class MissingReturnStatementError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "missing return statement")


class UnknownTestOpError(Error):
    def __init__(self, source_location: SourceLocation, test_op: str) -> None:
        super().__init__(source_location, f"unknown test operation {repr(test_op)}")


class MoreTestOpValuesRequiredError(Error):
    def __init__(
        self, source_location: SourceLocation, test_op_info: _TestOpInfo
    ) -> None:
        super().__init__(
            source_location,
            f"test operation {repr(test_op_info.op)} requires at least {test_op_info.min_number_of_values} values",
        )
