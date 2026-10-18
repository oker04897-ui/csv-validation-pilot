# CSV validation CLI

A standard-library Python CLI for finding missing values, duplicate keys, bad formats, unexpected characters and embedded line breaks. Reports identify the record, column and physical line range. Source files are read without modification.

## Run

Requires Python 3.10 or later. No packages, accounts or network access are needed to run the tool.

```bash
python3 csv_validate.py --schema schema.example.json --report /tmp/csv-findings.csv --format csv examples/invalid.csv
```

The synthetic example produces nine findings and exits `1`, the documented validation-failure status. See [the actual input and complete report](DEMO.md), [tool documentation](TOOL.md) and [example rules](schema.example.json).

## Verification

The independent CLI check exercises 17 scenarios covering error locations, multiline records, batch duplicates, malformed inputs, exit codes and unchanged input hashes.

- Local evidence: Python 3.10.21 and 3.12.3 on Ubuntu 24.04.1 / WSL2, 17 scenarios passed on each. See the [original verification report](verification/VERIFICATION.md).
- Additional execution: [public GitHub Actions run on Ubuntu 22.04](https://github.com/oker04897-ui/csv-validation-pilot/actions/runs/39132427865), 17 scenarios passed on each of Python 3.10.22 and 3.12.15. The run logs record the actual OS, interpreters, source hash and commit.
- Every included input is synthetic. These checks are technical evidence; they do not establish customer acceptance, demand, time savings or payment.

From the repository root, rerun the independent check using fresh output paths:

```bash
python3 verification/verify_cli.py --cli csv_validate.py --artifacts /tmp/csv-check-new --report /tmp/csv-check-new.json
```

The initial service offer was withdrawn. This repository now holds the implementation, examples and technical verification only.

## License

[MIT](LICENSE).
