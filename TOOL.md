# CSV validation service prototype

A headless, standard-library Python 3.10+ CLI that checks CSV files and writes a CSV or Markdown error report. It never cleans, rewrites, trims or normalizes source data.

The scope follows a [public CSV validation and maintenance buyer brief](https://www.freelancer.com/projects/bash/CSV-Data-Validation-Maintenance): configurable formats, missing and duplicate entries, unexpected characters/newlines, error locations, and command-line/CI use. **Every included CSV and rule is synthetic. No buyer files or agreed buyer schema were available, no buyer delivery occurred, and no payment is claimed.** This is a reusable demonstration for a scoped service offer.

## Run

No packages, network access or installation are required. Run from this directory:

```bash
python3 csv_validate.py --schema schema.example.json --report /tmp/valid-report.csv --format csv examples/valid-a.csv examples/valid-b.csv
```

This validates four data records across two files, exits `0`, and produces a report containing the column header and no violation rows.

```bash
python3 csv_validate.py --schema schema.example.json --report /tmp/errors.csv --format csv examples/invalid.csv
python3 csv_validate.py --schema schema.example.json --report /tmp/errors.md --format markdown examples/invalid.csv
```

Each invalid-sample command exits `1`, which is expected, and reports nine violations. One cell may fail multiple independent rules. The missing email has both `missing_value` and `pattern`; the embedded newline has both `forbidden_newline` and `forbidden_character`. The short final record has `column_count` and `missing_value`.

For a CI job, invoke the same command directly: status `1` fails validation; status `2` means configuration or I/O prevented a trustworthy complete report. Do not mask both statuses with an unconditional success command.

## Configure rules

Copy `schema.example.json` and agree the rules with the data owner before treating findings as customer acceptance criteria.

| Property | Meaning / default |
|---|---|
| `version` | Required integer `1` |
| `fields` | Required, nonempty array; every named field must appear in the header, in any order |
| `fields[].name` | Exact, case-sensitive header text; no trimming |
| `fields[].required` | `false` by default; `true` rejects an absent, empty or all-whitespace value |
| `fields[].pattern` | Optional Python regex; `re.fullmatch` must match the entire original cell, including an empty cell |
| `fields[].allow_newlines` | `false` by default; controls CR/LF inside a quoted cell |
| `fields[].allowed_characters` | Optional regex matched separately against every original Unicode character; e.g. `[A-Za-z가-힣 ]` |
| `unique_keys` | Optional array of field-name arrays; `[["id"]]` or `[["country", "id"]]`; every key is unique across the entire ordered batch |
| `allow_extra_columns` | `false` by default; permits unconfigured header columns if set to `true` |
| `allow_empty` | `false` by default; `true` permits both a zero-byte file and a valid header with no data records |
| `encoding` | `utf-8-sig` by default: UTF-8 with or without a BOM; any Python text encoding may be explicitly selected |
| `delimiter` | One character; comma by default; for TSV use `"\t"` in JSON |

Optional values are still subject to any configured pattern and character rules. To allow an empty value in a pattern, include an empty alternative explicitly. A missing configured header is always a structural violation, even when that field's values are optional. Additional columns, when allowed, still count toward the required width of each data record; their cell values have no field rules.

Keys use exact original strings; `A001` and ` A001` differ. A key with a missing or whitespace-only component is skipped to avoid treating missing data as a real duplicate identifier; use `required: true` to reject that data. A wrong-width record and an ambiguous duplicate key header are excluded from uniqueness checking. Duplicate values report the later record and the first occurrence's file/record in the message.

Unknown properties, duplicate JSON properties/field definitions, unsupported schema versions, invalid regexes and invalid rule types are configuration errors. This prevents a misspelled rule from silently doing nothing.

## Reports and locations

Both report formats contain these fields:

```text
file,row,column,column_index,physical_start,physical_end,code,message
```

- `file`: input path as passed to the CLI.
- `row`: logical CSV record number, counting the header as `1`; first data record is `2`. A quoted multiline cell counts as one record.
- `column`: header name; an empty string means the whole record. `column_index` is one-based, or `0` when no actual column can be identified. Composite duplicate keys list their component names and point to the first component's column index.
- `physical_start` / `physical_end`: one-based inclusive source line range for the record. A zero-byte file uses `0`; decoder read-ahead can make encoding-error positions approximate.
- `code`: stable category; `message`: short explanation. Field contents are represented by Unicode code points for disallowed-character reports, rather than pasted control characters.

Codes: `missing_header`, `duplicate_header`, `unexpected_header`, `column_count`, `missing_value`, `pattern`, `forbidden_newline`, `forbidden_character`, `duplicate_key`, `csv_syntax`, `invalid_encoding`, `empty_file`, `no_data`.

Structural and field violations accumulate, including across files. Quoted CR/LF is preserved during reading. Python's CSV parser runs with `strict=True`; if a syntax or decoding failure prevents further parsing of one file, that file stops at the error and later batch files are still checked. No reliable claim is made about records after an unrecoverable parse error. Python's default CSV field-length limit also applies.

## File safety and failure behavior

Inputs and schema are opened for reading only. A report cannot name the same path, symlink target or existing hard link as an input/schema. An existing ordinary report is replaced atomically only after all input reads and report rendering succeed. Its parent directory must already exist. On a configuration or source I/O error, the command exits `2`, writes a diagnostic to stderr, and preserves any existing report. A violation report is still written when parsing finishes with validation errors.

The command overwrites the requested report path. Use a dedicated output filename. A report path that is a symlink is replaced as a directory entry; its former target is not written. The tool does not attempt filesystem locking against another process changing files concurrently.

CSV reports are machine-readable data. Paths and column names come from the supplied files; treat them as untrusted text when importing reports into spreadsheet software. Markdown table text is escaped.

## Acceptance and limits

The independent checks under `verification/` exercise the public command, input hashes, batch uniqueness, reports, malformed data and path protection. Follow that directory's instructions for the current reproducible result.

This prototype is tested on the available Linux host and Python versions recorded in the verification evidence. Ubuntu 22.04 was requested by the buyer, but an actual Ubuntu 22.04 run has not been performed here. Python 3.10 compatibility is a target that can be checked separately; it does not prove that operating-system acceptance criterion.

The CLI reads records incrementally but retains the report and uniqueness indexes in memory, so memory grows with violations and distinct keys. It has no schema inference, automatic repair, application-specific date parsing, API integration, scheduler or delivery channel. Encode domain formats as agreed regular expressions or extend the contract after a real requirement is supplied. Performance and a maximum supported customer file size have not been measured.
