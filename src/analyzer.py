import dataclasses
import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import sympy
from sympy.logic import boolalg

from .parser import (
    CaseValue,
    ComponentDeclaration,
    CompositeCondiction,
    ConstantCondiction,
    IfStatement,
    OpType,
    ReturnStatement,
    Statement,
    SwitchStatement,
    TestCondiction,
    Transform,
    UnitDeclaration,
    Visitor,
)
from .scanner import SourceLocation
from .test_op_infos import TestOpInfo, test_op_infos


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
    transform_list: list[Transform]


@dataclass
class OrExpr:
    and_exprs: list["AndExpr"]


@dataclass
class AndExpr:
    test_exprs: list["TestExpr"]


@dataclass
class TestExpr:
    is_positive: bool
    file_offset_1: int
    file_offset_2: int
    test_id: int
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str

    reverse_op: str
    number_of_subkeys: int
    equals_real_values: bool
    unequals_real_values: bool
    children: list["TestExpr"]

    def virtual_key(self) -> Iterator[str]:
        yield self.key
        for i in range(0, self.number_of_subkeys):
            yield self.values[i]

    def number_of_real_values(self) -> int:
        return len(self.values) - self.number_of_subkeys

    def real_values(self) -> Iterator[str]:
        for i in range(self.number_of_subkeys, len(self.values)):
            yield self.values[i]

    def real_underlying_values(self) -> Iterator[str]:
        for i in range(self.number_of_subkeys, len(self.underlying_values)):
            yield self.underlying_values[i]


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
        p2_analyzer = _P2Analyzer(
            unit_declaration.default_transform_list, p1_analyzer.get_program_link()
        )
        raw_return_points = p2_analyzer.get_return_points()
        p3_analyzer = _P3Analyzer(raw_return_points)
        return_points = p3_analyzer.simplify_return_points(self._reduce_return_points)
        _P4Analyzer(
            unit_declaration,
            return_points,
            raw_return_points.default_return_point_file_offsets,
        ).check_return_statements()
        return return_points


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
    default_transform_list: list[Transform]
    default_return_point_file_offsets: set[int]
    file_offset_2_item: dict[int, "_P2ReturnPoint"]
    file_offsets_2_test_args: dict[tuple[int, int], "_TestArgs"]


@dataclass
class _P2ReturnPoint:
    file_offset: int
    transform_list: list[Transform]
    conditions: list[boolalg.Boolean]


@dataclass
class _TestArgs:
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str

    reverse_op: str
    number_of_subkeys: int
    equals_real_values: bool
    unequals_real_values: bool


class _P2Analyzer(Visitor):
    __slots__ = (
        "_program_link",
        "_symbols",
        "_condition_stack",
        "_return_points",
    )

    def __init__(
        self, default_transform_list: list[Transform], program_link: Statement
    ) -> None:
        self._program_link = program_link
        self._symbols: dict[str, sympy.Symbol] = {}
        self._condition_stack: list[boolalg.Boolean] = []
        self._return_points = _P2ReturnPoints(default_transform_list, set(), {}, {})

    def get_return_points(self) -> _P2ReturnPoints:
        if self._program_link is not None:
            self._program_link.accept_visit(self)

        return self._return_points

    def _get_or_new_symbol(
        self, file_offset_1: int, file_offset_2: int, test_args: _TestArgs
    ) -> sympy.Symbol:
        symbol_name = f"{file_offset_1},{file_offset_2}"
        symbol = self._symbols.get(symbol_name)
        if symbol is None:
            symbol = sympy.Symbol(symbol_name)
            self._symbols[symbol_name] = symbol
            self._return_points.file_offsets_2_test_args[
                file_offset_1, file_offset_2
            ] = test_args
        return symbol

    def visit_return_statement(self, return_statement: ReturnStatement) -> None:
        if len(self._condition_stack) == 0:
            condition = sympy.true
        else:
            condition = self._condition_stack[0]
            for i in range(1, len(self._condition_stack)):
                condition = boolalg.And(condition, self._condition_stack[i])

        transform_list = return_statement.transform_list
        file_offset = return_statement.source_location.file_offset
        if len(transform_list) == 0:
            transform_list = self._return_points.default_transform_list
            self._return_points.default_return_point_file_offsets.add(file_offset)
            file_offset = _dummy_file_offset

        return_point = self._return_points.file_offset_2_item.get(file_offset)
        if return_point is None:
            return_point = _P2ReturnPoint(
                file_offset,
                transform_list,
                [],
            )
            self._return_points.file_offset_2_item[file_offset] = return_point
        return_point.conditions.append(condition)

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        if_statement.condition.accept_visit(self)

        if (s := if_statement.body_link) is not None:
            s.accept_visit(self)

        other_condition = boolalg.Not(self._condition_stack.pop())

        for else_if_clause in if_statement.else_if_clauses:
            else_if_clause.condition.accept_visit(self)

            self._condition_stack[-1] = boolalg.And(
                other_condition, self._condition_stack[-1]
            )

            if (s := else_if_clause.body_link) is not None:
                s.accept_visit(self)

            other_condition = boolalg.And(
                other_condition, boolalg.Not(self._condition_stack.pop())
            )

        self._condition_stack.append(other_condition)

        if (s := if_statement.else_clause.body_link) is not None:
            s.accept_visit(self)

        del self._condition_stack[-1]

    def visit_switch_statement(self, switch_statement: SwitchStatement) -> None:
        case_values: set[str] = set()
        other_condition = None

        for case_clause in switch_statement.case_clauses:
            condition = None
            for case_value in case_clause.case_values:
                if case_value.value in case_values:
                    raise DuplicateCaseValueError(case_value)
                case_values.add(case_value.value)

                test_op_info = test_op_infos["in"]
                test_args = _TestArgs(
                    switch_statement.key,
                    switch_statement.key_index,
                    test_op_info.op,
                    [case_value.value],
                    [case_value.value],
                    case_value.fact,
                    test_op_info.reverse_op,
                    test_op_info.number_of_subkeys,
                    test_op_info.equals_real_values,
                    test_op_info.unequals_real_values,
                )
                if condition is None:
                    condition = self._get_or_new_symbol(
                        switch_statement.source_location.file_offset,
                        case_value.source_location.file_offset,
                        test_args,
                    )
                else:
                    condition = boolalg.Or(
                        condition,
                        self._get_or_new_symbol(
                            switch_statement.source_location.file_offset,
                            case_value.source_location.file_offset,
                            test_args,
                        ),
                    )
            assert condition is not None
            self._condition_stack.append(condition)

            if (s := case_clause.body_link) is not None:
                s.accept_visit(self)

            del self._condition_stack[-1]

            if other_condition is None:
                other_condition = boolalg.Not(condition)
            else:
                other_condition = boolalg.And(other_condition, boolalg.Not(condition))

        assert other_condition is not None
        self._condition_stack.append(other_condition)

        if (s := switch_statement.default_case_clause.body_link) is not None:
            s.accept_visit(self)

        del self._condition_stack[-1]

    def visit_constant_condition(self, constant_condition: ConstantCondiction) -> None:
        if constant_condition.constant:
            self._condition_stack.append(sympy.true)
        else:
            self._condition_stack.append(sympy.false)

    def visit_test_condition(self, test_condition: TestCondiction) -> None:
        test_op_info = test_op_infos.get(test_condition.op)
        if test_op_info is None:
            raise UnknownTestOpError(test_condition.source_location, test_condition.op)

        if len(test_condition.values) < test_op_info.min_number_of_values:
            raise InsufficientTestOpValuesError(
                test_condition.source_location, test_op_info
            )

        if (n := test_op_info.max_number_of_values) is not None and len(
            test_condition.values
        ) > n:
            raise TooManyTestOpValuesError(test_condition.source_location, test_op_info)

        if test_op_info.multiple_op is not None:
            # multiple_op is easy for _P3Analyzer._reduce_test_exprs
            test_op_info = test_op_infos[test_op_info.multiple_op]

        test_args = _TestArgs(
            test_condition.key,
            test_condition.key_index,
            test_op_info.op,
            test_condition.values,
            test_condition.underlying_values,
            test_condition.fact,
            test_op_info.reverse_op,
            test_op_info.number_of_subkeys,
            test_op_info.equals_real_values,
            test_op_info.unequals_real_values,
        )
        self._condition_stack.append(
            self._get_or_new_symbol(
                test_condition.source_location.file_offset,
                _dummy_file_offset,
                test_args,
            )
        )

    def visit_composite_condition(
        self, composite_condition: CompositeCondiction
    ) -> None:
        match composite_condition.logical_op_type:
            case OpType.LOGICAL_NOT:
                composite_condition.condition_1.accept_visit(self)
                self._condition_stack[-1] = boolalg.Not(self._condition_stack[-1])

            case OpType.LOGICAL_OR:
                composite_condition.condition_1.accept_visit(self)
                a = self._condition_stack.pop()
                assert composite_condition.condition_2 is not None
                composite_condition.condition_2.accept_visit(self)
                b = self._condition_stack.pop()

                self._condition_stack.append(
                    boolalg.Or(a, boolalg.And(boolalg.Not(a), b))
                    # use `a or ((not a) and b)` instead of `a or b` to make it easy for _P3Analyzer._reduce_test_exprs
                )

            case OpType.LOGICAL_AND:
                composite_condition.condition_1.accept_visit(self)
                a = self._condition_stack.pop()
                assert composite_condition.condition_2 is not None
                composite_condition.condition_2.accept_visit(self)
                b = self._condition_stack.pop()

                self._condition_stack.append(
                    boolalg.And(a, boolalg.Or(boolalg.Not(a), b))
                    # use `a and ((not a) or b)` instead of `a and b` to make it easy for _P3Analyzer._reduce_test_exprs
                )

            case _:
                assert False


class _P3AndExpr:
    __slots__ = (
        "test_exprs",
        "test_ids",
    )

    def __init__(self, and_expr: AndExpr) -> None:
        self.test_exprs = and_expr.test_exprs
        self.test_ids: set[int] = set()

    def to_and_expr(self) -> AndExpr:
        return AndExpr(self.test_exprs)


class _P3Analyzer:
    __slots__ = (
        "_raw_return_points",
        "_absolute_test_ids",
    )

    def __init__(self, raw_return_points: _P2ReturnPoints) -> None:
        self._raw_return_points = raw_return_points
        self._absolute_test_ids: dict[tuple[str, ...], int] = {}

    def simplify_return_points(self, reduce_return_points: bool) -> list[ReturnPoint]:
        return_points: list[ReturnPoint] = []

        for raw_return_point in self._raw_return_points.file_offset_2_item.values():
            conditions = self._simplify_conditions(raw_return_point.conditions)
            if isinstance(conditions, bool):
                if not conditions:
                    continue

                or_expr = OrExpr([AndExpr([])])
            else:
                or_expr = self._make_or_expr(conditions)

            return_points.append(
                ReturnPoint(
                    or_expr,
                    raw_return_point.file_offset,
                    raw_return_point.transform_list,
                )
            )

        def return_point_rank(return_point: ReturnPoint) -> float:
            if return_point.file_offset == _dummy_file_offset:
                return math.inf
            else:
                return float(return_point.file_offset)

        return_points.sort(key=return_point_rank)
        if reduce_return_points:
            return_points = self._reduce_return_points(return_points)

        return return_points

    def _simplify_conditions(
        self, conditions: list[boolalg.Boolean]
    ) -> bool | list[boolalg.Boolean]:
        if len(conditions) == 0:
            return True

        new_conditions: list[boolalg.Boolean] = []

        for condition in conditions:
            new_condition = boolalg.to_dnf(condition, False, False)
            if new_condition is sympy.true:
                return True
            if new_condition is sympy.false:
                continue

            new_conditions.append(new_condition)

        if len(new_conditions) == 0:
            return False
        return new_conditions

    def _make_or_expr(self, conditions: list[boolalg.Boolean]) -> OrExpr:
        def and_expr_rank(and_expr: AndExpr) -> Iterator[int]:
            for test_expr in and_expr.test_exprs:
                yield test_expr.file_offset_1
                yield test_expr.file_offset_2

        and_exprs: list[AndExpr] = []

        for condition in conditions:
            if condition.func is not boolalg.Or:
                and_exprs.append(self._make_and_expr(condition))
                continue

            and_exprs_2: list[AndExpr] = []
            for condition_2 in condition.args:
                and_exprs_2.append(self._make_and_expr(condition_2))  # type: ignore

            and_exprs_2.sort(key=lambda x: tuple(and_expr_rank(x)))
            and_exprs.extend(and_exprs_2)

        return OrExpr(and_exprs)

    def _make_and_expr(self, condition: boolalg.Boolean) -> AndExpr:
        if condition.func is not boolalg.And:
            return AndExpr([self._make_test_expr(condition)])  # type: ignore

        test_exprs: list[TestExpr] = []
        for condition_2 in condition.args:
            test_exprs.append(self._make_test_expr(condition_2))  # type: ignore

        test_exprs.sort(key=lambda x: (x.file_offset_1, x.file_offset_2))
        return AndExpr(test_exprs)

    def _make_test_expr(self, condition: boolalg.Boolean) -> TestExpr:
        is_positive = True
        if condition.func is boolalg.Not:
            is_positive = False
            condition = condition.args[0]  # type: ignore

        assert condition.func is sympy.Symbol
        symbol_name = condition.name  # type: ignore
        file_offset_1, file_offset_2 = map(int, symbol_name.split(",", 1))
        test_args = self._raw_return_points.file_offsets_2_test_args[
            file_offset_1, file_offset_2
        ]
        test_id = self._make_test_id(is_positive, test_args)
        return TestExpr(
            is_positive,
            file_offset_1,
            file_offset_2,
            test_id,
            test_args.key,
            test_args.key_index,
            test_args.op,
            test_args.values.copy(),  # could be modified
            test_args.underlying_values.copy(),  # could be modified
            test_args.fact,
            test_args.reverse_op,
            test_args.number_of_subkeys,
            test_args.equals_real_values,
            test_args.unequals_real_values,
            [],
        )

    def _make_test_id(self, is_positive: bool, test_args: _TestArgs) -> int:
        if is_positive:
            factor = 1
        else:
            factor = -1

        test_traits = (test_args.op, test_args.key, *test_args.values)
        absolute_test_id = self._absolute_test_ids.get(test_traits)
        if absolute_test_id is None:
            reverse_test_traits = (
                test_args.reverse_op,
                test_args.key,
                *test_args.values,
            )
            absolute_test_id = self._absolute_test_ids.get(reverse_test_traits)
            if absolute_test_id is None:
                absolute_test_id = 1 + len(self._absolute_test_ids)
                self._absolute_test_ids[test_traits] = absolute_test_id
            else:
                factor = -factor

        return factor * absolute_test_id

    def _reduce_return_points(
        self, return_points: list[ReturnPoint]
    ) -> list[ReturnPoint]:
        small_return_point: list[ReturnPoint] = []

        for return_point in return_points:
            or_expr = self._reduce_or_expr(return_point.or_expr)
            if or_expr is None:
                continue

            new_return_point = dataclasses.replace(return_point, or_expr=or_expr)
            small_return_point.append(new_return_point)

        return small_return_point

    def _reduce_or_expr(self, or_expr: OrExpr) -> OrExpr | None:
        and_exprs = self._reduce_and_exprs(or_expr.and_exprs)
        if and_exprs is None:
            return None

        new_or_expr = dataclasses.replace(or_expr, and_exprs=and_exprs)
        return new_or_expr

    def _reduce_and_exprs(self, and_exprs: list[AndExpr]) -> list[AndExpr] | None:
        small_and_exprs = dict(
            map(lambda x: (x[0], _P3AndExpr(x[1])), enumerate(and_exprs))
        )

        for i, and_expr in enumerate(and_exprs):
            test_exprs = self._reduce_test_exprs(and_expr.test_exprs)
            if test_exprs is None:
                small_and_exprs.pop(i)
                continue

            and_expr_2 = small_and_exprs[i]
            and_expr_2.test_exprs = test_exprs
            and_expr_2.test_ids = set(map(lambda x: x.test_id, test_exprs))

        for i in range(len(and_exprs)):
            if i not in small_and_exprs.keys():
                continue
            test_ids_x = small_and_exprs[i].test_ids

            for j in range(len(and_exprs)):
                if j == i or j not in small_and_exprs.keys():
                    continue
                test_ids_y = small_and_exprs[j].test_ids

                if test_ids_x.issubset(test_ids_y):
                    small_and_exprs.pop(j)

        if len(small_and_exprs) == 0:
            return None

        small_and_exprs_2 = list(small_and_exprs.values())
        self._rearrange_and_exprs(small_and_exprs_2)

        for and_expr in small_and_exprs_2:
            and_expr.test_exprs = self._merge_test_exprs(and_expr.test_exprs)

        return list(map(lambda x: x.to_and_expr(), small_and_exprs_2))

    @classmethod
    def _reduce_test_exprs(cls, test_exprs: list[TestExpr]) -> list[TestExpr] | None:
        small_test_exprs = dict(enumerate(test_exprs))

        for i, test_expr_x in enumerate(test_exprs):
            if i not in small_test_exprs.keys():
                continue

            x_real_values = None
            if (test_expr_x.is_positive and test_expr_x.equals_real_values) or (
                not test_expr_x.is_positive and test_expr_x.unequals_real_values
            ):
                x_real_values = set(test_expr_x.real_values())

            for j, test_expr_y in enumerate(test_exprs):
                if j == i or j not in small_test_exprs.keys():
                    continue

                if test_expr_y.test_id == test_expr_x.test_id:
                    # remove duplicate
                    small_test_exprs.pop(j)
                    continue

                if test_expr_y.test_id == -test_expr_x.test_id:
                    # conflict
                    return None

                if (
                    x_real_values is not None
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
                        if x_real_values.issuperset(test_expr_y.real_values()):
                            # `in[a, b, c]` vs `in[a, b]`
                            # remove duplicate
                            small_test_exprs.pop(j)
                            continue
                        elif x_real_values.isdisjoint(test_expr_y.real_values()):
                            # `in[a, b]` vs `in[c]`
                            # conflict
                            return None
                        # `in[a, b]` vs `in[a, c]`
                    else:
                        if x_real_values.issubset(test_expr_y.real_values()):
                            # `in[a, b]` vs `nin[a, b, c]`
                            # conflict
                            return None
                        elif x_real_values.isdisjoint(test_expr_y.real_values()):
                            # `in[a, b]` vs `nin[c]`
                            # remove unused
                            small_test_exprs.pop(j)
                            continue
                        # `in[a, b]` vs `nin[a, c]`

        return list(small_test_exprs.values())

    def _rearrange_and_exprs(self, and_exprs: list[_P3AndExpr]) -> None:
        k = len(self._absolute_test_ids)
        test_id_ref_counts: list[int] = (2 * k + 1) * [0]
        for and_expr in and_exprs:
            n = len(and_expr.test_exprs)
            for i, test_expr in enumerate(and_expr.test_exprs):
                test_id_ref_counts[k + test_expr.test_id] += n - i

        def and_expr_rank(and_expr: _P3AndExpr) -> Iterator[int]:
            for test_expr in and_expr.test_exprs:
                test_id_ref_count = test_id_ref_counts[k + test_expr.test_id]
                yield test_id_ref_count
                yield test_expr.file_offset_1
                yield test_expr.file_offset_2

        and_exprs.sort(key=lambda x: tuple(and_expr_rank(x)))

    @classmethod
    def _merge_test_exprs(cls, test_exprs: list[TestExpr]) -> list[TestExpr]:
        small_test_exprs = dict(enumerate(test_exprs))

        # merge phase 1
        for i, test_expr_x in enumerate(test_exprs):
            if i not in small_test_exprs.keys():
                continue

            if (test_expr_x.is_positive and test_expr_x.equals_real_values) or (
                not test_expr_x.is_positive and test_expr_x.unequals_real_values
            ):
                for j, test_expr_y in enumerate(test_exprs):
                    if j == i or j not in small_test_exprs.keys():
                        continue

                    if test_expr_y.op in (
                        test_expr_x.op,
                        test_expr_x.reverse_op,
                    ) and tuple(test_expr_y.virtual_key()) == tuple(
                        test_expr_x.virtual_key()
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
                            # merge `in[a, c]` into `in[a, b]`
                            test_expr_x.values.extend(test_expr_y.real_values())
                            test_expr_x.underlying_values.extend(
                                test_expr_y.real_underlying_values()
                            )
                        else:
                            # merge `nin[a, c]` into `in[a, b]`
                            cls._remove_real_values(
                                test_expr_x, set(test_expr_y.real_values())
                            )

                        test_expr_x.children.append(test_expr_y)
                        small_test_exprs.pop(j)

        # merge phase 2
        for i, test_expr_x in enumerate(test_exprs):
            if i not in small_test_exprs.keys():
                continue

            if (not test_expr_x.is_positive and test_expr_x.equals_real_values) or (
                test_expr_x.is_positive and test_expr_x.unequals_real_values
            ):
                for j, test_expr_y in enumerate(test_exprs):
                    if j == i or j not in small_test_exprs.keys():
                        continue

                    if (test_expr_y.is_positive, test_expr_y.op) in (
                        (
                            test_expr_x.is_positive,
                            test_expr_x.op,
                        ),
                        (
                            not test_expr_x.is_positive,
                            test_expr_x.reverse_op,
                        ),
                    ) and tuple(test_expr_y.virtual_key()) == tuple(
                        test_expr_x.virtual_key()
                    ):
                        # merge `nin[a, c]` into `nin[a, b]`
                        test_expr_x.values.extend(test_expr_y.real_values())
                        test_expr_x.underlying_values.extend(
                            test_expr_y.real_underlying_values()
                        )
                        test_expr_x.children.append(test_expr_y)
                        small_test_exprs.pop(j)

        # merge phase 3
        for i, test_expr in small_test_exprs.items():
            if test_expr.number_of_real_values() == 1:
                single_test_op = test_op_infos[test_expr.op].single_op
                if single_test_op is not None:
                    # multiple_op => single_op
                    small_test_exprs[i] = dataclasses.replace(
                        test_expr,
                        op=single_test_op,
                        reverse_op=test_op_infos[single_test_op].reverse_op,
                    )

        return list(small_test_exprs.values())

    @classmethod
    def _remove_real_values(cls, test_expr: TestExpr, target_values: set[str]) -> None:
        i = test_expr.number_of_subkeys
        for j in range(test_expr.number_of_subkeys, len(test_expr.values)):
            if test_expr.values[j] in target_values:
                continue

            test_expr.values[i] = test_expr.values[j]
            test_expr.underlying_values[i] = test_expr.underlying_values[j]
            i += 1

        del test_expr.values[i:]
        del test_expr.underlying_values[i:]


class _P4Analyzer(Visitor):
    __slots__ = (
        "_unit_declaration",
        "_return_point_file_offsets",
    )

    def __init__(
        self,
        unit_declaration: UnitDeclaration,
        return_points: list[ReturnPoint],
        default_return_point_file_offsets: set[int],
    ) -> None:
        self._unit_declaration = unit_declaration
        self._return_point_file_offsets: set[int] = set()
        for return_point in return_points:
            if return_point.file_offset >= 0:
                self._return_point_file_offsets.add(return_point.file_offset)
        self._return_point_file_offsets.update(default_return_point_file_offsets)

    def check_return_statements(self) -> None:
        for statement in self._unit_declaration.program:
            statement.accept_visit(self)

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        for statement in if_statement.body:
            statement.accept_visit(self)

        for else_if_clause in if_statement.else_if_clauses:
            for statement in else_if_clause.body:
                statement.accept_visit(self)

        for statement in if_statement.else_clause.body:
            statement.accept_visit(self)

    def visit_switch_statement(self, switch_statement: SwitchStatement) -> None:
        for case_clause in switch_statement.case_clauses:
            for statement in case_clause.body:
                statement.accept_visit(self)

        for statement in switch_statement.default_case_clause.body:
            statement.accept_visit(self)

    def visit_return_statement(self, return_statement: ReturnStatement) -> None:
        if (
            return_statement.source_location.file_offset
            not in self._return_point_file_offsets
        ):
            raise UnreachableReturnStatementError(return_statement.source_location)


_dummy_file_offset = -1


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        super().__init__(
            f"{source_location.file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )


class DuplicateCaseValueError(Error):
    def __init__(self, case_value: CaseValue) -> None:
        super().__init__(
            case_value.source_location,
            f"duplicate case value: {repr(case_value.value)}",
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


class InsufficientTestOpValuesError(Error):
    def __init__(
        self, source_location: SourceLocation, test_op_info: TestOpInfo
    ) -> None:
        super().__init__(
            source_location,
            f"test operation {repr(test_op_info.op)} requires at least {test_op_info.min_number_of_values} values",
        )


class TooManyTestOpValuesError(Error):
    def __init__(
        self, source_location: SourceLocation, test_op_info: TestOpInfo
    ) -> None:
        super().__init__(
            source_location,
            f"test operation {repr(test_op_info.op)} accepts at most {test_op_info.max_number_of_values} values",
        )


class UnreachableReturnStatementError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "unreachable return statement")
