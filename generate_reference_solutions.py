import subprocess
from typing import *


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
        with open(self.expected_output, 'wb') as test_input_file, open(self.process_input, 'rb') as source_input_file:
            test_input_file.write(source_input_file.read())
            test_input_file.flush()
        subprocess.run(["./sps-reference"] + self.args + [self.expected_output], timeout=1, check=True)


def main():
    test_cases: List[TestCase] = []
    with open('tests', 'r') as testsFile:
        testLines = [s.strip() for s in testsFile.readlines()]
        for i in range(int(len(testLines) / 7)):
            if testLines[7 * i] != "":
                args = [testLines[7 * i], testLines[7 * i + 1], testLines[7 * i + 2]]
            else:
                args = [testLines[7 * i + 2]]
            if testLines[7 * i + 5] != 'ERROR':
                test_cases.append(TestCase(args, testLines[7 * i + 3], testLines[7 * i + 4], testLines[7 * i + 5]))

    for test_case in test_cases:
        test_case.run_test()


if __name__ == '__main__':
    main()
