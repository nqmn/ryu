#!/usr/bin/env python

import os
import sys
import subprocess

sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(__file__))


if __name__ == '__main__':
    # Use pytest instead of nose
    test_args = ['pytest', 'ryu/tests/unit']

    # Add any additional arguments passed to this script
    if len(sys.argv) > 1:
        test_args.extend(sys.argv[1:])

    # Set verbosity based on environment variable
    verbosity = int(os.environ.get('PYTEST_VERBOSE', 1))
    if verbosity > 1:
        test_args.append('-v')
    if verbosity > 2:
        test_args.append('-vv')

    # Run pytest
    exit_status = subprocess.call(test_args)
    sys.exit(exit_status)
