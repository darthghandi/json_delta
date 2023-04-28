#!/usr/bin/env python3
"""json_cat(1) - Concatenate files together as a JSON array"""
import sys

from .. import ujson


def decode_or_str(flo):
    """If the contents of the file-like object are valid JSON, decode and
    return them, otherwise return them as a string."""
    text = flo.read()
    try:
        return ujson.loads(text)
    except ValueError:
        return text


def main():
    """Banana banana banana."""
    if len(sys.argv) == 1:
        args = ['-']
    else:
        args = sys.argv[1:]

    out = []
    for filename in args:
        if filename == '-':
            out.append(decode_or_str(sys.stdin))
        else:
            with open(filename) as file_obj:
                out.append(decode_or_str(file_obj))
    ujson.dump(out, sys.stdout)


if __name__ == '__main__':
    main()
