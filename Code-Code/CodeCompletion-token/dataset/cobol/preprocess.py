#! /usr/bin/env python3

import os
import sys
import argparse
import pathlib
import string
import tempfile
import subprocess
import time
import csv
import tempfile
import json
import pdb
import re
#import pygments
from pygments.token import Token
from lexer import Lexer

sys.path.insert(0, '../')



def get_path_info(file_path):
    folder = os.path.dirname(file_path)
    file_name = pathlib.Path(file_path).name
    extension = pathlib.Path(file_path).suffix
    file_name_without_suffix = file_name[ : -len(extension)]
    return {
        "folder": folder,
        "suffix": extension,
        "file_name": file_name,
        "file_name_without_suffix": file_name_without_suffix
    }


class Tokenizer:

    def __init__(self, partition_id=None, dataset_name=None):
        self.lexer = Lexer()
        self.lits = json.load(open("literals.json"))
    

    def load_tokens(self, src_path):
        result = []
        cobol_mode = self.lexer.compile_sample(src_path, cobol_mode='BOTH')
        if cobol_mode == 'FAIL':
            print(f"Compilation failed for {src_path}; should not happen")
            return result

        path_info = get_path_info(src_path)
        preprocessed_file = path_info['folder'] + '/' + path_info['file_name_without_suffix'] + '_preprocessed' + path_info['suffix']

        cobol_mode = self.lexer.preprocess_and_compile(src_path, cobol_mode=cobol_mode, output_file=preprocessed_file)
        if cobol_mode == 'FAIL':
            print(f"Compiling post Preprocessing failed ofr {src_path}; should not happen")
            return result

        cobol_mode, code_tokens = self.lexer.lex_and_compile(preprocessed_file, cobol_mode=cobol_mode)
        if cobol_mode == 'FAIL':
            print(f"Compiling post Lexing post Preprocessing failed ofr {src_path}; should not happen")
            return result

        result = code_tokens
        return result
    

    def load_tokens_nocompile(self, src_path):
        result = []

        path_info = get_path_info(src_path)
        preprocessed_file = path_info['folder'] + '/' + path_info['file_name_without_suffix'] + '_preprocessed' + path_info['suffix']

        cobol_mode = self.lexer.preprocess_and_nocompile(src_path, cobol_mode='BOTH', output_file=preprocessed_file)
        if cobol_mode == 'FAIL':
            print(f"Preprocessing failed ofr {src_path}; should not happen")
            return result

        result = self.lexer.get_tokens_unfiltered(preprocessed_file, cobol_mode='FREE')
        return result

    
    def write_file(self, filename, contents):
        try:
            with open(filename, 'w') as fp:
                fp.write(contents)
        except UnicodeEncodeError:
            with open(filename, 'wb') as fp:
                fp.write(contents.encode('utf-8'))


    def get_dest_dir(self,  dataset_name):
        reduced_folder = os.getcwd() + "/tokenized/" + dataset_name
        if not os.path.exists(reduced_folder):
            os.makedirs(reduced_folder)
        return reduced_folder


    def load_sample(self, sample_path, scratch_path):
        sample = None
        if not os.path.exists(sample_path):
            print ("Error: no source file is found @ " + sample_path)
            return sample
        try:    
            with open(sample_path,'r') as fd:
                sample = fd.read()
            self.write_file(scratch_path, sample)
        except:         
            print("ERROR: ", sys.exc_info()[0])
        return sample

   
    def get_dest_path(self, src_path, reduced_folder):
        dest_path = ""  # the reduced soruce code will be saved in dest_path
        path_info = get_path_info(src_path)
        file_cnt = 0
        while True:
            dest_file = path_info["file_name_without_suffix"] + ('' if file_cnt == 0 else ("_%d" % file_cnt)) + path_info["suffix"]
            dest_path = os.path.join(reduced_folder, dest_file)
            if not os.path.exists(dest_path):
                break
            else:
                file_cnt += 1
        return dest_path


    def process_string(self, token, special_chars={" ": "U+0020", ",": "U+002C"}):
        str_quote_options = ["'''", '"""', "'", '"']
        start_quote = ""
        end_quote = ""
        qualifier_regex = r"^[a-zA-Z]+"
        qualifier_match = re.search(qualifier_regex, token)
        # string qualifiers like 'r' for regex, 'f' for formatted string, 'b' for bytes, 'u' for unicode, etc (or combination of them)
        qualifier = "" if not qualifier_match else qualifier_match[0]
        # token string without qualifiers
        token_string = re.sub(qualifier_regex, "", token)
        # string literal without quotes
        str_lit = token_string
        for q in str_quote_options:
            if token_string.startswith(q):
                start_quote = q
                str_lit = str_lit[len(q) :]
                if token_string.endswith(q):
                    end_quote = q
                    str_lit = str_lit[: -len(q)]
                break
        # if start_quote in str_quote_options[:2]:
        #     return ""
        for sc in special_chars:
            str_lit = str_lit.replace(sc, special_chars[sc])
        return (
            f"{qualifier}{start_quote}<STR_LIT:{str_lit}>{end_quote}"
            if str_lit in self.lits['str']
            else f"{qualifier}{start_quote}<STR_LIT>{end_quote}"
        )


    def normalize_tokens(self, tokens):
        #pdb.set_trace()
        out_tokens = []
        prev_tokens = ''
        prev_eol = False
        prev_token = ''
        outstanding_eol= False
        update_track_vars = True

        for token_type,token_val in tokens:
            update_track_vars = True

            if token_type.parent == Token.Literal.String:
                out_tokens.append(self.process_string(token_val))

            elif token_type == Token.Literal.Number.Integer:
                if token_val.strip() in self.lits['num']:
                    out_tokens.append(f"<NUM_LIT:{token_val.strip()}>")
                else:
                    out_tokens.append("<NUM_LIT>")

            elif token_type == Token.Text and token_val == '\n':
                if prev_eol:
                    continue

            elif token_type == Token.Text.Whitespace:
                continue

            else:
                out_tokens.append(token_val.strip())
                
            #v2: enforcing EOL for all newlines 
            if token_val.endswith('\n'):
                out_tokens.append("<EOL>")
                prev_eol = True
            else:
                prev_eol = False

        while out_tokens[0] == "<EOL>":
            out_tokens = out_tokens[1:]
        while out_tokens[-1] == "<EOL>":
            out_tokens = out_tokens[:-1]

        return out_tokens


    def tokenize_loaded_sample(self, dataset_name, sample, src_path):
        dest_dir = self.get_dest_dir(dataset_name)
        #tokens = self.load_tokens(src_path)
        tokens = self.load_tokens_nocompile(src_path)
        tokens = self.normalize_tokens(tokens)
        tokens = ["<s>"] + tokens + ["</s>"]
        #pdb.set_trace()
        tokenized_code = " ".join(tokens)

        dest_path = self.get_dest_path(src_path, dest_dir)
        with open(dest_path, 'w') as code_fp:
            code_fp.write(tokenized_code)
        print("- save tokenized code @ " + dest_path)

        return {
            "input_src_path": src_path,
            "input_src_token_cnt": len(tokens),
            "reduced_src_path": dest_path
        }



    def get_finished_list(self, finished_list_file):
        # read what have been finished
        # finished_list contains res["input_src_path"] == src_path
        pathlib.Path(finished_list_file).touch()
        with open(finished_list_file, "r") as fp:
            finished_list = [line.split(", ")[0] for line in fp.readlines()]
        return finished_list
    
    
    def get_skipped_list(self, skipped_list_file):
        pathlib.Path(skipped_list_file).touch()
        with open(skipped_list_file,'r') as fd:
            skiplist = [i.strip() for i in fd.readlines()]
        return skiplist    
    
    
    def set_finished_list(self, res, finished_list_file):
        with open(finished_list_file, "a") as fp:
            line = "%s, %d, %s\n" % (res["input_src_path"], res["input_src_token_cnt"], res["reduced_src_path"])
            fp.write(line)
    

    def get_finished_list_all(self, num_partitions):
        finished_list = []
        for partition_id in range(1, num_partitions+1):
            filename = 'finished_list_' + str(partition_id) +  ".txt"
            pathlib.Path(filename).touch()
            with open(filename, "r") as fp:
                finished_list += [line.split(',')[0] for line in fp.readlines()]
        return finished_list


    def get_skipped_list_all(self, num_partitions):
        skipped_list = []
        for partition_id in range(1, num_partitions+1):
            filename = 'skipped_list_' + str(partition_id) +  ".txt"
            pathlib.Path(filename).touch()
            with open(filename, "r") as fp:
                skipped_list += [i.strip() for i in fp.readlines()]
        return skipped_list


    def tokenize(self, dataset_name, samples_dir, scratch_dir, num_partitions=1, partition_id=1):
        finished_list_file = "finished_list_" + str(partition_id) +  ".txt"
        skipped_list_file = "skipped_list_" + str(partition_id) + ".txt"

        finished_list_all = self.get_finished_list_all(num_partitions)
        skipped_list_all = self.get_skipped_list_all(num_partitions)

        ctr = len(finished_list_all)
        print(f"{ctr} samples already tokenized; resuming tokenization of other samples")

        samples = os.listdir(samples_dir)
        num_samples = len(samples)
        num_samples_per_partition = int(num_samples / num_partitions)
        sample_id_start = (partition_id-1) * num_samples_per_partition
        sample_id_end = sample_id_start + num_samples_per_partition
        if partition_id == num_partitions:
            sample_id_end += num_samples % num_partitions

        for sample_file in samples[sample_id_start: sample_id_end]:
            #pdb.set_trace()
            sample_path = samples_dir + '/' + sample_file
            src_path = scratch_dir + '/' + sample_file
            sample = self.load_sample(sample_path, src_path)
            if not sample:
               continue
            if src_path in finished_list_all or src_path in skipped_list_all: #don't redo work
                continue
            ctr += 1    
            print(f"tokenizing sample #{ctr}: {sample_file}", flush=True)
            res = self.tokenize_loaded_sample(dataset_name, sample, src_path)
            self.set_finished_list(res, finished_list_file)
            print(f"tokenizing sample #{ctr}: {sample_file}")
            #exit(0)
        
        print("Finished job")


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--num_partitions', dest='num_partitions', type=int, action="store", default=1, help="total number of parititons")
    parser.add_argument('--partition_id', dest='partition_id', type=int, action="store", default=1, help="partition id for this process")
    args = parser.parse_args()
    assert(args.partition_id >= 1)
    assert(args.partition_id <= args.num_partitions)
    print(f"Partition info: {args.partition_id}/{args.num_partitions}")
    return args


if __name__ == '__main__':
    args = get_args()
    #dataset_name = "cobol_opensource_validation"
    #dataset_name = "tmp_dataset"
    dataset_name = "codenet_cobol_code_completion/train"
    #dataset_name = "pretrain_cobol_data_improved_train_compiled"
    #dataset_name = "tmp_dataset"
    #work_dir_prefix = "/home/cobol_project/"
    work_dir_prefix = "/home/cobol_project/CodeXGLUE/Code-Code/CodeCompletion-token/dataset/cobol/"
    samples_dir = work_dir_prefix + dataset_name + '/'
    scratch_dir = work_dir_prefix + "preprocess_scratch"

    t = Tokenizer(partition_id=args.partition_id,
                        dataset_name=dataset_name)

    t.tokenize(dataset_name,
                samples_dir,
                scratch_dir,
                args.num_partitions,
                args.partition_id)
