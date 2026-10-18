# CSV validation demo — synthetic data

A repeatable pre-import check locates missing values, duplicate identifiers, bad formats, unexpected characters and embedded line breaks. The same command can fail a CI job before invalid CSV reaches the next system. Source CSV files are read only; this tool produces an error report, never cleaned data.

This demonstration uses invented data and example.com addresses. It is a prototype for a scoped validation service, not completed work on a buyer's files. Customer rules and Ubuntu 22.04 acceptance remain to be agreed and verified. No purchase, customer acceptance, time saving or payment is claimed.

## Good input

`examples/valid-a.csv`:

```csv
id,email,name
A001,minji@example.com,김민지
A002,jun@example.com,이준
```

A second synthetic file, `examples/valid-b.csv`, contains two additional distinct records. Together they contain four data records.

From the extracted package directory, run the following. The temporary report directory is created explicitly; the path shown below is the actual demo run's path.

```bash
mkdir -p /tmp/csv-service-demo-eoo9c53d
python3 csv_validate.py --schema schema.example.json --report /tmp/csv-service-demo-eoo9c53d/report.csv --format csv examples/valid-a.csv examples/valid-b.csv
```

Actual stdout:

```text
2 file(s), 4 data row(s), 0 violation(s); report: /tmp/csv-service-demo-eoo9c53d/report.csv
```

Exit status: **0**. The actual CSV report contains only its header:

```csv
file,row,column,column_index,physical_start,physical_end,code,message
```

## Bad input

`examples/invalid.csv` in full (the quoted third data record spans two physical lines):

```csv
id,email,name
A001,minji@example.com,김민지
A001,not-an-email,Invalid!
A003,,"첫 줄
둘째 줄"
A004,yuna@example.com
```

Run:

```bash
python3 csv_validate.py --schema schema.example.json --report /tmp/csv-service-demo-eoo9c53d/report.csv --format csv examples/invalid.csv
```

Actual stdout:

```text
1 file(s), 4 data row(s), 9 violation(s); report: /tmp/csv-service-demo-eoo9c53d/report.csv
```

Exit status: **1**, indicating validation findings. Stderr is empty. The exact generated CSV report follows; it has nine findings because independent rules may fail on the same cell:

```csv
file,row,column,column_index,physical_start,physical_end,code,message
examples/invalid.csv,3,email,2,3,3,pattern,Value does not fully match configured pattern
examples/invalid.csv,3,name,3,3,3,forbidden_character,Disallowed code points: U+0021
examples/invalid.csv,3,id,1,3,3,duplicate_key,Duplicates key (id) first seen at examples/invalid.csv row 2
examples/invalid.csv,4,email,2,4,5,missing_value,Required value is empty or whitespace
examples/invalid.csv,4,email,2,4,5,pattern,Value does not fully match configured pattern
examples/invalid.csv,4,name,3,4,5,forbidden_newline,Embedded CR or LF is not allowed
examples/invalid.csv,4,name,3,4,5,forbidden_character,Disallowed code points: U+000A
examples/invalid.csv,5,,0,6,6,column_count,"Expected 3 fields, found 2"
examples/invalid.csv,5,name,3,6,6,missing_value,Required value is empty or whitespace
```

The duplicate ID points back to its first occurrence. The multiline name is logical record 4 and physical lines 4–5. The last short record is logical record 5 but physical line 6; its missing name is also reported. This lets the data owner find the source problem without having the tool silently repair or discard it.

To obtain a human-readable table, change `--format csv` to `--format markdown` and choose a `.md` report path. For new inputs, replace the paths and configure the agreed rules in JSON. See [README.md](README.md) for rule semantics and [schema.example.json](schema.example.json) for the synthetic example rules.

## Verified environment and reproducible evidence

- Actual host: **Ubuntu 24.04.1 LTS, Linux x86-64, WSL2**, kernel `6.18.33.2-microsoft-standard-WSL2`, glibc 2.39.
- Executed interpreters: **Python 3.10.21 and Python 3.12.3**.
- Independent public-CLI checks: **17 scenarios passed on each interpreter**, covering validation, location accuracy, malformed inputs, batch keys, output formats, exit codes and preservation of source files.
- Final tested CLI SHA-256: `f147a84ccbe4aff2b6c85d50b9fb5f1c9e6bd1f116174a60754a51cc82907205`.
- Evidence: [verification/VERIFICATION.md](verification/VERIFICATION.md), [Python 3.10](verification/final-python310.json), [Python 3.12](verification/final-python312.json).
- **Ubuntu 22.04 has not been executed here.** Running Python 3.10 on Ubuntu 24.04 does not establish Ubuntu 22.04 acceptance.

All demo report contents above were produced by the delivered CLI. The independent checker is separate from the implementation; to rerun it, follow the commands in the verification report. The report directory there must be a fresh path.
