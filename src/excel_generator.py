import copy
import json
import re
import uuid

from xlsxwriter import Workbook
from xlsxwriter.worksheet import Format

from .analyzer import Component, ReturnPoint, TestExpr, Unit


class ExcelGenerator:
    __slots__ = (
        "_components",
        "_output_file_name",
        "_hilight_begin_mark",
        "_hilight_mark",
        "_workbook",
        "_cell_fmt",
        "_business_unit_hdr_fmt",
        "_business_scenario_hdr_fmt",
        "_business_scenario_cell_fmt",
        "_when_hdr_fmt",
        "_then_hdr_fmt",
        "_input_hdr_fmt",
        "_output_hdr_fmt",
        "_default_fmt",
        "_highlight_fmt",
        "_worksheet",
        "_row_index",
    )

    def __init__(self, components: list[Component], output_file_name: str) -> None:
        self._components = components
        self._output_file_name = output_file_name
        self._hilight_mark = "hl:" + uuid.uuid4().hex

    def dump_components(self) -> None:
        self._workbook = Workbook(self._output_file_name)
        self._set_formats()

        for component in self._components:
            self._worksheet = self._workbook.add_worksheet(component.alias)
            self._dump_component(component)

        self._workbook.close()

    def _set_formats(self) -> None:
        self._cell_fmt = self._workbook.add_format(
            {"border": True, "text_wrap": True, "valign": "vcenter"}
        )
        self._business_unit_hdr_fmt = self._workbook.add_format(
            {"border": True, "bold": True, "align": "center", "valign": "vcenter"}
        )
        self._business_scenario_hdr_fmt = self._workbook.add_format(
            {"border": True, "bold": True, "align": "center", "valign": "vcenter"}
        )
        self._business_scenario_cell_fmt = self._workbook.add_format(
            {
                "border": True,
                "text_wrap": True,
                "valign": "vcenter",
                "bg_color": "#FEFF54",
            }
        )
        self._when_hdr_fmt = self._workbook.add_format(
            {
                "border": True,
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#F3C343",
            }
        )
        self._then_hdr_fmt = self._workbook.add_format(
            {
                "border": True,
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#9FCE62",
            }
        )
        self._input_hdr_fmt = self._workbook.add_format(
            {
                "border": True,
                "bold": True,
                "text_wrap": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#FEFF54",
            }
        )
        self._output_hdr_fmt = self._workbook.add_format(
            {
                "border": True,
                "bold": True,
                "text_wrap": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#FEFF54",
            }
        )
        self._default_fmt = self._workbook.add_format()
        self._highlight_fmt = self._workbook.add_format({"font_color": "red"})

    def _dump_component(self, component: Component) -> None:
        self._row_index = 0

        for unit in component.units:
            self._dump_unit(unit)

    def _write_header(self, inputs: list[str], outputs: list[str]) -> None:
        first_row_index = self._row_index

        for i in range(2):
            column_index = 0

            # Business Unit
            if i == 1:
                self._merge_range(
                    first_row_index,
                    column_index,
                    self._row_index,
                    column_index,
                    "Business Unit",
                    self._business_unit_hdr_fmt,
                )
                self._worksheet.set_column(self._row_index, column_index, 30)
            column_index += 1

            # Business Scenario
            if i == 1:
                self._merge_range(
                    first_row_index,
                    column_index,
                    self._row_index,
                    column_index,
                    "Business Scenario",
                    self._business_scenario_hdr_fmt,
                )
                self._worksheet.set_column(self._row_index, column_index, 30)
            column_index += 1

            for j, input in enumerate(inputs):
                # When
                if i == 0 and j == len(inputs) - 1:
                    self._merge_range(
                        first_row_index,
                        column_index - j,
                        self._row_index,
                        column_index,
                        "When",
                        self._when_hdr_fmt,
                    )

                if i == 1:
                    self._worksheet.set_column(self._row_index, column_index, 50)
                    self._write_column(
                        self._row_index, column_index, input, self._input_hdr_fmt
                    )
                column_index += 1

            for j, output in enumerate(outputs):
                # Then
                if i == 0 and j == len(outputs) - 1:
                    self._merge_range(
                        first_row_index,
                        column_index - j,
                        self._row_index,
                        column_index,
                        "Then",
                        self._then_hdr_fmt,
                    )

                if i == 1:
                    self._worksheet.set_column(self._row_index, column_index, 50)
                    self._write_column(
                        self._row_index, column_index, output, self._output_hdr_fmt
                    )
                column_index += 1

            self._row_index += 1

    def _dump_unit(self, unit: Unit) -> None:
        inputs = self._gather_inputs(unit)
        outputs = self._gather_outputs(unit)
        self._write_header(inputs, outputs)

        first_row_index = self._row_index

        for return_point in unit.return_points:
            self._dump_return_point(return_point, inputs, outputs)

        self._merge_range(
            first_row_index,
            0,
            self._row_index - 1,
            0,
            unit.alias,
            self._cell_fmt,
        )

        self._row_index += 1

    def _gather_inputs(self, unit: Unit) -> list[str]:
        inputs: list[str] = []
        for return_point in unit.return_points:
            for and_expr in return_point.or_expr.and_exprs:
                for test_expr in and_expr.test_exprs:
                    input = test_expr.key
                    if input not in inputs:
                        inputs.append(input)
        return list(inputs)

    def _gather_outputs(self, unit: Unit) -> list[str]:
        outputs: list[str] = []
        for return_point in unit.return_points:
            for x in return_point.transform:
                output = x["to"]
                if output not in outputs:
                    outputs.append(output)
        return outputs

    def _dump_return_point(
        self,
        return_point: ReturnPoint,
        inputs: list[str],
        outputs: list[str],
    ) -> None:
        first_row_index = self._row_index
        and_exprs = return_point.or_expr.and_exprs

        for i, and_expr in enumerate(and_exprs):
            column_index = 1

            if i == len(and_exprs) - 1:
                self._merge_range(
                    first_row_index,
                    column_index,
                    self._row_index,
                    column_index,
                    return_point.transform_scenario,
                    self._business_scenario_cell_fmt,
                )
            column_index += 1

            for input in inputs:
                lines = []
                for test_expr in and_expr.test_exprs:
                    input_2 = test_expr.key
                    if input_2 == input:
                        lines.append(self._make_match_text(test_expr))
                text = "\n".join(lines) or "/"
                self._write_column(
                    self._row_index,
                    column_index,
                    text,
                    self._cell_fmt,
                )
                column_index += 1

            for output in outputs:
                if i == len(and_exprs) - 1:
                    lines = []
                    for transform_item in return_point.transform:
                        output_2 = transform_item["to"]
                        if output_2 == output:
                            lines.append(self._make_transform_item_text(transform_item))
                    text = "\n".join(lines) or "/"
                    self._merge_range(
                        first_row_index,
                        column_index,
                        self._row_index,
                        column_index,
                        text,
                        self._cell_fmt,
                    )
                column_index += 1

            self._row_index += 1

    def _make_match_text(self, test_expr: TestExpr) -> str:
        values = test_expr.values.copy()
        for i, v in enumerate(values):
            values[i] = self._hilight_text(v)
        match = {"op": self._hilight_text(test_expr.op), "values": values}
        match_text = json.dumps(match, ensure_ascii=False)
        if not test_expr.is_positive:
            match_text = self._hilight_text("NOT") + " " + match_text
        return match_text

    def _make_transform_item_text(self, transform_item: dict) -> str:
        transform_item = copy.deepcopy(transform_item)
        del transform_item["to"]
        del transform_item["underlying_to"]
        for operator in transform_item["operators"]:
            operator.pop("underlying_op_type", None)
            operator.pop("underlying_from", None)

            from1 = operator.get("from", [])
            for i, v in enumerate(from1):
                from1[i] = self._hilight_text(v)
            operator["op"] = self._hilight_text(operator["op"])
            values = operator.get("values", [])
            for i, v in enumerate(values):
                values[i] = self._hilight_text(v)
        transform_item_text = json.dumps(transform_item, ensure_ascii=False)
        return transform_item_text

    def _hilight_text(self, text: str) -> str:
        if text == "":
            return ""
        return f"<{self._hilight_mark}>{text}</{self._hilight_mark}>"

    def _render_hilighted_text(self, text: str) -> list[str | Format]:
        parts = re.split(rf"(</?{self._hilight_mark}>)", text)
        hilight_begin = f"<{self._hilight_mark}>"
        hilight_end = f"</{self._hilight_mark}>"
        hilighted_text: list[str | Format] = []

        for i, part in enumerate(parts):
            if part == "":
                continue

            if part == hilight_begin:
                hilighted_text.append(self._highlight_fmt)
            elif part == hilight_end:
                hilighted_text.append(self._default_fmt)
            else:
                hilighted_text.append(part)

        return hilighted_text

    def _write_column(self, row: int, col: int, text: str, format: Format) -> None:
        if self._hilight_mark in text:
            self._worksheet.write_rich_string(
                row, col, *self._render_hilighted_text(text), format
            )
        else:
            self._worksheet.write_column(row, col, [text], format)

    def _merge_range(
        self,
        first_row: int,
        first_col: int,
        last_row: int,
        last_col: int,
        text: str,
        format: Format,
    ) -> None:
        if (first_row, first_col) == (last_row, last_col):
            self._write_column(first_row, first_col, text, format)
            return

        if self._hilight_mark in text:
            self._worksheet.merge_range(first_row, first_col, last_row, last_col, "")
            self._worksheet.write_rich_string(
                first_row, first_col, *self._render_hilighted_text(text), format
            )
        else:
            self._worksheet.merge_range(
                first_row, first_col, last_row, last_col, text, format
            )
