import hashlib
import uuid

from .analyzer import Bundle


class Generator:
    def __init__(
        self,
        *,
        app_id: str,
        warehouse_name: str,
        bundle: Bundle,
    ) -> None:
        self._app_id = app_id
        self._warehouse_name = warehouse_name
        self._bundle = bundle
        self._next_component_id = 1

        self._run()

    @property
    def spec(self) -> dict:
        return self._spec

    def _run(self) -> None:
        components = self._dump_pipelines() + self._dump_match_transforms()
        self._spec = {
            "AppId": self._app_id,
            "WarehouseName": self._warehouse_name,
            "Components": components,
        }
        self._spec["ComponentCount"] = len(components)

    def _dump_pipelines(self) -> list[dict]:
        pipeline_specs = []
        for pipeline in self._bundle.pipelines:
            node_uuids: dict[str, str] = {}
            for node in pipeline.nodes:
                node_uuids[node.node_name] = _calculate_node_uuid(
                    pipeline.component_name, node.node_name
                )

            component_by_node = {}
            for node in pipeline.nodes:
                if node.is_head:
                    continue
                assert node.bound_component is not None
                component_by_node[node_uuids[node.node_name]] = (
                    node.bound_component.component_name
                )

            edges = []
            for node in pipeline.nodes:
                if node.is_head:
                    curr_node = ""
                else:
                    curr_node = node_uuids[node.node_name]
                for node_rule in node.node_rules:
                    if node_rule.next_node is None:
                        continue
                    next_node = node_uuids[node_rule.next_node.node_name]
                    whens = []
                    for key, expr in node_rule.test_key_and_expr_pairs:
                        whens.append(
                            {
                                "Expr": expr,
                                "Key": key,
                            }
                        )
                    edges.append(
                        {
                            "CurrNode": curr_node,
                            "NextNode": next_node,
                            "Whens": whens,
                        }
                    )

            config = {
                "ComponentByNode": component_by_node,
                "ComponentName": pipeline.component_name,
                "ComponentType": "TABLE_PIPELINE",
                "Edges": edges,
                "Head": "",
                "TableVersion": "v1.0.0",
            }
            pipeline_specs.append(
                {
                    "id": self._generate_component_id(),
                    "app_id": self._app_id,
                    "warehouse_name": self._warehouse_name,
                    "name": pipeline.component_name,
                    "type": "TABLE_PIPELINE",
                    "spec_version": "v1.0.0",
                    "describe": pipeline.description,
                    "config": config,
                    "config_version": "v1",
                    "config_version_seq": 1,
                    "is_external_dsl": 0 if pipeline.component_name == "root" else 2,
                }
            )
        return pipeline_specs

    def _dump_match_transforms(self) -> list[dict]:
        match_transform_specs = []
        for match_transform in self._bundle.match_transforms:
            when_headers: dict[str, None] = {}
            then_headers: dict[str, None] = {}
            rules = []
            for business_unit in match_transform.business_units:
                for business_unit_rule in business_unit.business_unit_rules:
                    whens = []
                    thens = []
                    for key, expr in business_unit_rule.test_key_and_expr_pairs:
                        whens.append(
                            {
                                "Expr": expr,
                                "Key": key,
                            }
                        )
                        when_headers[key] = None
                    for key, expr in business_unit_rule.set_key_and_expr_pairs:
                        thens.append(
                            {
                                "Expr": expr,
                                "Key": key,
                            }
                        )
                        then_headers[key] = None
                    rules.append(
                        {
                            "BusinessScenario": business_unit_rule.business_scenario,
                            "BusinessUnit": business_unit.business_unit,
                            "IsContinue": False,
                            "Thens": thens,
                            "Whens": whens,
                        }
                    )
            config = {
                "Rules": rules,
                "ThenHeaders": list(then_headers.keys()),
                "WhenHeaders": list(when_headers.keys()),
            }
            match_transform_specs.append(
                {
                    "id": self._generate_component_id(),
                    "app_id": self._app_id,
                    "warehouse_name": self._warehouse_name,
                    "name": match_transform.component_name,
                    "type": "TABLE_MATCH_TRANSFORM",
                    "spec_version": "v0.0.0",
                    "describe": match_transform.description,
                    "config": config,
                    "config_version": "v1",
                    "config_version_seq": 1,
                    "is_external_dsl": 2,
                }
            )
        return match_transform_specs

    def _generate_component_id(self) -> int:
        component_id = self._next_component_id
        self._next_component_id += 1
        return component_id


def _calculate_node_uuid(component_name: str, node_name: str) -> str:
    return str(
        uuid.UUID(hex=hashlib.md5(f"{component_name}:{node_name}".encode()).hexdigest())
    )
