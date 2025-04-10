import json
import os
from collections.abc import Iterator

from .analyzer import AndExpr, Component, ReturnPoint, TestExpr, Unit


class MatchTransformGenerator:
    __slots__ = (
        "_components",
        "_output_dir_name",
    )

    def __init__(self, components: list[Component], output_dir_name: str) -> None:
        self._components = components
        self._output_dir_name = output_dir_name

    def dump_components(self) -> None:
        output_file_names: set[str] = set()

        for component in self._components:
            for unit in component.units:
                output_file_name = os.path.join(
                    self._output_dir_name, unit.name + ".json"
                )
                if output_file_name in output_file_names:
                    raise ValueError(
                        f"output file {repr(output_file_name)} name conflicts"
                    )

                unit_data = json.dumps(
                    self._dump_unit(component, unit), ensure_ascii=False, indent=2
                )
                with open(output_file_name, "w") as f:
                    f.write(unit_data)

    def _dump_unit(self, component: Component, unit: Unit) -> dict:
        match_list = []
        transform_list = []

        for i, return_point in enumerate(unit.return_points):
            for and_expr in return_point.or_expr.and_exprs:
                match_list.append(self._dump_match(i, and_expr))
            transform_list.append(self._dump_transform(i, return_point))

        unit_2 = {
            "__comment__": f"{component.alias}: {unit.alias}",
            "tree": {
                # "has_next": False,
                # "key": 0,
                # "tree": None,
                "default_target_value_index": 0,
                "match": match_list,
            },
            "target_values": transform_list,
        }
        return unit_2

    def _dump_match(self, return_point_index: int, and_expr: AndExpr) -> dict:
        def make_tag(test_expr: TestExpr) -> str:
            if test_expr.is_positive:
                return "✅ " + test_expr.fact
            else:
                return "❌ " + test_expr.fact

        condition_list = []

        for test_expr in and_expr.test_exprs:
            tags: list[str] = [make_tag(test_expr)]
            for child_test_expr in test_expr.children:
                tags.append(make_tag(child_test_expr))

            condition = {
                "__comment__": "; ".join(tags),
                "key": test_expr.key_index,
                "__named_key__": test_expr.key,
                "values": test_expr.underlying_values,
                "__named_values__": test_expr.values,
                "operator": (
                    test_expr.op if test_expr.is_positive else test_expr.reverse_op
                ),
            }
            if test_expr.values == test_expr.underlying_values:
                condition.pop("__named_values__")
            condition_list.append(condition)

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

    def _dump_transform(
        self, return_point_index: int, return_point: ReturnPoint
    ) -> dict:
        transforms = []

        for transform in return_point.transform_list:
            operators = []

            for operator in transform.spec["operators"]:
                operator_2 = {"op": operator["op"]}

                if (v := operator.get("underlying_from")) is not None:
                    operator_2["from"] = v
                    operator_2["__named_from__"] = operator["from"]

                if (v := operator.get("underlying_values")) is not None:
                    operator_2["values"] = v
                    operator_2["__named_values__"] = operator["values"]
                elif (v := operator.get("values")) is not None:
                    operator_2["values"] = v

                if (v := operator.get("underlying_op_type")) is not None:
                    operator_2["op_type"] = v
                    operator_2["__named_op_type__"] = operator["op_type"]

                operators.append(operator_2)

            transform_2 = {
                "__comment__": transform.annotation,
                "to": transform.spec["underlying_to"],
                "__named_to__": transform.spec["to"],
                "operators": operators,
            }
            transforms.append(transform_2)

        transform = {
            "__target_value_index__": {return_point_index},
            "items": transforms,
        }
        return transform
