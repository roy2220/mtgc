import binascii
import json
import os
import subprocess
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
                program[bundle.name] = self._dump_bundle(bundle, debug_map)

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

    def _dump_bundle(self, bundle: Bundle, debug_map: list[str]) -> list[dict]:
        unit_list: list[dict] = []

        for unit in bundle.units:
            unit_list.append(
                self._dump_unit(unit, debug_map),
            )

        return unit_list

    def _dump_unit(self, unit: Unit, debug_map: list[str]) -> dict:
        transform_list: list[dict] = []
        match_list: list[dict] = []

        number_of_and_exprs = 0
        for return_point in unit.return_points:
            number_of_and_exprs += len(return_point.or_expr.and_exprs)

        all_and_exprs = number_of_and_exprs * [_dummy_and_expr]
        return_point_indexes = number_of_and_exprs * [-1]
        original_and_expr_index = 0
        original_and_expr_indexes = number_of_and_exprs * [-1]
        for return_point_index, return_point in enumerate(unit.return_points):
            transform_list.append(
                self._dump_transform(return_point_index, return_point)
            )

            for and_expr in return_point.or_expr.and_exprs:
                all_and_exprs[and_expr.index] = and_expr
                return_point_indexes[and_expr.index] = return_point_index
                original_and_expr_indexes[and_expr.index] = original_and_expr_index
                original_and_expr_index += 1

        unit_id = self._unit_id_generator.get_unit_id(unit.name)
        self._next_trace_point_id = unit_id * 10000 + 1

        for and_expr, return_point_index in zip(all_and_exprs, return_point_indexes):
            match_list.append(self._dump_match(and_expr, return_point_index))

        unit_2 = {
            "__unit_name__": unit.name,
            "tree": {
                # "has_next": False,
                # "key": 0,
                # "tree": None,
                "default_target_value_index": 0,
                "match": match_list,
            },
            "target_values": transform_list,
        }

        debug_map.append(f"========== {unit.name} ==========")
        self._next_trace_point_id = unit_id * 10000 + 1

        for and_expr, return_point_index in zip(all_and_exprs, return_point_indexes):
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
                    if self._trace_point_ids_key_index >= 1:
                        condition_tag = f"[{self._next_trace_point_id}] {condition_tag}"
                        self._next_trace_point_id += 1

                condition_tags.append(condition_tag)

            if self._trace_point_ids_key_index >= 1:
                if len(condition_tags) == 0:
                    condition_tags.append(f"[{self._next_trace_point_id}]")
                else:
                    condition_tags[-1] += f" [{self._next_trace_point_id}]"
                self._next_trace_point_id += 1

            debug_map.append(
                f"M{original_and_expr_indexes[and_expr.index]} => T{return_point_index}: "
                + "; ".join(condition_tags)
            )

        debug_map.append("")

        return unit_2

    @classmethod
    def _dump_transform(
        cls, return_point_index: int, return_point: ReturnPoint
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
            "__target_value_index__": return_point_index,
            "items": transforms,
        }
        return transform

    def _dump_match(self, and_expr: AndExpr, return_point_index: int) -> dict:
        condition_list: list[dict] = []

        for test_expr in and_expr.test_exprs:
            if test_expr.is_dismissed:
                continue
            if test_expr.is_merged:
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
                condition_list.append(
                    {
                        "__comment__": f"trace point {self._next_trace_point_id}",
                        "key": self._trace_point_ids_key_index,
                        "values": [str(self._next_trace_point_id)],
                        "operator": "MatchOp_X/TracePoint/True",
                    }
                )
                self._next_trace_point_id += 1

            condition_list.append(condition)

        if self._trace_point_ids_key_index >= 1:
            condition_list.append(
                {
                    "__comment__": f"trace point {self._next_trace_point_id}",
                    "key": self._trace_point_ids_key_index,
                    "values": [str(self._next_trace_point_id)],
                    "operator": "MatchOp_X/TracePoint/True",
                }
            )
            self._next_trace_point_id += 1

        match = {
            # "has_next": False,
            # "tree": None,
            "condition_node": {
                "condition": condition_list,
                "condition_type": 0,  # AND
            },
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
    compileBundle func(xBundle) (xFunction, error),
) (*Program, error) {
    data, err := os.ReadFile(programFileName)
    if err != nil {
        return nil, fmt.Errorf("read file %q: %v", programFileName, err)
    }

    var rawProgram map[string]xBundle
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
    program.{bundle.name}, err = compileBundle(rawProgram[bundleName])
    if err != nil {{
        return nil, fmt.Errorf("compile bundle %q: %v", bundleName, err)
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
