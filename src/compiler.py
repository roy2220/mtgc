import argparse
import glob
import os
import sys

from .analyzer import Analyzer, Component
from .excel_generator import ExcelGenerator
from .match_transform_generator import MatchTransformGenerator
from .parser import Parser
from .scanner import Scanner
from .test_op_infos import load_custom_test_op_infos_from_file


def main() -> None:
    parser = argparse.ArgumentParser(prog="mtgc")
    parser.add_argument(
        "DIR",
        nargs=1,
        type=str,
        help="input dir containing mtg files",
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
        "-m",
        metavar="DIR",
        nargs=1,
        type=str,
        required=True,
        help="output dir for match-transform files",
    )
    parser.add_argument(
        "-d",
        metavar="FILE",
        nargs=1,
        type=str,
        required=False,
        help="output debug log file",
    )
    namespace = parser.parse_args(sys.argv[1:])
    mtg_dir_name = namespace.DIR[0]
    excel_file_name = namespace.e[0]
    debug_log_file_name = namespace.d[0]
    match_transform_dir_name = namespace.m[0]

    mtg_file_names = glob.glob(os.path.join(mtg_dir_name, "*.mtg"))
    mtg_file_names.sort()

    if len(mtg_file_names) == 0:
        raise SystemExit(f"no mtg file found in {repr(mtg_dir_name)}")

    custom_test_op_infos_file_name = os.path.join(
        mtg_dir_name, ".custom_test_op_infos.json"
    )
    if os.path.exists(custom_test_op_infos_file_name):
        load_custom_test_op_infos_from_file(custom_test_op_infos_file_name)

    components: list[Component] = []
    for mtg_file_name in mtg_file_names:
        with open(mtg_file_name, "r") as f:
            scanner = Scanner(f)
            parser = Parser(scanner)
            analyzer = Analyzer(parser.get_component_declaration())
            components.append(analyzer.get_component())

    excel_generator = ExcelGenerator(components, excel_file_name)
    excel_generator.dump_components()

    match_transform_generator = MatchTransformGenerator(
        components, match_transform_dir_name, debug_log_file_name
    )
    match_transform_generator.dump_components()


if __name__ == "__main__":
    main()
