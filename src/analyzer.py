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
    description: str
    nodes: list["Node"]


@dataclass(kw_only=True)
class Node:
    source_location: SourceLocation
    node_name: str
    is_head: bool
    bound_component: Component | None
    node_rules: list["NodeRule"]


@dataclass(kw_only=True)
class NodeRule:
    test_key_and_expr_pairs: list[tuple[str, str]]
    next_node: Node | None


@dataclass(kw_only=True)
class MatchTransform:
    source_location: SourceLocation
    component_name: str
    description: str
    business_units: list["BusinessUnit"]


@dataclass(kw_only=True)
class BusinessUnit:
    source_location: SourceLocation
    business_unit: str
    business_unit_rules: list["BusinessUnitRule"]


@dataclass(kw_only=True)
class BusinessUnitRule:
    test_key_and_expr_pairs: list[tuple[str, str]]
    business_scenario: str
    set_key_and_expr_pairs: list[tuple[str, str]]


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

        self._run()

    @property
    def bundle(self) -> Bundle:
        return self._bundle

    def _run(self) -> None:
        self._bundle = Bundle(
            pipelines=self._get_pipelines(),
            match_transforms=self._get_match_transforms(),
        )

        raw_node_index = 0
        for pipeline in self._bundle.pipelines:
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
                description=raw_pipeline.description,
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
                if raw_node.is_head:
                    raise HeadUnexpectedError(raw_node.source_location)
                if raw_node.bound_component_name == "":
                    raise EmptyComponentNameError(raw_node.source_location)
            if raw_node.node_name == "":
                raise EmptyNodeNameError(raw_node.source_location)
            if raw_node.node_name in nodes.keys():
                raise DuplicateNodeNameError(
                    raw_node.source_location, raw_node.node_name
                )
            nodes[raw_node.node_name] = Node(
                source_location=raw_node.source_location,
                node_name=raw_node.node_name,
                is_head=raw_node.is_head,
                bound_component=None,
                node_rules=[],
            )
            self._raw_nodes.append(raw_node)

        for raw_node in raw_nodes:
            node = nodes[raw_node.node_name]
            node.node_rules = self._get_node_rules(raw_node.body, nodes)

        return list(nodes.values())

    def _get_node_rules(
        self, statements: list[parser.Statement], nodes: dict[str, Node]
    ) -> list[NodeRule]:
        return_points = ReturnPointCollector(statements).return_points
        node_rules: list[NodeRule] = []
        for return_point in return_points:
            next = return_point.return_statement.next
            assert next.source_location is not None
            next_node = None
            if next.next_node_name is not None:
                next_node = nodes.get(next.next_node_name)
                if next_node is None:
                    raise NodeNotFoundError(
                        next.source_location,
                        next.next_node_name,
                    )
            node_rules.append(
                NodeRule(
                    test_key_and_expr_pairs=return_point.test_key_and_expr_pairs,
                    next_node=next_node,
                )
            )
        return node_rules

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
                description=raw_match_transform.description,
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
            business_units.append(business_unit)
        return business_units

    def _get_business_unit_rules(
        self, statements: list[parser.Statement]
    ) -> list[BusinessUnitRule]:
        return_points = ReturnPointCollector(statements).return_points
        business_unit_rules: list[BusinessUnitRule] = []
        for return_point in return_points:
            set = return_point.return_statement.set
            assert set.source_location is not None
            business_unit_rules.append(
                BusinessUnitRule(
                    test_key_and_expr_pairs=return_point.test_key_and_expr_pairs,
                    business_scenario=set.business_scenario,
                    set_key_and_expr_pairs=set.key_and_expr_pairs,
                )
            )
        return business_unit_rules


@dataclass(kw_only=True)
class ReturnPoint:
    test_key_and_expr_pairs: list[tuple[str, str]]
    return_statement: parser.ReturnStatement


class ReturnPointCollector(parser.Visitor):
    def __init__(self, statements: list[parser.Statement]) -> None:
        self._statements = statements
        self._return_points: list[ReturnPoint] = []
        self._test_key_and_expr_pairs: list[tuple[str, str]] = []

        self._run()

    @property
    def return_points(self) -> list[ReturnPoint]:
        return self._return_points

    def _run(self) -> None:
        for statement in self._statements:
            statement.accept_visit(self)

    def visit_return_statement(self, return_statement: parser.ReturnStatement) -> None:
        self._return_points.append(
            ReturnPoint(
                test_key_and_expr_pairs=self._test_key_and_expr_pairs.copy(),
                return_statement=return_statement,
            )
        )

    def visit_if_statement(self, if_statement: parser.IfStatement) -> None:
        i = len(self._test_key_and_expr_pairs)

        if_statement.condition.accept_visit(self)
        for statement in if_statement.body:
            statement.accept_visit(self)

        del self._test_key_and_expr_pairs[i:]

    def visit_test_condition(self, test_condition: parser.TestCondition) -> None:
        self._test_key_and_expr_pairs.append((test_condition.key, test_condition.expr))

    def visit_composite_condition(
        self, composite_condition: parser.CompositeCondition
    ) -> None:
        composite_condition.condition_1.accept_visit(self)
        composite_condition.condition_2.accept_visit(self)


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


class HeadUnexpectedError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(
            source_location,
            f"HEAD should only appear as the first node in the pipeline",
        )


class NodeNotFoundError(Error):
    def __init__(self, source_location: SourceLocation, node_name: str) -> None:
        super().__init__(source_location, f"node {node_name!r} not found")
