import pdb
import os
import sys
import pathlib
import subprocess
import pygments
from pygments.lexers import CobolLexer
from pygments.lexers import CobolFreeformatLexer
from pygments.token import Token


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



class Lexer():
        
    def __init__(self):
        pass

    def print_tokens(self, lexer, code):
        tokens = lexer.get_tokens(code)
        for token in tokens:
            print(token)


    def print_code_without_comments(self, lexer, code):
        tokens = lexer.get_tokens(code)
        fd = open('out.cbl','w')
        for token in tokens:
            if token[0] == Token.Comment:
                continue
            fd.write(token[1])
        fd.close()     
        print('code without comments written to out.cbl')


    def example_lexer(self):
        lexer = CobolLexer()   
        #lexer = CobolFreeformatLexer()

        #with open('322.cbl') as fd:
        #with open('459.cbl') as fd:
        #with open('1085.cbl') as fd:
        with open('588.cbl') as fd:
        #with open('1725.cbl') as fd:
        #with open('23_1.cbl') as fd:
            code = fd.read()

        self.print_tokens(lexer, code)
        #print_code_without_comments(lexer, code)
        

    def example_lexer_perline(self):
        lexer = CobolLexer()
        #lexer = CobolFreeformatLexer()

        #with open('322.cbl') as fd:
        #with open('1085.cbl') as fd:
        #with open('459.cbl') as fd:
        #with open('preprocessed.cbl') as fd:
        with open('588.cbl') as fd:
            codelines = fd.readlines()

        for idx,line in enumerate(codelines):    
            for token in lexer.get_tokens(line):
                #print(idx, token)
                print(token)


    def run_process(self, cmd, verbose=False):
        try:
            p  = subprocess.run(cmd, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
            if verbose:
                print(' '.join(cmd))
                print(p.stdout.decode() + p.stderr.decode())
                print("\n")
            return p
        except:
            print("Unexpected error:", sys.exc_info()[0])


    def remove_file(self, filename):
        if os.path.exists(filename):
            os.remove(filename)


    def run_cmd(self, cmd, out_filename, sample_filepath, verbose=False):
        self.remove_file(out_filename)
        p = self.run_process(cmd, verbose)
        if p.returncode == 0 and os.path.exists(out_filename):
            return True
        if os.path.exists(out_filename):
            print(f"File compiled but with non-zero return code: {sample_filepath}")
            return True
        return False


    def compile_sample(self, sample_filepath, verbose=False, cobol_mode='BOTH'):
        compiler = "/usr/local/bin/cobc"
        res = False

        #obj_filename = 'test.o'
        path_info = get_path_info(sample_filepath)
        obj_filename = path_info['folder'] + '/' + path_info['file_name_without_suffix'] + '.o'

        if cobol_mode != 'FREE':
            cmd = [compiler, '-c', sample_filepath, '-o', obj_filename]
            res = self.run_cmd(cmd, obj_filename, sample_filepath, verbose)

        if res is True:
            return 'STRICT'

        if cobol_mode != 'STRICT':
            cmd = [compiler, '-free', '-c', sample_filepath, '-o', obj_filename]
            res = self.run_cmd(cmd, obj_filename, sample_filepath, verbose)
        
        if res is True:
            return 'FREE'

        return 'FAIL'


    def preprocess_sample(self, sample_filepath, out_filename, cobol_mode='BOTH'):
        compiler = "/usr/local/bin/cobc"
        res = False

        if cobol_mode != 'FREE':
            cmd = [compiler, '-E', sample_filepath, '-o', out_filename]
            res = self.run_cmd(cmd, out_filename, sample_filepath)
         
        if res is True:
            return 'STRICT'

        if cobol_mode != 'STRICT':
            cmd = [compiler, '-free', '-E', sample_filepath, '-o', out_filename]
            res = self.run_cmd(cmd, out_filename, sample_filepath)
        
        if res is True:
            return 'FREE'

        return 'FAIL'



    def lex_and_compile_v0_v1(self, sample_pathname, cobol_mode='STRICT'):
        lexer = CobolLexer()   
        if cobol_mode == 'FREE':
            lexer = CobolFreeformatLexer()

        with open(sample_pathname) as fd:
            sample_code = fd.read()
        
        tmp_filename = 'test.cbl'
        remove_file(tmp_filename)
        with open(tmp_filename, 'w') as fd:
            tokens = lexer.get_tokens(sample_code) 
            for token in tokens:
                #v0: not needed after comments removed via preprocessor
                #if token[0] == Token.Comment and token[1].lstrip().startswith('*'):
                #    continue

                #v1: working
                fd.write(token[1])

        #pdb.set_trace()
        res = self.compile_sample(tmp_filename, cobol_mode=cobol_mode)
        self.remove_file(tmp_filename)

        return res


    def lex_and_compile_v2(self, sample_pathname, cobol_mode='STRICT'):
        lexer = CobolLexer()   
        if cobol_mode == 'FREE':
            lexer = CobolFreeformatLexer()

        with open(sample_pathname) as fd:
            sample_codelines = fd.readlines()
        
        tmp_filename = 'test.cbl'
        remove_file(tmp_filename)

        with open(tmp_filename, 'w') as fd:
            for idx,line in enumerate(sample_codelines):
                for token in lexer.get_tokens(line): 
                    if token == (Token.Text, '\n'):
                        continue
                    #if token[0] == Token.Text.Whitespace:
                    #    continue
                    #fd.write(token[1]+" ")
                    fd.write(token[1])
                fd.write('\n')

        pdb.set_trace()
        res = self.compile_sample(tmp_filename, cobol_mode=cobol_mode)
        if res == 'FAIL':
            pdb.set_trace()
        self.remove_file(tmp_filename)

        return res

        
    def get_tokens(self, sample_pathname, cobol_mode='STRICT'):
        lexer = CobolLexer()   
        if cobol_mode == 'FREE':
            lexer = CobolFreeformatLexer()

        with open(sample_pathname) as fd:
            sample_codelines = fd.readlines()

        code_tokens = []
        token_idx = 1

        for line_idx,line in enumerate(sample_codelines):
            for token in lexer.get_tokens(line): 
                if token == (Token.Text, '\n'):
                    continue
                code_tokens.append( (token_idx, (line_idx+1, token[1])) )
                token_idx += 1

        return code_tokens
    

    def get_tokens_unfiltered(self, sample_pathname, cobol_mode='STRICT'):
        lexer = CobolLexer()   
        if cobol_mode == 'FREE':
            lexer = CobolFreeformatLexer()

        with open(sample_pathname) as fd:
            sample_codelines = fd.readlines()

        code_tokens = []
        token_idx = 1

        for line_idx,line in enumerate(sample_codelines):
            for token in lexer.get_tokens(line): 
                code_tokens.append(token)
                token_idx += 1

        return code_tokens

        
    def build_code(self, code_tokens):
        code = ""
        current_line = 0

        for token_idx, token in code_tokens:
            if current_line == 0:
                current_line = token[0]

            if current_line < token[0]:
                code += "\n"
                current_line = token[0]

            code += token[1]

        code += "\n"
        return code


    def lex_and_compile(self, sample_pathname, cobol_mode='STRICT'):
        code_tokens = self.get_tokens(sample_pathname, cobol_mode=cobol_mode)
        code = self.build_code(code_tokens)

        
        #tmp_filename = 'test.cbl'
        path_info = get_path_info(sample_pathname)
        tmp_filename = path_info['folder'] + '/' + path_info['file_name_without_suffix'] + '_lexed' + path_info['suffix']

        self.remove_file(tmp_filename)
        with open(tmp_filename, 'w') as fd:
            fd.write(code)

        #pdb.set_trace()
        res = self.compile_sample(tmp_filename, cobol_mode=cobol_mode)
        if res == 'FAIL':
            pdb.set_trace()
        self.remove_file(tmp_filename)

        #return res, code_tokens
        return res, self.get_tokens_unfiltered(sample_pathname, cobol_mode=cobol_mode)


    def preprocess_and_compile(self, sample_pathname, cobol_mode='STRICT', output_file=None):
        #tmp_filename = 'test.cbl'
        path_info = get_path_info(sample_pathname)
        tmp_filename = path_info['folder'] + '/' + path_info['file_name_without_suffix'] + '_preprocessed' + path_info['suffix']

        if output_file:
            tmp_filename = output_file

        self.remove_file(tmp_filename)

        res = self.preprocess_sample(sample_pathname, tmp_filename, cobol_mode=cobol_mode)
        if res == 'FAIL':
            print(f"Preprocessing failed ofr {sample_pathname}; should not happen")
            input('Press key to continue')
       
        #remove first line == preprocessor output
        with open(tmp_filename) as fd:
            code = fd.readlines()

        with open(tmp_filename,'w') as fd:
            for line in code[1:]:
                fd.write(line)

        res = self.compile_sample(tmp_filename, cobol_mode='FREE')
        if not output_file:
            self.remove_file(tmp_filename)

        return res
    

    def preprocess_and_nocompile(self, sample_pathname, cobol_mode='STRICT', output_file=None):
        if output_file:
            tmp_filename = output_file
        else:    
            path_info = get_path_info(sample_pathname)
            tmp_filename = path_info['folder'] + '/' + path_info['file_name_without_suffix'] + '_preprocessed' + path_info['suffix']

        self.remove_file(tmp_filename)

        res = self.preprocess_sample(sample_pathname, tmp_filename, cobol_mode=cobol_mode)
        if res == 'FAIL':
            print(f"Preprocessing failed ofr {sample_pathname}; should not happen")
            return res
       
        #remove first line == preprocessor output
        with open(tmp_filename) as fd:
            code = fd.readlines()

        with open(tmp_filename,'w') as fd:
            for line in code[1:]:
                fd.write(line)

        if not output_file:
            self.remove_file(tmp_filename)

        return res


    def preprocess_and_lex_and_compile(self, sample_pathname, cobol_mode='STRICT'):
        #preprocessed_file = 'preprocessed.cbl'
        path_info = get_path_info(sample_pathname)
        preprocessed_file = path_info['folder'] + '/' + path_info['file_name_without_suffix'] + '_preprocessed' + path_info['suffix']

        res = self.preprocess_and_compile(sample_pathname, cobol_mode=cobol_mode, output_file=preprocessed_file)
        if res == 'FAIL':
            print(f"Compiling post Preprocessing failed ofr {sample_pathname}; should not happen")
            input('Press key to continue')

        res, _ = self.lex_and_compile(preprocessed_file, cobol_mode='FREE')
        self.remove_file(preprocessed_file)
        return res
        


    def write_status_list(self, status_file, sample_filename):
        with open(status_file,'a') as fd:
            fd.write(sample_filename+"\n")


    def read_status_list(self, status_file):
        with open(status_file,'r') as fd:
            return [i.strip() for i in fd.readlines()]


    def load_sample(self, sample_path, scratch_path):
        sample = None
        if not os.path.exists(sample_path):
            print ("Error: no source file is found @ " + sample_path)
            return sample
        try:
            with open(sample_path,'r') as fd:
                sample = fd.read()
            with open(scratch_path,'w') as fd:
                fd.write(sample)
        except:
            print("ERROR: ", sys.exc_info()[0])
        return sample


    def lex_and_compile_samples(self):
        pass_ctr = 0
        sample_dir = '/home/cobol_project/dataset/cobol_opensource_validation'
        scratch_dir = '/home/cobol_project/dd/lexer_scratch'
        finished_list_file = 'finished_list'
        failed_list_file = 'failed_list'

        finished_list = self.read_status_list(finished_list_file)
        failed_list = self.read_status_list(failed_list_file)

        sample_files = os.listdir(sample_dir)
        for sample_filename in sample_files:
            #sample_filename = '398.cbl'
            if sample_filename in finished_list or sample_filename in failed_list:
                continue

            sample_pathname = sample_dir + '/' + sample_filename
            src_pathname = scratch_dir + '/' + sample_filename
            sample = self.load_sample(sample_pathname, src_pathname)

            #pdb.set_trace()
            res = self.compile_sample(src_pathname, cobol_mode='BOTH')
            if res == 'FAIL':
                print(f"Compilation failed for {src_pathname}; should not happen")
                input('Press key to continue')

            if res == 'FREE':
                #res = preprocess_and_compile(sample_pathname, cobol_mode='FREE')
                #res = lex_and_compile(sample_pathname, cobol_mode='FREE')
                res = self.preprocess_and_lex_and_compile(src_pathname, cobol_mode='FREE')
            else:
                #res = preprocess_and_compile(sample_pathname, cobol_mode='STRICT')
                #res = lex_and_compile(sample_pathname, cobol_mode='STRICT')
                res = self.preprocess_and_lex_and_compile(src_pathname, cobol_mode='STRICT')
            
            if res == 'FAIL':
                self.write_status_list(failed_list_file, sample_filename)
            else:    
                self.write_status_list(finished_list_file, sample_filename)
            #exit(0)


if __name__ == '__main__':
    obj = Lexer()
    #obj.lex_and_compile_samples()
    obj.example_lexer()
    #obj.example_lexer_perline()
