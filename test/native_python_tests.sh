#!/bin/sh

for PYTHON_BIN in $("${PYTHON27=python}" test_jig.py --python-binaries)
do
    echo "Testing Python implementation using binary $PYTHON_BIN"
    "$PYTHON_BIN" ../python/test/test.py -v
done
