import binascii
import dataclasses
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from .analyzer import AndExpr, Bundle, Component, OrExpr, ReturnPoint, TestExpr, Unit
from .key_registry import KeyRegistry
from .test_op_infos import replace_with_real_op


class MatchTransformGenerator:
    __slots__ = (
        "_components",
        "_program_file_name",
        "_go_program_loader_file_name",
        "_debug_map_file_name",
        "_trace_point_ids_key_index",
        "_next_trace_point_id",
        "_unit_id_generator",
    )

    def __init__(
        self,
        components: list[Component],
        program_file_name: str,
        go_program_loader_file_name: str,
        debug_map_file_name: str | None,
        key_registry: KeyRegistry,
    ) -> None:
        self._components = components
        self._program_file_name = program_file_name
        self._go_program_loader_file_name = go_program_loader_file_name
        self._debug_map_file_name = debug_map_file_name
        if (
            key_info := key_registry.lookup_key("TracePointIds")
        ) is not None and key_info.type == "*[]int32":
            self._trace_point_ids_key_index = key_info.index
        else:
            self._trace_point_ids_key_index = 0
        self._next_trace_point_id = 0
        self._unit_id_generator = _UnitIdGenerator()

    def dump_components(self) -> None:
        program: dict[str, list[dict]] = {}
        debug_map: list[str] = []

        for component in self._components:
            for bundle in component.bundles:
                if bundle.name in program.keys():
                    raise ValueError(f"bundle name {repr(bundle.name)} conflicts")
                program[bundle.name] = self._dump_bundle(component, bundle, debug_map)

        with open(self._program_file_name, "w") as f:
            f.write(
                json.dumps(
                    program,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        if self._debug_map_file_name is not None:
            with open(self._debug_map_file_name, "w") as f:
                f.write("\n".join(debug_map))

        source_code = self._dump_go_program_loader()
        with open(self._go_program_loader_file_name, "w") as f:
            f.write(self._format_go_code("".join(source_code)))

    def _dump_bundle(
        self, component: Component, bundle: Bundle, debug_map: list[str]
    ) -> list[dict]:
        unit_list: list[dict] = []

        for unit in bundle.units:
            unit_list.append(
                self._dump_unit(component, unit, debug_map),
            )

        return unit_list

    def _dump_unit(
        self, component: Component, unit: Unit, debug_map: list[str]
    ) -> dict:
        transform_list: list[dict] = []

        number_of_and_exprs = 0
        for return_point in unit.return_points:
            number_of_and_exprs += len(return_point.or_expr.and_exprs)

        all_and_exprs = number_of_and_exprs * [_dummy_and_expr]
        return_point_indexes = number_of_and_exprs * [-1]
        original_and_expr_index = 0
        original_and_expr_indexes = number_of_and_exprs * [-1]
        for return_point_index, return_point in enumerate(unit.return_points):
            transform_list.append(
                self._dump_transform(return_point, unit.name, return_point_index)
            )

            for and_expr in return_point.or_expr.and_exprs:
                all_and_exprs[and_expr.index] = and_expr
                return_point_indexes[and_expr.index] = return_point_index
                original_and_expr_indexes[and_expr.index] = original_and_expr_index
                original_and_expr_index += 1

        unit_id = self._unit_id_generator.get_unit_id(unit.name)
        self._next_trace_point_id = unit_id * 10000 + 1

        return_points = list(zip(all_and_exprs, return_point_indexes))
        enable_tree_map = any(
            map(
                lambda x: x == "feat:treemap",
                component.line_directives.get(unit.source_location.line_number, ()),
            )
        )
        # enable_tree_map = True
        match_list = self._dump_match_list(return_points, 0, unit.name, enable_tree_map)

        unit_2 = {
            "__unit_name__": unit.name,
            "tree": None,
            "target_values": transform_list,
        }
        if len(match_list) == 1 and match_list[0].get("has_next", False):
            unit_2["tree"] = match_list[0]["tree"]
        else:
            unit_2["tree"] = {
                "default_target_value_index": 0,
                "match": match_list,
            }

        debug_map.append(f"========== {unit.name} ==========")
        for and_expr, return_point_index in return_points:
            condition_tags: list[str] = []

            for test_expr in and_expr.test_exprs:
                if test_expr.is_merged:
                    continue

                if len(test_expr.merged_children) == 0:
                    condition_tag = make_condition_tag(test_expr)
                else:
                    condition_tag = "{ " + make_condition_tag(test_expr)
                    for child_test_expr in test_expr.merged_children:
                        condition_tag += "; " + make_condition_tag(child_test_expr)
                    condition_tag += " }"

                if test_expr.is_dismissed:
                    condition_tag = "~~" + condition_tag
                else:
                    if (trace_point_id := test_expr.trace_point_id) is not None:
                        condition_tag = f"[{trace_point_id}] {condition_tag}"

                condition_tags.append(condition_tag)

            if (trace_point_id := and_expr.trailing_trace_point_id) is not None:
                if len(condition_tags) == 0:
                    condition_tags.append(f"[{trace_point_id}]")
                else:
                    condition_tags[-1] += f" [{trace_point_id}]"

            debug_map.append(
                f"M{original_and_expr_indexes[and_expr.index]} => T{return_point_index}: "
                + "; ".join(condition_tags)
            )

        debug_map.append("")

        return unit_2

    @classmethod
    def _dump_transform(
        cls, return_point: ReturnPoint, unit_name: str, return_point_index: int
    ) -> dict:
        transforms: list[dict] = []

        for transform in return_point.transform_list:
            operators: list[dict] = []

            for operator in transform.operators:
                operator_2: dict[str, Any] = {"op": operator.op}

                if (v := operator.underlying_from) is not None:
                    operator_2["from"] = v
                    operator_2["__named_from__"] = operator.from1

                if (v := operator.values) is not None:
                    operator_2["values"] = v

                if (v := operator.underlying_op_type) is not None:
                    operator_2["op_type"] = v
                    operator_2["__named_op_type__"] = operator.op_type

                operators.append(operator_2)

            transform_2 = {
                "__comment__": transform.annotation,
                "to": transform.underlying_to,
                "__named_to__": transform.to,
                "operators": operators,
            }
            transforms.append(transform_2)

        transform = {
            "__anchor__": f"{unit_name}_{return_point_index}",
            "items": transforms,
        }
        return transform

    def _dump_match_list(
        self,
        return_points: list[tuple[AndExpr, int]],
        first_test_expr_index: int,
        unit_name: str,
        enable_tree_map: bool,
    ) -> list[dict]:
        if enable_tree_map:

            @dataclass
            class TestPathItem:
                op: str = ""
                key_index: int = 0
                test_ids: tuple[int, ...] = ()

            @dataclass
            class TestPath:
                type: str = ""
                items: list[TestPathItem] = dataclasses.field(default_factory=list)

            test_paths: list[TestPath] = []
            for return_point in return_points:
                and_expr = return_point[0]
                test_path = TestPath()
                for i in range(first_test_expr_index, len(and_expr.test_exprs)):
                    test_expr = and_expr.test_exprs[i]
                    test_path_item = TestPathItem(
                        key_index=test_expr.key_index,
                        test_ids=(test_expr.test_id,)
                        + tuple(v.test_id for v in test_expr.merged_children),
                    )
                    if test_expr.is_negative:
                        op = test_expr.reverse_op
                    else:
                        op = test_expr.op
                    if op in ("eq", "in"):
                        test_path_item.op = "IN"
                    elif op in ("neq", "nin"):
                        test_path_item.op = "NOT_IN"
                    test_path.items.append(test_path_item)
                    if not (test_expr.is_dismissed or test_expr.is_merged):
                        if test_path_item.op == "IN":
                            if len(test_path_item.test_ids) == 1:
                                test_path.type = "CASE"
                                break
                        elif test_path_item.op == "NOT_IN":
                            test_path.type = "DEFAULT_CASE"
                            break
                test_paths.append(test_path)

            MIN_HIT_COUNT = 4
            for x, test_path_x in enumerate(test_paths[: -MIN_HIT_COUNT + 1]):
                if test_path_x.type == "":
                    continue

                i = len(test_path_x.items) - 1
                hit_count = 1
                for y in range(x + 1, len(test_paths)):
                    test_path_y = test_paths[y]
                    if not (
                        test_path_y.type == test_path_x.type
                        and len(test_path_y.items) == i + 1
                        and test_path_y.items[i].key_index
                        == test_path_x.items[i].key_index
                        and test_path_y.items[:i] == test_path_x.items[:i]
                    ):
                        break
                    hit_count += 1
                if hit_count < MIN_HIT_COUNT:
                    continue

                if test_path_x.type == "CASE":
                    last_op = None
                    for y in range(x + hit_count, len(test_paths)):
                        test_path_y = test_paths[y]
                        if last_op is None:
                            last_op = test_path_y.items[i].op
                        assert (
                            len(test_path_y.items) > i
                            and last_op != ""
                            and test_path_y.items[i].op == last_op
                            and test_path_y.items[i].key_index
                            == test_path_x.items[i].key_index
                            and test_path_y.items[:i] == test_path_x.items[:i]
                        ), f"unit_name={unit_name} test_path_x={test_path_x} test_path_y={test_path_y}"
                elif test_path_x.type == "DEFAULT_CASE":
                    for y in range(x + hit_count, len(test_paths)):
                        test_path_y = test_paths[y]
                        assert (
                            len(test_path_y.items) > i
                            and test_path_y.items[i].op == "IN"
                            and len(test_path_y.items[i].test_ids) == 1
                            and test_path_y.items[i].key_index
                            == test_path_x.items[i].key_index
                            and test_path_y.items[:i] == test_path_x.items[:i]
                        ), f"unit_name={unit_name} test_path_x={test_path_x} test_path_y={test_path_y}"

                match_list: list[dict] = []
                for and_expr, return_point_index in return_points[:x]:
                    match_list.append(
                        self._dump_match(
                            and_expr,
                            return_point_index,
                            first_test_expr_index,
                            unit_name,
                        )
                    )
                test_expr_index = first_test_expr_index + i
                test_expr = return_points[x][0].test_exprs[test_expr_index]
                if test_path_x.type == "CASE":
                    return_points_a = return_points[x : x + hit_count]
                    return_points_b = return_points[x + hit_count :]
                else:
                    return_points_a = return_points[x + hit_count :]
                    return_points_b = return_points[x : x + hit_count]

                for return_point in return_points[x:]:
                    return_point[0].test_exprs[test_expr_index].trace_point_id = -1

                match_list.append(
                    {
                        "has_next": True,
                        "tree": {
                            "default_target_value_index": 0,
                            "key": test_expr.key_index,
                            "__named_key__": test_expr.key,
                            "tree": self._dump_tree_map(
                                return_points_a,
                                test_expr_index,
                                unit_name,
                            ),
                            "match": self._dump_match_list(
                                return_points_b,
                                test_expr_index + 1,
                                unit_name,
                                True,
                            ),
                        },
                    }
                )
                return match_list

        match_list: list[dict] = []
        for and_expr, return_point_index in return_points:
            match_list.append(
                self._dump_match(
                    and_expr, return_point_index, first_test_expr_index, unit_name
                )
            )
        return match_list

    def _dump_tree_map(
        self,
        return_points: list[tuple[AndExpr, int]],
        test_expr_index: int,
        unit_name: str,
    ) -> dict[str, dict]:
        value_2_return_points: dict[str, list[tuple[AndExpr, int]]] = {}
        for return_point in return_points:
            test_expr = return_point[0].test_exprs[test_expr_index]
            for v in test_expr.values:
                return_points_of_value = value_2_return_points.get(v)
                if return_points_of_value is None:
                    return_points_of_value = []
                    value_2_return_points[v] = return_points_of_value
                return_points_of_value.append(return_point)

        tree_map: dict[str, dict] = {}
        for value, return_points_of_value in value_2_return_points.items():
            match_list = self._dump_match_list(
                return_points_of_value,
                test_expr_index + 1,
                unit_name,
                True,
            )
            if len(match_list) == 1 and match_list[0].get("has_next", False):
                tree_map[value] = match_list[0]["tree"]
            else:
                tree_map[value] = {
                    "default_target_value_index": 0,
                    "match": match_list,
                }
        return tree_map

    def _dump_match(
        self,
        and_expr: AndExpr,
        return_point_index: int,
        first_test_expr_index: int,
        unit_name: str,
    ) -> dict:
        condition_list: list[dict] = []

        for i in range(first_test_expr_index, len(and_expr.test_exprs)):
            test_expr = and_expr.test_exprs[i]
            if test_expr.is_dismissed or test_expr.is_merged:
                continue

            condition_tags: list[str] = [make_condition_tag(test_expr)]
            for child_test_expr in test_expr.merged_children:
                condition_tags.append(make_condition_tag(child_test_expr))

            if test_expr.is_negative:
                op = test_expr.reverse_op
            else:
                op = test_expr.op
            op = replace_with_real_op(op)

            condition = {
                "__comment__": "; ".join(condition_tags),
                "key": test_expr.key_index,
                "__named_key__": test_expr.key,
                "values": test_expr.underlying_values,
                "__named_values__": test_expr.values,
                "operator": op,
            }
            if test_expr.values == test_expr.underlying_values:
                condition.pop("__named_values__")

            if self._trace_point_ids_key_index >= 1:
                if test_expr.trace_point_id is None:
                    test_expr.trace_point_id = self._next_trace_point_id
                    self._next_trace_point_id += 1
                condition_list.append(
                    {
                        "__comment__": f"trace point {test_expr.trace_point_id}",
                        "key": self._trace_point_ids_key_index,
                        "values": [str(test_expr.trace_point_id)],
                        "operator": "MatchOp_X/TracePoint/True",
                    }
                )

            condition_list.append(condition)

        if self._trace_point_ids_key_index >= 1:
            if and_expr.trailing_trace_point_id is None:
                and_expr.trailing_trace_point_id = self._next_trace_point_id
                self._next_trace_point_id += 1
            condition_list.append(
                {
                    "__comment__": f"trace point {and_expr.trailing_trace_point_id}",
                    "key": self._trace_point_ids_key_index,
                    "values": [str(and_expr.trailing_trace_point_id)],
                    "operator": "MatchOp_X/TracePoint/True",
                }
            )

        match = {
            "condition_node": {
                "condition": condition_list,
                "condition_type": 0,  # AND
            },
            "__target_value_anchor__": f"{unit_name}_{return_point_index}",
            "target_value_index": return_point_index,
        }
        return match

    def _dump_go_program_loader(self) -> list[str]:
        source_code: list[str] = []

        package_name = os.path.basename(
            os.path.dirname(os.path.abspath(self._go_program_loader_file_name))
        )
        source_code.append(
            f"""\
// Code generated by mtgc; DO NOT EDIT.
package {package_name}

import (
    "encoding/json"
    "fmt"
    "os"
)

type Program struct {{
"""
        )
        for component in self._components:
            for bundle in component.bundles:
                source_code.append(
                    f"""\
    {bundle.name} xFunction
"""
                )

        source_code.append(
            """\
}

func LoadProgram(
    programFileName string,
    compileMatchTransforms func([]xMatchTransform) (xFunction, error),
) (*Program, error) {
    data, err := os.ReadFile(programFileName)
    if err != nil {
        return nil, fmt.Errorf("read file %q: %v", programFileName, err)
    }

    var rawProgram map[string][]xMatchTransform
    if err := json.Unmarshal(data, &rawProgram); err != nil {
        return nil, fmt.Errorf("unmarshal program from file %q: %v", programFileName, err)
    }

    var program Program

    var bundleName string
    defer func() {
        if r := recover(); r != nil {
            panic(fmt.Sprintf("panic detected during compiling bundle %q: %v", bundleName, r))
        }
    }()
"""
        )
        for component in self._components:
            for bundle in component.bundles:
                source_code.append(
                    f"""\

    bundleName = "{bundle.name}"
    program.{bundle.name}, err = compileMatchTransforms(rawProgram[bundleName])
    if err != nil {{
        return nil, fmt.Errorf("compile match-transforms from bundle %q: %v", bundleName, err)
    }}
"""
                )

        source_code.append(
            """\

    return &program, nil
}
"""
        )

        return source_code

    @classmethod
    def _format_go_code(cls, go_code: str) -> str:
        try:
            result = subprocess.run(
                ["gofmt"], input=go_code, capture_output=True, text=True, check=True
            )
            return result.stdout
        except Exception:
            return go_code


class _UnitIdGenerator:
    __slots__ = (
        "_unit_name_2_id",
        "_unit_ids",
    )

    _MAX_NUMBER_OF_UNITS = 9999

    def __init__(self) -> None:
        self._unit_name_2_id: dict[str, int] = {}
        self._unit_ids: set[int] = set()

    def get_unit_id(self, unit_name: str) -> int:
        unit_id = self._unit_name_2_id.get(unit_name)
        if unit_id is None:
            unit_id = 1 + binascii.crc32(unit_name.encode()) % self._MAX_NUMBER_OF_UNITS
            if len(self._unit_ids) == self._MAX_NUMBER_OF_UNITS:
                raise ValueError("too many units")
            while unit_id in self._unit_ids:
                unit_id = 1 + (unit_id + 1) % self._MAX_NUMBER_OF_UNITS
            self._unit_name_2_id[unit_name] = unit_id
            self._unit_ids.add(unit_id)
        return unit_id


_dummy_and_expr = AndExpr(test_exprs=[], index=-1)


def make_condition_tag(test_expr: TestExpr) -> str:
    if test_expr.is_negative:
        return "❌ " + test_expr.fact
    else:
        return "✅ " + test_expr.fact
