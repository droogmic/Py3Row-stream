import csv
from flask import Flask
app = Flask(__name__)

NUM_ERGS = 4

@app.route('/')
def disp_ergs():
    return_str = ""
    for erg_num in range(NUM_ERGS):
        with open(f'erg{erg_num}.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                row_str = f"Name: {row['Name']:<16} | Distance: {row['Distance']:<16} | Time: {row['Time']:<16} <br/>\n"
                return_str += row_str
    print(return_str)
    return return_str
