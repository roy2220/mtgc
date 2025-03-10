import unittest
from io import StringIO

from src.analyzer import Analyzer
from src.parser import Parser
from src.scanner import Scanner


class TestAnalyzer(unittest.TestCase):
    def test_get_composite_statement(self):
        source = """\
if test(1001, "eq", "aaa") {
    return 1
}

if test(1001, "eq", "bbb") {

    if !test(2001, "eq", "ccc") {
        return 2
    }

} else {

    switch get(3001) {
    case "xxx":
        return 3

    case "yyy":

    default:
        return 4
    }
}

return 5
"""
        scanner = Scanner(StringIO(source))
        parser = Parser(scanner)
        analyzer = Analyzer(parser.get_program())
        for rp in analyzer.get_return_points():
            print(rp.condiction, "==>", rp.return_value)


if __name__ == "__main__":
    unittest.main()
