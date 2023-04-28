#!/usr/bin/env python3
"""json_diff(1) - Compute deltas between JSON-serialized objects."""
from __future__ import print_function, unicode_literals
import sys
import argparse
import time
import os
from contextlib import closing

from .. import __VERSION__, load_and_diff, load_and_udiff, ujson


def udiff_headers(left, right):
    """Generate three strings representing the header lines for a u-format diff."""
    time_format = '%Y-%m-%d %H:%m:%S %Z'
    if left is None:
        assert right is sys.stdin
        for line in ('--- <stdin>[0]', '+++ <stdin>[1]'):
            yield line
    else:
        for flo, sigil in ((left, '---'), (right, '+++')):
            if hasattr(flo, 'name'):
                name = flo.name
                try:
                    mtime = os.stat(name).st_mtime
                    dateline = time.strftime(time_format, time.localtime(mtime))
                except OSError:
                    dateline = ''
            else:
                name = '????'
            yield '{} {}\t{}'.format(sigil, name, dateline)


def main():
    """Banana banana banana."""
    parser = argparse.ArgumentParser(
        description=
        '''Produces deltas between JSON-serialized data structures.
        If no arguments are specified, stdin will be expected to be a
        JSON structure [left, right], and the output will be written
        to stdout.
        ''',
    )
    parser.add_argument('left', nargs='?', type=argparse.FileType('r'),
                        help='Starting point for the comparison.')
    parser.add_argument(
        'right', nargs='?', type=argparse.FileType('r'),
        help='Result for the comparison.  Standard input is the default.',
        default=sys.stdin
    )
    parser.add_argument(
        '--output', '-o', type=argparse.FileType('w'), metavar='FILE',
        help='Filename to output the diff to.  Standard output is the default.',
        default=sys.stdout
    )
    parser.add_argument('--verbose', '-v',
                        help='Print compression statistics on stderr',
                        action='store_true')
    parser.add_argument(
        '--unified', '-u',
        help='Outputs a more legible diff, in a format inspired by diff -u',
        action='store_true'
    )
    parser.add_argument(
        '--fast', '-f',
        help='Trade potentially increased diff size for a faster result.',
        action='store_false'
    )
    version = '''%(prog)s - part of json-delta {}
Copyright 2012-2015 Philip J. Roberts <himself@phil-roberts.name>.
BSD License applies; see http://opensource.org/licenses/BSD-2-Clause
'''.format(__VERSION__)
    parser.add_argument(
        '--version', action='version', version=version
    )

    namespace = parser.parse_args()
    if namespace.left is None:
        assert namespace.right is sys.stdin
        left_text = None
        right_text = None
        both_text = sys.stdin.read()
        diff = load_and_diff(both=both_text,
                                        verbose=namespace.verbose,
                                        minimal=namespace.fast)
    else:
        with closing(namespace.left) as left_f, \
                closing(namespace.right) as right_f:
            left_text = left_f.read()
            right_text = right_f.read()
        both_text = None
        diff = load_and_diff(left_text, right_text,
                                        verbose=namespace.verbose,
                                        minimal=namespace.fast)
    with closing(namespace.output) as out_f:
        if namespace.unified:
            for line in udiff_headers(namespace.left, namespace.right):
                print(line, file=out_f)
            for line in load_and_udiff(left_text, right_text,
                                                  both_text, diff):
                print(line, file=out_f)
        else:
            ujson.dump(diff, out_f)
    return 0


if __name__ == '__main__':
    sys.exit(main())
