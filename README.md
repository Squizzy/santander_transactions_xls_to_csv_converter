# What is this?

Python App to convert the Santander UK bank individual transactions downloads in XLS format
into CSV for import into homebanking apps such as Homebank or Firefly iii

# Usage
App to convert the Santander UK bank individual transactions downloaded in XLS format
into CSV files for import into homebanking apps such as Homebank or Firefly iii
v1.0

Usage:  
    To process all XLS in the input directory:
        - python santander_transactions_xls_to_csv_converter.py

    To process specific individual XLS files:
        - python santander_transactions_xls_to_csv_converter.py <filename>.xls

    In case 1, files must be stored in the director: in/
    In case 2, the path to the XLS file needs to be specified if it is not in the current directory

    In both cases, the output files are created under:
        - Generic CSV             :   out-generic/
        - Homebank-compliance CSV :   out-homebank/

# Version
v1.0: Working version generating generic CSV and Homebank-specific CSV

# Misc
- Released under GPL
- Fork/Modify at will
- If improvements / mods / additions are desired, open an issue in Github