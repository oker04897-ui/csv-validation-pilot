# CSV validation: a repeatable report before your next import

Find missing values, duplicate keys, bad formats, unexpected characters and embedded line breaks. Get the exact record, column and physical line range, with a command you can run again. The validator reads your source files without rewriting them.

**The code is free under the MIT license. A proposed USD 15 service pilot covers configuring and running one agreed check, delivering its findings and explaining how to repeat it.** No customer purchase or revenue is claimed. OpenAI Codex implements and verifies the work for the human GitHub operator [@oker04897-ui](https://github.com/oker04897-ui).

## See it work

Requires Python 3.10 or later. No dependencies, accounts or network access are needed to run the CLI.

```bash
python3 csv_validate.py --schema schema.example.json --report /tmp/csv-findings.csv --format csv examples/invalid.csv
```

The included synthetic example produces **nine findings** and exits `1`, the documented validation-failure status. [See the actual input and complete report](DEMO.md). [Tool documentation](TOOL.md) explains the rules, output fields, limitations and exit codes.

The independent CLI check exercised **17 scenarios on each of Python 3.10.21 and 3.12.3**, covering error locations, multiline records, batch duplicates, malformed inputs, exit codes and unchanged input hashes. See the [verification report](verification/VERIFICATION.md) and [reproducible check](verification/verify_cli.py). The actual host was Ubuntu 24.04.1 / WSL2. Ubuntu 22.04 has not been tested. Every included input is synthetic.

## Proposed USD 15 pilot

Before any invoice, we review a non-sensitive sample and agree the rules, expected results, delivery time and permitted data handling.

| Item | Proposed scope, subject to sample review |
| --- | --- |
| Input | One authorized UTF-8 CSV, up to 1 MiB, 1,000 logical data records and 10 columns |
| Rules | Up to five agreed checks covering required values, regex formats, duplicate keys or allowed characters/newlines |
| Delivery | Runnable CLI, your rules JSON, CSV or Markdown findings, file hashes and rerun instructions |
| Acceptance | Agreed normal/error examples match the expected findings and locations; original input hashes remain unchanged |
| Correction | One adjustment to the agreed rule interpretation; new data, rules or features need a new agreement |
| Price | USD 15, proposed and unaccepted; payment via a PayPal commercial invoice once scope and account readiness are confirmed |

These are service scope limits, not measured capacity claims. Source cleaning, schema changes, production login/deployment, actual CI integration, Ubuntu 22.04 certification and large-file performance guarantees need separate agreement. Delivery time is agreed before invoicing; this page does not promise immediate or unattended service.

## Ask whether your CSV fits

Open an issue with a **non-sensitive outline** of the columns, checks, approximate size and desired result. No payment is due for a scope question. Do not post production records, credentials, payment details or private customer information. An appropriate private data and invoicing channel must be agreed before exchanging those details.

We use Codex for code and automated checks. Customer data is used only within the agreed authorization; sending production data to an AI service requires explicit permission for that processing. If suitable, you can run the supplied CLI locally and share a sanitized findings report instead.

This independent offer does not move Freelancer clients or payments off their platform. The tool's initial scope was informed by a [public paid validation brief](https://www.freelancer.com/projects/bash/CSV-Data-Validation-Maintenance); we have not received that buyer's records, contract, acceptance or payment.

## License

The implementation and synthetic examples are available under [MIT](LICENSE). The paid pilot is an offer of configuration, execution and support for an agreed input; buying it is not required to use the code.
