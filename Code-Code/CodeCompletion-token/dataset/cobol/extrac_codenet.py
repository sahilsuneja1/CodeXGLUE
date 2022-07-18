import csv
import os
import shutil
import pdb

def write_file(dirname, csv_row):
    with open(dirname + csv_row[0] +'.cbl','w') as fd:
        fd.write(csv_row[1])


def extract_files_from_csv(filename, out_dir):
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)    #skip header row
        for row in csv_reader:
            write_file(out_dir, row)
        

def run():
    dirname = "codenet_cobol_code_completion/"

    for filename in os.listdir(dirname):
        if not filename.endswith('.csv'):
            continue

        dataset_split = filename.split('.csv')[0].split('_')[-1]
        out_dir = dirname + dataset_split + '/'

        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)

        print(f"Extracting files from {filename}")
        extract_files_from_csv(dirname + filename, out_dir)

run()
