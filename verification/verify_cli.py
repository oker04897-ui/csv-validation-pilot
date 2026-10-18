#!/usr/bin/env python3
"""Independent buyer-facing checks for the CSV validation service CLI.

All inputs are synthetic. Tests call the command in separate headless processes,
read its CSV/Markdown reports, and compare observable errors and original hashes.
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path


REPORT_FIELDS = ["file", "row", "column", "column_index", "physical_start",
                 "physical_end", "code", "message"]
SCHEMA = {
    "version": 1,
    "fields": [
        {"name": "id", "required": True, "pattern": "R[0-9]{3}",
         "allowed_characters": "[A-Z0-9]", "allow_newlines": False},
        {"name": "name", "required": True,
         "allowed_characters": "[ -~\r\n]", "allow_newlines": False},
        {"name": "email", "required": True,
         "pattern": r"[^@\s]+@example\.com", "allow_newlines": False},
    ],
    "unique_keys": [["id"]],
    "allow_extra_columns": False,
    "allow_empty": False,
    "encoding": "utf-8-sig",
    "delimiter": ",",
}
EXPECTED_BAD_FINDINGS = {
    ("first.csv", 3, "name", 2, 3, 3, "missing_value"),
    ("first.csv", 4, "id", 1, 4, 4, "pattern"),
    ("first.csv", 4, "id", 1, 4, 4, "forbidden_character"),
    ("first.csv", 4, "email", 3, 4, 4, "pattern"),
    ("first.csv", 5, "name", 2, 5, 5, "forbidden_character"),
    ("first.csv", 6, "name", 2, 6, 7, "forbidden_newline"),
    ("second.csv", 2, "id", 1, 2, 2, "duplicate_key"),
}


def finding_locations(errors):
    return {(Path(e["file"]).name, int(e["row"]), e["column"],
             int(e["column_index"]), int(e["physical_start"]),
             int(e["physical_end"]), e["code"]) for e in errors}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put_csv(path, rows, encoding="utf-8", delimiter=","):
    with path.open("w", encoding=encoding, newline="") as stream:
        writer = csv.writer(stream, delimiter=delimiter)
        writer.writerows(rows)


class Verification:
    def __init__(self, cli, python, artifacts):
        self.cli = cli.resolve()
        self.python = python
        self.artifacts = artifacts.resolve()
        self.results = []

    def run(self, folder, files, schema=SCHEMA, report_name="errors.csv",
            output_format="csv", schema_raw=None, expected_exit=0,
            protect_existing_report=True):
        config = folder / "rules.json"
        config.write_text(schema_raw if schema_raw is not None else
                          json.dumps(schema, ensure_ascii=False), encoding="utf-8")
        report = folder / report_name
        originals = {str(path): sha(path) for path in files if path.is_file()}
        originals[str(config)] = sha(config)
        if report.is_file() and protect_existing_report:
            originals[str(report)] = sha(report)
        command = [self.python, str(self.cli), "--schema", str(config),
                   "--report", str(report), "--format", output_format]
        command += [str(path) for path in files]
        started = utc_now()
        process = subprocess.run(command, cwd=str(folder), capture_output=True,
                                 text=True, timeout=10,
                                 env={**os.environ, "PYTHONUTF8": "1"})
        call = {"command": command, "started_utc": started, "ended_utc": utc_now(),
                "exit_code": process.returncode, "stdout": process.stdout,
                "stderr": process.stderr, "report": str(report),
                "before_sha256": originals}
        call["after_sha256"] = {
            path: sha(Path(path)) if Path(path).is_file() else None
            for path in originals
        }
        self.current["calls"].append(call)
        assert call["after_sha256"] == originals, "Input/config/existing output changed"
        assert process.returncode == expected_exit, \
            "Expected exit {}, observed {}; stderr={!r}".format(
                expected_exit, process.returncode, process.stderr)
        if expected_exit == 2:
            assert process.stderr.strip(), "Configuration/IO failure has no diagnostic"
            assert "Traceback (most recent call last)" not in process.stderr, \
                "Failure exposed an unhandled traceback"
            return process, None, report
        assert report.is_file(), "Expected report was not written"
        if output_format == "csv":
            with report.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                assert reader.fieldnames == REPORT_FIELDS, "Report columns differ"
                rows = list(reader)
            for row in rows:
                assert all(row[field] is not None for field in REPORT_FIELDS), \
                    "Malformed report record"
                assert row["code"] and row["message"], "Missing error code or explanation"
                assert int(row["row"]) >= 0, "Negative logical record number"
                assert int(row["physical_start"]) >= 0, "Negative physical line"
                assert int(row["physical_end"]) >= int(row["physical_start"]), \
                    "Physical range is reversed"
            call["observed_findings"] = rows
            return process, rows, report
        return process, report.read_text(encoding="utf-8"), report

    def case(self, name, function):
        folder = self.artifacts / name
        folder.mkdir(parents=True)
        self.current = {"name": name, "calls": [], "fixture_kind": "synthetic"}
        try:
            function(folder)
            self.current["status"] = "pass"
        except Exception as error:
            self.current.update(status="fail", error_type=type(error).__name__,
                                error=str(error), traceback=traceback.format_exc())
        self.results.append(self.current)
        print("{}: {}{}".format(name, self.current["status"],
                               " - " + self.current.get("error", "")
                               if self.current["status"] == "fail" else ""))

    @staticmethod
    def valid_file(folder, name="input.csv"):
        path = folder / name
        put_csv(path, [["id", "name", "email"],
                       ["R001", "Alice", "alice@example.com"]])
        return path

    @staticmethod
    def bad_files(folder):
        first, second = folder / "first.csv", folder / "second.csv"
        put_csv(first, [
            ["id", "name", "email"],
            ["R001", "Alice", "alice@example.com"],
            ["R002", "", "empty-name@example.com"],
            ["bad", "Bob", "invalid-address"],
            ["R003", "Eve\tAdmin", "eve@example.com"],
            ["R004", "Two\nlines", "multiline@example.com"],
            ["R005", "Kate", "kate@example.com"],
        ])
        put_csv(second, [["id", "name", "email"],
                         ["R001", "Duplicate", "duplicate@example.com"],
                         ["R006", "Normal", "normal@example.com"]])
        return [first, second]

    def valid_batch(self, folder):
        first = self.valid_file(folder, "one.csv")
        second = folder / "two.csv"
        put_csv(second, [["email", "id", "name"],
                         ["bob@example.com", "R002", "Bob"]], encoding="utf-8-sig")
        _, errors, _ = self.run(folder, [first, second])
        assert errors == [], "Valid input produced validation errors"

    def all_error_locations(self, folder):
        _, errors, _ = self.run(folder, self.bad_files(folder), expected_exit=1)
        observed = finding_locations(errors)
        expected = EXPECTED_BAD_FINDINGS
        self.current["expected_findings"] = [list(item) for item in sorted(expected)]
        assert observed == expected, \
            "Missing/unexpected error locations: missing={!r}; extra={!r}".format(
                expected - observed, observed - expected)
        assert len(errors) == len(expected), "Duplicate report records"

    def markdown_report(self, folder):
        _, text, _ = self.run(folder, self.bad_files(folder), report_name="errors.md",
                             output_format="markdown", expected_exit=1)
        for field in REPORT_FIELDS:
            assert field in text, "Markdown report lacks field " + field
        for code in ["missing_value", "pattern", "forbidden_character",
                     "forbidden_newline", "duplicate_key"]:
            assert code in text, "Markdown omitted error category " + code
        assert "first.csv" in text and "second.csv" in text, \
            "Markdown lacks source file locations"
        assert text.count("forbidden_newline") == 1, "Markdown duplicates/omits newline error"
        table = [line for line in text.splitlines() if line.startswith("|")]
        columns = [value.strip() for value in table[0].strip("|").split("|")]
        assert columns == REPORT_FIELDS, "Markdown report field order differs"
        rows = []
        for line in table[2:]:
            values = [value.strip() for value in line.strip("|").split("|")]
            assert len(values) == len(REPORT_FIELDS), "Markdown table row is malformed"
            rows.append(dict(zip(columns, values)))
        assert finding_locations(rows) == EXPECTED_BAD_FINDINGS, \
            "Markdown does not preserve every expected error location"
        assert len(rows) == len(EXPECTED_BAD_FINDINGS), "Markdown duplicate/missing rows"

    def composite_uniqueness(self, folder):
        schema = json.loads(json.dumps(SCHEMA))
        schema["unique_keys"] = [["id", "name"]]
        first, second = folder / "one.csv", folder / "two.csv"
        put_csv(first, [["id", "name", "email"],
                       ["R001", "Alice", "a@example.com"],
                       ["R001", "Bob", "b@example.com"]])
        put_csv(second, [["id", "name", "email"],
                        ["R001", "Alice", "c@example.com"]])
        _, errors, _ = self.run(folder, [first, second], schema=schema, expected_exit=1)
        assert [(Path(e["file"]).name, int(e["row"]), e["code"]) for e in errors] == \
            [("two.csv", 2, "duplicate_key")], "Composite key handling is incorrect"

    def header_errors(self, folder):
        path = folder / "headers.csv"
        put_csv(path, [["id", "name", "name", "extra"],
                       ["R001", "Alice", "Alice", "x"]])
        _, errors, _ = self.run(folder, [path], expected_exit=1)
        assert {e["code"] for e in errors} >= {
            "missing_header", "duplicate_header", "unexpected_header"}
        assert all(int(e["row"]) == 1 for e in errors), "Header issue not located at header"

    def ragged_rows(self, folder):
        path = folder / "ragged.csv"
        put_csv(path, [["id", "name", "email"], ["R001", "Alice"],
                       ["R002", "Bob", "bob@example.com", "extra"]])
        _, errors, _ = self.run(folder, [path], expected_exit=1)
        positions = {(int(e["row"]), e["code"]) for e in errors}
        assert (2, "column_count") in positions and (3, "column_count") in positions, \
            "Ragged rows were not all located"

    def empty_file(self, folder):
        path = folder / "empty.csv"
        path.write_bytes(b"")
        _, errors, _ = self.run(folder, [path], expected_exit=1)
        assert any(e["code"] == "empty_file" and int(e["row"]) == 0
                   for e in errors), "Empty file has no meaningful finding"

    def header_only(self, folder):
        path = folder / "headers-only.csv"
        put_csv(path, [["id", "name", "email"]])
        _, errors, _ = self.run(folder, [path], expected_exit=1)
        assert any(e["code"] == "no_data" for e in errors), "No-data input was accepted"

    def malformed_csv(self, folder):
        path = folder / "malformed.csv"
        path.write_text('id,name,email\nR001,"unclosed,alice@example.com\n', encoding="utf-8")
        _, errors, _ = self.run(folder, [path], expected_exit=1)
        assert any(e["code"] == "csv_syntax" for e in errors), "Broken quotes were accepted"

    def semicolon_config(self, folder):
        schema = json.loads(json.dumps(SCHEMA))
        schema["delimiter"] = ";"
        path = folder / "semicolon.csv"
        put_csv(path, [["id", "name", "email"],
                       ["R001", "Alice", "a@example.com"]], delimiter=";")
        _, errors, _ = self.run(folder, [path], schema=schema)
        assert errors == [], "Configured delimiter was ignored"

    def missing_input(self, folder):
        self.run(folder, [folder / "not-present.csv"], expected_exit=2)

    def bad_schema_json(self, folder):
        self.run(folder, [self.valid_file(folder)], schema_raw="{broken", expected_exit=2)

    def bad_schema_regex(self, folder):
        schema = json.loads(json.dumps(SCHEMA))
        schema["fields"][0]["pattern"] = "["
        self.run(folder, [self.valid_file(folder)], schema=schema, expected_exit=2)

    def existing_report(self, folder):
        (folder / "errors.csv").write_bytes(b"DO NOT REPLACE\n")
        self.run(folder, [folder / "missing-input.csv"], expected_exit=2)

    def atomic_report_replace(self, folder):
        (folder / "errors.csv").write_bytes(b"OLD REPORT\n")
        _, errors, report = self.run(folder, [self.valid_file(folder)],
                                     protect_existing_report=False)
        assert errors == [], "Valid rerun did not replace the report"
        assert report.read_bytes() != b"OLD REPORT\n", "Existing report was not updated"

    def report_is_input(self, folder):
        path = self.valid_file(folder)
        self.run(folder, [path], report_name=path.name, expected_exit=2)

    def report_is_schema(self, folder):
        self.run(folder, [self.valid_file(folder)], report_name="rules.json", expected_exit=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.artifacts.exists():
        parser.error("--artifacts must be a new folder")
    if not args.cli.is_file():
        parser.error("--cli does not exist")
    started, timer = utc_now(), time.perf_counter()
    before = sha(args.cli)
    args.artifacts.mkdir(parents=True)
    verifier = Verification(args.cli, args.python, args.artifacts)
    checks = ["valid_batch", "all_error_locations", "markdown_report",
              "composite_uniqueness", "header_errors", "ragged_rows",
              "empty_file", "header_only", "malformed_csv", "semicolon_config",
              "missing_input", "bad_schema_json", "bad_schema_regex",
              "existing_report", "atomic_report_replace", "report_is_input",
              "report_is_schema"]
    for name in checks:
        verifier.case(name, getattr(verifier, name))
    runtime = subprocess.run([args.python, "-c", "import sys,platform;print(sys.version);print(platform.platform())"],
                             capture_output=True, text=True, timeout=10)
    report = {
        "buyer_source": "https://www.freelancer.com/projects/bash/CSV-Data-Validation-Maintenance",
        "buyer_project_id": 40772594,
        "fixture_kind": "synthetic; no buyer files received",
        "started_utc": started, "ended_utc": utc_now(),
        "elapsed_seconds": round(time.perf_counter() - timer, 6),
        "cli": str(args.cli.resolve()), "cli_sha256_before": before,
        "cli_sha256_after": sha(args.cli),
        "target_python": args.python, "runtime_observed": runtime.stdout,
        "host_platform": platform.platform(),
        "host_os_release": Path("/etc/os-release").read_text()
                           if Path("/etc/os-release").exists() else None,
        "results": verifier.results,
        "passed": sum(r["status"] == "pass" for r in verifier.results),
        "failed": sum(r["status"] == "fail" for r in verifier.results),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["passed", "failed", "elapsed_seconds",
                                            "cli_sha256_before", "cli_sha256_after"]}))
    return int(report["failed"] > 0 or report["cli_sha256_before"] != report["cli_sha256_after"])


if __name__ == "__main__":
    raise SystemExit(main())
