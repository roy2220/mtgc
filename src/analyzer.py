import os
import parser
from dataclasses import dataclass

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


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        short_file_name = os.path.basename(source_location.file_name)
        super().__init__(
            f"{short_file_name}:{source_location.line_number}:{source_location.column_number}: {description}"
        )
