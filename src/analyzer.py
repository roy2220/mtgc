import dataclasses
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
    file_offset: int
    symbol_value_id: int
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
        for i in range(self.number_of_real_values()):
            yield self.values[self.number_of_subkeys + i]

    def real_underlying_values(self) -> Iterator[str]:
        for i in range(self.number_of_real_values()):
            yield self.underlying_values[self.number_of_subkeys + i]


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
        return_points = p3_analyzer.simplify_return_points(self._reduce_return_points)
        _P4Analyzer(unit_declaration, return_points).check_return_statements()
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
    file_offset_2_item: dict[int, "_P2ReturnPoint"]
    symbol_id_2_test_args: dict[str, "_TestArgs"]


@dataclass
class _P2ReturnPoint:
    file_offset: int
    transform_list: list[Transform]
    condiction: boolalg.Boolean


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
        "_symbol_value_ids",
        "_symbols",
        "_condiction_stack",
        "_return_points",
    )

    def __init__(self, program_link: Statement) -> None:
        self._program_link = program_link
        self._symbol_value_ids: dict[tuple[str, ...], int] = {}
        self._symbols: dict[str, sympy.Symbol] = {}
        self._condiction_stack: list[boolalg.Boolean] = []
        self._return_points = _P2ReturnPoints({}, {})

    def get_return_points(self) -> _P2ReturnPoints:
        if self._program_link is not None:
            self._program_link.accept_visit(self)

        return self._return_points

    def _get_or_new_symbol(
        self, file_offset: int, test_args: _TestArgs
    ) -> sympy.Symbol:
        symbol_value = (test_args.op, test_args.key, *test_args.values)
        symbol_value_id = self._symbol_value_ids.get(symbol_value)
        if symbol_value_id is None:
            reverse_symbol_value = (
                test_args.reverse_op,
                test_args.key,
                *test_args.values,
            )
            symbol_value_id = self._symbol_value_ids.get(reverse_symbol_value)
            if symbol_value_id is None:
                symbol_value_id = 1 + len(self._symbol_value_ids)
                self._symbol_value_ids[symbol_value] = symbol_value_id

        symbol_id = f"{file_offset}-{symbol_value_id}"
        symbol = self._symbols.get(symbol_id)
        if symbol is None:
            symbol = sympy.Symbol(symbol_id)
            self._symbols[symbol_id] = symbol
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
                return_statement.transform_list,
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

                test_op_info = test_op_infos["in"]
                test_args = _TestArgs(
                    switch_statement.key,
                    switch_statement.key_index,
                    test_op_info.op,
                    [case_value],
                    [case_value],
                    fact,
                    test_op_info.reverse_op,
                    test_op_info.number_of_subkeys,
                    test_op_info.equals_real_values,
                    test_op_info.unequals_real_values,
                )
                if condiction is None:
                    condiction = self._get_or_new_symbol(
                        case_clause.source_location.file_offset, test_args
                    )
                else:
                    condiction = boolalg.Or(
                        condiction,
                        self._get_or_new_symbol(
                            case_clause.source_location.file_offset, test_args
                        ),
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
        test_op_info = test_op_infos.get(test_condiction.op)
        if test_op_info is None:
            raise UnknownTestOpError(
                test_condiction.source_location, test_condiction.op
            )

        if len(test_condiction.values) < test_op_info.min_number_of_values:
            raise InsufficientTestOpValuesError(
                test_condiction.source_location, test_op_info
            )

        if (n := test_op_info.max_number_of_values) is not None and len(
            test_condiction.values
        ) > n:
            raise TooManyTestOpValuesError(
                test_condiction.source_location, test_op_info
            )

        if test_op_info.multiple_op is not None:
            # multiple_op is easy for _P3Analyzer._reduce_test_exprs
            test_op_info = test_op_infos[test_op_info.multiple_op]

        test_args = _TestArgs(
            test_condiction.key,
            test_condiction.key_index,
            test_op_info.op,
            test_condiction.values,
            test_condiction.underlying_values,
            test_condiction.fact,
            test_op_info.reverse_op,
            test_op_info.number_of_subkeys,
            test_op_info.equals_real_values,
            test_op_info.unequals_real_values,
        )
        self._condiction_stack.append(
            self._get_or_new_symbol(
                test_condiction.source_location.file_offset, test_args
            )
        )

    def visit_composite_condiction(
        self, composite_condiction: CompositeCondiction
    ) -> None:
        match composite_condiction.logical_op_type:
            case OpType.LOGICAL_NOT:
                composite_condiction.condiction1.accept_visit(self)
                self._condiction_stack[-1] = boolalg.Not(self._condiction_stack[-1])

            case OpType.LOGICAL_OR:
                composite_condiction.condiction1.accept_visit(self)
                a = self._condiction_stack.pop()
                assert composite_condiction.condiction2 is not None
                composite_condiction.condiction2.accept_visit(self)
                b = self._condiction_stack.pop()

                self._condiction_stack.append(
                    boolalg.Or(a, boolalg.And(boolalg.Not(a), b))
                    # use `a or ((not a) and b)` instead of `a or b` to make it easy for _P3Analyzer._reduce_test_exprs
                )

            case OpType.LOGICAL_AND:
                composite_condiction.condiction1.accept_visit(self)
                a = self._condiction_stack.pop()
                assert composite_condiction.condiction2 is not None
                composite_condiction.condiction2.accept_visit(self)
                b = self._condiction_stack.pop()

                self._condiction_stack.append(
                    boolalg.And(a, boolalg.Or(boolalg.Not(a), b))
                    # use `a and ((not a) or b)` instead of `a and b` to make it easy for _P3Analyzer._reduce_test_exprs
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
                    raw_return_point.transform_list,
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
        symbol_id = condiction.name  # type: ignore
        file_offset, symbol_value_id = map(int, symbol_id.split("-", 1))
        test_args = self._raw_return_points.symbol_id_2_test_args[symbol_id]
        return TestExpr(
            is_positive,
            file_offset,
            symbol_value_id,
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
        test_expr_key_sets: dict[int, set[int]] = {}
        small_and_exprs: dict[int, AndExpr] = {}

        for i, and_expr in enumerate(and_exprs):
            test_exprs = cls._reduce_test_exprs(and_expr.test_exprs)
            if test_exprs is None:
                continue

            test_expr_key_sets[i] = set(cls._make_test_expr_keys(test_exprs))
            test_exprs = cls._merge_test_exprs(test_exprs)
            small_and_exprs[i] = dataclasses.replace(and_expr, test_exprs=test_exprs)

        for i in range(0, len(and_exprs)):
            if i not in test_expr_key_sets.keys():
                continue

            for j in range(0, len(and_exprs)):
                if j == i or j not in test_expr_key_sets.keys():
                    continue

                if test_expr_key_sets[i].issubset(test_expr_key_sets[j]):
                    test_expr_key_sets.pop(j)
                    small_and_exprs.pop(j)

        if len(small_and_exprs) == 0:
            return None

        return list(small_and_exprs.values())

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

                if test_expr_y.symbol_value_id == test_expr_x.symbol_value_id:
                    if test_expr_y.is_positive == test_expr_x.is_positive:
                        # remove duplicate
                        small_test_exprs.pop(j)
                        continue
                    else:
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

    @classmethod
    def _make_test_expr_keys(cls, test_exprs: list[TestExpr]) -> Iterator[int]:
        for test_expr in test_exprs:
            if test_expr.is_positive:
                yield test_expr.symbol_value_id
            else:
                yield -test_expr.symbol_value_id

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
        self, unit_declaration: UnitDeclaration, return_points: list[ReturnPoint]
    ) -> None:
        self._unit_declaration = unit_declaration
        self._return_point_file_offsets: set[int] = set()
        for return_point in return_points:
            self._return_point_file_offsets.add(return_point.file_offset)

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
