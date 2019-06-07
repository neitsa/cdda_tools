#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import copy
import json
import logging
import math
import pathlib
import sys
from typing import Dict, List, Union

logger = logging.getLogger(__name__)

JsonDataType = List[Dict[str, Union[str, List[Dict[str, str]]]]]

# note: see https://tex.stackexchange.com/questions/269547/rowcolor-for-a-multirow about multirows and colors.


def escape_latex_text(text: str) -> str:
    simple_escapes = "&%$#_{}"
    if any([c in text for c in simple_escapes]):
        for ch in simple_escapes:
            if ch in text:
                text = text.replace(ch, "\\" + ch)

    if len(text) == 1:
        complex_escapes = "\\~^"
        if any([c in text for c in complex_escapes]):
            latex_complex_escape = {
                "~": r"\textasciitilde",
                "^": r"\textasciicircum",
                "\\": r"\textbackslash"
            }
            for ch in complex_escapes:
                if ch in text:
                    text = text.replace(ch, latex_complex_escape[ch])

    if text == " ":
        text = "<space>"

    return text


class Binding:
    __slots__ = ["input_method", "key"]

    def __init__(self, input_method: str, key: str) -> None:
        self.input_method = input_method
        if isinstance(key, list):
            if len(key) > 1:
                raise ValueError
            else:
                key = key[0]
        self.key = key

    @classmethod
    def from_entry(cls, binding: Dict[str, str]) -> "Binding":
        return cls(**binding)

    def to_latex(self) -> str:
        if not self.key:
            return "<unbound> & <unbound>"
        key = escape_latex_text(self.key)
        fmt_key = "\\cmd{%s}" % key
        return f"{self.input_method} & {fmt_key}"

    def is_same_binding(self, other: 'Binding') -> bool:
        # gets whether or not it's the same key (case insensitive)
        return self.key.lower() == other.key.lower()


class KeyBinding:
    MAX_NAME_LINE_LENGTH = 30

    def __init__(self, id: str, category: str, name: str, bindings: List[Dict[str, str]]) -> None:
        self.id = id
        self.category = category
        self.name = name
        self.bindings: List[Binding] = list()
        if bindings:
            for e in bindings:
                self.bindings.append(Binding.from_entry(e))
            self.bindings.sort(key=lambda b: b.key.lower())

    @property
    def num_text_lines(self) -> int:
        num_bindings = len(self.bindings) if self.bindings else 1
        if len(self.name) >= self.MAX_NAME_LINE_LENGTH:
            lines_for_name = math.ceil(len(self.name) / self.MAX_NAME_LINE_LENGTH)
        else:
            lines_for_name = 0
        total = num_bindings + lines_for_name
        return total

    @property
    def category_title(self) -> str:
        return self.category.replace("_", " ").title()

    @classmethod
    def from_entry(cls, entry) -> "KeyBinding":
        keys = ['id', 'category', 'name', 'bindings']
        d = {k: v for (k, v) in entry.items() if k in keys}
        if "category" not in d:
            d.update({"category": "General"})
        if "bindings" not in d:
            logger.debug(f"no bindings for: {entry['id']}")
            d.update({"bindings": None})
        if "name" not in d:
            name = entry['id'].title()
            name = name.replace("_", " ")
            logger.debug(f"no name for: {entry['id']}; replacing with: {name}")
            d.update({"name": name})
        return cls(**d)

    def to_latex(self, is_last_entry: bool) -> List[str]:
        binding_strings: List[str] = list()
        end_line = '\\\\' if is_last_entry else '\\hlx'

        if len(self.bindings) <= 1:
            # one or zero bindings.
            bindings = self.bindings[0].to_latex() if self.bindings else "<unbound> & <unbound>"
            name = escape_latex_text(self.name)
            binding_strings.append(f"{name} & {bindings} {end_line}")
        else:
            # multi bindings for the same entry. It's touchy because of the row colors.
            for i, binding in enumerate(self.bindings):
                # next_binding = self.bindings[i + 1] if i < len(self.bindings) else None
                if i == len(self.bindings) - 1:  # last binding
                    col = r"\multirow{-%i}{*}{%s}" % (len(self.bindings), escape_latex_text(self.name))
                    binding_strings.append(f"{col} & {binding.to_latex()} {end_line}")
                else:
                    binding_strings.append(f"& {binding.to_latex()} \\\\")

        return binding_strings


class KeyBindingContainer:
    MAX_LINES = 50
    TAB_SPACES = 12

    def __init__(self, json_data: JsonDataType):
        self.key_binding_categories: Dict[str: List[KeyBinding]] = dict()
        for entry in json_data:
            key_binding_entry = KeyBinding.from_entry(entry)
            if not self.key_binding_categories.get(key_binding_entry.category_title):
                self.key_binding_categories[key_binding_entry.category_title] = list()
            self.key_binding_categories[key_binding_entry.category_title].append(key_binding_entry)

        # sort entries by name
        for k, v in self.key_binding_categories.items():
            v.sort(key=lambda e: e.name)

        self._colors = ["white", "gray!10"]  # alternating colors for rows.

    def generate_table_header(self, category_name: str, is_continuation: bool, add_comment_separator: bool = True):
        table_header_strings = [
            "%\n% {cat_name}\n%".format(cat_name=category_name),
            r"        \begin{tabularx}{\linewidth}{ | X | l | l | }",
            self.generate_multicolumn(category_name, is_continuation),
            r"            \toprule",
            r"            \rowcolor{impt}",  # color for the next row
            r"            \textbf{Name} &  \textbf{Input} & \textbf{Key} \tabularnewline \hline \hline",
        ]

        if add_comment_separator:
            table_header_strings.insert(0, f"% {'-' * 120}")
        return '\n'.join(table_header_strings)

    @staticmethod
    def generate_multicolumn(category_name: str, is_continuation: bool) -> str:
        cont_name = " (cont.)" if is_continuation else ""
        full_category_name = category_name + cont_name
        if len(category_name) < 25:
            content = r"\multicolumn{3}{l}{\cellcolor{lightblue} \headbf{%s}%s} \\" % (category_name, cont_name)
            return f"{' ' * 12}{content}"
        else:
            if len(full_category_name) >= 50:
                raise ValueError("Category name is really too long and this case is not handled")
            words = full_category_name.split(' ')
            lines = list()
            current_line = list()
            for word in words:
                current_line.append(word)
                current_line_len = sum(len(w) for w in current_line)
                if current_line_len > 25:
                    popped_word = current_line.pop(-1)
                    lines.append(copy.copy(current_line))
                    current_line.clear()
                    current_line.append(popped_word)
            lines.append(current_line)

            start = ' ' * 12 + r"\multicolumn{3}{l}{\headbf{\makecell[l]{\cellcolor{lightblue} "
            output = [start, ]
            for i, line in enumerate(lines):
                if i == 1:
                    output.append(r"\footnotesize{. . .}\\\cellcolor{lightblue}")
                output.append(' '.join(line))

            output.append(r"}}} \\")
            return ''.join(output)

    @staticmethod
    def generate_table_footer() -> str:
        table_footer_strings = [
            r"            \bottomrule",
            r"        \end{tabularx}",
            r"        \spacebtwtables",
        ]
        return '\n'.join(table_footer_strings)

    def generate_entry(self, entry: KeyBinding, is_last_entry: bool, entry_tab: int, starting_color: str) -> str:
        entry_strings: List[str] = entry.to_latex(is_last_entry)
        output_strings: List[str] = list()
        for i, entry_string in enumerate(entry_strings):
            # row color
            row_color = r"\rowcolor{%s}" % starting_color
            output_strings.append(f"{' ' * entry_tab}{row_color}")
            output_strings.append(f"{' ' * entry_tab}{entry_string}")
        return '\n'.join(output_strings)

    def generate_table_entries(self, category_name: str) -> str:
        entries: List[KeyBinding] = self.key_binding_categories[category_name]
        entry_strings: List[str] = list()

        total_lines = 0
        for i, e in enumerate(entries):
            entry_num_text_lines = e.num_text_lines
            if entry_num_text_lines + total_lines >= self.MAX_LINES:
                yield "\n".join(entry_strings)
                total_lines = 0
                entry_strings.clear()
            total_lines += entry_num_text_lines
            is_last_entry = i == len(entries) - 1
            starting_color = self._colors[i % len(self._colors)]
            entry_string = self.generate_entry(e, is_last_entry, self.TAB_SPACES, starting_color)
            entry_strings.append(entry_string)

        if entry_strings:
            yield "\n".join(entry_strings)

    def generate_latex_tables(self) -> str:
        sorted_categories = sorted(e for e in self.key_binding_categories.keys())
        for category in sorted_categories:
            yield self.category_to_latex_table(category)

    def category_to_latex_table(self, category_name: str) -> str:
        generated_tables = list()
        for i, string_entries in enumerate(self.generate_table_entries(category_name)):
            table_header = self.generate_table_header(category_name, i != 0, i == 0)
            if i > 0:
                table_header = f"\n{table_header}"
            table_footer = self.generate_table_footer()
            table = '\n'.join([table_header, string_entries, table_footer])
            generated_tables.append(table)

        return '\n'.join(generated_tables)


def main(args):
    file_paths: List[pathlib.Path] = list()

    # main input file
    if not args.keybindings.is_file():
        logger.error(f"The given json input file path '{args.keybindings!s}' is not a file or does not exist.")
        return -1
    file_paths.append(args.keybindings)

    # additional input file(s)
    if args.additional_input:
        args.additional_input = [pathlib.Path(p) for p in args.additional_input]
        has_error = False
        for additional_file_path in args.additional_input:
            if not additional_file_path.is_file():
                has_error = True
                logger.error(f"The given additional json input file path '{additional_file_path}' "
                             f"is not a file or does not exist.")
            else:
                file_paths.append(additional_file_path)

        if has_error:
            return -1

    # read json from all input files
    json_data = list()
    for file_path in file_paths:
        with file_path.open("r") as f:
            json_data.extend(json.load(f))

    # read latex template file.
    template_file: pathlib.Path = args.template
    if not template_file.is_file():
        logger.error(f"The given .tex input template file path '{template_file}' is not a file or does not exist.")
        return -1

    with template_file.open("r") as template_f:
        template = template_f.read()

    # display a few info
    total_keys = sum([len(e['bindings']) if e.get("bindings") else 0 for e in json_data])
    unbound_entries = sum([1 if e.get("bindings") is None else 0 for e in json_data])
    logger.info(f"Found {len(json_data)} entries; total keys: {total_keys}; unbound entries: {unbound_entries}")

    # parse everything
    logger.info("Parsing json entries.")
    k_container = KeyBindingContainer(json_data)

    # generate latex
    logger.info("Generating latex output.")
    output = '\n'.join(latex_table for latex_table in k_container.generate_latex_tables())
    with args.output.open("w") as out_f:
        latex_output = template.replace(r"%{template}", output)
        logger.info(f"Writing output file: {args.output!s}")
        out_f.write(latex_output)

    logger.info("Done!")
    return 0


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="TODO")

    arg_parser.add_argument("-l", "--log-level",
                            choices=['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],  default='INFO',
                            help="Set the logging level.")

    arg_parser.add_argument("keybindings", type=pathlib.Path, action="store",
                            help="Path to CDDA keybindings.json input file.")

    arg_parser.add_argument("-a", action="append", dest="additional_input", default=[],
                            help="Add other input files to input.")

    arg_parser.add_argument("-o", "--output",
                            type=pathlib.Path, action="store", default="./cdda_keybindings.tex",
                            help="Path to latex output file.")

    arg_parser.add_argument("-t", "--template", type=pathlib.Path, action="store",
                            default="./cdda_keybindings_template.tex",
                            help="Template path.")

    parsed_args = arg_parser.parse_args()

    logging_level = logging.getLevelName(parsed_args.log_level)
    logging.basicConfig(level=logging_level)
    logger.setLevel(logging_level)

    sys.exit(main(parsed_args))
