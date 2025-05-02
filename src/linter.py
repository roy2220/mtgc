from .analyzer import Bundle, Component, ReturnPoint, Transform, Unit
from .parser import KeyInfo, KeyRegistry
from .scanner import SourceLocation


class Linter:
    __slots__ = (
        "_warnings",
        "_checkers",
    )

    def __init__(self, components: list[Component], key_registry: KeyRegistry) -> None:
        self._warnings: list[str] = []
        self._checkers: list[_Checker] = [
            _NameChecker(components, key_registry, self._warnings),
        ]

    def check_components(self) -> list[str]:
        for checker in self._checkers:
            checker.walk_components()
        return self._warnings


class _Checker:
    __slots__ = (
        "_components",
        "_key_registry",
        "_warnings",
        "_walk_level",
        "component",
        "component_name",
        "bundle",
        "bundle_name",
        "unit",
        "unit_name",
        "return_point",
        "transform",
    )

    def __init__(
        self,
        components: list[Component],
        key_registry: KeyRegistry,
        warnings: list[str],
    ) -> None:
        self._components = components
        self._key_registry = key_registry
        self._warnings = warnings
        self._walk_level = 0

    def lookup_key(self, key: str) -> KeyInfo | None:
        return self._key_registry.lookup_key(key)

    def add_warning(self, source_location: SourceLocation, message: str) -> None:
        self._warnings.append(
            f"{source_location.file_name}:{source_location.line_number}:{source_location.column_number}: {message}"
        )

    def walk_components(self) -> None:
        assert self._walk_level == 0

        for component in self._components:
            self._walk_level = 1
            self.component = component
            self.component_name = _convert_key_to_field_path(component.name)
            self.check_component()

    def check_component(self) -> None:
        pass

    def walk_bundles(self):
        assert self._walk_level == 1

        for bundle in self.component.bundles:
            self._walk_level = 2
            self.bundle = bundle
            self.bundle_name = _convert_key_to_field_path(bundle.name)
            self.check_bundle()

    def check_bundle(self) -> None:
        pass

    def walk_units(self) -> None:
        assert self._walk_level == 2

        for unit in self.bundle.units:
            self._walk_level = 3
            self.unit = unit
            self.unit_name = _convert_key_to_field_path(unit.name)
            self.check_unit()

    def check_unit(self) -> None:
        return

    def walk_return_points(self) -> None:
        assert self._walk_level == 3

        for return_point in self.unit.return_points:
            self._walk_level = 4
            self.return_point = return_point
            self.check_return_point()

    def check_return_point(self) -> None:
        pass

    def walk_transform_list(self) -> None:
        assert self._walk_level == 4

        for transform in self.return_point.transform_list:
            self._walk_level = 5
            self.transform = transform
            self.check_transform()

    def check_transform(self) -> None:
        pass


class _NameChecker(_Checker):
    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._transform_to_keys_within_bundle: dict[tuple[str, ...], SourceLocation] = (
            {}
        )
        self._transform_to_keys_within_unit: dict[tuple[str, ...], SourceLocation] = {}

    def check_component(self) -> None:
        key_info = self.lookup_key(self.component.name)
        if key_info is None:
            self.add_warning(
                self.component.source_location,
                f"component name should be a existent key, but component name {repr(self.component.name)} does not satisfy",
            )
            return

        self.walk_bundles()

    def check_bundle(self) -> None:
        self._transform_to_keys_within_bundle.clear()

        key_info = self.lookup_key(self.bundle.name)
        if key_info is None:
            self.add_warning(
                self.bundle.source_location,
                "bundle name should be a existent key, "
                + f"but bundle name {repr(self.bundle.name)} does not satisfy",
            )
            return

        if not _field_paths_are_overlap(self.component_name, self.bundle_name):
            self.add_warning(
                self.bundle.source_location,
                "bundle name should start with component name, "
                + f"but bundle name {repr(self.bundle.name)} is not like {repr(self.component.name+"[_*]")}",
            )
            return

        self.walk_units()

    def check_unit(self) -> None:
        self._transform_to_keys_within_unit.clear()

        if not _field_paths_are_overlap(self.bundle_name, self.unit_name):
            self.add_warning(
                self.unit.source_location,
                "unit name should start with bundle name, "
                + f"but unit name {repr(self.unit.name)} is not like {repr(self.bundle.name+"[_*]")}",
            )
            return

        self.walk_return_points()

        for (
            transform_to_key_x,
            source_location_x,
        ) in self._transform_to_keys_within_unit.items():
            for (
                transform_to_key_y,
                source_location_y,
            ) in self._transform_to_keys_within_bundle.items():
                if not _field_paths_are_overlap(transform_to_key_x, transform_to_key_y):
                    continue

                if len(transform_to_key_x) == len(transform_to_key_y):
                    self.add_warning(
                        source_location_x,
                        "the `to` key of transform should be set within a single unit, "
                        + f"but key {repr(_convert_field_path_to_key(transform_to_key_x))} is also set within another units at {source_location_y.line_number}:{source_location_y.column_number}",
                    )
                elif len(transform_to_key_x) > len(transform_to_key_y):
                    self.add_warning(
                        source_location_x,
                        "the `to` key of transform should be set within a single unit, "
                        + f"but key {repr(_convert_field_path_to_key(transform_to_key_x))} is also implicitly set within another units at {source_location_y.line_number}:{source_location_y.column_number}",
                    )
                else:
                    self.add_warning(
                        source_location_y,
                        "the `to` key of transform should be set within a single unit, "
                        + f"but key {repr(_convert_field_path_to_key(transform_to_key_y))} is also implicitly set within another units at {source_location_x.line_number}:{source_location_x.column_number}",
                    )

        self._transform_to_keys_within_bundle.update(
            self._transform_to_keys_within_unit
        )

    def check_return_point(self) -> None:
        self.walk_transform_list()

    def check_transform(self) -> None:
        transform_to_key = _convert_key_to_field_path(self.transform.spec["to"])

        if _field_paths_are_overlap(self.bundle_name, transform_to_key):
            if transform_to_key not in self._transform_to_keys_within_unit.keys():
                self._transform_to_keys_within_unit[transform_to_key] = (
                    self.transform.source_location
                )
        else:
            self.add_warning(
                self.transform.source_location,
                "the `to` key of transform should start with bundle name, "
                + f"but key {repr(_convert_field_path_to_key(transform_to_key))} is not like {repr(self.bundle.name+"[_*]")}",
            )


_key_2_field_path: dict[str, tuple[str, ...]] = {}


def _convert_key_to_field_path(key: str) -> tuple[str, ...]:
    field_path = _key_2_field_path.get(key)
    if field_path is None:
        field_path = tuple(key.split("_"))
        _key_2_field_path[key] = field_path
    return field_path


_field_path_2_key: dict[tuple[str, ...], str] = {}


def _convert_field_path_to_key(field_path: tuple[str, ...]) -> str:
    key = _field_path_2_key.get(field_path)
    if key is None:
        key = "_".join(field_path)
        _field_path_2_key[field_path] = key
    return key


def _field_paths_are_overlap(
    field_path_1: tuple[str, ...], field_path_2: tuple[str, ...]
) -> bool:
    n = min(len(field_path_1), len(field_path_2))
    return field_path_1[:n] == field_path_2[:n]
