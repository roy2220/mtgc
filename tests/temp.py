from src import component, operator


class ParamParse(component.TABLE_MATCH_TRANSFORM):
    def MmpName(self):  # 业务
        operator.set("", "", "")


import ast
import inspect

function_source = inspect.getsource(ParamParse)
print(function_source)
tree = ast.parse(function_source)
print(ast.dump(tree))
