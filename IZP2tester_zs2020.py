from argparse import ArgumentParser
from typing import *

import subprocess
import shutil
import json
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

def _run_test(executable, args, filename, memcheck=False, maxstack=False):
    tmp_file_name = filename + '.tmp'
    arguments = ((['valgrind', '--log-fd=1', '-q', '--leak-check=full'] if memcheck else []) +
                 (['--max-stackframe=4040064'] if memcheck and maxstack else []) +
                 [f'./{executable}'] + args + [tmp_file_name])

    shutil.copyfile(filename, tmp_file_name)

    ret_type = None
    ret_msg = None
    try:
        p = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(timeout=3)

        if p.returncode:
            raise subprocess.CalledProcessError(p.returncode - 256, ' '.join(arguments))
        if out:
            ret_type = TestResult.MEM_ERROR
            ret_msg = out.decode()
        else:
            ret_type = TestResult.OK

    except subprocess.TimeoutExpired:
        ret_type = TestResult.TIMEOUT
    except subprocess.CalledProcessError as err:
        ret_type = TestResult.SEGFAULT if err.returncode == -11 else TestResult.ERROR

    try:
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

class TestCase:

    def __init__(self, name: str, exe_path: str, args: List[str], file_input: str, memcheck:bool=False, maxstack:bool=False):
        self.name = name
        self.exe_path = exe_path
        self.args = args
        self.file_input = file_input

        self.memcheck = memcheck
        self.maxstack = maxstack

    def run_test(self):

        # run the reference and user's test
        ref_res = _run_test('sps-reference', self.args, self.file_input, False, False)
        test_res = _run_test(self.exe_path, self.args, self.file_input, self.memcheck, self.maxstack)

        printable_args = ' '.join("'" + x + "'" if x != '-d' else x for x in self.args)
        same_msgs = ref_res.msg == test_res.msg
        passed = ref_res.type == test_res.type and same_msgs and not ref_res.memcheck_msg

        status_part = f'[ {f"{cLGREEN}ok" if passed else f"{cLRED}er"}{cRESET} ] test: {self.name}'
        first_log_part = f'{cYELLOW}expected{" = received" if same_msgs else ""}{cRESET}:\n{ref_res.msg}{cbYELLOW}EOF{cRESET}\n'
        second_log_part = f'\n{cYELLOW}received{cRESET}:\n{test_res.msg}{cbYELLOW}EOF{cRESET}\n' if not same_msgs else ''
        valgrind_log = "" if test_res.type != TestResult.MEM_ERROR else (f"\n{cYELLOW}valgrind:{cRESET}\n" + test_res.memcheck_msg)

        return passed, (f'{cBLUE}----------------------{cRESET}\n'
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

    try:
        passed_count = 0
        for i, test_case in enumerate(test_cases, 1):

            success, data = test_case.run_test()
            if success:
                passed_count += 1
            if not success or parsed.v:
                print(data)

            if i % 20 == 0 or (i % 5 == 0 and parsed.mc):
                print(f'Ran test {i} of {len(test_cases)}')

        print(f"Passed {passed_count} tests out of {i}. " + (f'{cLGREEN}That\'s 100%!!{cRESET}' if passed_count == len(test_cases) else f'{cLRED}rip{cRESET}'))

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
