import json
import os
from dataclasses import dataclass
from typing import Iterator

import jsonschema


@dataclass(kw_only=True)
class KeyInfo:
    key: str
    index: int
    type: str


class KeyRegistry:
    __slots__ = (
        "_processed_warehouse_dir_names",
        "_key_infos",
    )

    def __init__(self) -> None:
        self._processed_warehouse_dir_names: set[str] = set()
        self._key_infos: dict[str, KeyInfo] = {}

    def load_keys_from_warehouse(self, warehouse_dir_name: str) -> None:
        if warehouse_dir_name in self._processed_warehouse_dir_names:
            return

        self._parse_symbol_file(warehouse_dir_name)
        self._parse_symbol_table_file(warehouse_dir_name)

        self._processed_warehouse_dir_names.add(warehouse_dir_name)

    def _parse_symbol_file(self, warehouse_dir_name: str) -> None:
        symbol_file_name = os.path.join(warehouse_dir_name, "symbol.json")

        with open(symbol_file_name, "r") as f:
            key_info_list = json.load(f)

        jsonschema.validate(key_info_list, _key_info_list_schema)

        for key_info in key_info_list:
            key = key_info["Key"]
            self._key_infos[key] = KeyInfo(
                key=key, index=key_info["Idx"], type=key_info["Type"]
            )

    def _parse_symbol_table_file(self, warehouse_dir_name: str) -> None:
        # we love hacking

        def get_underlying_type(s: str, i: int) -> tuple[str | None, int]:
            ss = "\nvar symbolTableGetFor"
            j = s.find(ss, i)
            if j == -1:
                return None, -1
            i = j + len(ss)

            ss = "="
            j = s.find(ss, i)
            if j == -1:
                return None, -1
            target = s[i:j]
            i = j + len(ss)

            underlying_type = _underlying_types.get(target.rstrip())

            return underlying_type, i

        def get_key_infos(s: str, i: int) -> tuple[Iterator[KeyInfo], int]:
            ss = "{"
            j = s.find(ss, i)
            if j == -1:
                return iter(()), -1
            i = j + len(ss)

            ss = "}"
            j = s.find(ss, i)
            if j == -1:
                return iter(()), -1
            target = s[i:j]
            i = j + len(ss)

            key_infos = do_get_key_infos(target)

            return key_infos, i

        def do_get_key_infos(s: str) -> Iterator[KeyInfo]:
            i = 0
            while True:
                ss = ":"
                j = s.find(ss, i)
                if j == -1:
                    return
                target = s[i:j]
                i = j + len(ss)

                key_info = self._key_infos.get(target.strip())

                ss = "\n"
                j = s.find(ss, i)
                if j == -1:
                    return
                i = j + len(ss)

                if key_info is not None:
                    yield key_info

        symbol_table_file_name = os.path.join(warehouse_dir_name, "symbol_table.go")
        with open(symbol_table_file_name, "r") as f:
            source_code = f.read()

        i = 0
        while True:
            underlying_type, i = get_underlying_type(source_code, i)
            if i == -1:
                break
            if underlying_type is None:
                continue

            key_infos, i = get_key_infos(source_code, i)
            if i == -1:
                break
            for key_info in key_infos:
                key_info.type = underlying_type

    def lookup_key(self, key: str) -> KeyInfo | None:
        return self._key_infos.get(key)


_key_info_list_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Idx": {"type": "integer"},
            "Key": {"type": "string", "minLength": 1},
            "Type": {"type": "string", "minLength": 1},
        },
        "required": ["Idx", "Key"],
    },
}

_underlying_types = {
    "Bool": "bool",
    "BoolPtr": "*bool",
    "EnumInt32": "int32",
    "EnumInt32Slice": "[]int32",
    "Float32": "float32",
    "Float32Ptr": "*float32",
    "Float32Slice": "[]float32",
    "Float64": "float64",
    "Float64Ptr": "*float64",
    "Float64Slice": "[]float64",
    "Int32": "int32",
    "Int32Ptr": "*int32",
    "Int32Slice": "[]int32",
    "Int64": "int64",
    "Int64Ptr": "*int64",
    "Int64Slice": "[]int64",
    "Int": "int",
    "IntPtr": "*int",
    "IntSlice": "[]int",
    "StringBoolMap": "map[string]bool",
    "StringPtr": "*string",
    "StringSlice": "[]string",
    "String": "string",
}
