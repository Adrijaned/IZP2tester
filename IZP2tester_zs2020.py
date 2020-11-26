import subprocess
from typing import *
import tempfile
import sys
import json
import os

from argparse import ArgumentParser


class TestCase:
    args: List[str]
    process_input: str
    expected_output: str
    actual_output: str
    name: str
    valgrind_out: str = ""

    def __init__(self, args: List[str], process_input: str, name: str, expected_output: str, valgrind:bool=False, valgrind_stack:bool=False):
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
                program_with_args = ["./sps"] + self.args + [test_input_file.name]
                subprocess.run(program_with_args, timeout=1, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                test_input_file.seek(0)
                self.actual_output = test_input_file.read().decode("utf-8")

            except UnicodeDecodeError:
                self.actual_output = "BINARY_TRASH\n\n"
            except TimeoutError:
                self.actual_output = "TIMED OUT\n\n"
            except subprocess.CalledProcessError as err:
                # -11 represents SEGFAULT: https://code-examples.net/en/q/11dd30f
                self.actual_output = ('SEGFAULT' if err.returncode == -11 else 'ERROR') + '\n\n'


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
                self.valgrind_out = out.decode() if not err else '<valgrind check failed>'

    def is_passed(self):
        if self.expected_output != 'ERROR':
            with open(self.expected_output, 'r') as resultFile:
                exp_out = resultFile.read()
        else:
            exp_out = 'ERROR\n\n'
        return exp_out == self.actual_output and self.valgrind_out == ''

    def get_log(self) -> str:
        printable_args = '"' + ('" "'.join(self.args)) + '"'
        if self.expected_output != 'ERROR':
            with open(self.expected_output, 'r') as resultFile:
                exp_out = resultFile.read()
        else:
            exp_out = 'ERROR\n\n'
        valgrind_log = "" if self.valgrind_out == "" else ("\nVALGRIND OUTPUT\n" + self.valgrind_out)
        return (f"----------------------\n"
                f"Test case: {self.name}\n"
                f"\n"
                f"{'PASSED' if self.is_passed() else 'FAILED'}\n\n"
                f"INPUT FILE:\n"
                f"{self.process_input}\n"
                f"\n"
                f"ARGUMENTS:\n"
                f'{printable_args}\n'
                f'\n'
                f'EXPECTED OUTPUT:\n'
                f'{exp_out}END_OF_OUTPUT\n'
                f'\n'
                f'ACTUAL OUTPUT\n'
                f'{self.actual_output}END_OF_OUTPUT\n'
                f'{valgrind_log}')

def main():

    parser = ArgumentParser()
    parser.add_argument('-mc', '--mem-check', dest='mc', action='store_true', help='run a memory check with valgrind')
    parser.add_argument('-ms', '--max-stack', dest='ms', action='store_true', help='use larger stack size for valgrind')
    parser.add_argument('-v', '--verbose',    dest='v',  action='store_true', help='increase verbosity')

    parsed = parser.parse_args()

    test_cases: List[TestCase] = []
    with open('tests.json', 'r') as testsFile:
        tests_dict = json.loads(testsFile.read())
    for test in tests_dict:
        args = [test['cmds']]
        if test.get('delim'):
            args = ['-d', test['delim']] + args
        test_cases += [TestCase(args, test['input'], test['name'], test['output'], parsed.mc, parsed.ms)]

    passedCount = 0
    for i, test_case in enumerate(test_cases):
        i += 1
        if i % 20 == 0 or (i % 5 == 0 and parsed.mc):
            print(f'Running test {i} of {len(test_cases)}')
        test_case.run_test()
        isPassed = test_case.is_passed()
        if isPassed:
            passedCount += 1
        if not isPassed or parsed.v:
            print(test_case.get_log())
    print(f"Passed {passedCount} tests out of {i}.")

if __name__ == '__main__':
    main()
