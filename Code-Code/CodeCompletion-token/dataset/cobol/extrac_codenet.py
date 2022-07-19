import csv
import random
import os
import shutil
import pdb
import json

def write_file(dirname, csv_row):
    with open(dirname + csv_row[0] +'.cbl','w') as fd:
        fd.write(csv_row[1])


def extract_files_from_csv(filename, out_dir):
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)    #skip header row
        for row in csv_reader:
            write_file(out_dir, row)
        

def run_extract_raw_samples():
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

def combine_files(dirname, dataset_split, sample_ids):
    fdw = open(dirname+dataset_split+'.txt', 'w')
    for sample_id in sample_ids:
        with open(dirname+dataset_split+'/'+str(sample_id)+'.cbl') as fd:
            code = fd.read()
        fdw.write(code+"\n")    
    fdw.close()

def run_combine_preprocessed_samples():
    dirname = 'tokenized/codenet_cobol_code_completion/'
    dataset_splits = ['test', 'dev', 'train']
    for dataset_split in dataset_splits:
        subdir = dirname + dataset_split
        sample_filenames = os.listdir(subdir)
        sample_ids = sorted([int(i.strip('.cbl')) for i in sample_filenames])
        combine_files(dirname, dataset_split, sample_ids)

def get_sample_dict(sample_id, code):
    s = {}
    s["id"] = sample_id

    code_split = code.split()
    end = random.randint(int(0.15 * len(code_split)), len(code_split))
    s["input"] = ' '.join(code_split[0:end])
    
    answer = []
    for token in code_split[end:]:
        #if token == '.':
        if token == '<EOL>':
            answer.append(token) 
            break
        answer.append(token) 

    sample_query = s.copy()
    sample_query["gt"] = ""

    sample_answer = s.copy()
    sample_answer["gt"] = ' '.join(answer) 

    return sample_query, sample_answer


def combine_files_linelevel(dirname, dataset_split, sample_ids):
    fdw1 = open(dirname+dataset_split+'.json', 'w')
    fdw2 = open(dirname+dataset_split+'_answers.json', 'w')
    for sample_id in sample_ids:
        with open(dirname+dataset_split+'/'+str(sample_id)+'.cbl') as fd:
            code = fd.read()
        sample_query, sample_answer = get_sample_dict(sample_id, code)
        json.dump(sample_query, fdw1)
        json.dump(sample_answer, fdw2)
        fdw1.write("\n")    
        fdw2.write("\n")    
    fdw1.close()
    fdw2.close()


def run_combine_preprocessed_samples_linelevel_benchmark():
    dirname = 'tokenized/codenet_cobol_code_completion/'
    dataset_splits = ['test']
    for dataset_split in dataset_splits:
        subdir = dirname + dataset_split
        sample_filenames = os.listdir(subdir)
        sample_ids = sorted([int(i.strip('.cbl')) for i in sample_filenames])
        combine_files_linelevel(dirname, dataset_split, sample_ids)


#run_extract_raw_samples()
#run_combine_preprocessed_samples()
run_combine_preprocessed_samples_linelevel_benchmark()
