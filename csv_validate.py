#!/usr/bin/env python3
"""Validate CSV batches without changing their source files (Python 3.10+)."""

import argparse
import codecs
import csv
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile


REPORT_FIELDS = (
    "file", "row", "column", "column_index", "physical_start", "physical_end",
    "code", "message",
)


class ConfigurationError(ValueError):
    """A schema or invocation is unusable."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError("Duplicate schema property: " + key)
        result[key] = value
    return result


def check_properties(obj, allowed, where):
    if not isinstance(obj, dict):
        raise ConfigurationError(where + " must be an object")
    unknown = set(obj) - set(allowed)
    if unknown:
        raise ConfigurationError(
            where + " has unknown properties: " + ", ".join(sorted(unknown))
        )


def boolean(obj, name, default, where):
    value = obj.get(name, default)
    if not isinstance(value, bool):
        raise ConfigurationError(where + "." + name + " must be true or false")
    return value


def regex_rule(field, name, where):
    if name not in field:
        return None
    if not isinstance(field[name], str):
        raise ConfigurationError(where + "." + name + " must be a regex string")
    try:
        return re.compile(field[name])
    except re.error as exc:
        raise ConfigurationError(where + "." + name + ": " + str(exc)) from exc


def load_schema(path):
    with open(path, encoding="utf-8") as stream:
        schema = json.load(stream, object_pairs_hook=unique_object)
    check_properties(schema, {
        "version", "fields", "unique_keys", "allow_extra_columns",
        "allow_empty", "encoding", "delimiter",
    }, "schema")
    if type(schema.get("version")) is not int or schema["version"] != 1:
        raise ConfigurationError("schema.version must be 1")
    encoding = schema.get("encoding", "utf-8-sig")
    if not isinstance(encoding, str):
        raise ConfigurationError("schema.encoding must be a text encoding name")
    try:
        codec = codecs.lookup(encoding)
        if not codec._is_text_encoding:
            raise LookupError("Not a text encoding")
    except LookupError as exc:
        raise ConfigurationError("Unsupported text encoding: " + encoding) from exc
    delimiter = schema.get("delimiter", ",")
    if (not isinstance(delimiter, str) or len(delimiter) != 1
            or delimiter in '\r\n\x00"'):
        raise ConfigurationError("schema.delimiter must be one non-quote character")
    fields = schema.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ConfigurationError("schema.fields must be a nonempty array")
    compiled = {}
    for index, field in enumerate(fields):
        where = "fields[{}]".format(index)
        check_properties(field, {
            "name", "required", "pattern", "allow_newlines", "allowed_characters",
        }, where)
        name = field.get("name")
        if not isinstance(name, str) or not name or "\n" in name or "\r" in name:
            raise ConfigurationError(where + ".name must be nonempty single-line text")
        if name in compiled:
            raise ConfigurationError("Duplicate field name: " + name)
        compiled[name] = {
            "required": boolean(field, "required", False, where),
            "allow_newlines": boolean(field, "allow_newlines", False, where),
            "pattern": regex_rule(field, "pattern", where),
            "allowed_characters": regex_rule(field, "allowed_characters", where),
        }
    unique_keys = schema.get("unique_keys", [])
    if not isinstance(unique_keys, list):
        raise ConfigurationError("schema.unique_keys must be an array of arrays")
    seen_keys = set()
    for key in unique_keys:
        if (not isinstance(key, list) or not key
                or any(not isinstance(name, str) or name not in compiled for name in key)
                or len(set(key)) != len(key)):
            raise ConfigurationError("Each unique key must name distinct configured fields")
        if tuple(key) in seen_keys:
            raise ConfigurationError("Duplicate unique key configuration")
        seen_keys.add(tuple(key))
    return {
        "fields": compiled, "unique_keys": unique_keys,
        "encoding": encoding, "delimiter": delimiter,
        "allow_extra_columns": boolean(schema, "allow_extra_columns", False, "schema"),
        "allow_empty": boolean(schema, "allow_empty", False, "schema"),
    }


def same_path(first, second):
    if Path(first).resolve() == Path(second).resolve():
        return True
    try:
        return os.path.samefile(first, second)
    except (FileNotFoundError, OSError):
        return False


def validate_file(path, schema, errors, seen):
    """Collect errors in one file; keep uniqueness state across the batch."""
    record_number = 0
    previous_line = 0
    data_rows = 0

    def error(code, message, row=0, column="", column_index=0, start=0, end=0):
        errors.append(dict(zip(REPORT_FIELDS, (
            str(path), row, column, column_index, start, end, code, message,
        ))))

    # newline="" preserves quoted CR/LF and delegates record boundaries to csv.
    with open(path, "r", encoding=schema["encoding"], newline="") as stream:
        reader = csv.reader(stream, delimiter=schema["delimiter"], strict=True)
        header = None
        positions = {}
        try:
            for values in reader:
                record_number += 1
                start = previous_line + 1
                end = reader.line_num
                previous_line = end
                if header is None:
                    header = values
                    for index, name in enumerate(header, 1):
                        if name in positions:
                            error("duplicate_header", "Header occurs more than once",
                                  1, name, index, start, end)
                        else:
                            positions[name] = index - 1
                        if name not in schema["fields"] and not schema["allow_extra_columns"]:
                            error("unexpected_header", "Header is not configured",
                                  1, name, index, start, end)
                    for name in schema["fields"]:
                        if name not in positions:
                            error("missing_header", "Configured header is missing",
                                  1, name, 0, start, end)
                    continue
                data_rows += 1
                if len(values) != len(header):
                    error("column_count", "Expected {} fields, found {}".format(
                        len(header), len(values)), record_number, "", 0, start, end)
                for index, name in enumerate(header):
                    if name not in schema["fields"]:
                        continue
                    value = values[index] if index < len(values) else ""
                    rule = schema["fields"][name]
                    location = (record_number, name, index + 1, start, end)
                    if rule["required"] and not value.strip():
                        error("missing_value", "Required value is empty or whitespace", *location)
                    if rule["pattern"] is not None and rule["pattern"].fullmatch(value) is None:
                        error("pattern", "Value does not fully match configured pattern", *location)
                    if not rule["allow_newlines"] and ("\r" in value or "\n" in value):
                        error("forbidden_newline", "Embedded CR or LF is not allowed", *location)
                    if rule["allowed_characters"] is not None:
                        invalid = sorted(set(char for char in value
                                             if rule["allowed_characters"].fullmatch(char) is None))
                        if invalid:
                            # Avoid embedding source content or control characters in reports.
                            codes = ", ".join("U+{:04X}".format(ord(c)) for c in invalid[:12])
                            if len(invalid) > 12:
                                codes += ", ..."
                            error("forbidden_character", "Disallowed code points: " + codes, *location)
                if len(values) != len(header):
                    continue
                for key_index, key in enumerate(schema["unique_keys"]):
                    if any(name not in positions or header.count(name) != 1 for name in key):
                        continue
                    key_values = tuple(values[positions[name]] for name in key)
                    if any(not value.strip() for value in key_values):
                        continue
                    first = seen[key_index].get(key_values)
                    if first is not None:
                        error("duplicate_key", "Duplicates key ({}) first seen at {} row {}".format(
                            ", ".join(key), first[0], first[1]), record_number,
                            ",".join(key), positions[key[0]] + 1, start, end)
                    else:
                        seen[key_index][key_values] = (str(path), record_number)
        except csv.Error as exc:
            error("csv_syntax", str(exc), record_number + 1, "", 0,
                  previous_line + 1, max(reader.line_num, previous_line + 1))
        except UnicodeError as exc:
            error("invalid_encoding", "Cannot decode using {}: {}".format(
                schema["encoding"], exc.reason), record_number + 1, "", 0,
                previous_line + 1, max(reader.line_num, previous_line + 1))
        if header is None and not errors_for_file(errors, path):
            if not schema["allow_empty"]:
                error("empty_file", "File contains no CSV header or data")
        elif header is not None and data_rows == 0 and not schema["allow_empty"]:
            error("no_data", "File has a header but no data rows", 1, "", 0, 1, previous_line)
    return data_rows


def errors_for_file(errors, path):
    return any(error["file"] == str(path) for error in errors)


def markdown_cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace("\\", "\\\\").replace("|", "\\|").replace(
        "\r", "&#13;").replace("\n", "&#10;")


def render_report(errors, report_format):
    output = io.StringIO(newline="")
    if report_format == "csv":
        writer = csv.DictWriter(output, fieldnames=REPORT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(errors)
    else:
        output.write("# CSV validation report\n\n{} violation(s).\n\n".format(len(errors)))
        output.write("| " + " | ".join(REPORT_FIELDS) + " |\n")
        output.write("| " + " | ".join("---" for _ in REPORT_FIELDS) + " |\n")
        for error in errors:
            output.write("| " + " | ".join(markdown_cell(error[name]) for name in REPORT_FIELDS) + " |\n")
    return output.getvalue()


def write_report(path, text):
    """Replace only the requested report path after preparing the whole report."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=path.parent, prefix=".csv-validation-",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True, help="JSON rule file")
    parser.add_argument("--report", required=True, help="Destination CSV or Markdown report")
    parser.add_argument("--format", choices=("csv", "markdown"), default="csv")
    parser.add_argument("files", nargs="+", help="CSV input paths (read only)")
    args = parser.parse_args(argv)
    try:
        for protected in [args.schema] + args.files:
            if same_path(args.report, protected):
                raise ConfigurationError("Report must not overwrite an input or the schema")
        schema = load_schema(args.schema)
        errors = []
        seen = [{} for _ in schema["unique_keys"]]
        rows = 0
        for path in args.files:
            rows += validate_file(path, schema, errors, seen)
        write_report(args.report, render_report(errors, args.format))
    except (OSError, UnicodeError, json.JSONDecodeError, ConfigurationError, LookupError) as exc:
        print("csv-validate: " + str(exc), file=sys.stderr)
        return 2
    print("{} file(s), {} data row(s), {} violation(s); report: {}".format(
        len(args.files), rows, len(errors), args.report))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
