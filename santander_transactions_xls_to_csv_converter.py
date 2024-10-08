""" Python App to convert the Santander UK bank individual transactions downloads in XLS format
into CSV for import into homebanking apps such as Homebank or Firefly iii"""

__author__ = "Squizzy"
__copyright__ = "Copyright 2024, Squizzy"
__credits__ = ""
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Squizzy"

from bs4 import BeautifulSoup
from datetime import datetime
from sys import argv
from typing import TypedDict
import csv
import os

THIS_FILENAME = "santander_transactions_xls_to_csv_converter.py"

# Generate individual statements csv for generic use
GENERATE_CSV_GENERIC = True
# Generate individual statements csv for Homebank
GENERATE_CSV_HOMEBANK = True
# Generate an All-In-One csv combining all the individual statements csv
GENERATE_CSV_AIO = True


# Class defining the type hints for the CSV parameters for the reader and writer
class csv_parameters_types(TypedDict):
    fieldnames: list[str]
    lineterminator: str
    delimiter: str
    escapechar: str | None
    quoting: int

# The folder with the XLS files relative to the current directory
INPUT_FOLDER_WITH_XLS = 'in/'

# Output details for generic CSV files
OUTPUT_FOLDER_FOR_CSV_GENERIC = 'out-generic/'
FILENAME_END_CSV_GENERIC = 'santander-generic.csv'
FILENAME_AIO_CSV_GENERIC = 'aio' + FILENAME_END_CSV_GENERIC
PARAMETERS_CSV_GENERIC: csv_parameters_types = {
    'fieldnames': ['date', 'detail', 'amount in', 'amount out', 'balance'],
    'lineterminator': '\n',
    'delimiter': ',',
    'escapechar': None,
    'quoting': csv.QUOTE_MINIMAL
}

# Output details for Homebank CSV files
OUTPUT_FOLDER_FOR_CSV_HOMEBANK = 'out-homebank/'
FILENAME_END_CSV_HOMEBANK = 'santander-homebank.csv'
FILENAME_AIO_CSV_HOMEBANK = 'aio' + FILENAME_END_CSV_HOMEBANK
PARAMETERS_CSV_HOMEBANK: csv_parameters_types = {
    'fieldnames': ['date', 'payment', 'number', 'payee', 'memo', 'amount', 'category', 'tags'],
    'lineterminator': '\n',
    'delimiter': ';',
    'escapechar': None,
    'quoting': csv.QUOTE_MINIMAL,
}


APP_USAGE = f"""
App to convert the Santander UK bank individual transactions downloaded in XLS format
into CSV files for import into homebanking apps such as Homebank or Firefly iii
v1.0

Usage: 
    To process all XLS in the input directory:
        - python {THIS_FILENAME}
    
    To process specific individual XLS files:
        - python {THIS_FILENAME} <filename>.xls
    
    In case 1, files must be stored in the director: {INPUT_FOLDER_WITH_XLS}
    In case 2, the path to the XLS file needs to be specified if it is not in the current directory
            
    In both cases, the output files are created under:
        - Generic CSV             :   {OUTPUT_FOLDER_FOR_CSV_GENERIC}
        - Homebank-compliance CSV :   {OUTPUT_FOLDER_FOR_CSV_HOMEBANK}
"""


def log(message, arg = None) -> None:
    """
    Logs a message to the console with optional formatting.

    Args:
        message (str): The message to be logged.
        arg (str, optional): Formatting option. If 'tab', the message is followed by a tab.
                             If None or any other value, the message is followed by a newline.

    Returns:
        None
    """

    print(message, end = '\n' if not arg else '\t' if arg == 'tab' else '')
    
    
def are_there_files_to_process() -> bool:
    """
    Checks if there are any files in the input folder.

    Returns:
        bool: True if there are files in the input folder, False otherwise.
    """
    
    # Check if there are files to process
    if not os.path.exists(INPUT_FOLDER_WITH_XLS):
        print("input folder 'in' not found, no file to process, exiting")
        return False
    
    if len(os.listdir(INPUT_FOLDER_WITH_XLS)) == 0:
        print("input folder 'in' is empty, no file to process, exiting")
        return False
    
    if "xls" not in os.listdir(INPUT_FOLDER_WITH_XLS)[0].split('.')[-1]:
        print("input folder 'in' contains no .xls files, no file to process, exiting")
        return False
    
    log("input folder 'in' contains .xls files, processing...")
    return True
   
    
def create_output_folders() -> bool:
    """
    Creates the output folders 'out' and 'out-homebank' if they don't exist.

    Returns:
        bool: True if the output folders were created, False otherwise.
    """
    
    # Create directory for Generic CSV files if it doesn't exist and will be needed
    if GENERATE_CSV_GENERIC:

        if not os.path.exists(OUTPUT_FOLDER_FOR_CSV_GENERIC):
            try:
                os.makedirs(OUTPUT_FOLDER_FOR_CSV_GENERIC)
            except Exception as e:
                log(f'output folder {OUTPUT_FOLDER_FOR_CSV_GENERIC} could not be created: {e}')
                return False
            log(f'output folder {OUTPUT_FOLDER_FOR_CSV_GENERIC} created')
            
        else:
            log(f'output folder {OUTPUT_FOLDER_FOR_CSV_GENERIC} already exists')
    
    # Create directory for Homebank-specific CSV files if it doesn't exist and will be needed
    if GENERATE_CSV_HOMEBANK:

        if not os.path.exists(OUTPUT_FOLDER_FOR_CSV_HOMEBANK):
            try:
                os.makedirs(OUTPUT_FOLDER_FOR_CSV_HOMEBANK)
            except Exception as e:
                log(f'output folder {OUTPUT_FOLDER_FOR_CSV_HOMEBANK} could not be created: {e}')
                return False
            log(f'output folder {OUTPUT_FOLDER_FOR_CSV_HOMEBANK} created')   

        else:
            log(f'output folder {OUTPUT_FOLDER_FOR_CSV_HOMEBANK} already exists')     
    
    return True
    
    
def extract_individual_statement_transactions_dictionary_from_XLS(filename: str, destination: str = '') -> list[dict[str, str|float]]:
    """
    Extracts transaction data from an XLS file and converts it into a list of dictionaries.

    This function reads an XLS file (which is actually in HTML format), parses its content,
    and extracts transaction data. It can create either a Homebank-specific dictionary
    or a more generic dictionary based on the 'destination' parameter.

    Args:
        filename (str): The name of the XLS file to process.
        destination (str, optional): Specifies the output format. 
                                    If 'homebank', creates a Homebank-specific dictionary. 
                                    Defaults to an empty string, which creates a generic dictionary.

    Returns:
        list[dict[str, str|float]]: A list of dictionaries, where each dictionary represents
                                    a transaction with various fields like date, amount, memo, etc.

    Note:
        - The function assumes the XLS file is in HTML format and contains a single table.
        - The rows are reversed to put earlier transactions at the top.
        - Only rows with 9 elements are processed; others are considered separators.
    """
    
    
    # Type hint the output
    dict_lines: list[dict[str, str|float]]= []
    
    # Open the requested xls file in HTML format as read-only
    with open(filename, 'r') as f:
    
        # Parse the HTML.
        soup = BeautifulSoup(f, 'lxml')
        # It has only one table, extract it
        table = soup.find_all('table')
        # Extract all rows
        rows = table[0].find_all('tr')
        
        # Reverse the rows so that the earlier transactions are at the top
        rows.reverse()
        
        # Process each row one at a time
        for row in rows:
            
            line:list[str] = []
            
            # Extract all cells of that row into a list
            for cell in row.find_all('td'):
                line.append(str(cell.text.strip()))
            
            # Create a dictionary from the list
            line_dict:dict[str, str | float]= {}
            
            # Check if the line has 9 elements - if not, it is a separator
            if len(line) == 9:
                
                # If a homebank-specific CSV is requested, create specific dictionary
                if destination == 'homebank':
                    line_dict = {
                        'date': line[1],
                        'payment': 0,
                        'number': '',
                        'payee': '',
                        'memo': line[3] + line[4],
                        'amount': float((line[5]).replace(',','').replace('£','')) if line[5] else -float((line[6]).replace(',','').replace('£','')),
                        'category': '',
                        'tags': '',
                    }
                    
                    
                # Otherwise, create a more generic dictionary
                # This option is the default (if destination is not 'homebank')
                # Other options could be added inbetween if other app-specific CSVs are needed
                else:
                    line_dict = {
                        'date': line[1],
                        'detail': line[3] + line[4],
                        'amount in': line[5],
                        'amount out': line[6],
                        'balance': line[7],
                    }
                
                # Add the dictionary to the list that will be returned
                dict_lines.append(line_dict)

    return dict_lines    
    

def get_start_and_end_dates_from_individual_statement_transactions_dictionary(this_statement: list[dict[str, str|float]]) -> tuple[str, str]:
    """
    Extracts the start and end dates from a list of statement transactions.
    This is needed for the CSV file name which can't have a slash in it.
    However the slash is used in the CSV for clarity

    Args:
        this_statement (list[dict[str, str|float]]): A list of dictionaries representing transactions.

    Returns:
        tuple[str, str]: A tuple containing the start date and end date in 'YYYYMMDD' format.

    Note:
        - Assumes the transactions are sorted chronologically.
        - The first transaction's date is used as the start date.
        - The last transaction's date is used as the end date.
    """

    # convert dates from DD/MM/YYYY to YYYYMMDD
    start_date = datetime.strptime(str(this_statement[0]['date']), "%d/%m/%Y").strftime('%Y%m%d')
    end_date = datetime.strptime(str(this_statement[-1]['date']), "%d/%m/%Y").strftime('%Y%m%d')
    
    return start_date, end_date
    
    
def write_individual_statement_transactions_dictionary_to_csv(dict_lines: list[dict[str, str|float]], flag: str, csv_file: str, destination: str = '') -> None:
    """
    Writes a list of dictionaries to a CSV file.

    Args:
        dict_lines (list[dict[str, str|float]]): A list of dictionaries representing transactions.
        flag (str): The file opening mode ('w' for write, 'a' for append).
        csv_file (str): The path and name of the CSV file to write.
        destination (str, optional): Specifies the output format. 
                                     If 'homebank', uses Homebank-specific settings.
                                     Defaults to an empty string, which uses generic settings.

    Returns:
        None

    Note:
        - The function adjusts CSV writing settings based on the 'destination' parameter.
        - For 'homebank' destination, it uses specific field names and CSV formatting.
        - For generic destination, it uses different field names and CSV formatting.
    """   
    
    # Open the individual statement CSV file
    with open(csv_file, flag) as f:
        
        # Set the csv fields and format in the case of homebank
        if destination == 'homebank':
            csv_parameters = PARAMETERS_CSV_HOMEBANK
        
        # Set the csv fields and format in the case of generic
        else:
            csv_parameters = PARAMETERS_CSV_GENERIC

        # Create the CVS writer instance using above settings
        writer = csv.DictWriter(f, 
                                fieldnames=csv_parameters['fieldnames'], 
                                lineterminator=csv_parameters['lineterminator'], 
                                delimiter=csv_parameters['delimiter'], 
                                escapechar=csv_parameters['escapechar'], 
                                quoting=csv_parameters['quoting']
                                )
        
        # create the CSV header
        writer.writeheader()
        
        # Write the rows
        writer.writerows(dict_lines)
        
        log(f'Created: {csv_file}')
    
    
def generate_individual_statement_csv(filename: str, destination: str = '') -> list[dict[str, str|float]]:
    """
    Creates a CSV file from a given XLS file containing bank statement data.

    This function reads an XLS file, extracts the transaction data, identifies the
    start and end dates of the transactions, and writes the data to a CSV file.
    The CSV file is named using the start and end dates of the transactions.

    Args:
        filename (str): The name of the XLS file to process.
        destination (str, optional): Specifies the output format. 
                            If 'homebank', creates a Homebank-specific dictionary. 
                            Defaults to an empty string, which creates a generic dictionary.

    Returns:
        list[dict[str, str|float]]: A list of dictionaries representing the transactions
                                    extracted from the XLS file.

    Note:
        - The function uses the `extract_dictionary_from_file` function to read the XLS file.
        - The output CSV file is created in the 'out-homebank' directory.
        - The function logs various steps of the process.
    """

    # Process a statement XLS, retrieving a dictionary formated either generically, or for Homebase
    log(f'\nReading: {filename}: ', 'tab')
    this_statement_transactions: list[dict[str, str|float]] = extract_individual_statement_transactions_dictionary_from_XLS(filename, destination)
    log(f'Read {len(this_statement_transactions)} lines')
    
    # Identify the first and last dates of the transations in this dictionary
    start_date, end_date = get_start_and_end_dates_from_individual_statement_transactions_dictionary(this_statement_transactions)
    log(f'Start date: {start_date} - End date: {end_date} -> ', 'tab')
    
    # Create the output filenames based on the dates above
    if destination == 'homebank':
        filename_csv = OUTPUT_FOLDER_FOR_CSV_HOMEBANK + start_date + '-' + end_date + FILENAME_END_CSV_HOMEBANK
    else:
        filename_csv = OUTPUT_FOLDER_FOR_CSV_GENERIC + start_date + '-' + end_date + FILENAME_END_CSV_GENERIC

    # Write the dictionary passed as argument to a csv named using these dates
    write_individual_statement_transactions_dictionary_to_csv(this_statement_transactions, "w", filename_csv, destination)
    
    return this_statement_transactions


def generate_individual_statements_csv_for_all_input_XLS(destination: str = '') -> None:
    """
    Creates individual CSV files for all XLS files in the input directory.

    Args:
        destination (str, optional): Specifies the output format. 
                                     If 'homebank', creates Homebank-specific CSV files.
                                     Defaults to an empty string, which creates generic CSV files.

    Returns:
        None

    Note:
        - The function processes all .xls files in the 'in' directory.
        - It uses the create_statement_csv function to process each file.
        - The resulting CSV files are saved in either the generic or Homebank-specific output folder,
          depending on the 'destination' parameter.
    """

    files_list = sorted(os.listdir(INPUT_FOLDER_WITH_XLS))

    # Loop through each file
    for filename in files_list:
        
        # Only process .xls files
        if filename.endswith('.xls'):

            # Create a CSV file from the XLS file
            generate_individual_statement_csv(INPUT_FOLDER_WITH_XLS + filename, destination)


def create_aio_statement_csv(destination: str = '') -> bool:

    # Load the required information to create the all-in-one file
    if destination == 'homebank':
        # Create a list of all files from the desired directory, including the path to it from the current directory
        files_list = list(map(lambda x: OUTPUT_FOLDER_FOR_CSV_HOMEBANK + x , sorted(os.listdir(OUTPUT_FOLDER_FOR_CSV_HOMEBANK))))
        
        # Remove the Homebank-specific all-in-one file
        if OUTPUT_FOLDER_FOR_CSV_HOMEBANK + FILENAME_AIO_CSV_HOMEBANK in files_list:
            files_list.remove(OUTPUT_FOLDER_FOR_CSV_HOMEBANK + FILENAME_AIO_CSV_HOMEBANK)
        
        # Create the filename for the all-in-one file
        filename_aio = OUTPUT_FOLDER_FOR_CSV_HOMEBANK + FILENAME_AIO_CSV_HOMEBANK
        
        # Set the CSV parameters to use for the Homebank-specific all-in-one file
        csv_parameters = PARAMETERS_CSV_HOMEBANK
        
    else:
        # Create a list of all files from the desired directory, including the path to it from the current directory
        files_list = list(map(lambda x: OUTPUT_FOLDER_FOR_CSV_GENERIC + x , sorted(os.listdir(OUTPUT_FOLDER_FOR_CSV_GENERIC))))
        
        # Remove the generic all-in-one file
        if OUTPUT_FOLDER_FOR_CSV_GENERIC + FILENAME_AIO_CSV_GENERIC in files_list: 
            files_list.remove(OUTPUT_FOLDER_FOR_CSV_GENERIC + FILENAME_AIO_CSV_GENERIC)
        
        # Create the filename for the all-in-one file
        filename_aio = OUTPUT_FOLDER_FOR_CSV_GENERIC + FILENAME_AIO_CSV_GENERIC
        
        # Set the CSV parameters to use for the generic all-in-one file
        csv_parameters = PARAMETERS_CSV_GENERIC
        
    # Check that there are files to process
    if len(files_list) == 0:
        print("No files to process. This file is generated from the individual CSV files, create them first, exiting")
        return False

    # Last date found in the transactions statement that was just processed
    # Initially a random date far far into the past
    last_date = "00010101"
    
    # Open the all-in-one file    
    with open (filename_aio, 'w') as f2:
        writer = csv.DictWriter(f2, 
                                fieldnames=csv_parameters['fieldnames'],
                                lineterminator=csv_parameters['lineterminator'],
                                delimiter=csv_parameters['delimiter'],
                                escapechar=csv_parameters['escapechar'],
                                quoting=csv_parameters['quoting'])
        
        writer.writeheader()
        
        # Loop through each file in the folder
        for filename in files_list:
            log(f'Processing {filename}', 'tab')
            
            # Open the file to be processed
            with open (filename, 'r') as f:
                reader = csv.DictReader(f, 
                                        fieldnames=csv_parameters['fieldnames'],
                                        lineterminator=csv_parameters['lineterminator'],
                                        delimiter=csv_parameters['delimiter'],
                                        escapechar=csv_parameters['escapechar'],
                                        quoting=csv_parameters['quoting'])
            
                # skip the individual statement header (first line of the file)
                next(reader, None)
                
                # Loop through each line of the individual statement file
                for row in reader:

                    # Extract the date of the current transaction
                    this_date = datetime.strptime(str(row['date']), "%d/%m/%Y").strftime('%Y%m%d')
                    
                    # If the date is later than the last date of the previous individual statement,
                    # then write the row to the all-in-one file
                    if this_date > last_date:
                        writer.writerow(row)
                        
                # Set the last date to the last date of the current individual statement
                last_date = this_date
            log(f'Processed {filename}')
            
    log(f'Created {filename_aio}')        
    
    return True

    
def main() -> int:
    """
    Main function to process bank statement XLS files and create CSV files.

    This function handles two scenarios:
    1. If a filename is provided as a command-line argument, it processes that single file.
    2. If no argument is provided, it processes all XLS files in the Input directory.

    The function creates individual CSV files for each XLS file and optionally creates
    an all-in-one CSV file combining all statements.

    Returns:
        int: 0 if the process completes successfully, 1 if there's an error with the input file.

    Note:
        - The function creates an output directory if it doesn't exist.
        - For single file processing, the file must have a .xls extension.
        - For batch processing, it calls `create_all_individual_statement_csvs()`.
        - The all-in-one CSV creation is currently commented out.
    """

    # Create the required output directory(ies) as needed
    if not create_output_folders():
        return 1
      
      
    # If the app was launched with a filename as argument, process only this file
    if len(argv) > 1:
        
        # Only one file can be specified
        if len(argv) > 2:
            print(APP_USAGE)
            return 1
    
        # retrieve the filename
        filename = argv[1]

        # verify that at least the filename has the .xls extension
        if not filename.endswith('.xls'):
            print(APP_USAGE)
            return 1

        if GENERATE_CSV_GENERIC:
            # Proceed to create the generic CSV file
            generate_individual_statement_csv(filename)
        
        if GENERATE_CSV_HOMEBANK:
            # Proceed to create the homebase CSV file
            generate_individual_statement_csv(filename, "homebank")
        
        return 0
        
        
    # If no arguments are provided, batch process    
    else:

        # Check if there are any files in the input folder
        if not are_there_files_to_process():
            print(APP_USAGE)
            return 1
    
        # If generic files are requested
        if GENERATE_CSV_GENERIC:
            # batch generate the individual CSV
            generate_individual_statements_csv_for_all_input_XLS()

            # If an AIO is requested, create it
            if GENERATE_CSV_AIO:
                if not create_aio_statement_csv():
                    print("Error creating all-in-one generic CSV file")
                    return 1
                
        # If homebank specific CSV are requested
        if GENERATE_CSV_HOMEBANK:
            # batch generate the individual CSV
            generate_individual_statements_csv_for_all_input_XLS("homebank")
            
            # If an AIO is requested, create it
            if GENERATE_CSV_AIO:
                if not create_aio_statement_csv("homebank"):
                    print("Error creating all-in-one Homebank CSV file")
                    return 1

        return 0


if __name__ == '__main__':
    main()