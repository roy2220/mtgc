from typing import Any, Callable

pipeline_classes = []
match_transform_classes = []


def TABLE_PIPELINE(component_name: str) -> Callable[[type], type]:
    def wrapper(c: type) -> type:
        pipeline_classes.append(c)
        return c

    return wrapper


def HEAD() -> Callable[[Callable[[Any], "Next"]], Callable[[Any], "Next"]]:
    def wrapper(f: Callable[[Any], "Next"]) -> Callable[[Any], "Next"]:
        return f

    return wrapper


def NODE(
    bound_component_name: str,
) -> Callable[[Callable[[Any], "Next"]], Callable[[Any], "Next"]]:
    def wrapper(f: Callable[[Any], "Next"]) -> Callable[[Any], "Next"]:
        return f

    return wrapper


class Next:
    def __init__(self, next_node: Callable[[], "Next"] | None) -> None:
        pass


def TABLE_MATCH_TRANSFORM(component_name: str) -> Callable[[type], type]:
    def wrapper(c: type) -> type:
        match_transform_classes.append(c)
        return c

    return wrapper


def BUSINESS_UNIT(
    business_unit: str,
) -> Callable[[Callable[[Any], "Set"]], Callable[[Any], "Set"]]:
    def wrapper(f: Callable[[Any], "Set"]) -> Callable[[Any], "Set"]:
        return f

    return wrapper


class Set:
    def __init__(
        self,
        business_scenario: str,
        key_and_expr_pairs: list[tuple[str, str]],
    ) -> None:
        pass


class Test:
    def __init__(
        self,
        key: str,
        op: str,
        values: bool | int | float | str | list[bool | int | float | str],
    ) -> None:
        pass

    def __bool__(self) -> bool:
        return True
