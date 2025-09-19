from typing import Any, Callable

pipeline_classes = []
match_transform_classes = []
private_component_classes = []


def TABLE_PIPELINE() -> Callable[[type], type]:
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


def TABLE_MATCH_TRANSFORM() -> Callable[[type], type]:
    def wrapper(c: type) -> type:
        match_transform_classes.append(c)
        return c

    return wrapper


class Next:
    def __init__(self, next_node: Callable[[], "Next"] | None) -> None:
        pass


def BUSINESS_UNIT(
    business_unit: str,
) -> Callable[[Callable[[Any], "Set"]], Callable[[Any], "Set"]]:
    def wrapper(f: Callable[[Any], "Set"]) -> Callable[[Any], "Set"]:
        return f

    return wrapper


def describe(descriptions: str) -> Callable[[type], type]:
    def wrapper(c: type) -> type:
        return c

    return wrapper


def TABLE_PRIVATE_COMPONENT() -> Callable[[type], type]:
    def wrapper(c: type) -> type:
        private_component_classes.append(c)
        return c

    return wrapper


class Set:
    def __init__(
        self,
        business_scenario: str,
        *key_and_expr_pairs: tuple[str, str],
    ) -> None:
        pass


class Test:
    def __init__(self, key: str, expr: str) -> None:
        pass

    def __bool__(self) -> bool:
        return True
