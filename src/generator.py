import ast
import json


class Generator:
    def process_table_match_transform(self, class_def: ast.ClassDef):
        call = class_def.decorator_list[0]
        assert isinstance(call, ast.Call)
        attribute = call.func
        assert isinstance(attribute, ast.Attribute)
        assert attribute.attr == "TABLE_MATCH_TRANSFORM"
        assert len(call.args) == 1
        constant = call.args[0]
        assert isinstance(constant, ast.Constant)
        component_name = constant.value
        assert isinstance(component_name, str)

        for function_def in class_def.body:
            assert isinstance(function_def, ast.FunctionDef)
            assert len(function_def.decorator_list) == 1
            call = function_def.decorator_list[0]
            assert isinstance(call, ast.Call)
            attribute = call.func
            assert isinstance(attribute, ast.Attribute)
            assert attribute.attr == "BUSINESS_UNIT"
            assert len(call.args) == 1
            constant = call.args[0]
            assert isinstance(constant, ast.Constant)
            business_unit = constant.value
            assert isinstance(business_unit, str)

            l = []

            for s in function_def.body:
                expr = s
                assert isinstance(expr, ast.Expr)
                call = expr.value
                assert isinstance(call, ast.Call)
                attribute = call.func
                assert isinstance(attribute, ast.Attribute)
                assert attribute.attr == "set"
                assert len(call.args) == 3
                business_scenario = ""
                key = ""
                expr = ""
                for i, arg in enumerate(call.args):
                    constant = arg
                    assert isinstance(constant, ast.Constant)
                    v = constant.value
                    assert isinstance(v, str)
                    match i:
                        case 0:
                            business_scenario = v
                        case 1:
                            key = v
                        case _:
                            expr = v
                print(business_scenario, key, expr)
                l.append(
                    {
                        "BusinessScenario": business_scenario,
                        "BusinessUnit": business_unit,
                        "IsContinue": False,
                        "Thens": [
                            {
                                "Expr": expr,
                                "Key": key,
                            }
                        ],
                        "Whens": [],
                    },
                )

            print(json.dumps(l, indent=2, ensure_ascii=False))
            # print(ast.dump(function_def, indent=2))
