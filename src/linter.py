import re
from dataclasses import dataclass
from typing import Iterator

from .analyzer import Bundle, Component
from .key_registry import KeyRegistry
from .scanner import SourceLocation

type _FieldPath = tuple[str, ...]


@dataclass(kw_only=True)
class _KeyRelatedBundleNames:
    closest: dict[_FieldPath, _FieldPath]
    stub_query: dict[_FieldPath, _FieldPath]


class Linter:
    __slots__ = (
        "_warnings",
        "_checkers",
    )

    def __init__(self, components: list[Component], key_registry: KeyRegistry) -> None:
        key_related_bundle_names = self._make_key_related_bundle_names(components)

        self._warnings: list[str] = []
        self._checkers: list[_Checker] = [
            _NameChecker(
                components,
                key_registry,
                key_related_bundle_names,
                self._warnings,
            ),
            _BundleDependencyChecker(
                components,
                key_related_bundle_names,
                self._warnings,
            ),
            _UnitDependencyChecker(
                components,
                key_related_bundle_names,
                self._warnings,
            ),
            _TypeChecker(
                components,
                key_registry,
                self._warnings,
            ),
        ]

    @classmethod
    def _make_key_related_bundle_names(
        cls, components: list[Component]
    ) -> _KeyRelatedBundleNames:
        walker = _Walker(components)

        bundle_names: set[_FieldPath] = set()
        for _ in walker.walk_components():
            for _ in walker.walk_bundles():
                bundle_names.add(walker.bundle_name)

        keys: set[_FieldPath] = set()
        for _ in walker.walk_components():
            for _ in walker.walk_bundles():
                for _ in walker.walk_units():
                    for _ in walker.walk_return_points():
                        for _ in walker.walk_test_exprs():
                            keys.add(walker.test_key)
                        for _ in walker.walk_transforms():
                            keys.add(walker.to_key)
                            for _ in walker.walk_transform_operators():
                                keys.update(walker.from_keys)

        closest_bundle_names: dict[_FieldPath, _FieldPath] = {}
        stub_query_bundle_names: dict[_FieldPath, _FieldPath] = {}

        for key in keys:
            for n in reversed(range(1, 1 + len(key))):
                bundle_name = key[:n]
                if bundle_name in bundle_names:
                    closest_bundle_names[key] = bundle_name
                    break

                field_name = key[n - 1]
                if _stub_field_name_pattern.fullmatch(
                    field_name
                ) is not None and not field_name.endswith("Query"):
                    stub_query_bundle_name = bundle_name[: n - 1] + (
                        field_name + "Query",
                    )
                    if stub_query_bundle_name in bundle_names:
                        stub_query_bundle_names[key] = stub_query_bundle_name
                    break

        return _KeyRelatedBundleNames(
            closest=closest_bundle_names,
            stub_query=stub_query_bundle_names,
        )

    def check_components(self) -> list[str]:
        for checker in self._checkers:
            checker.check_components()
        return self._warnings


class _Walker:
    __slots__ = (
        "_components",
        "_walk_level",
        "component",
        "component_index",
        "component_name",
        "bundle",
        "bundle_index",
        "bundle_name",
        "unit",
        "unit_index",
        "unit_name",
        "return_point",
        "return_point_index",
        "test_expr",
        "test_key",
        "transform",
        "to_key",
        "transform_operator",
        "from_keys",
    )

    def __init__(self, components: list[Component]) -> None:
        self._components = components
        self._walk_level = 0

    def walk_components(self) -> Iterator[None]:
        assert self._walk_level == 0

        for i, component in enumerate(self._components):
            self._walk_level = 1
            self.component = component
            self.component_index = i
            self.component_name = _convert_key_to_field_path(component.name)

            yield

        if self._walk_level != 0:
            self._walk_level = 0
            delattr(self, "component")
            delattr(self, "component_index")
            delattr(self, "component_name")

    def walk_bundles(self) -> Iterator[None]:
        assert self._walk_level == 1

        for i, bundle in enumerate(self.component.bundles):
            self._walk_level = 2
            self.bundle = bundle
            self.bundle_index = i
            self.bundle_name = _convert_key_to_field_path(bundle.name)

            yield

        if self._walk_level != 1:
            self._walk_level = 1
            delattr(self, "bundle")
            delattr(self, "bundle_index")
            delattr(self, "bundle_name")

    def walk_units(self) -> Iterator[None]:
        assert self._walk_level == 2

        for i, unit in enumerate(self.bundle.units):
            self._walk_level = 3
            self.unit = unit
            self.unit_index = i
            self.unit_name = _convert_key_to_field_path(unit.name)

            yield

        if self._walk_level != 2:
            self._walk_level = 2
            delattr(self, "unit")
            delattr(self, "unit_index")
            delattr(self, "unit_name")

    def walk_return_points(self) -> Iterator[None]:
        assert self._walk_level == 3

        for i, return_point in enumerate(self.unit.return_points):
            self._walk_level = 4
            self.return_point = return_point
            self.return_point_index = i

            yield

        if self._walk_level != 3:
            self._walk_level = 3
            delattr(self, "return_point")
            delattr(self, "return_point_index")

    def walk_test_exprs(self) -> Iterator[None]:
        assert self._walk_level == 4

        for and_expr in self.return_point.or_expr.and_exprs:
            for test_expr in and_expr.test_exprs:
                self._walk_level = 5
                self.test_expr = test_expr
                self.test_key = _convert_key_to_field_path(test_expr.key)

                yield

        if self._walk_level != 4:
            self._walk_level = 4
            delattr(self, "test_expr")
            delattr(self, "test_key")

    def walk_transforms(self) -> Iterator[None]:
        assert self._walk_level == 4

        for transform in self.return_point.transform_list:
            self._walk_level = 5
            self.transform = transform
            self.to_key = _convert_key_to_field_path(transform.to)

            yield

        if self._walk_level != 4:
            self._walk_level = 4
            delattr(self, "transform")
            delattr(self, "to_key")

    def walk_transform_operators(self) -> Iterator[None]:
        assert self._walk_level == 5

        for transform_operator in self.transform.operators:
            self._walk_level = 6
            self.transform_operator = transform_operator
            self.from_keys = []
            if transform_operator.from1 is not None:
                for from_key in transform_operator.from1:
                    self.from_keys.append(_convert_key_to_field_path(from_key))

            yield

        if self._walk_level != 5:
            self._walk_level = 5
            delattr(self, "transform_operator")
            delattr(self, "from_keys")


class _Checker(_Walker):
    __slots__ = ("_warnings",)

    def __init__(self, components: list[Component], warnings: list[str]) -> None:
        super().__init__(components)
        self._warnings = warnings

    def add_warning(self, source_location: SourceLocation, message: str) -> None:
        line_directives = self.component.line_directives.get(
            source_location.line_number
        )
        if line_directives is not None:
            for line_directive in line_directives:
                if line_directive == "lint:ignore":
                    return

        self._warnings.append(
            f"{source_location.short_file_name}:{source_location.line_number}:{source_location.column_number}: {message}"
        )

    def check_components(self) -> None:
        raise NotImplementedError()


class _NameChecker(_Checker):
    __slots__ = (
        "_key_registry",
        "_key_related_bundle_names",
        "_to_keys_within_bundle",
        "_to_keys_within_unit",
        "_checked_test_ids_within_unit",
        "_to_keys_within_return_point",
    )

    def __init__(
        self,
        components: list[Component],
        key_registry: KeyRegistry,
        key_related_bundle_names: _KeyRelatedBundleNames,
        warnings: list[str],
    ) -> None:
        super().__init__(components, warnings)
        self._key_registry = key_registry
        self._key_related_bundle_names = key_related_bundle_names
        self._to_keys_within_bundle: dict[_FieldPath, SourceLocation] = {}
        self._to_keys_within_unit: dict[_FieldPath, list[SourceLocation]] = {}
        self._checked_test_ids_within_unit: set[int] = set()
        self._to_keys_within_return_point: dict[_FieldPath, SourceLocation] = {}

    def check_components(self) -> None:
        for _ in self.walk_components():
            key_info = self._key_registry.lookup_key(self.component.name)
            if key_info is None:
                self.add_warning(
                    self.component.source_location,
                    "component name should be a existent key, "
                    f"but component name {repr(self.component.name)} does not satisfy",
                )
                continue

            self._check_bundles()

    def _check_bundles(self) -> None:
        for _ in self.walk_bundles():
            self._to_keys_within_bundle.clear()

            key_info = self._key_registry.lookup_key(self.bundle.name)
            if key_info is None:
                self.add_warning(
                    self.bundle.source_location,
                    "bundle name should be a existent key, "
                    + f"but bundle name {repr(self.bundle.name)} does not satisfy",
                )
                continue

            if not _field_path_has_prefix(self.bundle_name, self.component_name):
                self.add_warning(
                    self.bundle.source_location,
                    "bundle name should start with component name, "
                    + f"but bundle name {repr(self.bundle.name)} is not like {repr(self.component.name+"[_*]")}",
                )
                continue

            self._check_units()

    def _check_units(self) -> None:
        for _ in self.walk_units():
            self._to_keys_within_unit.clear()
            self._checked_test_ids_within_unit.clear()

            if not _field_path_has_prefix(self.unit_name, self.bundle_name):
                self.add_warning(
                    self.unit.source_location,
                    "unit name should start with bundle name, "
                    + f"but unit name {repr(self.unit.name)} is not like {repr(self.bundle.name+"[_*]")}",
                )
                continue

            self._check_return_points()

            for (
                to_key_x,
                source_locations_x,
            ) in self._to_keys_within_unit.items():
                for (
                    to_key_y,
                    source_location_y,
                ) in self._to_keys_within_bundle.items():
                    if not _field_paths_are_overlap(to_key_x, to_key_y):
                        continue

                    if len(to_key_x) == len(to_key_y):
                        for source_location_x in source_locations_x:
                            self.add_warning(
                                source_location_x,
                                "duplicate `to` key of transform should only be used within a single unit, "
                                + f"but key {repr(_convert_field_path_to_key(to_key_x))} is also used within another units on line {source_location_y.line_number}",
                            )
                    elif len(to_key_x) < len(to_key_y):
                        for source_location_x in source_locations_x:
                            self.add_warning(
                                source_location_x,
                                "duplicate `to` key of transform should only be used within a single unit, "
                                + f"but key {repr(_convert_field_path_to_key(to_key_x))} is also used implicitly within another units on line {source_location_y.line_number}",
                            )
                    else:
                        for source_location_x in source_locations_x:
                            self.add_warning(
                                source_location_y,
                                "duplicate `to` key of transform should only be used within a single unit, "
                                + f"but key {repr(_convert_field_path_to_key(to_key_y))} is also used implicitly within another units on line {source_location_y.line_number}",
                            )

            for k, vs in self._to_keys_within_unit.items():
                v = self._to_keys_within_bundle.get(k)
                if v is not None:
                    continue
                self._to_keys_within_bundle[k] = vs[0]

    def _check_return_points(self) -> None:
        for _ in self.walk_return_points():
            self._to_keys_within_return_point.clear()

            self._check_test_exprs()
            self._check_transforms()

            for k, v in self._to_keys_within_return_point.items():
                vs = self._to_keys_within_unit.get(k)
                if vs is None:
                    vs = []
                    self._to_keys_within_unit[k] = vs
                vs.append(v)

    def _check_transforms(self) -> None:
        for _ in self.walk_transforms():
            if not _field_path_has_prefix(self.to_key, self.bundle_name):
                self.add_warning(
                    self.transform.source_location,
                    "the `to` key of transform should start with bundle name, "
                    + f"but key {repr(self.transform.to)} is not like {repr(self.bundle.name+"[_*]")}",
                )
                continue

            closest_bundle_name = self._key_related_bundle_names.closest.get(
                self.to_key
            )
            assert closest_bundle_name is not None
            if self.bundle_name != closest_bundle_name:
                self.add_warning(
                    self.transform.source_location,
                    "the `to` key of transform should only be used within its closest bundle, "
                    + f"but key {repr(self.transform.to)} is not used within bundle {repr(_convert_field_path_to_key(closest_bundle_name))}",
                )
                continue

            if self.to_key in self._to_keys_within_return_point.keys():
                self.add_warning(
                    self.transform.source_location,
                    "the `to` key of transform should only be used once within a transform list, "
                    + f"but key {repr(self.transform.to)} is used many times",
                )
                continue

            self._to_keys_within_return_point[self.to_key] = (
                self.transform.source_location
            )

            self._check_transform_operators()

    def _check_test_exprs(self) -> None:
        for _ in self.walk_test_exprs():
            test_id = abs(self.test_expr.test_id)
            try:
                if test_id in self._checked_test_ids_within_unit:
                    continue

                if self.test_expr.op.startswith("v_"):
                    continue

                for value in self.test_expr.values:
                    if self._key_registry.lookup_key(value) is not None:
                        self.add_warning(
                            self.test_expr.source_location,
                            "value of test is unlikely to be a existent key, "
                            + f"value {repr(value)} seems suspicious",
                        )
            finally:
                self._checked_test_ids_within_unit.add(test_id)

    def _check_transform_operators(self) -> None:
        for _ in self.walk_transform_operators():
            if (values := self.transform_operator.values) is not None:
                for value in values:
                    if self._key_registry.lookup_key(value) is not None:
                        self.add_warning(
                            self.transform.source_location,
                            "value of transform operator is unlikely to be a existent key, "
                            + f"value {repr(value)} seems suspicious",
                        )


class _BundleDependencyChecker(_Checker):
    __slots__ = (
        "_key_related_bundle_names",
        "_all_bundles",
        "_required_bundle_names",
        "_visited_bundle_names",
    )

    def __init__(
        self,
        components: list[Component],
        key_related_bundle_names: _KeyRelatedBundleNames,
        warnings: list[str],
    ) -> None:
        super().__init__(components, warnings)
        self._key_related_bundle_names = key_related_bundle_names
        self._all_bundles: dict[_FieldPath, Bundle] = {}
        self._required_bundle_names: dict[_FieldPath, set[_FieldPath]] = {}
        self._visited_bundle_names: set[_FieldPath] = set()

    def check_components(self) -> None:
        for _ in self.walk_components():
            for _ in self.walk_bundles():
                self._all_bundles[self.bundle_name] = self.bundle
                self._required_bundle_names[self.bundle_name] = set()

                for _ in self.walk_units():
                    for _ in self.walk_return_points():
                        for _ in self.walk_test_exprs():
                            self._update_required_bundle_names(self.test_key)

                        for _ in self.walk_transforms():
                            for _ in self.walk_transform_operators():
                                for from_key in self.from_keys:
                                    self._update_required_bundle_names(from_key)

        for _ in self.walk_components():
            self._check_bundles()

    def _update_required_bundle_names(self, key: _FieldPath) -> None:
        for required_bundle_name in (
            self._key_related_bundle_names.closest.get(key),
            self._key_related_bundle_names.stub_query.get(key),
        ):
            if required_bundle_name is None:
                continue
            if required_bundle_name == self.bundle_name:
                continue
            self._required_bundle_names[self.bundle_name].add(required_bundle_name)

    def _check_bundles(self) -> None:
        bundle_name_stack: list[_FieldPath] = []

        def visit_bundle(bundle_name: _FieldPath) -> None:
            if bundle_name in self._visited_bundle_names:
                return

            try:
                for i, bundle_name_2 in enumerate(bundle_name_stack):
                    if bundle_name_2 == bundle_name:
                        bundle_source_location = self._all_bundles[
                            bundle_name
                        ].source_location
                        bundle_names = bundle_name_stack[i:]
                        bundle_names.append(bundle_name)
                        bundle_path = " => ".join(
                            map(lambda x: "_".join(x), bundle_names)
                        )
                        self.add_warning(
                            bundle_source_location,
                            f"circular bundle dependency is detected: {bundle_path}",
                        )
                        return

                bundle_name_stack.append(bundle_name)
                for required_bundle_name in self._required_bundle_names[bundle_name]:
                    visit_bundle(required_bundle_name)
                bundle_name_stack.pop()
            finally:
                self._visited_bundle_names.add(bundle_name)

        for _ in self.walk_bundles():
            visit_bundle(self.bundle_name)


class _UnitDependencyChecker(_Checker):
    __slots__ = (
        "_key_related_bundle_names",
        "_to_key_2_unit_index_within_bundle",
        "_checked_test_ids_within_unit",
    )

    def __init__(
        self,
        components: list[Component],
        key_related_bundle_names: _KeyRelatedBundleNames,
        warnings: list[str],
    ) -> None:
        super().__init__(components, warnings)
        self._key_related_bundle_names = key_related_bundle_names
        self._to_key_2_unit_index_within_bundle: dict[_FieldPath, int] = {}
        self._checked_test_ids_within_unit: set[int] = set()

    def check_components(self) -> None:
        for _ in self.walk_components():
            for _ in self.walk_bundles():
                self._to_key_2_unit_index_within_bundle.clear()

                for _ in self.walk_units():
                    for _ in self.walk_return_points():
                        self._check_transforms()

                for _ in self.walk_units():
                    self._checked_test_ids_within_unit.clear()

                    for _ in self.walk_return_points():
                        self._check_test_exprs()
                        for _ in self.walk_transforms():
                            self._check_transform_operators()

    def _check_transforms(self) -> None:
        for _ in self.walk_transforms():
            closest_bundle_name = self._key_related_bundle_names.closest.get(
                self.to_key, ()
            )
            if closest_bundle_name != self.bundle_name:
                continue

            self._to_key_2_unit_index_within_bundle[self.to_key] = self.unit_index

    def _check_test_exprs(self) -> None:
        for _ in self.walk_test_exprs():
            test_id = abs(self.test_expr.test_id)
            try:
                if test_id in self._checked_test_ids_within_unit:
                    continue

                closest_bundle_name = self._key_related_bundle_names.closest.get(
                    self.test_key, ()
                )
                if closest_bundle_name != self.bundle_name:
                    continue

                test_key_is_empty = True
                for (
                    to_key,
                    unit_index,
                ) in self._to_key_2_unit_index_within_bundle.items():
                    if not _field_paths_are_overlap(self.test_key, to_key):
                        continue

                    test_key_is_empty = False
                    if unit_index > self.unit_index:
                        self.add_warning(
                            self.test_expr.source_location,
                            "test key should only be used after it has been set, "
                            + f"but key {repr(self.test_expr.key)} is not yet set",
                        )
                        break

                if test_key_is_empty:
                    self.add_warning(
                        self.test_expr.source_location,
                        "test key should only be used after it has been set, "
                        + f"but key {repr(self.test_expr.key)} has never been set",
                    )
            finally:
                self._checked_test_ids_within_unit.add(test_id)

    def _check_transform_operators(self) -> None:
        for i, _ in enumerate(self.walk_transform_operators()):
            for from_key in self.from_keys:
                closest_bundle_name = self._key_related_bundle_names.closest.get(
                    from_key, ()
                )
                if closest_bundle_name != self.bundle_name:
                    continue

                test_key_is_empty = True
                for (
                    to_key,
                    unit_index,
                ) in self._to_key_2_unit_index_within_bundle.items():
                    if not _field_paths_are_overlap(from_key, to_key):
                        continue

                    test_key_is_empty = False
                    if unit_index > self.unit_index:
                        raw_from_keys = self.transform_operator.from1
                        assert raw_from_keys is not None
                        self.add_warning(
                            self.transform.source_location,
                            "the `from` key of transform operator should only be used after it has been set, "
                            + f"but key {repr(raw_from_keys[i])} is not yet set",
                        )
                        break

                if test_key_is_empty:
                    raw_from_keys = self.transform_operator.from1
                    assert raw_from_keys is not None
                    self.add_warning(
                        self.transform.source_location,
                        "the `from` key of transform operator should only be used after it has been set, "
                        + f"but key {repr(raw_from_keys[i])} has never been set",
                    )


class _TypeChecker(_Checker):
    _integer_value_pattern = re.compile(r"-?[0-9]+")
    _float_value_pattern = re.compile(r"-?[0-9]+(\.[0-9]+)?")
    _nullable_type_pattern = re.compile(r"(\*|\[\]|map\[.*\]).*")
    _type_with_length_pattern = re.compile(r"(string|\[\]|map\[.*\]).*")

    __slots__ = (
        "_key_registry",
        "_checked_test_ids_within_unit",
        "_to_key_info",
    )

    def __init__(
        self,
        components: list[Component],
        key_registry: KeyRegistry,
        warnings: list[str],
    ) -> None:
        super().__init__(components, warnings)
        self._key_registry = key_registry
        self._checked_test_ids_within_unit: set[int] = set()

    def check_components(self) -> None:
        for _ in self.walk_components():
            for _ in self.walk_bundles():
                for _ in self.walk_units():
                    self._checked_test_ids_within_unit.clear()

                    for _ in self.walk_return_points():
                        self._check_test_exprs()
                        self._check_transforms()

    def _check_test_exprs(self) -> None:
        for _ in self.walk_test_exprs():
            test_id = abs(self.test_expr.test_id)
            try:
                if test_id in self._checked_test_ids_within_unit:
                    continue

                is_v_op = self.test_expr.op.startswith("v_")
                test_key_info_a = self._key_registry.lookup_key(self.test_expr.key)
                assert test_key_info_a is not None

                match self.test_expr.op:
                    case (
                        "in"
                        | "v_in"
                        | "nin"
                        | "v_nin"
                        | "eq"
                        | "v_eq"
                        | "neq"
                        | "v_neq"
                        | "gt"
                        | "v_gt"
                        | "lte"
                        | "v_lte"
                        | "lt"
                        | "v_lt"
                        | "gte"
                        | "v_gte"
                    ):
                        for value in self.test_expr.values:
                            if is_v_op:
                                test_key_info_b = self._key_registry.lookup_key(value)
                                assert test_key_info_b is not None
                                if not self._check_type_compatibility(
                                    test_key_info_b.type,
                                    test_key_info_a.type,
                                ):
                                    self.add_warning(
                                        self.test_expr.source_location,
                                        f"invalid test op {repr(self.test_expr.op)}, "
                                        + f"the type of test key B {repr(test_key_info_b.key)} <{test_key_info_b.type}> is incompatible with "
                                        + f"the type of test key A {repr(test_key_info_a.key)} <{test_key_info_a.type}>",
                                    )
                            else:
                                if not self._check_value_compatibility(
                                    value, test_key_info_a.type
                                ):
                                    self.add_warning(
                                        self.test_expr.source_location,
                                        f"invalid test op {repr(self.test_expr.op)}, "
                                        + f"value {"<null>" if value is None else repr(value)} is incompatible with "
                                        + f"the type of test key {repr(test_key_info_a.key)} <{test_key_info_a.type}>",
                                    )

                    case "v_in_list" | "v_nin_list":
                        for test_key_b in self.test_expr.values:
                            test_key_info_b = self._key_registry.lookup_key(test_key_b)
                            assert test_key_info_b is not None
                            if not test_key_info_b.type.startswith("[]"):
                                self.add_warning(
                                    self.test_expr.source_location,
                                    f"invalid test op {repr(self.test_expr.op)}, "
                                    + f"the type of test key B {repr(test_key_info_b.key)} <{test_key_info_b.type}> is not a slice",
                                )
                                continue
                            element_type = test_key_info_b.type[2:]
                            if not self._check_type_compatibility(
                                element_type, test_key_info_a.type
                            ):
                                self.add_warning(
                                    self.test_expr.source_location,
                                    f"invalid test op {repr(self.test_expr.op)}, "
                                    + f"the element type of test key B {repr(test_key_info_b.key)} <{element_type}> is incompatible with "
                                    + f"the type of test key A {repr(test_key_info_a.key)} <{test_key_info_a.type}>",
                                )

                    case (
                        "len_eq"
                        | "v_len_eq"
                        | "len_neq"
                        | "v_len_neq"
                        | "len_gt"
                        | "v_len_gt"
                        | "len_lte"
                        | "v_len_lte"
                        | "len_lt"
                        | "v_len_lt"
                        | "len_gte"
                        | "v_len_gte"
                    ):
                        if (
                            self._type_with_length_pattern.fullmatch(
                                test_key_info_a.type
                            )
                            is None
                        ):
                            self.add_warning(
                                self.test_expr.source_location,
                                f"invalid test op {repr(self.test_expr.op)}, "
                                + f"the type of test key {repr(test_key_info_a.key)} has no length",
                            )
                            continue

                        length_type = "int"
                        for value in self.test_expr.values:
                            if is_v_op:
                                test_key_info_b = self._key_registry.lookup_key(value)
                                assert test_key_info_b is not None
                                if not self._check_type_compatibility(
                                    test_key_info_b.type,
                                    length_type,
                                ):
                                    self.add_warning(
                                        self.test_expr.source_location,
                                        f"the type of test key B {repr(test_key_info_b.key)} <{test_key_info_b.type}> is incompatible with "
                                        + f"the length type <{length_type}>",
                                    )
                            else:
                                if not self._check_value_compatibility(
                                    value, length_type
                                ):
                                    self.add_warning(
                                        self.test_expr.source_location,
                                        f"invalid test op {repr(self.test_expr.op)}, "
                                        + f"value {"<null>" if value is None else repr(value)} is incompatible with "
                                        + f"the length type <{length_type}>",
                                    )
            finally:
                self._checked_test_ids_within_unit.add(test_id)

    def _check_transforms(self) -> None:
        for _ in self.walk_transforms():
            to_key_info = self._key_registry.lookup_key(self.transform.to)
            assert to_key_info is not None
            self._to_key_info = to_key_info
            self._check_transform_operators()

    def _check_transform_operators(self) -> None:
        for _ in self.walk_transform_operators():
            if (
                self.transform_operator.op == "bypass"
                and len(self.transform.operators) == 1
            ):
                if (from1 := self.transform_operator.from1) is not None:
                    from_key_info = self._key_registry.lookup_key(from1[0])
                    assert from_key_info is not None
                    if not self._check_type_compatibility(
                        from_key_info.type, self._to_key_info.type
                    ):
                        self.add_warning(
                            self.transform.source_location,
                            f"the type of `from` key {repr(from_key_info.key)} <{from_key_info.type}> is incompatible with "
                            + f"the type of `to` key {repr(self._to_key_info.key)} <{self._to_key_info.type}>",
                        )
                else:
                    if (values := self.transform_operator.values) is None:
                        value = None
                    else:
                        value = values[0]
                    if not self._check_value_compatibility(
                        value, self._to_key_info.type
                    ):
                        self.add_warning(
                            self.transform.source_location,
                            f"value {"<null>" if value is None else repr(value)} is incompatible with "
                            + f"the type of `to` key {repr(self._to_key_info.key)} <{self._to_key_info.type}>",
                        )

    @classmethod
    def _check_value_compatibility(cls, value: str | None, to_type: str) -> bool:
        if value is None:
            return cls._nullable_type_pattern.fullmatch(to_type) is not None
        match to_type:
            case "string":
                return True
            case "bool":
                return value in ("true", "false")
            case (
                "int"
                | "int8"
                | "int16"
                | "int32"
                | "int64"
                | "uint"
                | "uint8"
                | "uint16"
                | "uint32"
                | "uint64"
            ):
                return cls._integer_value_pattern.fullmatch(value) is not None
            case "float32" | "float64":
                return cls._float_value_pattern.fullmatch(value) is not None
        return False

    @classmethod
    def _check_type_compatibility(cls, from_type: str, to_type: str) -> bool:
        if from_type == to_type:
            return True
        match to_type:
            case "string":
                return from_type in (
                    "bool",
                    "int",
                    "int8",
                    "int16",
                    "int32",
                    "int64",
                    "uint",
                    "uint8",
                    "uint16",
                    "uint32",
                    "uint64",
                    "float32",
                    "float64",
                )
            case (
                "int"
                | "int8"
                | "int16"
                | "int32"
                | "int64"
                | "uint"
                | "uint8"
                | "uint16"
                | "uint32"
                | "uint64"
            ):
                return from_type in (
                    "int",
                    "int8",
                    "int16",
                    "int32",
                    "int64",
                    "uint",
                    "uint8",
                    "uint16",
                    "uint32",
                    "uint64",
                )
            case "float32" | "float64":
                return from_type in (
                    "int",
                    "int8",
                    "int16",
                    "int32",
                    "int64",
                    "uint",
                    "uint8",
                    "uint16",
                    "uint32",
                    "uint64",
                    "float32",
                    "float64",
                )
        return False


_field_path_separator = "_"
_key_2_field_path: dict[str, _FieldPath] = {}
_field_path_2_key: dict[_FieldPath, str] = {}


def _convert_key_to_field_path(key: str) -> _FieldPath:
    field_path = _key_2_field_path.get(key)
    if field_path is None:
        field_path = tuple(key.split(_field_path_separator))
        _key_2_field_path[key] = field_path
    return field_path


def _convert_field_path_to_key(field_path: _FieldPath) -> str:
    key = _field_path_2_key.get(field_path)
    if key is None:
        key = _field_path_separator.join(field_path)
        _field_path_2_key[field_path] = key
    return key


def _field_path_has_prefix(
    field_path: _FieldPath, field_path_prefix: _FieldPath
) -> bool:
    n = len(field_path_prefix)
    return len(field_path) >= n and field_path[:n] == field_path_prefix


def _field_paths_are_overlap(
    field_path_1: _FieldPath, field_path_2: _FieldPath
) -> bool:
    n = min(len(field_path_1), len(field_path_2))
    return field_path_1[:n] == field_path_2[:n]


_stub_field_name_pattern = re.compile(r"Stub[A-Z].*")
