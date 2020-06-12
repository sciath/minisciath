from __future__ import print_function

import sys
import os
import argparse
import subprocess
import shlex
import re
import filecmp
import difflib

import yaml


def get_arguments():
    parser = argparse.ArgumentParser(description='TinyTest')
    parser.add_argument('input_filename',
                        type=str,
                        help='Name of input file defining tests')
    parser.add_argument(
        '-t',
        '--test-subset',
        type=str,
        help='comma-separated (no spaces) list of names of tests to run',
        required=False)
    parser.add_argument('-u',
                        '--update',
                        help='Update expected output of all tests that are run',
                        required=False,
                        action='store_true')
    return parser.parse_args()


def get_tests_from_file(input_filename):

    with open(input_filename, 'r') as input_file:
        test_data = yaml.safe_load(input_file)

    tests = {}
    if not isinstance(test_data, list):
        raise Exception(
            'Incorrectly formatted input file (must have a top level sequence)')
    for entry in test_data:
        if not isinstance(entry, dict):
            raise Exception(
                'Incorrectly formatted test entry (must be a mapping)')
        if 'expected' not in entry or not entry['expected']:
            raise Exception('Each test entry must defined an expected file')
        if 'command' not in entry:
            raise Exception('Each test entry must specify a command')
        if 'name' not in entry:
            raise Exception('Each test entry must specify a name')
        if not re.match(r'^\w+$', entry['name']):
            raise Exception(
                'Illegal test name %s - use numbers, letters, and underscores' %
                entry['name'])
        if entry['name'] in tests:
            raise Exception('Duplicate test name %s not allowed' %
                            entry['name'])

        tests[entry['name']] = {
            'command': entry['command'],
            'expected': entry['expected']
        }
    return tests


def run():

    args = get_arguments()

    tests = get_tests_from_file(args.input_filename)

    if args.test_subset:
        active_tests = args.test_subset.split(',')
        for test_name in active_tests:
            if test_name not in tests:
                raise Exception("Unrecognized test %s selected" % test_name)
    else:
        active_tests = tests.keys()

    diff_failed = []
    missing = []
    for test_name in active_tests:
        command = tests[test_name]['command']
        expected = tests[test_name]['expected']

        print('Running', test_name)
        print('  ', command)

        output_filename = expected if args.update else test_name + '.output'
        with open(output_filename, 'w') as output_file:
            subprocess.call(shlex.split(command),
                            stdout=output_file,
                            stderr=subprocess.STDOUT)

        if args.update:
            print('Expected output updated.')
        else:
            if os.path.isfile(expected):
                if filecmp.cmp(output_filename, expected):
                    print('Success.')
                else:
                    print('FAILURE. Output differs from expected:')
                    diff_failed.append(test_name)
                    with open(output_filename, 'r') as output_file:
                        lines_output = output_file.readlines()
                    with open(expected, 'r') as expected_file:
                        lines_expected = expected_file.readlines()
                    for line in difflib.unified_diff(lines_expected,
                                                     lines_output,
                                                     fromfile=expected,
                                                     tofile=output_filename):
                        print(line, end='')
            else:
                print('FAILURE. Missing expected file %s' % expected)
                missing.append(test_name)
                with open(output_filename, 'r') as output_file:
                    lines_output = output_file.readlines()
                    for line in lines_output:
                        print("+" + line, end='')
        print()

    if diff_failed or missing:
        print('FAILURE (%d of %d tests)' %
              (len(diff_failed) + len(missing), len(tests)))
        if missing:
            print('To generate missing expected files from current output')
            print('  ', 'python', sys.argv[0], args.input_filename, '--update',
                  '-t', ','.join(missing))
        if diff_failed:
            print('To re-run with only failed tests')
            print('  ', 'python', sys.argv[0], args.input_filename, '-t',
                  ','.join(diff_failed))
        sys.exit(1)
    else:
        if not args.update:
            print('SUCCESS (%d of %d tests)' % (len(active_tests), len(tests)))
        sys.exit(0)


if __name__ == '__main__':
    run()
