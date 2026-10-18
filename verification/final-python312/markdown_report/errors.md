# CSV validation report

7 violation(s).

| file | row | column | column_index | physical_start | physical_end | code | message |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/first.csv | 3 | name | 2 | 3 | 3 | missing_value | Required value is empty or whitespace |
| /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/first.csv | 4 | id | 1 | 4 | 4 | pattern | Value does not fully match configured pattern |
| /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/first.csv | 4 | id | 1 | 4 | 4 | forbidden_character | Disallowed code points: U+0061, U+0062, U+0064 |
| /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/first.csv | 4 | email | 3 | 4 | 4 | pattern | Value does not fully match configured pattern |
| /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/first.csv | 5 | name | 2 | 5 | 5 | forbidden_character | Disallowed code points: U+0009 |
| /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/first.csv | 6 | name | 2 | 6 | 7 | forbidden_newline | Embedded CR or LF is not allowed |
| /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/second.csv | 2 | id | 1 | 2 | 2 | duplicate_key | Duplicates key (id) first seen at /home/csh/30projects/deliverables/csv-validation-service/verification/final-python312/markdown_report/first.csv row 2 |
