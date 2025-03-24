import dataclasses
import json
import tempfile
import unittest
from io import StringIO

from src.analyzer import Analyzer
from src.parser import Parser
from src.scanner import Scanner


class TestAnalyzer(unittest.TestCase):
    def test_get_composite_statement(self):
        with tempfile.NamedTemporaryFile(delete_on_close=True) as fp:
            fp.write(
                """\
[
  { "Idx": 1199995, "Key": "CampaignInfo_CountryCode" },
  { "Idx": 1199996, "Key": "TrackingCoreModel_DeviceInfo_CountryCode" },
  { "Idx": 1199997, "Key": "DemandInfo_CCTDuplicate_IsDuplicate" },
  { "Idx": 1199998, "Key": "DemandInfo_RequestDuplicate_IsDuplicate" },
  { "Idx": 1199999, "Key": "RequestInfo_BasicInfo_RequestScenario" },
  { "Idx": 1200000, "Key": "FilterContext" },
  { "Idx": 1200001, "Key": "FilterContext_DemandFilterFlag_IsFilter" },
  { "Idx": 1200002, "Key": "FilterContext_DemandFilterFlag_FilterReason" },
  { "Idx": 1200003, "Key": "FilterContext_DemandDuplicateFilterFlag_IsFilter" },
  { "Idx": 1200004, "Key": "FilterContext_DemandDuplicateFilterFlag_FilterReason" },
  { "Idx": 1200000, "Key": "FilterContext_DemandCountryFilterFlag_IsFilter" },
  { "Idx": 1200005, "Key": "FilterContext_DemandCountryFilterFlag_FilterReason" }
]
""".encode()
            )
            fp.flush()

            source = (
                f'import "{fp.name}"\n'
                + """\
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
            )
            scanner = Scanner(StringIO(source))
            parser = Parser(scanner)
            analyzer = Analyzer(parser.get_component_declaration())
            component = analyzer.get_component()
            print(
                json.dumps(
                    dataclasses.asdict(component), indent="  ", ensure_ascii=False
                )
            )


if __name__ == "__main__":
    unittest.main()
