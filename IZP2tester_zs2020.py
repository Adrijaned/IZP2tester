import subprocess
from typing import *
import tempfile
import sys
import json


class TestCase:
    args: List[str]
    process_input: str
    expected_output: str
    actual_output: str
    name: str
    valgrind_out: str = ""

    def __init__(self, args: List[str], process_input: str, name: str, expected_output: str, valgrind:bool=False):
        self.args = args
        self.process_input = process_input
        self.name = name
        self.expected_output = expected_output
        self.valgrind = valgrind

    def run_test(self):
        with tempfile.NamedTemporaryFile() as test_input_file, open(self.process_input, 'rb') as source_input_file:
            test_input_file.write(source_input_file.read())
            test_input_file.flush()
            try:
                program_with_args = ["./sps"] + self.args + [test_input_file.name]
                subprocess.run(program_with_args, timeout=1, check=True)
                test_input_file.seek(0)
                self.actual_output = test_input_file.read().decode("utf-8")
            except UnicodeDecodeError:
                self.actual_output = "BINARY_TRASH\n\n"
            except TimeoutError:
                self.actual_output = "TIMED OUT\n\n"
            except subprocess.CalledProcessError as err:
                # -11 represents SEGFAULT: https://code-examples.net/en/q/11dd30f
                if err.returncode == -11:
                    self.actual_output = "SEGFAULT\n\n"
                else:
                    self.actual_output = "ERROR\n\n"
            if self.valgrind:
                test_input_file.seek(0)
                source_input_file.seek(0)
                test_input_file.truncate()
                test_input_file.write(source_input_file.read())
                test_input_file.flush()
                try:
                    self.valgrind_out = subprocess.run(['valgrind', '-q', '--leak-check=full'] + program_with_args, capture_output=True).stderr.decode('utf-8')
                except:
                    print("ahaha")

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
            exp_out = 'ERROR'
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
    test_cases: List[TestCase] = []
    with open('tests.json', 'r') as testsFile:
        tests_dict = json.loads(testsFile.read())
    for test in tests_dict:
        args = [test['cmds']]
        if test.get('delim'):
            args = ['-d', test['delim']] + args
        test_cases += [TestCase(args, test['input'], test['name'], test['output'], '-mc' in sys.argv)]

    passedCount, wholeCount = 0, 0
    for test_case in test_cases:
        wholeCount += 1
        if wholeCount % 20 == 0 or (wholeCount % 5 == 0 and '-mc' in sys.argv):
            print(f'Running test {wholeCount} of {len(test_cases)}')
        test_case.run_test()
        isPassed = test_case.is_passed()
        if isPassed:
            passedCount += 1
        if not isPassed or '-v' in sys.argv:
            print(test_case.get_log())
    print(f"Passed {passedCount} tests out of {wholeCount}.")

if __name__ == '__main__':
    main()
