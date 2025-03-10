import dataclasses
import json
import unittest
from io import StringIO

from src.analyzer import Analyzer
from src.parser import Parser
from src.scanner import Scanner


class TestAnalyzer(unittest.TestCase):
    def test_get_composite_statement(self):
        source = """\
component DemoInfo as "just demo"
{
    unit Test1 as "Test1"
    {
        switch get("Var_MyKey") {
            case "abc", "efg":
                return transform(`{"value": 1}`) as "Value1"
            case "xyz":
                return transform(`{"value": 2}`) as "Value2"
            default:
                return transform(`{"value": 3}`) as "Value3"
        }
        return transform(`{"value": 4}`) as "Value4"
    }

    unit Test2 as "Test2"
    {
        if test("Var_1", "eq", "100") ||
           !(test("Var_2", "eq", "200") && test("Var_3", "eq", "300")) {

            return transform(`{"value": 11}`) as "Value1"
        } else if (test("Var_4", "eq", "400") || test("Var_5", "eq", "500")) && !test("Var_6", "eq", "600") {

            return transform(`{"value": 22}`) as "Value2"
        } else {
            if true || !false {
                return transform(`{"value": 33}`) as "Value3"
            }
            return transform(`{}`) as "Value2"
        }
    }
}
"""
        scanner = Scanner(StringIO(source))
        parser = Parser(scanner)
        analyzer = Analyzer(parser.get_component_declaration())
        component = analyzer.get_component()
        print(
            json.dumps(dataclasses.asdict(component), indent="  ", ensure_ascii=False)
        )


if __name__ == "__main__":
    unittest.main()
