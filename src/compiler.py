import argparse
import glob
import os
import sys

from src.analyzer import Analyzer, Component
from src.excel_generator import ExcelGenerator
from src.parser import Parser
from src.scanner import Scanner


def main() -> None:
    parser = argparse.ArgumentParser(prog="mtgc")
    parser.add_argument(
        "-e",
        metavar="FILE",
        nargs=1,
        type=str,
        required=True,
        help="output excel file",
    )
    parser.add_argument(
        "DIR",
        nargs=1,
        type=str,
        help="input dir containing mtg files",
    )
    namespace = parser.parse_args(sys.argv[1:])
    mtg_dir_name = namespace.DIR[0]
    excel_file_name = namespace.e[0]
    mtg_file_names = glob.glob(os.path.join(mtg_dir_name, "*.mtg"))

    if len(mtg_file_names) == 0:
        raise SystemExit(f"no mtg file found in {repr(mtg_dir_name)}")

    components: list[Component] = []
    for mtg_file_name in mtg_file_names:
        with open(mtg_file_name, "r") as f:
            scanner = Scanner(f)
            parser = Parser(scanner)
            analyzer = Analyzer(parser.get_component_declaration())
            components.append(analyzer.get_component())

    excel_generator = ExcelGenerator(components, excel_file_name)
    excel_generator.dump_components()


if __name__ == "__main__":
    main()
