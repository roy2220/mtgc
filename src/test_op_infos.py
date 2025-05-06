import json
from dataclasses import dataclass

import jsonschema


@dataclass(kw_only=True)
class TestOpInfo:
    op: str
    reverse_op: str

    min_number_of_values: int = 0
    max_number_of_values: int | None = None
    number_of_subkeys: int = 0
    equals_real_values: bool = False
    unequals_real_values: bool = False
    multiple_op: str | None = None
    single_op: str | None = None


test_op_infos: dict[str, TestOpInfo] = {
    "in": TestOpInfo(
        op="in",
        reverse_op="nin",
        min_number_of_values=1,
        equals_real_values=True,
        single_op="eq",
    ),
    "nin": TestOpInfo(
        op="nin",
        reverse_op="in",
        min_number_of_values=1,
        unequals_real_values=True,
        single_op="neq",
    ),
    "eq": TestOpInfo(
        op="eq",
        reverse_op="neq",
        min_number_of_values=1,
        max_number_of_values=1,
        equals_real_values=True,
        multiple_op="in",
    ),
    "neq": TestOpInfo(
        op="neq",
        reverse_op="eq",
        min_number_of_values=1,
        max_number_of_values=1,
        unequals_real_values=True,
        multiple_op="nin",
    ),
    "gt": TestOpInfo(
        op="gt",
        reverse_op="lte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "lte": TestOpInfo(
        op="lte",
        reverse_op="gt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "lt": TestOpInfo(
        op="lt",
        reverse_op="gte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "gte": TestOpInfo(
        op="gte",
        reverse_op="lt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "len_eq": TestOpInfo(
        op="len_eq",
        reverse_op="len_neq",
        min_number_of_values=1,
        max_number_of_values=1,
        equals_real_values=True,
    ),
    "len_neq": TestOpInfo(
        op="len_neq",
        reverse_op="len_eq",
        min_number_of_values=1,
        max_number_of_values=1,
        unequals_real_values=True,
    ),
    "len_gt": TestOpInfo(
        op="len_gt",
        reverse_op="len_lte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "len_lte": TestOpInfo(
        op="len_lte",
        reverse_op="len_gt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "len_lt": TestOpInfo(
        op="len_lt",
        reverse_op="len_gte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "len_gte": TestOpInfo(
        op="len_gte",
        reverse_op="len_lt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_in": TestOpInfo(
        op="v_in",
        reverse_op="v_nin",
        min_number_of_values=1,
        single_op="v_eq",
    ),
    "v_nin": TestOpInfo(
        op="v_nin",
        reverse_op="v_in",
        min_number_of_values=1,
        single_op="v_neq",
    ),
    "v_in_list": TestOpInfo(
        op="v_in_list",
        reverse_op="v_nin_list",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_nin_list": TestOpInfo(
        op="v_nin_list",
        reverse_op="v_in_list",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_eq": TestOpInfo(
        op="v_eq",
        reverse_op="v_neq",
        min_number_of_values=1,
        max_number_of_values=1,
        multiple_op="v_in",
    ),
    "v_neq": TestOpInfo(
        op="v_neq",
        reverse_op="v_eq",
        min_number_of_values=1,
        max_number_of_values=1,
        multiple_op="v_nin",
    ),
    "v_gt": TestOpInfo(
        op="v_gt",
        reverse_op="v_lte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_lte": TestOpInfo(
        op="v_lte",
        reverse_op="v_gt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_lt": TestOpInfo(
        op="v_lt",
        reverse_op="v_gte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_gte": TestOpInfo(
        op="v_gte",
        reverse_op="v_lt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_len_eq": TestOpInfo(
        op="v_len_eq",
        reverse_op="v_len_neq",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_len_neq": TestOpInfo(
        op="v_len_neq",
        reverse_op="v_len_eq",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_len_gt": TestOpInfo(
        op="v_len_gt",
        reverse_op="v_len_lte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_len_lte": TestOpInfo(
        op="v_len_lte",
        reverse_op="v_len_gt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_len_lt": TestOpInfo(
        op="v_len_lt",
        reverse_op="v_len_gte",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_len_gte": TestOpInfo(
        op="v_len_gte",
        reverse_op="v_len_lt",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "has_substring": TestOpInfo(
        op="has_substring",
        reverse_op="not_has_substring",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "not_has_substring": TestOpInfo(
        op="not_has_substring",
        reverse_op="has_substring",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "regex": TestOpInfo(
        op="regex",
        reverse_op="not_regex",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "not_regex": TestOpInfo(
        op="not_regex",
        reverse_op="regex",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "has_prefix": TestOpInfo(
        op="has_prefix",
        reverse_op="not_has_prefix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "not_has_prefix": TestOpInfo(
        op="not_has_prefix",
        reverse_op="has_prefix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "has_suffix": TestOpInfo(
        op="has_suffix",
        reverse_op="not_has_suffix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "not_has_suffix": TestOpInfo(
        op="not_has_suffix",
        reverse_op="has_suffix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_has_substring": TestOpInfo(
        op="has_substring",
        reverse_op="not_has_substring",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_not_has_substring": TestOpInfo(
        op="not_has_substring",
        reverse_op="has_substring",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_regex": TestOpInfo(
        op="regex",
        reverse_op="not_regex",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_not_regex": TestOpInfo(
        op="not_regex",
        reverse_op="regex",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_has_prefix": TestOpInfo(
        op="has_prefix",
        reverse_op="not_has_prefix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_not_has_prefix": TestOpInfo(
        op="not_has_prefix",
        reverse_op="has_prefix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_has_suffix": TestOpInfo(
        op="has_suffix",
        reverse_op="not_has_suffix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
    "v_not_has_suffix": TestOpInfo(
        op="not_has_suffix",
        reverse_op="has_suffix",
        min_number_of_values=1,
        max_number_of_values=1,
    ),
}

_custom_test_op_infos = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "minLength": 1},
            "reverse_op": {"type": "string", "minLength": 1},
            "min_number_of_values": {"type": "integer", "minimum": 0},
            "max_number_of_values": {"type": "integer", "minimum": 0},
            "number_of_subkeys": {"type": "integer", "minimum": 0},
            "equals_real_values": {"type": "boolean"},
            "unequals_real_values": {"type": "boolean"},
            "multiple_op": {"type": "string", "minLength": 1},
            "single_op": {"type": "string", "minLength": 1},
        },
        "required": ["op", "reverse_op"],
    },
}


def load_custom_test_op_infos_from_file(file_name: str) -> None:
    with open(file_name, "r") as f:
        data = f.read()
    try:
        raw_custom_test_op_infos = json.loads(data)
    except Exception:
        raise InvalidCustomTestOpInfoDataError(f"{repr(file_name)} not a JSON file")

    try:
        jsonschema.validate(raw_custom_test_op_infos, _custom_test_op_infos)
    except Exception as e:
        raise InvalidCustomTestOpInfoDataError(str(e))

    for raw_custom_test_op_info in raw_custom_test_op_infos:
        test_op_infos[raw_custom_test_op_info["op"]] = TestOpInfo(
            **raw_custom_test_op_info
        )


def replace_with_real_op(op: str) -> str:
    match op:
        case "v_in_list":
            return "v_in"
        case "v_nin_list":
            return "v_nin"
        case _:
            return op


class InvalidCustomTestOpInfoDataError(Exception):
    pass
