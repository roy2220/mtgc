import enum
import json
import re
import uuid
from dataclasses import dataclass

from xlsxwriter import Workbook
from xlsxwriter.utility import xl_rowcol_to_cell
from xlsxwriter.worksheet import Format

from .analyzer import AndExpr, Bundle, Component, ReturnPoint, TestExpr, Transform, Unit
from .test_op_infos import is_v_op, replace_with_real_op


@dataclass(kw_only=True)
class _SymbolReference:
    kind: "_SymbolReferenceKind"
    symbol_key: str
    worksheet_name: str
    loc: tuple[int, int]
    business_unit_name: str
    business_unit_loc: tuple[int, int]
    business_scenario_num: int
    business_scenario_loc: tuple[int, int]


class _SymbolReferenceKind(enum.IntEnum):
    THEN = enum.auto()
    WHEN = enum.auto()
    THEN_EXTRA = enum.auto()
    WHEN_EXTRA = enum.auto()


class ExcelGenerator:
    __slots__ = (
        "_components",
        "_output_file_name",
        "_style_mark",
        "_symbol_references",
        "_workbook",
        "_cell_fmt",
        "_hyperlink_cell_fmt",
        "_business_unit_hdr_fmt",
        "_business_unit_cell_fmt",
        "_business_scenario_hdr_fmt",
        "_business_scenario_cell_fmt",
        "_when_hdr_fmt",
        "_then_hdr_fmt",
        "_input_hdr_fmt",
        "_output_hdr_fmt",
        "_symbol_key_hdr_fmt",
        "_symbol_reference_kind_hdr_fmt",
        "_symbol_reference_kind_cell_fmts",
        "_source_business_component_hdr_fmt",
        "_source_business_component_cell_fmt",
        "_source_business_scenario_hdr_fmt",
        "_default_text_fmt",
        "_highlight_text_fmt",
        "_conceal_text_fmt",
        "_delete_text_fmt",
        "_worksheet_name",
        "_worksheet",
        "_row_index",
        "_business_unit_name",
        "_business_unit_loc",
        "_business_scenario_num",
        "_business_scenario_loc",
    )

    def __init__(self, components: list[Component], output_file_name: str) -> None:
        self._components = components
        self._output_file_name = output_file_name
        self._style_mark = uuid.uuid4().hex
        self._symbol_references: list[_SymbolReference] = []

    def dump_components(self) -> None:
        self._workbook = Workbook(self._output_file_name)
        self._set_formats()

        index_worksheet = self._workbook.add_worksheet("Index")

        for component in self._components:
            if component.alias == "":
                self._worksheet_name = component.name
            else:
                self._worksheet_name = component.alias
            self._worksheet = self._workbook.add_worksheet(self._worksheet_name)
            self._dump_component(component)

        self._worksheet = index_worksheet
        self._dump_symbol_references()

        self._workbook.close()

    def _set_formats(self) -> None:
        font_size = 8

        common_format_properties = {
            "border": True,
            "font_size": font_size,
            "text_wrap": True,
            "valign": "vcenter",
        }

        self._cell_fmt = self._workbook.add_format(
            {
                **common_format_properties,
            }
        )
        self._hyperlink_cell_fmt = self._workbook.add_format(
            {
                "font_color": "blue",
                "underline": 1,
                **common_format_properties,
            }
        )
        self._business_unit_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#D9D9D9",
                "bold": True,
                **common_format_properties,
            }
        )
        self._business_unit_cell_fmt = self._workbook.add_format(
            {
                **common_format_properties,
            }
        )
        self._business_scenario_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#D9D9D9",
                "bold": True,
                **common_format_properties,
            }
        )
        self._business_scenario_cell_fmt = self._workbook.add_format(
            {
                **common_format_properties,
            }
        )
        self._when_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#F1C43D",
                "bold": True,
                **common_format_properties,
            }
        )
        self._then_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#B5CE99",
                "bold": True,
                **common_format_properties,
            }
        )
        self._input_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#F1C43D",
                "bold": True,
                **common_format_properties,
            }
        )
        self._output_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#B5CE99",
                "bold": True,
                **common_format_properties,
            }
        )
        self._symbol_key_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#D9D9D9",
                "bold": True,
                **common_format_properties,
            }
        )
        self._symbol_reference_kind_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#D9D9D9",
                "bold": True,
                **common_format_properties,
            }
        )
        self._symbol_reference_kind_cell_fmts = {
            _SymbolReferenceKind.WHEN: self._workbook.add_format(
                {
                    "align": "center",
                    "bg_color": "#F1C43D",
                    **common_format_properties,
                }
            ),
            _SymbolReferenceKind.THEN: self._workbook.add_format(
                {
                    "align": "center",
                    "bg_color": "#B5CE99",
                    **common_format_properties,
                }
            ),
            _SymbolReferenceKind.WHEN_EXTRA: self._workbook.add_format(
                {
                    "align": "center",
                    **common_format_properties,
                }
            ),
            _SymbolReferenceKind.THEN_EXTRA: self._workbook.add_format(
                {
                    "align": "center",
                    **common_format_properties,
                }
            ),
        }
        self._source_business_component_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#D9D9D9",
                "bold": True,
                **common_format_properties,
            }
        )
        self._source_business_component_cell_fmt = self._workbook.add_format(
            {
                "align": "center",
                **common_format_properties,
            }
        )
        self._source_business_scenario_hdr_fmt = self._workbook.add_format(
            {
                "align": "center",
                "bg_color": "#D9D9D9",
                "bold": True,
                **common_format_properties,
            }
        )
        self._default_text_fmt = self._workbook.add_format({"font_size": 8})
        self._highlight_text_fmt = self._workbook.add_format(
            {
                "font_color": "#FF0000",
                "font_size": font_size,
            }
        )
        self._conceal_text_fmt = self._workbook.add_format(
            {
                "font_color": "#808080",
                "font_size": font_size,
                "italic": True,
            }
        )
        self._delete_text_fmt = self._workbook.add_format(
            {
                "font_size": font_size,
                "font_strikeout": True,
            }
        )

    def _dump_component(self, component: Component) -> None:
        self._row_index = 0

        for bundle in component.bundles:
            self._dump_bundle(bundle)

    def _dump_bundle(self, bundle: Bundle) -> None:
        for unit in bundle.units:
            self._dump_unit(unit)

    def _dump_unit(self, unit: Unit) -> None:
        self._business_unit_name = unit.name
        self._business_unit_loc = (self._row_index, 0)
        self._business_scenario_num = 0
        self._business_scenario_loc = (-1, -1)

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
            self._make_business_unit_cell_text(unit),
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
            for transform in return_point.transform_list:
                output = transform.to
                if output not in outputs:
                    outputs.append(output)
        return outputs

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
                self._worksheet.set_column(column_index, column_index, 50)
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
                self._worksheet.set_column(column_index, column_index, 80)
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
                    self._worksheet.set_column(column_index, column_index, 50)
                    self._write_column(
                        self._row_index, column_index, input, self._input_hdr_fmt
                    )
                    self._reference_symbol(
                        _SymbolReferenceKind.WHEN, input, column_index
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
                    self._worksheet.set_column(column_index, column_index, 50)
                    self._write_column(
                        self._row_index, column_index, output, self._output_hdr_fmt
                    )
                    self._reference_symbol(
                        _SymbolReferenceKind.THEN, output, column_index
                    )
                column_index += 1

            self._row_index += 1

    def _make_business_unit_cell_text(self, unit: Unit) -> str:
        if unit.alias == "":
            return unit.name
        else:
            return f"{unit.name}\n{self._conceal_text("-- " + unit.alias)}"

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
            if i == 0:
                self._business_scenario_num += 1
                self._business_scenario_loc = (self._row_index, column_index)

            if i == len(and_exprs) - 1:
                self._merge_range(
                    first_row_index,
                    column_index,
                    self._row_index,
                    column_index,
                    self._make_business_scenario_cell_text(
                        and_exprs, return_point.transform_list
                    ),
                    self._business_scenario_cell_fmt,
                )
            column_index += 1

            # When
            for input in inputs:
                match_texts: list[str] = []
                condition_tags: list[str] = []
                for test_expr in and_expr.test_exprs:
                    if test_expr.is_merged:
                        continue
                    input_2 = test_expr.key
                    if input_2 == input:
                        match_texts.append(self._make_match_text(test_expr))
                        condition_tags.append(self._make_condition_tag(test_expr))
                        self._reference_extra_symbols_in_test_expr(
                            test_expr, column_index
                        )
                        for merged_test_expr in test_expr.merged_children:
                            condition_tags.append(
                                self._make_condition_tag(merged_test_expr)
                            )
                            self._reference_extra_symbols_in_test_expr(
                                merged_test_expr, column_index
                            )
                text = f"\nand\n".join(match_texts)
                self._write_column(
                    self._row_index,
                    column_index,
                    text or "/",
                    self._cell_fmt,
                )
                if len(condition_tags) >= 1:
                    self._write_comment(
                        self._row_index,
                        column_index,
                        "; ".join(condition_tags),
                    )
                column_index += 1

            # Then
            for output in outputs:
                if i == len(and_exprs) - 1:
                    transform_texts: list[str] = []
                    transform_annotations: list[str] = []
                    for transform in return_point.transform_list:
                        output_2 = transform.to
                        if output_2 == output:
                            transform_texts.append(self._make_transform_text(transform))
                            transform_annotations.append(transform.annotation)
                            self._reference_extra_symbols_in_transform(
                                transform, column_index
                            )
                    text = f"\nand\n".join(transform_texts)
                    self._merge_range(
                        first_row_index,
                        column_index,
                        self._row_index,
                        column_index,
                        text or "/",
                        self._cell_fmt,
                    )
                    if len(transform_annotations) >= 1:
                        self._write_comment(
                            self._row_index,
                            column_index,
                            "; ".join(transform_annotations),
                        )
                column_index += 1

            self._row_index += 1

    def _make_business_scenario_cell_text(
        self, and_exprs: list[AndExpr], transform_list: list[Transform]
    ) -> str:
        lines: list[str] = []

        lines.append("▶ WHEN")
        for i, and_expr in enumerate(and_exprs):
            condition_tags = list(
                map(self._make_condition_tag_with_style, and_expr.test_exprs)
            )

            if len(condition_tags) == 0:
                lines.append("[No condition]")
                break

            condition_number = self._conceal_text(f"[condition-{1+i}]")
            line = f"{condition_number}  " + "; ".join(condition_tags)
            lines.append(line)

        lines.append("▶ THEN")
        if len(transform_list) == 0:
            lines.append("[No action]")
        else:
            for i, transform in enumerate(transform_list):
                action_number = self._conceal_text(f"[action-{1+i}]")
                line = f"{action_number}  " + transform.annotation
                lines.append(line)

        return "\n".join(lines)

    def _make_match_text(self, test_expr: TestExpr) -> str:
        parts: list[str] = []
        if test_expr.is_negative:
            op = test_expr.reverse_op
        else:
            op = test_expr.op
        op = replace_with_real_op(op)

        parts.append(self._hilight_text(op))
        parts.append("(")
        for i, value in enumerate(test_expr.values):
            if i >= 1:
                parts.append(",")
            parts.append(json.dumps(self._hilight_text(value), ensure_ascii=False))
        parts.append(")")
        return " ".join(parts)

    def _make_condition_tag(self, test_expr: TestExpr) -> str:
        if test_expr.is_negative:
            return "❌ " + test_expr.fact
        else:
            return "✅ " + test_expr.fact

    def _make_condition_tag_with_style(self, test_expr: TestExpr) -> str:
        if test_expr.is_negative:
            return "❌ " + self._delete_text(test_expr.fact)
        else:
            return "✅ " + test_expr.fact

    def _make_transform_text(self, transform: Transform) -> str:
        parts: list[str] = []
        for i, operator in enumerate(transform.operators):
            if i >= 1:
                parts.append("|")

            parts.append(self._hilight_text(operator.op))
            parts.append("(")

            from1 = operator.from1
            if from1 is None:
                from1 = []
            else:
                from1 = from1.copy()
            for i, v in enumerate(from1):
                from1[i] = self._hilight_text(v)
            if len(from1) >= 1:
                parts.append("from")
                parts.append("=")
                parts.append(json.dumps(from1, ensure_ascii=False))

            values = operator.values
            if values is None:
                values = []
            else:
                values = values.copy()
            for i, v in enumerate(values):
                values[i] = self._hilight_text(v)
            if len(values) >= 1:
                if len(from1) >= 1:
                    parts.append(",")
                parts.append("values")
                parts.append("=")
                parts.append(json.dumps(values, ensure_ascii=False))

            op_type = operator.op_type
            if op_type is not None:
                if len(from1) + len(values) >= 1:
                    parts.append(",")
                parts.append("op_type")
                parts.append("=")
                parts.append(
                    json.dumps(self._hilight_text(op_type), ensure_ascii=False)
                )

            parts.append(")")

        return " ".join(parts)

    def _dump_symbol_references(self) -> None:
        self._row_index = 0
        column_index = 0

        self._worksheet.set_column(column_index, column_index, 80)
        self._write_column(
            self._row_index, column_index, "Symbol Key", self._symbol_key_hdr_fmt
        )
        column_index += 1
        self._worksheet.set_column(column_index, column_index, 25)
        self._write_column(
            self._row_index,
            column_index,
            "Symbol Reference Kind",
            self._symbol_reference_kind_hdr_fmt,
        )
        column_index += 1

        self._worksheet.set_column(column_index, column_index, 25)
        self._write_column(
            self._row_index,
            column_index,
            "Source Business Component",
            self._source_business_component_hdr_fmt,
        )
        column_index += 1

        self._worksheet.set_column(column_index, column_index, 80)
        self._write_column(
            self._row_index,
            column_index,
            "Source Business Unit",
            self._source_business_scenario_hdr_fmt,
        )
        column_index += 1

        self._row_index += 1
        self._worksheet.freeze_panes(self._row_index, column_index)

        last_symbol_key = ""
        reference_num = 1

        for symbol_reference in sorted(
            self._symbol_references,
            key=lambda x: (
                x.symbol_key,
                x.kind.value,
                x.worksheet_name,
                *x.business_unit_loc,
                *x.business_scenario_loc,
            ),
        ):
            column_index = 0

            if symbol_reference.symbol_key == last_symbol_key:
                reference_num += 1
            else:
                last_symbol_key = symbol_reference.symbol_key
                reference_num = 1

            # Symbol Key
            url = f"internal:'{symbol_reference.worksheet_name}'!{xl_rowcol_to_cell(*symbol_reference.loc)}"
            self._worksheet.write_url(
                self._row_index,
                column_index,
                url,
                self._hyperlink_cell_fmt,
                string=f"{symbol_reference.symbol_key} [{reference_num}]",
            )
            column_index += 1

            # Symbol Reference Kind
            self._write_column(
                self._row_index,
                column_index,
                symbol_reference.kind.name,
                self._symbol_reference_kind_cell_fmts[symbol_reference.kind],
            )
            column_index += 1

            # Source Business Component
            self._write_column(
                self._row_index,
                column_index,
                symbol_reference.worksheet_name,
                self._source_business_component_cell_fmt,
            )
            column_index += 1

            # Source Business Unit
            if symbol_reference.business_scenario_num == 0:
                url_2 = f"internal:'{symbol_reference.worksheet_name}'!{xl_rowcol_to_cell(*symbol_reference.business_unit_loc)}"
                self._worksheet.write_url(
                    self._row_index,
                    column_index,
                    url_2,
                    self._hyperlink_cell_fmt,
                    string=symbol_reference.business_unit_name,
                )
            else:
                url_2 = f"internal:'{symbol_reference.worksheet_name}'!{xl_rowcol_to_cell(*symbol_reference.business_scenario_loc)}"
                self._worksheet.write_url(
                    self._row_index,
                    column_index,
                    url_2,
                    self._hyperlink_cell_fmt,
                    string=f"{symbol_reference.business_unit_name} - Scenario {symbol_reference.business_scenario_num}",
                )
            column_index += 1

            self._row_index += 1

    def _reference_symbol(
        self,
        symbol_reference_kind: _SymbolReferenceKind,
        symbol_key: str,
        column_index: int,
    ) -> None:
        self._symbol_references.append(
            _SymbolReference(
                kind=symbol_reference_kind,
                symbol_key=symbol_key,
                worksheet_name=self._worksheet_name,
                loc=(self._row_index, column_index),
                business_unit_name=self._business_unit_name,
                business_unit_loc=self._business_unit_loc,
                business_scenario_num=self._business_scenario_num,
                business_scenario_loc=self._business_scenario_loc,
            )
        )

    def _reference_extra_symbols_in_test_expr(
        self, test_expr: TestExpr, column_index: int
    ) -> None:
        if is_v_op(test_expr.op):
            for value in test_expr.values:
                if value.startswith("^"):
                    continue
                self._symbol_references.append(
                    _SymbolReference(
                        kind=_SymbolReferenceKind.WHEN_EXTRA,
                        symbol_key=value,
                        worksheet_name=self._worksheet_name,
                        loc=(self._row_index, column_index),
                        business_unit_name=self._business_unit_name,
                        business_unit_loc=self._business_unit_loc,
                        business_scenario_num=self._business_scenario_num,
                        business_scenario_loc=self._business_scenario_loc,
                    )
                )

    def _reference_extra_symbols_in_transform(
        self, transform: Transform, column_index: int
    ) -> None:
        for operator in transform.operators:
            from1 = operator.from1
            if from1 is None:
                from1 = []
            for symbol_key in from1:
                self._symbol_references.append(
                    _SymbolReference(
                        kind=_SymbolReferenceKind.THEN_EXTRA,
                        symbol_key=symbol_key,
                        worksheet_name=self._worksheet_name,
                        loc=(self._row_index, column_index),
                        business_unit_name=self._business_unit_name,
                        business_unit_loc=self._business_unit_loc,
                        business_scenario_num=self._business_scenario_num,
                        business_scenario_loc=self._business_scenario_loc,
                    )
                )

    def _hilight_text(self, text: str) -> str:
        return self._stylize_text(text, "highlight")

    def _conceal_text(self, text: str) -> str:
        return self._stylize_text(text, "conceal")

    def _delete_text(self, text: str) -> str:
        return self._stylize_text(text, "delete")

    def _stylize_text(self, text: str, style: str) -> str:
        if text == "":
            return ""
        return f"<{style}:{self._style_mark}>{text}</{style}:{self._style_mark}>"

    def _render_colorful_text(self, text: str) -> list[str | Format]:
        parts = re.split(rf"(</?(?:[^:]+):{self._style_mark}>)", text)
        colorful_text: list[str | Format] = []

        for i, part in enumerate(parts):
            if part == "":
                continue

            if self._style_mark in part:
                if part.startswith("<highlight:"):
                    colorful_text.append(self._highlight_text_fmt)
                elif part.startswith("<conceal:"):
                    colorful_text.append(self._conceal_text_fmt)
                elif part.startswith("<delete:"):
                    colorful_text.append(self._delete_text_fmt)
                elif part.startswith("</"):
                    colorful_text.append(self._default_text_fmt)
                else:
                    assert False
            else:
                colorful_text.append(part)

        if colorful_text[-1] is self._default_text_fmt:
            colorful_text.pop()

        return colorful_text

    def _write_column(self, row: int, col: int, text: str, format: Format) -> None:
        if self._style_mark in text:
            self._worksheet.write_rich_string(
                row, col, *self._render_colorful_text(text), format
            )
        else:
            self._worksheet.write_column(row, col, [text], format)

    def _write_comment(self, row: int, col: int, comment: str) -> None:
        self._worksheet.write_comment(row, col, comment)

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

        if self._style_mark in text:
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
