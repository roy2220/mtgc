import copy
import json
import re
import uuid

from xlsxwriter import Workbook
from xlsxwriter.worksheet import Format

from .analyzer import AndExpr, Component, ReturnPoint, TestExpr, Unit


class ExcelGenerator:
    __slots__ = (
        "_components",
        "_output_file_name",
        "_color_mark",
        "_workbook",
        "_cell_fmt",
        "_business_unit_hdr_fmt",
        "_business_unit_cell_fmt",
        "_business_scenario_hdr_fmt",
        "_business_scenario_cell_fmt",
        "_when_hdr_fmt",
        "_then_hdr_fmt",
        "_input_hdr_fmt",
        "_output_hdr_fmt",
        "_default_fmt",
        "_highlight_fmt",
        "_conceal_fmt",
        "_worksheet",
        "_row_index",
    )

    def __init__(self, components: list[Component], output_file_name: str) -> None:
        self._components = components
        self._output_file_name = output_file_name
        self._color_mark = uuid.uuid4().hex

    def dump_components(self) -> None:
        self._workbook = Workbook(self._output_file_name)
        self._set_formats()

        for component in self._components:
            self._worksheet = self._workbook.add_worksheet(component.alias)
            self._dump_component(component)

        self._workbook.close()

    def _set_formats(self) -> None:
        self._cell_fmt = self._workbook.add_format(
            {
                "border": True,
                "font_size": 11,
                "text_wrap": True,
                "valign": "vcenter",
            }
        )
        self._business_unit_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bold": True,
                "border": True,
                "font_size": 11,
                "valign": "vcenter",
            }
        )
        self._business_unit_cell_fmt = self._workbook.add_format(
            {
                "align": "center",
                "border": True,
                "font_size": 11,
                "text_wrap": True,
                "valign": "vcenter",
            }
        )
        self._business_scenario_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bold": True,
                "border": True,
                "font_size": 11,
                "valign": "vcenter",
            }
        )
        self._business_scenario_cell_fmt = self._workbook.add_format(
            {
                "border": True,
                "font_size": 11,
                "text_wrap": True,
                "valign": "vcenter",
            }
        )
        self._when_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#F1C43D",
                "bold": True,
                "border": True,
                "font_size": 11,
                "valign": "vcenter",
            }
        )
        self._then_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#B5CE99",
                "bold": True,
                "border": True,
                "font_size": 11,
                "valign": "vcenter",
            }
        )
        self._input_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#F1C43D",
                "bold": True,
                "border": True,
                "font_size": 11,
                "text_wrap": True,
                "valign": "vcenter",
            }
        )
        self._output_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#B5CE99",
                "bold": True,
                "border": True,
                "font_size": 11,
                "text_wrap": True,
                "valign": "vcenter",
            }
        )
        self._default_fmt = self._workbook.add_format()
        self._highlight_fmt = self._workbook.add_format(
            {
                "font_color": "#FF0000",
                "font_size": 11,
            }
        )
        self._conceal_fmt = self._workbook.add_format(
            {
                "font_color": "#808080",
                "font_size": 11,
                "italic": True,
            }
        )

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
                self._worksheet.set_column(self._row_index, column_index, 50)
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
                self._worksheet.set_column(self._row_index, column_index, 70)
            column_index += 1

            for j, input in enumerate(inputs):
                # When
                if i == 0 and j == len(inputs) - 1:
                    self._merge_range(
                        first_row_index,
                        column_index - j,
                        self._row_index,
                        column_index,
                        "WHEN",
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
                        "THEN",
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
            f"{unit.alias}\n{self._conceal_text("("+unit.name+")")}",
            self._business_unit_cell_fmt,
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

            # Business Scenario
            if i == len(and_exprs) - 1:
                self._merge_range(
                    first_row_index,
                    column_index,
                    self._row_index,
                    column_index,
                    self._make_business_scenario_text(
                        and_exprs, return_point.transform_annotation
                    ),
                    self._business_scenario_cell_fmt,
                )
            column_index += 1

            # When
            for input in inputs:
                make_match_texts = []
                for test_expr in and_expr.test_exprs:
                    input_2 = test_expr.key
                    if input_2 == input:
                        make_match_texts.append(self._make_match_text(test_expr))
                text = f"\nand\n".join(make_match_texts)
                self._write_column(
                    self._row_index,
                    column_index,
                    text or "/",
                    self._cell_fmt,
                )
                column_index += 1

            # Then
            for output in outputs:
                if i == len(and_exprs) - 1:
                    transform_item_texts = []
                    for transform_item in return_point.transform:
                        output_2 = transform_item["to"]
                        if output_2 == output:
                            transform_item_texts.append(
                                self._make_transform_item_text(transform_item)
                            )
                    text = f"\nand\n".join(transform_item_texts)
                    self._merge_range(
                        first_row_index,
                        column_index,
                        self._row_index,
                        column_index,
                        text or "/",
                        self._cell_fmt,
                    )
                column_index += 1

            self._row_index += 1

    def _make_business_scenario_text(
        self, and_exprs: list[AndExpr], transform_annotation: str
    ) -> str:
        def make_tag(test_expr: TestExpr) -> str:
            if test_expr.is_positive:
                return "✅ " + test_expr.fact
            else:
                return "❌ " + test_expr.fact

        lines = ["▶ " + transform_annotation]
        for and_expr in and_exprs:
            tags: list[str] = []
            for test_expr in and_expr.test_exprs:
                tags.append(make_tag(test_expr))
                for child_test_expr in test_expr.children:
                    tags.append(make_tag(child_test_expr))

            if len(tags) == 0:
                # always
                break

            line_number = self._conceal_text(f"[{len(lines)}]")
            line = f"{line_number} " + "; ".join(tags)
            lines.append(line)

        return "\n".join(lines)

    def _make_match_text(self, test_expr: TestExpr) -> str:
        parts = []
        if test_expr.is_positive:
            op = test_expr.op
        else:
            op = test_expr.reverse_op

        parts.append(self._hilight_text(op))
        parts.append("(")
        for i, value in enumerate(test_expr.values):
            if i >= 1:
                parts.append(",")
            parts.append(json.dumps(self._hilight_text(value), ensure_ascii=False))
        parts.append(")")
        return " ".join(parts)

    def _make_transform_item_text(self, transform_item: dict) -> str:
        parts = []
        for i, operator in enumerate(transform_item["operators"]):
            if i >= 1:
                parts.append("|")

            parts.append(self._hilight_text(operator["op"]))
            parts.append("(")

            from1 = operator.get("from", []).copy()
            for i, v in enumerate(from1):
                from1[i] = self._hilight_text(v)
            if len(from1) >= 1:
                parts.append("from")
                parts.append("=")
                parts.append(json.dumps(from1, ensure_ascii=False))

            values = operator.get("values", []).copy()
            for i, v in enumerate(values):
                values[i] = self._hilight_text(v)
            if len(values) >= 1:
                if len(from1) >= 1:
                    parts.append(",")
                parts.append("values")
                parts.append("=")
                parts.append(json.dumps(values, ensure_ascii=False))

            op_type = operator.get("op_type", "")
            if op_type != "":
                if len(from1) + len(values) >= 1:
                    parts.append(",")
                parts.append("op_type")
                parts.append("=")
                parts.append(
                    json.dumps(self._hilight_text(op_type), ensure_ascii=False)
                )

            parts.append(")")

        return " ".join(parts)

    def _hilight_text(self, text: str) -> str:
        return self._color_text(text, "hl")

    def _conceal_text(self, text: str) -> str:
        return self._color_text(text, "cc")

    def _color_text(self, text: str, style: str) -> str:
        if text == "":
            return ""
        return f"<{style}:{self._color_mark}>{text}</{style}:{self._color_mark}>"

    def _render_colorful_text(self, text: str) -> list[str | Format]:
        parts = re.split(rf"(</?(?:hl|cc):{self._color_mark}>)", text)
        colorful_text: list[str | Format] = []

        for i, part in enumerate(parts):
            if part == "":
                continue

            if self._color_mark in part:
                if part.startswith("<hl:"):
                    colorful_text.append(self._highlight_fmt)
                elif part.startswith("<cc:"):
                    colorful_text.append(self._conceal_fmt)
                elif part.startswith("</"):
                    colorful_text.append(self._default_fmt)
                else:
                    assert False
            else:
                colorful_text.append(part)

        if colorful_text[-1] is self._default_fmt:
            colorful_text.pop()

        return colorful_text

    def _write_column(self, row: int, col: int, text: str, format: Format) -> None:
        if self._color_mark in text:
            self._worksheet.write_rich_string(
                row, col, *self._render_colorful_text(text), format
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

        if self._color_mark in text:
            self._worksheet.merge_range(
                first_row, first_col, last_row, last_col, "", format
            )
            self._worksheet.write_rich_string(
                first_row, first_col, *self._render_colorful_text(text), format
            )
        else:
            self._worksheet.merge_range(
                first_row, first_col, last_row, last_col, text, format
            )
