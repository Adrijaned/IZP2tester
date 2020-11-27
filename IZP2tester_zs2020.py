from typing import *
import subprocess
import tempfile
import json
import os

from argparse import ArgumentParser

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


class TestCase:
    args: List[str]
    process_input: str
    expected_output: str
    actual_output: str
    name: str
    valgrind_out: str = ""

    def __init__(self, exe_path: str, args: List[str], process_input: str, name: str, expected_output: str, valgrind:bool=False, valgrind_stack:bool=False):
        self.exe_path = exe_path
        self.args = args
        self.process_input = process_input
        self.name = name
        self.expected_output = expected_output
        self.valgrind = valgrind
        self.valgrind_stack = valgrind_stack

    def run_test(self):
        with tempfile.NamedTemporaryFile() as test_input_file, open(self.process_input, 'rb') as source_input_file:
            test_input_file.write(source_input_file.read())
            test_input_file.flush()
            try:
                program_with_args = [f"./{self.exe_path}"] + self.args + [test_input_file.name]
                subprocess.run(program_with_args, timeout=1, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                test_input_file.seek(0)
                self.actual_output = test_input_file.read().decode("utf-8")

            except UnicodeDecodeError:
                self.actual_output = f"BINARY_TRASH\n\n"
            except TimeoutError:
                self.actual_output = f"TIMED OUT\n\n"
            except subprocess.CalledProcessError as err:
                # -11 represents SEGFAULT: https://code-examples.net/en/q/11dd30f
                self.actual_output = (f'SEGFAULT' if err.returncode == -11 else f'ERROR') + '\n'


            if self.valgrind:
                test_input_file.seek(0)
                source_input_file.seek(0)
                test_input_file.truncate()
                test_input_file.write(source_input_file.read())
                test_input_file.flush()


                cmd_line = ['valgrind', '--log-fd=1', '-q', '--leak-check=full'] + \
                    (['--max-stackframe=4040064'] if self.valgrind_stack else []) + \
                    program_with_args

                p = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = p.communicate()
                self.valgrind_out = out.decode()

    def is_passed(self):
        if self.expected_output != 'ERROR':
            with open(self.expected_output, 'r') as resultFile:
                exp_out = resultFile.read()
        else:
            exp_out = 'ERROR\n'
        return exp_out == self.actual_output and self.valgrind_out == ''

    def get_log(self) -> str:
        wrapped_args = ['"' + x + '"' for x in self.args[:-1]] + ["'" + self.args[-1] + "'"]
        printable_args = ' '.join(wrapped_args)

        if self.expected_output != 'ERROR':
            with open(self.expected_output, 'r') as resultFile:
                exp_out = resultFile.read()
        else:
            exp_out = 'ERROR\n'

        passed = self.is_passed()

        status_part = f'[ {f"{cLGREEN}ok" if self.is_passed() else f"{cLRED}er"}{cRESET} ] test: {self.name}'
        first_log_part = f'{cYELLOW}expected{" = received" if passed else ""}{cRESET}:\n{exp_out}{cbYELLOW}EOF{cRESET}\n'
        second_log_part = f'\n{cYELLOW}received{cRESET}:\n{self.actual_output}{cbYELLOW}EOF{cRESET}\n' if not passed else ''
        valgrind_log = "" if self.valgrind_out == "" else (f"\n{cYELLOW}valgrind:{cRESET}\n" + self.valgrind_out)

        return (f'{cBLUE}----------------------{cRESET}\n'
                f'{status_part}\n\n'
                f'input: {self.process_input}\n'
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

        test_cases += [TestCase(parsed.path, args, test['input'], test['name'], test['output'], parsed.mc, parsed.ms)]

    try:
        passed_count = 0
        for i, test_case in enumerate(test_cases, 1):

            if i % 20 == 0 or (i % 5 == 0 and parsed.mc):
                print(f'Running test {i} of {len(test_cases)}')

            test_case.run_test()
            is_passed = test_case.is_passed()
            if is_passed:
                passed_count += 1
            if not is_passed or parsed.v:
                print(test_case.get_log())

        print(f"Passed {passed_count} tests out of {i}. " + (f'{cLGREEN}That\'s 100%!!{cRESET}' if passed_count == len(test_cases) else f'{cLRED}rip{cRESET}'))

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
