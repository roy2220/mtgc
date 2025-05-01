from .analyzer import Bundle, Component, ReturnPoint, Transform, Unit
from .parser import KeyRegistry
from .scanner import SourceLocation


class Linter:
    __slots__ = (
        "_components",
        "_key_registry",
        "_warnings",
        "_transform_to_keys_within_bundle",
        "_transform_to_keys_within_unit",
    )

    def __init__(self, components: list[Component], key_registry: KeyRegistry) -> None:
        self._components = components
        self._key_registry = key_registry
        self._warnings: list[str] = []
        self._transform_to_keys_within_bundle: dict[str, Unit] = {}
        self._transform_to_keys_within_unit: dict[str, SourceLocation] = {}

    def check_components(self) -> list[str]:
        for component in self._components:
            self._check_component(component)
        return self._warnings

    def _check_component(self, component: Component) -> None:
        key_index = self._key_registry.lookup_key(component.name)
        if key_index is None:
            self._add_warning(
                component.source_location,
                f"component name should be a symbol key, but component name {repr(component.name)} does not satisfy",
            )
            return

        for bundle in component.bundles:
            self._transform_to_keys_within_bundle.clear()
            self._check_bundle(component, bundle)

    def _check_bundle(self, component: Component, bundle: Bundle) -> None:
        key_index = self._key_registry.lookup_key(bundle.name)
        if key_index is None:
            self._add_warning(
                bundle.source_location,
                f"bundle name should be a symbol key, but bundle name {repr(bundle.name)} does not satisfy",
            )
            return

        if not (
            bundle.name == component.name
            or bundle.name.startswith(component.name + "_")
        ):
            self._add_warning(
                bundle.source_location,
                f"bundle name should start with component name, but bundle name {repr(bundle.name)} is not {repr(component.name+"[_*]")}",
            )
            return

        for unit in bundle.units:
            self._transform_to_keys_within_unit.clear()
            self._check_unit(bundle, unit)

            shared_transform_to_keys = (
                self._transform_to_keys_within_unit.keys()
                & self._transform_to_keys_within_bundle.keys()
            )
            for transform_to_key in shared_transform_to_keys:
                source_location = self._transform_to_keys_within_unit[transform_to_key]
                another_unit = self._transform_to_keys_within_bundle[transform_to_key]
                self._add_warning(
                    source_location,
                    f"key to which transform is applied should be used within only one unit, but key {repr(transform_to_key)} is used within both units {repr(unit.name)} and {repr(another_unit.name)}",
                )
            for transform_to_key in self._transform_to_keys_within_unit:
                if transform_to_key not in self._transform_to_keys_within_bundle:
                    self._transform_to_keys_within_bundle[transform_to_key] = unit

    def _check_unit(self, bundle: Bundle, unit: Unit) -> None:
        if not (unit.name == bundle.name or unit.name.startswith(bundle.name + "_")):
            self._add_warning(
                unit.source_location,
                f"unit name should start with bundle name, but unit name {repr(unit.name)} is not {repr(bundle.name+"[_*]")}",
            )

        for return_point in unit.return_points:
            self._check_return_point(bundle, unit, return_point)

    def _check_return_point(
        self, bundle: Bundle, unit: Unit, return_point: ReturnPoint
    ) -> None:
        for transform in return_point.transform_list:
            transform_to_key = transform.spec["to"]

            if transform_to_key.startswith(bundle.name + "_"):
                if transform_to_key not in self._transform_to_keys_within_unit.keys():
                    self._transform_to_keys_within_unit[transform_to_key] = (
                        transform.source_location
                    )
            else:
                self._add_warning(
                    transform.source_location,
                    f"key to which transform is applied should start with bundle name, but key {repr(transform_to_key)} is not {repr(bundle.name+"[_*]")}",
                )

    def _add_warning(self, source_location: SourceLocation, message: str) -> None:
        self._warnings.append(
            f"{source_location.file_name}:{source_location.line_number}:{source_location.column_number}: {message}"
        )
