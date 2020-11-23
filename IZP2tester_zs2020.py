import subprocess
from typing import *
import tempfile
import sys


class TestCase:
    args: List[str]
    process_input: str
    expected_output: str
    actual_output: str
    name: str

    def __init__(self, args: List[str], process_input: str, name: str, expected_output: str):
        self.args = args
        self.process_input = process_input
        self.name = name
        self.expected_output = expected_output

    def run_test(self):
        with tempfile.NamedTemporaryFile() as test_input_file, open(self.process_input, 'rb') as source_input_file:
            test_input_file.write(source_input_file.read())
            test_input_file.flush()
            try:
                subprocess.run(["./sps"] + self.args + [test_input_file.name], timeout=1000, check=True)
                test_input_file.seek(0)
                self.actual_output = test_input_file.read().decode("utf-8")
            except TimeoutError:
                self.actual_output = "TIMED OUT"
            except subprocess.CalledProcessError:
                self.actual_output = "ERROR"

    def is_passed(self):
        if self.expected_output != 'ERROR':
            with open(self.expected_output, 'r') as resultFile:
                exp_out = resultFile.read()
        else:
            exp_out = 'ERROR'
        return exp_out == self.actual_output

    def get_log(self) -> str:
        printable_args = '"' + ('" "'.join(self.args)) + '"'
        if self.expected_output != 'ERROR':
            with open(self.expected_output, 'r') as resultFile:
                exp_out = resultFile.read()
        else:
            exp_out = 'ERROR'
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
                f'{self.actual_output}END_OF_OUTPUT\n')

def main():
    test_cases: List[TestCase] = []
    with open('tests', 'r') as testsFile:
        testLines = [s.strip() for s in testsFile.readlines()]
        for i in range(int(len(testLines) / 7)):
            if testLines[7*i] != "":
                args = [testLines[7 * i], testLines[7 * i + 1], testLines[7 * i + 2]]
            else:
                args = [testLines[7 * i + 2]]
            test_cases.append(TestCase(args, testLines[7 * i + 3], testLines[7 * i + 4], testLines[7 * i + 5]))

    for test_case in test_cases:
        test_case.run_test()
        if not test_case.is_passed() or '-v' in sys.argv:
            print(test_case.get_log())

if __name__ == '__main__':
    main()
