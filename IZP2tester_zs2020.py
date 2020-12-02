from multiprocessing.pool import ThreadPool
from threading import Thread, Lock
from argparse import ArgumentParser
from typing import *

import subprocess
import shutil
import string
import random
import json
import time
import os


cLGREEN = '\033[1;92m'
cbLRED = '\033[1;91m'
cLRED = '\033[91m'
cRESET = '\033[0m'
cbYELLOW = '\033[1;93m'
cYELLOW = '\033[93m'
cINVERT = '\033[7m'
cBLUE = '\033[1;34m'
cbMAGENTA = '\033[1;105m'
cbLGRAY = '\033[1;37m'
cbCYAN = '\033[1;46m'

class TestResult:
    SEGFAULT = "segfault"
    ERROR = "error"
    BINARY = "binary"
    TIMEOUT = "timeout"
    OK = "ok"
    MEM_ERROR = "memerror"

    def __init__(self, type, msg='', memcheck_msg=''):
        self.type = type
        self.msg = msg
        self.memcheck_msg = memcheck_msg

def get_tmp_filename(length=8):
    alphabet = string.digits + string.ascii_letters
    return ''.join(random.choice(alphabet) for i in range(length)) + '.tmp'


def _run_test(executable, args, filename, memcheck=False, maxstack=False):
    tmp_file_name = get_tmp_filename()
    tmp_valgrind_out = get_tmp_filename()
    cmd_line = ' '.join([(f'valgrind --log-file={tmp_valgrind_out} -q --leak-check=full' if memcheck else ''),
        ('--max-stackframe=4040064' if memcheck and maxstack else ''),
        f'./{executable}',
        ' '.join(map(lambda x: '"' + x.replace('\\', '\\\\').replace('"', '\\"') + '"', args)),
        tmp_file_name
    ])

    shutil.copyfile(filename, tmp_file_name)

    ret_type = None
    ret_msg = None

    try:
        try:
            p = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = p.communicate(timeout=3)

            try:
                with open(tmp_valgrind_out) as f:
                    valgrind_out = f.read()
            except IOError:
                valgrind_out = ''

            if p.returncode:
                raise subprocess.CalledProcessError(p.returncode - 256, cmd_line)
            if valgrind_out:
                ret_type = TestResult.MEM_ERROR
                ret_msg = valgrind_out
            else:
                ret_type = TestResult.OK

        except subprocess.TimeoutExpired:
            p.terminate()
            ret_type = TestResult.TIMEOUT
        except subprocess.CalledProcessError as err:
            ret_type = TestResult.SEGFAULT if err.returncode == -117 else TestResult.ERROR


        try:
            with open(tmp_file_name) as f:
                contents = f.read()
        except UnicodeDecodeError as e:
            return TestResult(TestResult.BINARY, 'BINARY OUTPUT\n')

        if ret_type == TestResult.MEM_ERROR:
            return TestResult(ret_type, contents, ret_msg)
        elif ret_type in [TestResult.OK, TestResult.BINARY]:
            return TestResult(ret_type, contents)
        else:
            return TestResult(ret_type, str(ret_type).upper() + '\n')
    finally:
        os.unlink(tmp_file_name)
        if memcheck:
            os.unlink(tmp_valgrind_out)

class TestCase:

    def __init__(self, name: str, exe_path: str, args: List[str], file_input: str, memcheck:bool=False, maxstack:bool=False):
        self.name = name
        self.exe_path = exe_path
        self.args = args
        self.file_input = file_input

        self.memcheck = memcheck
        self.maxstack = maxstack

        self.passed = None

    def run_test(self):

        # run the reference and user's test
        ref_res = _run_test('sps-reference', self.args, self.file_input, False, False)
        test_res = _run_test(self.exe_path, self.args, self.file_input, self.memcheck, self.maxstack)

        printable_args = ' '.join("'" + x + "'" if x != '-d' else x for x in self.args)
        same_msgs = ref_res.msg == test_res.msg
        self.passed = ref_res.type == test_res.type and same_msgs and not ref_res.memcheck_msg

        status_part = f'[ {f"{cLGREEN}ok" if self.passed else f"{cLRED}er"}{cRESET} ] test: {self.name}'
        first_log_part = f'{cYELLOW}expected{" = received" if same_msgs else ""}{cRESET}:\n{ref_res.msg}{cbYELLOW}EOF{cRESET}\n'
        second_log_part = f'\n{cYELLOW}received{cRESET}:\n{test_res.msg}{cbYELLOW}EOF{cRESET}\n' if not same_msgs else ''
        valgrind_log = "" if test_res.type != TestResult.MEM_ERROR else (f"\n{cYELLOW}valgrind:{cRESET}\n" + test_res.memcheck_msg)

        return (f'{cBLUE}----------------------{cRESET}\n'
                f'{status_part}\n\n'
                f'input: {self.file_input}\n'
                f'args:  {printable_args}\n\n'
                f'{first_log_part}'
                f'{second_log_part}'
                f'{valgrind_log}')


class _ArgumentParser(ArgumentParser):

    # override automatic short-help-printing on error
    def error(self, message):
        raise SystemExit(message)

    # override printing help twice on -h
    def print_help(self, *args):
        return self.format_help()

def main():

    # init parser
    parser = _ArgumentParser()
    parser.add_argument('path', metavar='sps_executable', help='path to the sps executable')
    parser.add_argument('-mc', '--mem-check', dest='mc', action='store_true', help='run a memory check with valgrind')
    parser.add_argument('-ms', '--max-stack', dest='ms', action='store_true', help='use larger stack size for valgrind')
    parser.add_argument('-v', '--verbose',    dest='v',  action='store_true', help='increase verbosity')

    # parse arguments
    try:
        parsed = parser.parse_args()
    except SystemExit:
        print(parser.format_help())
        exit()

    test_cases: List[TestCase] = []

    # load test cases
    with open('tests.json', 'r') as testsFile:
        tests_dict = json.loads(testsFile.read())

    for test in tests_dict:
        args = [test['cmds']]
        if test.get('delim'):
            args = ['-d', test['delim']] + args

        test_cases += [TestCase(test['name'], parsed.path, args, test['input'], parsed.mc, parsed.ms)]

    print_lock = Lock()

    # run test_case and print result
    def run_and_print_test(test_case):
        global running
        data = test_case.run_test()

        if not test_case.passed or parsed.v:
            with print_lock:
                print(data)

    # run in background and continuously print number of completed tests so far
    def print_elapsed_test_nums():
        last_count = 0
        while True:
            n_completed = len([test for test in test_cases if test.passed != None])
            if n_completed == len(test_cases):
                break

            if last_count + 10 < n_completed:
                last_count += 10
                print(f'completed {last_count} out of {len(test_cases)}')

            time.sleep(.1)

    # print number of completed test cases while they're being mapped
    Thread(target=print_elapsed_test_nums, daemon=True).start()

    try:
        with ThreadPool(4) as p:
            p.map(run_and_print_test, test_cases)

        passed_count = len([test_case for test_case in test_cases if test_case.passed])
        test_count   = len(test_cases)
        print(f"Passed {passed_count} tests out of {test_count}. " + (f'{cLGREEN}That\'s 100%!!{cRESET}' if passed_count == test_count else f'{cLRED}rip{cRESET}'))

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
