import argparse
import glob
import os
import sys

from termcolor import colored

from .analyzer import Analyzer, Component
from .analyzer import Error as AnalyzerError
from .excel_generator import ExcelGenerator
from .key_registry import KeyRegistry
from .linter import Linter
from .match_transform_generator import MatchTransformGenerator
from .parser import Error as ParserError
from .parser import Parser
from .scanner import Error as ScannerError
from .scanner import Scanner
from .test_op_infos import load_custom_test_op_infos_from_file

_error_mark = "[" + colored("ERROR", "red", attrs=["bold"]) + "] "
_warning_mark = "[" + colored("WARNING", "yellow", attrs=["bold"]) + "] "


def main() -> None:
    parser = argparse.ArgumentParser(prog="mtgc")
    parser.add_argument(
        "DIR",
        nargs=1,
        type=str,
        help="input dir containing mtg files",
    )
    parser.add_argument(
        "-p",
        metavar="DIR",
        nargs=1,
        type=str,
        required=True,
        help="output program file",
    )
    parser.add_argument(
        "-g",
        metavar="DIR",
        nargs=1,
        type=str,
        required=True,
        help="output go program loader file",
    )
    parser.add_argument(
        "-e",
        metavar="FILE",
        nargs=1,
        type=str,
        required=True,
        help="output excel file",
    )
    parser.add_argument(
        "-d",
        metavar="FILE",
        nargs=1,
        type=str,
        required=False,
        help="output debug map file",
    )
    namespace = parser.parse_args(sys.argv[1:])
    mtg_dir_name = namespace.DIR[0]
    program_file_name = namespace.p[0]
    go_program_loader_file_name = namespace.g[0]
    excel_file_name = namespace.e[0]
    debug_map_file_name = namespace.d[0]

    mtg_file_names = glob.glob(os.path.join(mtg_dir_name, "*.mtg"))
    mtg_file_names.sort()

    if len(mtg_file_names) == 0:
        raise SystemExit(f"no mtg file found in {repr(mtg_dir_name)}")

    try:
        components, key_registry = _compile_mtg_files(
            mtg_dir_name=mtg_dir_name,
            mtg_file_names=mtg_file_names,
            program_file_name=program_file_name,
            go_program_loader_file_name=go_program_loader_file_name,
            excel_file_name=excel_file_name,
            debug_map_file_name=debug_map_file_name,
        )
    except (ScannerError, AnalyzerError, ParserError) as e:
        sys.stderr.write(_error_mark + str(e) + "\n")
        sys.exit(1)

    linter = Linter(components, key_registry)
    for warning in linter.check_components():
        sys.stderr.write(_warning_mark + warning + "\n")


def _compile_mtg_files(
    *,
    mtg_dir_name: str,
    mtg_file_names: list[str],
    program_file_name: str,
    go_program_loader_file_name: str,
    excel_file_name: str,
    debug_map_file_name: str | None,
) -> tuple[list[Component], KeyRegistry]:
    custom_test_op_infos_file_name = os.path.join(
        mtg_dir_name, ".custom_test_op_infos.json"
    )
    if os.path.exists(custom_test_op_infos_file_name):
        load_custom_test_op_infos_from_file(custom_test_op_infos_file_name)

    key_registry = KeyRegistry()
    components: list[Component] = []
    for mtg_file_name in mtg_file_names:
        with open(mtg_file_name, "r") as f:
            scanner = Scanner(
                f, mtg_file_name, os.path.relpath(mtg_file_name, mtg_dir_name)
            )
            parser = Parser(scanner, key_registry)
            analyzer = Analyzer(parser.get_component_declaration())
            components.append(analyzer.get_component())

    match_transform_generator = MatchTransformGenerator(
        components,
        program_file_name,
        go_program_loader_file_name,
        debug_map_file_name,
        key_registry,
    )
    match_transform_generator.dump_components()

    excel_generator = ExcelGenerator(components, excel_file_name)
    excel_generator.dump_components()

    return components, key_registry


if __name__ == "__main__":
    main()
