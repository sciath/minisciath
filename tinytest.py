''' TinyTest, a minimal testing framework '''

import sys
import argparse
import yaml
import subprocess
import shlex
import re
import filecmp
import difflib


def run():
    parser = argparse.ArgumentParser(description = 'TinyTest')
    parser.add_argument('input_filename', help = 'Name of input file defining tests', type = str)
    parser.add_argument('-t','--test-subset', help = 'comma-separated (no spaces) list of names of tests to run', type = str, required=False)
    parser.add_argument('-u','--update', help = 'Update expected output of all tests that are run', required = False, action = 'store_true');
    args = parser.parse_args()

    with open(args.input_filename, 'r') as input_file:
        test_data = yaml.safe_load(input_file);

    tests = {}
    if type(test_data) != list:
        raise Exception('Incorrectly formatted input file (must have a sequence at the top level)')
    for entry in test_data:
        if type(entry) != dict:
            raise Exception('Incorrectly formatted test entry (must be a mapping)')
        if 'expected' not in entry or not entry['expected']:
            raise Exception('Each test entry must defined an expected file')
        if 'command' not in entry:
            raise Exception('Each test entry must specify a command')
        if 'name' not in entry:
            raise Exception('Each test entry must specify a name')
        if not re.match(r'^\w+$', entry['name']):
            raise Exception('Illegal test name %s - use only numbers, letters, and underscores' % entry['name'])
        if entry['name'] in tests:
            raise Exception('Duplicate test name %s not allowed' % entry['name'])

        tests[entry['name']] = {'command': entry['command'], 'expected_filename': entry['expected']}

    test_subset = args.test_subset.split(',') if args.test_subset else None
    if test_subset:
        for test_name in test_subset:
            if test_name not in tests:
                raise Exception("Unrecognized test %s selected" % test_name)

    failures = []
    for test_name,test_data in tests.items():
        if test_subset and test_name not in test_subset :
            continue
        print('Running', test_name)
        print('  ', test_data['command'])

        output_filename = test_data['expected_filename'] if args.update else test_name + '.output'
        with open(output_filename, 'w') as output_file:
            subprocess.call(shlex.split(test_data['command']), stdout=output_file, stderr=subprocess.STDOUT)

        if args.update:
            print('Expected output updated.')
        else:
            if filecmp.cmp(output_filename, test_data['expected_filename']):
                print('Success.')
            else:
                print('FAILURE. Output differs from expected:')
                failures.append(test_name)
                with open(test_data['expected_filename'], 'r') as expected_file, open(output_filename, 'r') as output_file:
                    lines_output = output_file.readlines()
                    lines_expected = expected_file.readlines()
                    for line in difflib.unified_diff(lines_expected, lines_output, fromfile=test_data['expected_filename'], tofile=output_filename):
                        print(line, end='')
            print()

    if failures:
        print('FAILURE.')
        print('To re-run with only failed tests')
        print('  ','python', sys.argv[0], args.input_filename, '-t', ','.join(failures));
    else:
        print('Success.')

if __name__ == '__main__':
    run()
