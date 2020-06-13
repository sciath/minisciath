#!/usr/bin/env python
""" MiniSciATH, a minimal testing system """
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


FAILURE_STRING= '\033[41;37mFAILURE\033[0m'

class Test:
    """ A P.O.D. class to hold data for a test """

    def __init__(self, name, command, expected, group=None):
        self.name = name
        self.command = command
        self.expected = expected
        self.group = group


def run():
    """ The main function for MiniSciATH """
    args = _get_arguments()

    tests, active_tests = _get_tests_from_file(args)

    diff_failed = []
    missing = []
    for test in active_tests:
        _execute(args=args, test=test, diff_failed=diff_failed, missing=missing)

    exit_code = _report(args=args,
                        active_tests=active_tests,
                        tests=tests,
                        diff_failed=diff_failed,
                        missing=missing)

    sys.exit(exit_code)


def _get_arguments():
    parser = argparse.ArgumentParser(description='MiniSciATH')
    parser.add_argument('input_filename',
                        type=str,
                        help='Name of input file defining tests')
    parser.add_argument('-t',
                        '--test-subset',
                        type=str,
                        help='comma-separated names of tests to run',
                        required=False)
    parser.add_argument('-u',
                        '--update',
                        help='Update expected output of all tests that are run',
                        required=False,
                        action='store_true')
    parser.add_argument('--only-group',
                        type=str,
                        help='Exclude tests outside of a given group',
                        required=False)
    parser.add_argument('--exclude-group',
                        type=str,
                        help='Exclude tests from a given group',
                        required=False)
    return parser.parse_args()


def _execute(args, test, diff_failed, missing):
    _print_info('Running', test.name)
    print('  ', test.command)

    output_filename = test.expected if args.update else test.name + '.output'
    with open(output_filename, 'w') as output_file:
        subprocess.call(shlex.split(test.command),
                        stdout=output_file,
                        stderr=subprocess.STDOUT)

    if args.update:
        _print_info('Expected output updated.')
    else:
        if os.path.isfile(test.expected):
            success = _verify(output_filename, test.expected)
            if not success:
                diff_failed.append(test.name)
        else:
            _print_info('%s Expected file %s missing' % (FAILURE_STRING, test.expected))
            missing.append(test.name)
    print()


def _get_tests_from_file(args):
    with open(args.input_filename, 'r') as input_file:
        test_data = yaml.safe_load(input_file)

    tests = []
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

        test = Test(
            name=entry['name'],
            command=entry['command'],
            expected=entry['expected'],
        )

        if 'group' in entry:
            if not entry['group']:
                raise Exception('Empty group name for test %s not allowed' %
                                test.name)
            test.group = entry['group']

        tests.append(test)

    if args.test_subset:
        name_to_test = {}
        for test in tests:
            name_to_test[test.name] = test
        active_test_names = args.test_subset.split(',')
        active_tests = []
        for test_name in active_test_names:
            if name_to_test[test.name] not in tests:
                raise Exception("Unrecognized test %s selected" % test_name)
            active_tests.append(name_to_test[test_name])
    else:
        active_tests = tests

    if args.exclude_group:
        group = args.exclude_group
        active_tests = [test for test in active_tests if test.group != group]
    if args.only_group:
        group = args.only_group
        active_tests = [test for test in active_tests if test.group == group]

    return tests, active_tests


def _print_info(*args, **kwargs):
    print('\033[104;37m[MiniSciATH]\033[0m', *args, **kwargs)


def _report(args, active_tests, tests, diff_failed, missing):
    group_info = ''
    if args.only_group:
        group_info += '(only group %s)' % args.only_group
    if args.exclude_group:
        group_info += '(excluding group %s)' % args.exclude_group
    if diff_failed or missing:
        _print_info('%s %s (%d of %d total tests)' %
              (FAILURE_STRING, group_info, len(diff_failed) + len(missing), len(tests)))
        if missing:
            _print_info('To generate missing expected files from current output')
            print('  ', sys.argv[0], args.input_filename, '-t', ','.join(missing),
                  '--update')
        if diff_failed:
            _print_info('To re-run with only failed tests')
            print('  ', sys.argv[0], args.input_filename, '-t', ','.join(diff_failed))
        exit_code = 1
    else:
        if not args.update:
            _print_info('SUCCESS %s (%d of %d total tests)' %
                  (group_info, len(active_tests), len(tests)))
        exit_code = 0
    return exit_code


def _verify(output_filename, expected):
    if filecmp.cmp(output_filename, expected):
        _print_info('Success.')
        return True
    with open(output_filename, 'r') as output_file:
        lines_output = output_file.readlines()
    with open(expected, 'r') as expected_file:
        lines_expected = expected_file.readlines()
    _print_info('%s. Output differs from expected:' % FAILURE_STRING)
    for line in difflib.unified_diff(lines_expected,
                                     lines_output,
                                     fromfile=expected,
                                     tofile=output_filename):
        print(line, end='')
    return False


if __name__ == '__main__':
    run()
