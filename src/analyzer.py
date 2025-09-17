import os
from dataclasses import dataclass
from typing import Callable

from . import parser
from .parser import SourceLocation


@dataclass(kw_only=True)
class Bundle:
    pipelines: list["Pipeline"]
    match_transforms: list["MatchTransform"]


type Component = "Pipeline | MatchTransform"


@dataclass(kw_only=True)
class Pipeline:
    source_location: SourceLocation
    component_name: str
    nodes: list["Node"]


@dataclass(kw_only=True)
class Node:
    source_location: SourceLocation
    node_name: str
    bound_component: Component | None
    node_rules: list["NodeRule"]


@dataclass(kw_only=True)
class NodeRule:
    test_exprs: list["TestExpr"]
    next_node: Node | None


@dataclass(kw_only=True)
class MatchTransform:
    source_location: SourceLocation
    component_name: str
    business_units: list["BusinessUnit"]


@dataclass(kw_only=True)
class BusinessUnit:
    source_location: SourceLocation
    business_unit: str
    business_unit_rules: list["BusinessUnitRule"]


@dataclass(kw_only=True)
class BusinessUnitRule:
    test_exprs: list["TestExpr"]
    business_scenario: str
    key_and_expr_pairs: list[tuple[str, str]]


@dataclass(kw_only=True)
class TestExpr:
    pass


class Analyzer:
    def __init__(
        self,
        raw_pipelines: list[parser.Pipeline],
        raw_match_transforms: list[parser.MatchTransform],
    ) -> None:
        self._raw_pipelines = raw_pipelines
        self._raw_match_transforms = raw_match_transforms

        self._raw_nodes: list[parser.Node] = []
        self._components: dict[str, Component] = {}

        self.bundle = self._run()

    def _run(self) -> Bundle:
        bundle = Bundle(
            pipelines=self._get_pipelines(),
            match_transforms=self._get_match_transforms(),
        )

        raw_node_index = 0
        for pipeline in bundle.pipelines:
            for node in pipeline.nodes:
                raw_node = self._raw_nodes[raw_node_index]
                if raw_node.bound_component_name is not None:
                    bound_component = self._components.get(
                        raw_node.bound_component_name, None
                    )
                    if bound_component is None:
                        raise ComponentNotFoundError(
                            raw_node.source_location, raw_node.bound_component_name
                        )
                    node.bound_component = bound_component
                raw_node_index += 1

        return bundle

    def _get_pipelines(self) -> list[Pipeline]:
        pipelines: list[Pipeline] = []
        for raw_pipeline in self._raw_pipelines:
            if raw_pipeline.component_name == "":
                raise EmptyComponentNameError(raw_pipeline.source_location)
            if raw_pipeline.component_name in self._components.keys():
                raise DuplicateComponentNameError(
                    raw_pipeline.source_location, raw_pipeline.component_name
                )
            pipeline = Pipeline(
                source_location=raw_pipeline.source_location,
                component_name=raw_pipeline.component_name,
                nodes=self._get_nodes(raw_pipeline.nodes),
            )
            self._components[raw_pipeline.component_name] = pipeline
            pipelines.append(pipeline)
        return pipelines

    def _get_nodes(self, raw_nodes: list[parser.Node]) -> list[Node]:
        nodes: dict[str, Node] = {}
        for i, raw_node in enumerate(raw_nodes):
            if i == 0:
                if not raw_node.is_head:
                    raise HeadExpectedError(raw_node.source_location)
            else:
                if raw_node.bound_component_name == "":
                    raise EmptyComponentNameError(raw_node.source_location)
            if raw_node.node_name == "":
                raise EmptyNodeNameError(raw_node.source_location)
            if raw_node.node_name in nodes.keys():
                raise DuplicateNodeNameError(
                    raw_node.source_location, raw_node.node_name
                )

            raw_node.next_statement = _P1Analyzer(
                raw_node.source_location, raw_node.body
            ).next_statement

            nodes[raw_node.node_name] = Node(
                source_location=raw_node.source_location,
                node_name=raw_node.node_name,
                bound_component=None,
                node_rules=self._get_node_rules(raw_node.body),
            )
            self._raw_nodes.append(raw_node)
        return list(nodes.values())

    def _get_node_rules(self, body: list[parser.Statement]) -> list[NodeRule]:
        return []

    def _get_match_transforms(self) -> list[MatchTransform]:
        match_transforms: list[MatchTransform] = []
        for raw_match_transform in self._raw_match_transforms:
            if raw_match_transform.component_name == "":
                raise EmptyComponentNameError(raw_match_transform.source_location)
            if raw_match_transform.component_name in self._components.keys():
                raise DuplicateComponentNameError(
                    raw_match_transform.source_location,
                    raw_match_transform.component_name,
                )
            match_transform = MatchTransform(
                source_location=raw_match_transform.source_location,
                component_name=raw_match_transform.component_name,
                business_units=self._get_business_units(
                    raw_match_transform.business_units
                ),
            )
            self._components[raw_match_transform.component_name] = match_transform
            match_transforms.append(match_transform)
        return match_transforms

    def _get_business_units(
        self,
        raw_business_units: list[parser.BusinessUnit],
    ) -> list[BusinessUnit]:
        business_units: list[BusinessUnit] = []
        for raw_business_unit in raw_business_units:
            business_unit = BusinessUnit(
                source_location=raw_business_unit.source_location,
                business_unit=raw_business_unit.business_unit,
                business_unit_rules=self._get_business_unit_rules(
                    raw_business_unit.body
                ),
            )

            raw_business_unit.next_statement = _P1Analyzer(
                raw_business_unit.source_location, raw_business_unit.body
            ).next_statement

            business_units.append(business_unit)
        return business_units

    def _get_business_unit_rules(
        self, body: list[parser.Statement]
    ) -> list[BusinessUnitRule]:
        return []


class _P1Analyzer(parser.Visitor):
    def __init__(
        self, source_location: SourceLocation, body: list[parser.Statement]
    ) -> None:
        self._source_location = source_location
        self._body = body
        self._next_statement_setter_stack: list[Callable[[parser.Statement], None]] = []

        self.next_statement = self._run()

    def _run(self) -> parser.Statement:
        next_statement = None

        def set_next_statement(s: parser.Statement) -> None:
            nonlocal next_statement
            next_statement = s

        self._visit_body(set_next_statement, self._body)

        if len(self._next_statement_setter_stack) >= 1:
            raise MissingReturnStatementError(self._source_location)

        assert next_statement is not None
        return next_statement

    class _Return(Exception):
        pass

    def _visit_body(
        self,
        set_next_statement: Callable[[parser.Statement], None],
        body: list[parser.Statement],
    ) -> None:
        i = len(self._next_statement_setter_stack)
        self._next_statement_setter_stack.append(set_next_statement)

        for s in body:
            for f in self._next_statement_setter_stack[i:]:
                f(s)
            del self._next_statement_setter_stack[i:]

            try:
                s.accept_visit(self)
            except self._Return:
                return

    def visit_return_statement(self, return_statement: parser.ReturnStatement) -> None:
        raise self._Return()

    def visit_if_statement(self, if_statement: parser.IfStatement) -> None:
        def set_next_statement(s: parser.Statement) -> None:
            if_statement.next_statement = s

        self._visit_body(set_next_statement, if_statement.body)

        if (else_clause := if_statement.else_clause).source_location is not None:

            def set_next_statement(s: parser.Statement) -> None:
                else_clause.next_statement = s

            self._visit_body(set_next_statement, else_clause.body)


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        short_file_name = os.path.relpath(source_location.file_name)
        super().__init__(
            f"{short_file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )


class EmptyComponentNameError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "empty component name")


class DuplicateComponentNameError(Error):
    def __init__(self, source_location: SourceLocation, component_name: str) -> None:
        super().__init__(
            source_location, f"duplicate component name {component_name!r}"
        )


class EmptyNodeNameError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "empty node name")


class DuplicateNodeNameError(Error):
    def __init__(self, source_location: SourceLocation, node_name: str) -> None:
        super().__init__(source_location, f"duplicate node name {node_name!r}")


class ComponentNotFoundError(Error):
    def __init__(self, source_location: SourceLocation, component_name: str) -> None:
        super().__init__(source_location, f"component {component_name!r} not found")


class HeadExpectedError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(
            source_location, f"the first node in the pipeline should be HEAD"
        )


class MissingReturnStatementError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, f"missing return statement")
