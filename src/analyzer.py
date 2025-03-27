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
    file_offset: int
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str


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
    symbol_name_2_test_args: dict[str, "_TestArgs"]


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


class _P2Analyzer(Visitor):
    __slots__ = (
        "_program_link",
        "_symbols",
        "_condiction_stack",
        "_return_points",
    )

    def __init__(self, program_link: Statement) -> None:
        self._program_link = program_link
        self._symbols: dict[str, sympy.Symbol] = {}
        self._condiction_stack: list[boolalg.Boolean] = []
        self._return_points = _P2ReturnPoints({}, {})

    def get_return_points(self) -> _P2ReturnPoints:
        if self._program_link is not None:
            self._program_link.accept_visit(self)

        return self._return_points

    def _get_or_new_symbol(self, test_args: _TestArgs) -> sympy.Symbol:
        symbol_name = json.dumps(
            [test_args.key, test_args.op, *test_args.values], ensure_ascii=False
        )
        symbol = self._symbols.get(symbol_name)
        if symbol is None:
            symbol = sympy.Symbol(symbol_name)
            self._symbols[symbol_name] = symbol
            self._return_points.symbol_name_2_test_args[symbol_name] = test_args
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

                test_args = _TestArgs(
                    switch_statement.source_location.file_offset,
                    switch_statement.key,
                    switch_statement.key_index,
                    "eq",
                    [case_value],
                    [case_value],
                    fact,
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
        test_args = _TestArgs(
            test_condiction.source_location.file_offset,
            test_condiction.key,
            test_condiction.key_index,
            test_condiction.op,
            test_condiction.values,
            test_condiction.underlying_values,
            test_condiction.fact,
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
        return boolalg.to_dnf(condiction, True, True)

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
        symbol_name = condiction.name  # type: ignore
        test_args = self._raw_return_points.symbol_name_2_test_args[symbol_name]
        return TestExpr(
            is_positive,
            test_args.file_offset,
            test_args.key,
            test_args.key_index,
            test_args.op,
            test_args.values,
            test_args.underlying_values,
            test_args.fact,
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

            small_return_point.append(
                dataclasses.replace(return_point, or_expr=or_expr)
            )

        return small_return_point

    @classmethod
    def _reduce_or_expr(cls, or_expr: OrExpr) -> OrExpr | None:
        and_exprs = cls._reduce_and_exprs(or_expr.and_exprs)
        if and_exprs is None:
            return None

        return dataclasses.replace(or_expr, and_exprs=and_exprs)

    @classmethod
    def _reduce_and_exprs(cls, and_exprs: list[AndExpr]) -> list[AndExpr] | None:
        small_and_exprs: list[AndExpr] = []

        for and_expr in and_exprs:
            test_exprs = cls._reduce_test_exprs(and_expr.test_exprs)
            if test_exprs is None:
                continue

            small_and_exprs.append(dataclasses.replace(and_expr, test_exprs=test_exprs))

        if len(small_and_exprs) == 0:
            return None

        return small_and_exprs

    @classmethod
    def _reduce_test_exprs(cls, test_exprs: list[TestExpr]) -> list[TestExpr] | None:
        small_test_exprs = dict(enumerate(test_exprs))

        for test_expr_x in test_exprs:
            if not (test_expr_x.is_positive, test_expr_x.op) == (True, "eq"):
                continue

            for i, test_expr_y in enumerate(test_exprs):
                if test_expr_y is not test_expr_x and (
                    test_expr_y.key,
                    test_expr_y.op,
                ) == (
                    test_expr_x.key,
                    "eq",
                ):
                    assert test_expr_y.values != test_expr_x.values

                    if test_expr_y.is_positive:
                        # conflict
                        return None

                    small_test_exprs.pop(i)

        return list(small_test_exprs.values())


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
