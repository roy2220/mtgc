import dataclasses
import json
import unittest
from io import StringIO

from src.analyzer import Analyzer
from src.excel_generator import ExcelGenerator
from src.parser import Parser
from src.scanner import Scanner


class TestExcelGenerator(unittest.TestCase):
    def test_get_composite_statement(self):
        source = """\
import "/workspace/tracking/internal/domain/warehouse/symbol.json"

component DemandFilterFlag as "过滤打标组件"
{
    unit DemandFilterFlag as "Demand 视角 - 最终过滤打标"
    {
        if test("FilterContext_DemandCountryFilterFlag_IsFilter", "eq", "true") {

                return transform(`[
                    {
                        "operators": [{"op": "bool/set", "values": ["true"], "op_type": "FilterContext"}],
                        "to": "FilterContext_DemandFilterFlag_IsFilter"
                    },
                    {
                        "operators": [{"op": "bypass", "values": ["demand_country_filter"]}],
                        "to": "FilterContext_DemandFilterFlag_FilterReason"
                    }
                ]`) as "国家匹配过滤"

        }

        if test("FilterContext_DemandDuplicateFilterFlag_IsFilter", "eq", "true") {

                return transform(`[
                    {
                        "operators": [{"op": "bool/set", "values": ["true"], "op_type": "FilterContext"}],
                        "to": "FilterContext_DemandFilterFlag_IsFilter"
                    },
                    {
                        "operators": [{"op": "bypass", "values": ["demand_duplicate_filter"]}],
                        "to": "FilterContext_DemandFilterFlag_FilterReason"
                    }
                ]`) as "流量去重过滤"

        }

        return transform(`[
            {
                "operators": [{"op": "bool/set", "values": ["false"], "op_type": "FilterContext"}],
                "to": "FilterContext_DemandFilterFlag_IsFilter"
            }
        ]`) as "默认正常流量"

    }

    unit DemandDuplicateFilterFlag as "广告主视角 - 流量去重过滤打标"
    {
        switch get("RequestInfo_BasicInfo_RequestScenario") {
            case "click":

                if test("DemandInfo_RequestDuplicate_IsDuplicate", "eq", "true") {

                    return transform(`[
                        {
                            "operators": [{"op": "bool/set", "values": ["true"], "op_type": "FilterContext"}],
                            "to": "FilterContext_DemandDuplicateFilterFlag_IsFilter"
                        },
                        {
                            "operators": [{"op": "bypass", "values": ["duplicate_request"]}],
                            "to": "FilterContext_DemandDuplicateFilterFlag_FilterReason"
                        }
                    ]`) as "点击请求纬度去重"

                }

                if test("DemandInfo_CCTDuplicate_IsDuplicate", "eq", "true") {

                    return transform(`[
                        {
                            "operators": [{"op": "bool/set", "values": ["true"], "op_type": "FilterContext"}],
                            "to": "FilterContext_DemandDuplicateFilterFlag_IsFilter"
                        },
                        {
                            "operators": [{"op": "bypass", "values": ["duplicate_cct"]}],
                            "to": "FilterContext_DemandDuplicateFilterFlag_FilterReason"
                        }
                    ]`) as "CCT用户维度去重"

                }

            case "impression":

                if test("DemandInfo_RequestDuplicate_IsDuplicate", "eq", "true") {

                    return transform(`[
                        {
                            "operators": [{"op": "bool/set", "values": ["true"], "op_type": "FilterContext"}],
                            "to": "FilterContext_DemandDuplicateFilterFlag_IsFilter"
                        },
                        {
                            "operators": [{"op": "bypass", "values": ["duplicate_request"]}],
                            "to": "FilterContext_DemandDuplicateFilterFlag_FilterReason"
                        }
                    ]`) as "展示请求纬度去重"

                }
        }

        return transform(`[]`) as "默认不去重"
    }

    unit DemandCountryFilterFlag as "广告主视角 - 国家匹配过滤打标"
    {
        if test("RequestInfo_BasicInfo_RequestScenario", "eq", "click")
            && test("TrackingCoreModel_DeviceInfo_CountryCode", "v_nin", "CampaignInfo_CountryCode") {

            return transform(`[
                {
                    "operators": [{"op": "bool/set", "values": ["true"], "op_type": "FilterContext"}],
                    "to": "FilterContext_DemandCountryFilterFlag_IsFilter"
                },
                {
                    "operators": [{"op": "bypass", "values": ["country_banned"]}],
                    "to": "FilterContext_DemandCountryFilterFlag_FilterReason"
                }
            ]`) as "展示请求纬度去重"
        }

        return transform(`[]`) as "默认不过滤"
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
        excel_generator = ExcelGenerator([component], "/data/demo.xlsx")
        excel_generator.dump_components()


if __name__ == "__main__":
    unittest.main()
