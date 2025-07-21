import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import sympy
from sympy.logic import boolalg

from .parser import (
    BundleDeclaration,
    CaseValue,
    ComponentDeclaration,
    CompositeCondiction,
    ConstantCondiction,
    GotoStatement,
    IfStatement,
    Label,
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


@dataclass(kw_only=True)
class Component:
    source_location: SourceLocation
    name: str
    alias: str
    bundles: list["Bundle"]
    line_directives: dict[int, list[str]]


@dataclass(kw_only=True)
class Bundle:
    source_location: SourceLocation
    name: str
    units: list["Unit"]


@dataclass(kw_only=True)
class Unit:
    source_location: SourceLocation
    name: str
    alias: str
    return_points: list["ReturnPoint"]


@dataclass(kw_only=True)
class ReturnPoint:
    source_location: SourceLocation
    or_expr: "OrExpr"
    transform_list: list[Transform]


@dataclass(kw_only=True)
class OrExpr:
    and_exprs: list["AndExpr"]


@dataclass(kw_only=True)
class AndExpr:
    test_exprs: list["TestExpr"]
    index: int

    # for debugging
    trailing_trace_point_id: int | None = None


@dataclass(kw_only=True)
class TestExpr:
    test_id: int
    source_location: SourceLocation
    is_negative: bool
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str
    reverse_op: str
    is_dismissed: bool
    is_merged: bool
    merged_children: list["TestExpr"]

    # for debugging
    trace_point_id: int | None = None


class Analyzer:
    __slots__ = (
        "_component_declaration",
        "_optimization_level",
    )

    def __init__(
        self,
        component_declaration: ComponentDeclaration,
        optimization_level: int = 2,
    ) -> None:
        self._component_declaration = component_declaration
        self._optimization_level = optimization_level

    def get_component(self) -> Component:
        return Component(
            source_location=self._component_declaration.source_location,
            name=self._component_declaration.name,
            alias=self._component_declaration.alias,
            bundles=self._get_bundles(),
            line_directives=self._component_declaration.line_directives,
        )

    def _get_bundles(self) -> list[Bundle]:
        bundles: list[Bundle] = []
        bundle_names: set[str] = set()

        for bundle_declaration in self._component_declaration.bundles:
            if bundle_declaration.name in bundle_names:
                raise DuplicateBundleNameError(bundle_declaration)
            bundle_names.add(bundle_declaration.name)

            bundles.append(
                Bundle(
                    source_location=bundle_declaration.source_location,
                    name=bundle_declaration.name,
                    units=self._get_units(bundle_declaration.units),
                )
            )

        return bundles

    def _get_units(self, unit_declarations: list[UnitDeclaration]) -> list[Unit]:
        units: list[Unit] = []
        unit_names: set[str] = set()

        for unit_declaration in unit_declarations:
            if unit_declaration.name in unit_names:
                raise DuplicateUnitNameError(unit_declaration)
            unit_names.add(unit_declaration.name)

            units.append(
                Unit(
                    source_location=unit_declaration.source_location,
                    name=unit_declaration.name,
                    alias=unit_declaration.alias,
                    return_points=self._get_return_points(unit_declaration),
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
        p2_return_points = p2_analyzer.get_return_points()
        p3_analyzer = _P3Analyzer(p2_return_points)
        p3_return_points = p3_analyzer.simplify_return_points(self._optimization_level)
        _P4Analyzer(
            unit_declaration,
            p3_return_points,
            p2_return_points.default_return_point_file_offsets,
        ).check_return_statements()
        return [x.to_return_point() for x in p3_return_points]


class _P1Analyzer(Visitor):
    __slots__ = (
        "_unit_declaration",
        "_link_setter_stack",
        "_labeled_return_statements",
        "_goto_statements",
    )

    def __init__(self, unit_declaration: UnitDeclaration) -> None:
        self._unit_declaration = unit_declaration
        self._link_setter_stack: list[Callable[[Statement], None]] = []
        self._labeled_return_statements: dict[str, ReturnStatement] = {}
        self._goto_statements: list[GotoStatement] = []

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

        for goto_statement in self._goto_statements:
            return_statement = self._labeled_return_statements.get(
                goto_statement.label_name
            )
            if return_statement is None:
                raise UndefinedLabelError(goto_statement)
            goto_statement.return_statement = return_statement

        return program_link

    def _visit_block(self, statements: list[Statement]) -> None:
        first_link_setter_index = len(self._link_setter_stack) - 1

        for i, statement in enumerate(statements):
            for link_setter in self._link_setter_stack[first_link_setter_index:]:
                link_setter(statement)
            del self._link_setter_stack[first_link_setter_index:]

            if isinstance(statement, ReturnStatement):
                self._add_labeled_return_statement(statement)
                for statement in statements[i + 1 :]:
                    if isinstance(statement, ReturnStatement):
                        self._add_labeled_return_statement(statement)
                return

            if isinstance(statement, GotoStatement):
                self._goto_statements.append(statement)
                return

            statement.accept_visit(self)

    def _add_labeled_return_statement(self, return_statement: ReturnStatement) -> None:
        label = return_statement.label
        if label is None:
            return
        if label.name in self._labeled_return_statements.keys():
            raise DuplicateLabelNameError(label)
        self._labeled_return_statements[label.name] = return_statement

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        def set_link_1(s: Statement) -> None:
            if_statement.body_link = s

        self._link_setter_stack.append(set_link_1)
        self._visit_block(if_statement.body)

        for else_if_clause in if_statement.else_if_clauses:

            def set_link_2(s: Statement, else_if_clause=else_if_clause) -> None:
                else_if_clause.body_link = s

            self._link_setter_stack.append(set_link_2)
            self._visit_block(else_if_clause.body)

        def set_link_3(s: Statement) -> None:
            if_statement.else_clause.body_link = s

        self._link_setter_stack.append(set_link_3)
        self._visit_block(if_statement.else_clause.body)

    def visit_switch_statement(self, switch_statement: SwitchStatement) -> None:
        for case_clause in switch_statement.case_clauses:

            def set_link_1(s: Statement, case_clause=case_clause) -> None:
                case_clause.body_link = s

            self._link_setter_stack.append(set_link_1)
            self._visit_block(case_clause.body)

        def set_link_2(s: Statement) -> None:
            switch_statement.default_case_clause.body_link = s

        self._link_setter_stack.append(set_link_2)
        self._visit_block(switch_statement.default_case_clause.body)


@dataclass(kw_only=True)
class _P2ReturnPoints:
    default_transform_list: list[Transform]
    default_return_point_file_offsets: set[int]
    file_offset_2_item: dict[int, "_P2ReturnPoint"]
    file_offsets_2_test_args: dict[tuple[int, int], "_TestArgs"]


@dataclass(kw_only=True)
class _P2ReturnPoint:
    source_location: SourceLocation
    file_offset: int
    transform_list: list[Transform]
    conditions: list[boolalg.Boolean]


@dataclass(kw_only=True)
class _TestArgs:
    source_location: SourceLocation
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
        self._return_points = _P2ReturnPoints(
            default_transform_list=default_transform_list,
            default_return_point_file_offsets=set(),
            file_offset_2_item={},
            file_offsets_2_test_args={},
        )

    def get_return_points(self) -> _P2ReturnPoints:
        if self._program_link is not None:
            self._program_link.accept_visit(self)

        return self._return_points

    def _get_or_new_symbol(
        self, file_offsets: tuple[int, int], test_args: _TestArgs
    ) -> sympy.Symbol:
        symbol_name = f"{file_offsets[0]},{file_offsets[1]}"
        symbol = self._symbols.get(symbol_name)
        if symbol is None:
            symbol = sympy.Symbol(symbol_name)
            self._symbols[symbol_name] = symbol
            self._return_points.file_offsets_2_test_args[file_offsets] = test_args
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
                source_location=return_statement.source_location,
                file_offset=file_offset,
                transform_list=transform_list,
                conditions=[],
            )
            self._return_points.file_offset_2_item[file_offset] = return_point
        return_point.conditions.append(condition)

    def visit_goto_statement(self, goto_statement: GotoStatement) -> None:
        s = goto_statement.return_statement
        assert s is not None
        s.accept_visit(self)

    def visit_if_statement(self, if_statement: IfStatement) -> None:
        if_statement.condition.accept_visit(self)

        s = if_statement.body_link
        assert s is not None
        s.accept_visit(self)

        other_condition = boolalg.Not(self._condition_stack.pop())

        for else_if_clause in if_statement.else_if_clauses:
            else_if_clause.condition.accept_visit(self)

            self._condition_stack[-1] = boolalg.And(
                other_condition, self._condition_stack[-1]
            )

            s = else_if_clause.body_link
            assert s is not None
            s.accept_visit(self)

            other_condition = boolalg.And(
                other_condition, boolalg.Not(self._condition_stack.pop())
            )

        self._condition_stack.append(other_condition)

        s = if_statement.else_clause.body_link
        assert s is not None
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
                    source_location=case_value.source_location,
                    key=switch_statement.key,
                    key_index=switch_statement.key_index,
                    op=test_op_info.op,
                    values=[case_value.value],
                    underlying_values=[case_value.value],
                    fact=case_value.fact,
                    reverse_op=test_op_info.reverse_op,
                    number_of_subkeys=test_op_info.number_of_subkeys,
                    equals_real_values=test_op_info.equals_real_values,
                    unequals_real_values=test_op_info.unequals_real_values,
                )
                if condition is None:
                    condition = self._get_or_new_symbol(
                        (
                            switch_statement.source_location.file_offset,
                            case_value.source_location.file_offset,
                        ),
                        test_args,
                    )
                else:
                    condition = boolalg.Or(
                        condition,
                        self._get_or_new_symbol(
                            (
                                switch_statement.source_location.file_offset,
                                case_value.source_location.file_offset,
                            ),
                            test_args,
                        ),
                    )
            assert condition is not None
            self._condition_stack.append(condition)

            s = case_clause.body_link
            assert s is not None
            s.accept_visit(self)

            del self._condition_stack[-1]

            if other_condition is None:
                other_condition = boolalg.Not(condition)
            else:
                other_condition = boolalg.And(other_condition, boolalg.Not(condition))

        assert other_condition is not None
        self._condition_stack.append(other_condition)

        s = switch_statement.default_case_clause.body_link
        assert s is not None
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
            # multiple_op is easy for _P3Analyzer._reduce_test_exprs()
            test_op_info = test_op_infos[test_op_info.multiple_op]

        test_args = _TestArgs(
            source_location=test_condition.source_location,
            key=test_condition.key,
            key_index=test_condition.key_index,
            op=test_op_info.op,
            values=test_condition.values,
            underlying_values=test_condition.underlying_values,
            fact=test_condition.fact,
            reverse_op=test_op_info.reverse_op,
            number_of_subkeys=test_op_info.number_of_subkeys,
            equals_real_values=test_op_info.equals_real_values,
            unequals_real_values=test_op_info.unequals_real_values,
        )
        self._condition_stack.append(
            self._get_or_new_symbol(
                (test_condition.source_location.file_offset, _dummy_file_offset),
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
                    # use `a or ((not a) and b)` instead of `a or b` to make it easy for _P3Analyzer._reduce_test_exprs()
                )

            case OpType.LOGICAL_AND:
                composite_condition.condition_1.accept_visit(self)
                a = self._condition_stack.pop()
                assert composite_condition.condition_2 is not None
                composite_condition.condition_2.accept_visit(self)
                b = self._condition_stack.pop()

                self._condition_stack.append(
                    boolalg.And(a, boolalg.Or(boolalg.Not(a), b))
                    # use `a and ((not a) or b)` instead of `a and b` to make it easy for _P3Analyzer._reduce_test_exprs()
                )

            case _:
                assert False


@dataclass(kw_only=True)
class _P3ReturnPoint:
    source_location: SourceLocation
    or_expr: "_P3OrExpr"
    transform_list: list[Transform]

    file_offset: int

    def to_return_point(self) -> ReturnPoint:
        return ReturnPoint(
            source_location=self.source_location,
            or_expr=self.or_expr.to_or_expr(),
            transform_list=self.transform_list,
        )


@dataclass(kw_only=True)
class _P3OrExpr:
    and_exprs: list["_P3AndExpr"]

    def to_or_expr(self) -> OrExpr:
        return OrExpr(and_exprs=[x.to_and_expr() for x in self.and_exprs])


@dataclass(kw_only=True)
class _P3AndExpr:
    test_exprs: list["_P3TestExpr"]
    index: int

    test_ids: set[int]
    rank: list[int]

    def to_and_expr(self) -> AndExpr:
        return AndExpr(
            test_exprs=[x.to_test_expr() for x in self.test_exprs], index=self.index
        )


@dataclass(kw_only=True)
class _P3TestExpr:
    test_id: int
    source_location: SourceLocation
    is_negative: bool
    key: str
    key_index: int
    op: str
    values: list[str]
    underlying_values: list[str]
    fact: str
    reverse_op: str
    is_merged: bool
    is_dismissed: bool
    merged_children: list["_P3TestExpr"]

    file_offsets: tuple[int, int]
    number_of_subkeys: int
    equals_real_values: bool
    unequals_real_values: bool

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

    def to_test_expr(self) -> TestExpr:
        return TestExpr(
            test_id=self.test_id,
            source_location=self.source_location,
            is_negative=self.is_negative,
            key=self.key,
            key_index=self.key_index,
            op=self.op,
            values=self.values,
            underlying_values=self.underlying_values,
            fact=self.fact,
            reverse_op=self.reverse_op,
            is_dismissed=self.is_dismissed,
            is_merged=self.is_merged,
            merged_children=[x.to_test_expr() for x in self.merged_children],
        )


class _P3Analyzer:
    __slots__ = (
        "_raw_return_points",
        "_absolute_test_ids",
    )

    def __init__(self, raw_return_points: _P2ReturnPoints) -> None:
        self._raw_return_points = raw_return_points
        self._absolute_test_ids: dict[tuple[str, ...], int] = {}

    def simplify_return_points(self, optimization_level: int) -> list[_P3ReturnPoint]:
        return_points = self._make_return_points()

        if optimization_level >= 1:
            return_points = self._reduce_return_points(return_points)

        all_and_exprs = self._arrange_all_and_exprs(return_points)

        if optimization_level >= 2:
            self._dismiss_redundant_and_exprs(all_and_exprs)

        if optimization_level >= 1:
            self._merge_test_exprs(return_points)

        return return_points

    def _make_return_points(self) -> list[_P3ReturnPoint]:
        def return_point_rank(return_point: _P3ReturnPoint) -> float:
            if return_point.file_offset == _dummy_file_offset:
                return math.inf
            else:
                return float(return_point.file_offset)

        return_points: list[_P3ReturnPoint] = []

        for raw_return_point in self._raw_return_points.file_offset_2_item.values():
            conditions = self._expand_conditions(raw_return_point.conditions)
            if isinstance(conditions, bool):
                if not conditions:
                    continue

                or_expr = _P3OrExpr(
                    and_exprs=[
                        _P3AndExpr(test_exprs=[], index=-1, test_ids=set(), rank=[])
                    ]
                )
            else:
                or_expr = self._make_or_expr(conditions)

            return_points.append(
                _P3ReturnPoint(
                    source_location=raw_return_point.source_location,
                    or_expr=or_expr,
                    transform_list=raw_return_point.transform_list,
                    file_offset=raw_return_point.file_offset,
                )
            )

        return_points.sort(key=return_point_rank)
        return return_points

    def _expand_conditions(
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

    def _make_or_expr(self, conditions: list[boolalg.Boolean]) -> _P3OrExpr:
        def and_expr_rank(and_expr: _P3AndExpr) -> Iterator[int]:
            for test_expr in and_expr.test_exprs:
                yield test_expr.file_offsets[0]
                yield test_expr.file_offsets[1]

        or_expr = _P3OrExpr(and_exprs=[])

        for condition in conditions:
            if condition.func is not boolalg.Or:
                or_expr.and_exprs.append(self._make_and_expr(condition))
                continue

            and_exprs_2: list[_P3AndExpr] = []
            for condition_2 in condition.args:
                and_exprs_2.append(self._make_and_expr(condition_2))  # type: ignore

            and_exprs_2.sort(key=lambda x: tuple(and_expr_rank(x)))
            or_expr.and_exprs.extend(and_exprs_2)

        return or_expr

    def _make_and_expr(self, condition: boolalg.Boolean) -> _P3AndExpr:
        and_expr = _P3AndExpr(test_exprs=[], index=-1, test_ids=set(), rank=[])

        if condition.func is not boolalg.And:
            and_expr.test_exprs.append(self._make_test_expr(condition))
            return and_expr

        for condition_2 in condition.args:
            and_expr.test_exprs.append(self._make_test_expr(condition_2))  # type: ignore

        and_expr.test_exprs.sort(key=lambda x: x.file_offsets)
        return and_expr

    def _make_test_expr(self, condition: boolalg.Boolean) -> _P3TestExpr:
        condition_is_negative = False
        if condition.func is boolalg.Not:
            condition_is_negative = True
            condition = condition.args[0]  # type: ignore

        assert condition.func is sympy.Symbol
        symbol_name = condition.name  # type: ignore
        file_offset_1, file_offset_2 = map(int, symbol_name.split(",", 1))
        test_args = self._raw_return_points.file_offsets_2_test_args[
            file_offset_1, file_offset_2
        ]

        return _P3TestExpr(
            test_id=self._make_test_id(condition_is_negative, test_args),
            source_location=test_args.source_location,
            is_negative=condition_is_negative,
            key=test_args.key,
            key_index=test_args.key_index,
            op=test_args.op,
            values=test_args.values.copy(),
            underlying_values=test_args.underlying_values.copy(),
            fact=test_args.fact,
            reverse_op=test_args.reverse_op,
            is_merged=False,
            is_dismissed=False,
            merged_children=[],
            file_offsets=(file_offset_1, file_offset_2),
            number_of_subkeys=test_args.number_of_subkeys,
            equals_real_values=test_args.equals_real_values,
            unequals_real_values=test_args.unequals_real_values,
        )

    def _make_test_id(self, condition_is_negative: bool, test_args: _TestArgs) -> int:
        if condition_is_negative:
            factor = -1
        else:
            factor = 1

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

    @classmethod
    def _reduce_return_points(
        cls, return_points: list[_P3ReturnPoint]
    ) -> list[_P3ReturnPoint]:
        return_point_indexes = list(range(len(return_points)))

        for i, return_point in enumerate(return_points):
            or_expr = cls._reduce_or_expr(return_point.or_expr)
            if or_expr is None:
                return_point_indexes[i] = -1
                continue

            return_point.or_expr = or_expr

        return list(
            map(
                lambda x: return_points[x],
                filter(lambda x: x != -1, return_point_indexes),
            )
        )

    @classmethod
    def _reduce_or_expr(cls, or_expr: _P3OrExpr) -> _P3OrExpr | None:
        and_exprs = cls._reduce_and_exprs(or_expr.and_exprs)
        if and_exprs is None:
            return None

        or_expr.and_exprs = and_exprs
        return or_expr

    @classmethod
    def _reduce_and_exprs(cls, and_exprs: list[_P3AndExpr]) -> list[_P3AndExpr] | None:
        and_expr_indexes = list(range(len(and_exprs)))

        for i, and_expr in enumerate(and_exprs):
            test_exprs = cls._reduce_test_exprs(and_expr.test_exprs)
            if test_exprs is None:
                and_expr_indexes[i] = -1
                continue

            and_expr.test_exprs = test_exprs
            and_expr.test_ids = set(map(lambda x: x.test_id, test_exprs))

        for i, and_expr_x in enumerate(and_exprs):
            if and_expr_indexes[i] == -1:
                continue

            for j, and_expr_y in enumerate(and_exprs):
                if j == i or and_expr_indexes[j] == -1:
                    continue

                if and_expr_x.test_ids.issubset(and_expr_y.test_ids):
                    and_expr_indexes[j] = -1

        new_and_exprs = list(
            map(lambda x: and_exprs[x], filter(lambda x: x != -1, and_expr_indexes))
        )
        if len(new_and_exprs) == 0:
            return None
        return new_and_exprs

    @classmethod
    def _reduce_test_exprs(
        cls, test_exprs: list[_P3TestExpr]
    ) -> list[_P3TestExpr] | None:
        test_expr_indexes = list(range(len(test_exprs)))

        for i, test_expr_x in enumerate(test_exprs):
            if test_expr_indexes[i] == -1:
                continue

            x_real_values = None
            if (not test_expr_x.is_negative and test_expr_x.equals_real_values) or (
                test_expr_x.is_negative and test_expr_x.unequals_real_values
            ):
                x_real_values = set(test_expr_x.real_values())

            for j, test_expr_y in enumerate(test_exprs):
                if j == i or test_expr_indexes[j] == -1:
                    continue

                if test_expr_y.test_id == test_expr_x.test_id:
                    # remove duplicate
                    test_expr_indexes[j] = -1
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
                    if (test_expr_y.is_negative, test_expr_y.op) in (
                        (
                            test_expr_x.is_negative,
                            test_expr_x.op,
                        ),
                        (
                            not test_expr_x.is_negative,
                            test_expr_x.reverse_op,
                        ),
                    ):
                        if x_real_values.issubset(test_expr_y.real_values()):
                            # X=`in[a, b]` vs Y=`in[a, b, c]`
                            # remove duplicate
                            test_expr_indexes[j] = -1
                            continue
                        elif x_real_values.isdisjoint(test_expr_y.real_values()):
                            # X=`in[a, b]` vs Y=`in[c]`
                            # conflict
                            return None
                        else:
                            pass  # `in[a, b]` vs `in[a, c]`, _do_merge_test_exprs() will deal with it
                    else:
                        if x_real_values.issubset(test_expr_y.real_values()):
                            # X=`in[a, b]` vs Y=`nin[a, b, c]`
                            # conflict
                            return None
                        elif x_real_values.isdisjoint(test_expr_y.real_values()):
                            # X=`in[a, b]` vs Y=`nin[c]`
                            # remove unused
                            test_expr_indexes[j] = -1
                            continue
                        else:
                            pass  # `in[a, b]` vs `nin[a, c]`, _do_merge_test_exprs() will deal with it

        return list(
            map(lambda x: test_exprs[x], filter(lambda x: x != -1, test_expr_indexes))
        )

    def _arrange_all_and_exprs(
        self, return_points: list[_P3ReturnPoint]
    ) -> list[_P3AndExpr]:
        all_and_exprs: list[_P3AndExpr] = []
        for return_point in return_points:
            all_and_exprs.extend(return_point.or_expr.and_exprs)

        k = len(self._absolute_test_ids)
        test_id_ref_weights: list[int] = (2 * k + 1) * [0]
        for and_expr in all_and_exprs:
            n = len(and_expr.test_exprs)
            for i, test_expr in enumerate(and_expr.test_exprs):
                weight = n - i
                test_id_ref_weights[k + test_expr.test_id] += weight
                test_id_ref_weights[k - test_expr.test_id] -= weight

        def and_expr_rank(and_expr: _P3AndExpr) -> list[int]:
            if len(and_expr.rank) == 0:
                for test_expr in and_expr.test_exprs:
                    and_expr.rank.extend(
                        (
                            test_id_ref_weights[k + test_expr.test_id],
                            *test_expr.file_offsets,
                            int(test_expr.is_negative),
                        )
                    )

            return and_expr.rank

        all_and_exprs.sort(key=lambda x: and_expr_rank(x))

        i = 0
        for return_point in return_points:
            return_point.or_expr.and_exprs.sort(key=lambda x: x.rank)

            for and_expr in return_point.or_expr.and_exprs:
                and_expr.index = i
                i += 1

        return all_and_exprs

    @classmethod
    def _dismiss_redundant_and_exprs(cls, all_and_exprs: list[_P3AndExpr]) -> None:
        test_id_sets: set[tuple[int, ...]] = set()

        for i, and_expr in enumerate(all_and_exprs):
            and_expr.index = i

            new_test_id_list: list[int] = []
            for test_expr in and_expr.test_exprs:
                if (*new_test_id_list, -test_expr.test_id) in test_id_sets:
                    test_expr.is_dismissed = True
                    continue

                new_test_id_list.append(test_expr.test_id)

            new_test_ids = tuple(new_test_id_list)
            new_test_id_sets: list[tuple[int, ...]] = [new_test_ids]
            while len(new_test_id_sets) >= 1:
                new_test_ids = new_test_id_sets.pop(0)

                if len(new_test_ids) == 0 or new_test_ids in test_id_sets:
                    continue

                test_id_sets.add(new_test_ids)
                new_test_ids_prefix, last_new_test_id = (
                    new_test_ids[:-1],
                    new_test_ids[-1],
                )

                for test_ids in tuple(test_id_sets):
                    if len(test_ids) <= len(new_test_ids_prefix):
                        continue
                    if test_ids[: len(new_test_ids_prefix)] != new_test_ids_prefix:
                        continue

                    test_ids_suffix = test_ids[len(new_test_ids_prefix) :]
                    if -last_new_test_id in test_ids_suffix:
                        new_test_ids_2 = new_test_ids_prefix + tuple(
                            x for x in test_ids_suffix if x != -last_new_test_id
                        )
                        new_test_id_sets.append(new_test_ids_2)
                        test_id_sets.remove(test_ids)

    @classmethod
    def _merge_test_exprs(cls, return_points: list[_P3ReturnPoint]) -> None:
        for return_point in return_points:
            for and_expr in return_point.or_expr.and_exprs:
                cls._do_merge_test_exprs(and_expr.test_exprs)

    @classmethod
    def _do_merge_test_exprs(cls, test_exprs: list[_P3TestExpr]) -> None:
        # merge phase 1
        for i, test_expr_x in enumerate(test_exprs):
            if test_expr_x.is_merged:
                continue

            if (not test_expr_x.is_negative and test_expr_x.equals_real_values) or (
                test_expr_x.is_negative and test_expr_x.unequals_real_values
            ):
                for j, test_expr_y in enumerate(test_exprs):
                    if j == i or test_expr_y.is_merged:
                        continue

                    if test_expr_x.is_dismissed != test_expr_y.is_dismissed:
                        # only merge test exprs that are both or neither dismissed
                        continue

                    if test_expr_y.op in (
                        test_expr_x.op,
                        test_expr_x.reverse_op,
                    ) and tuple(test_expr_y.virtual_key()) == tuple(
                        test_expr_x.virtual_key()
                    ):
                        if (test_expr_y.is_negative, test_expr_y.op) in (
                            (
                                test_expr_x.is_negative,
                                test_expr_x.op,
                            ),
                            (
                                not test_expr_x.is_negative,
                                test_expr_x.reverse_op,
                            ),
                        ):
                            # merge Y=`in[a, c]` into X=`in[a, b]`
                            test_expr_x.values.extend(test_expr_y.real_values())
                            test_expr_x.underlying_values.extend(
                                test_expr_y.real_underlying_values()
                            )
                        else:
                            # merge Y=`nin[a, c]` into X=`in[a, b]`
                            cls._remove_real_values(
                                test_expr_x, set(test_expr_y.real_values())
                            )

                        test_expr_x.merged_children.append(test_expr_y)
                        test_expr_y.is_merged = True

        # merge phase 2
        for i, test_expr_x in enumerate(test_exprs):
            if test_expr_x.is_merged:
                continue

            if (test_expr_x.is_negative and test_expr_x.equals_real_values) or (
                not test_expr_x.is_negative and test_expr_x.unequals_real_values
            ):
                for j, test_expr_y in enumerate(test_exprs):
                    if j == i or test_expr_y.is_merged:
                        continue

                    if test_expr_x.is_dismissed != test_expr_y.is_dismissed:
                        # only merge test exprs that are both or neither dismissed
                        continue

                    if (test_expr_y.is_negative, test_expr_y.op) in (
                        (
                            test_expr_x.is_negative,
                            test_expr_x.op,
                        ),
                        (
                            not test_expr_x.is_negative,
                            test_expr_x.reverse_op,
                        ),
                    ) and tuple(test_expr_y.virtual_key()) == tuple(
                        test_expr_x.virtual_key()
                    ):
                        # merge `Y=nin[a, c]` into X=`nin[a, b]`
                        test_expr_x.values.extend(test_expr_y.real_values())
                        test_expr_x.underlying_values.extend(
                            test_expr_y.real_underlying_values()
                        )
                        test_expr_x.merged_children.append(test_expr_y)
                        test_expr_y.is_merged = True

        # merge phase 3
        for test_expr in test_exprs:
            if test_expr.number_of_real_values() == 1:
                single_test_op = test_op_infos[test_expr.op].single_op
                if single_test_op is not None:
                    # multiple_op => single_op
                    test_expr.op = single_test_op
                    test_expr.reverse_op = test_op_infos[single_test_op].reverse_op

    @classmethod
    def _remove_real_values(
        cls, test_expr: _P3TestExpr, target_values: set[str]
    ) -> None:
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
        return_points: list[_P3ReturnPoint],
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

    def visit_goto_statement(self, goto_statement: GotoStatement) -> None:
        s = goto_statement.return_statement
        assert s is not None
        self.visit_return_statement(s)

    def visit_return_statement(self, return_statement: ReturnStatement) -> None:
        if (
            return_statement.source_location.file_offset
            not in self._return_point_file_offsets
        ):
            raise UnreachableReturnStatementError(return_statement.source_location)


_dummy_file_offset = -1
_dummy_source_location = SourceLocation(
    file_name="", short_file_name="", file_offset=-1, line_number=0, column_number=0
)


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        super().__init__(
            f"{source_location.short_file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )


class DuplicateBundleNameError(Error):
    def __init__(self, bundle_declaration: BundleDeclaration) -> None:
        super().__init__(
            bundle_declaration.source_location,
            f"duplicate bundle name {repr(bundle_declaration.name)}",
        )


class DuplicateUnitNameError(Error):
    def __init__(self, unit_declaration: UnitDeclaration) -> None:
        super().__init__(
            unit_declaration.source_location,
            f"duplicate unit name {repr(unit_declaration.name)}",
        )


class DuplicateCaseValueError(Error):
    def __init__(self, case_value: CaseValue) -> None:
        super().__init__(
            case_value.source_location,
            f"duplicate case value {repr(case_value.value)}",
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


class DuplicateLabelNameError(Error):
    def __init__(self, label: Label) -> None:
        super().__init__(
            label.source_location,
            f"duplicate label name {repr(label.name)}",
        )


class UndefinedLabelError(Error):
    def __init__(self, goto_statement: GotoStatement) -> None:
        super().__init__(
            goto_statement.source_location,
            f"label {repr(goto_statement.label_name)} not defined",
        )
