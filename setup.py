#!/usr/bin/env python

import sys, os

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, 'src'))
sys.path.insert(0, os.path.join(HERE, 'test'))

import json_delta
from setuptools import setup

with open('README') as f:
    LONG_DESC = f.read()

setup(
    name="json_delta",

    version=json_delta.__VERSION__,

    description="A diff/patch pair for JSON-serialized data structures.",
    long_description=LONG_DESC,
    url="http://json-delta.readthedocs.org/",

    author="Phil Roberts",
    author_email="himself@phil-roberts.name",

    license="BSD",

    keywords=['JSON', 'delta', 'diff', 'patch', 'compression'],

    classifiers=[
        'Development Status :: 4 - Beta',
        
        'Intended Audience :: Developers',

        'License :: OSI Approved :: BSD License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    package_dir={'': 'src'},
    packages=['json_delta'],

    scripts=['src/json_cat', 'src/json_diff', 'src/json_patch'],
    
    test_suite="test.build_test_suite",

    zip_safe=True
)
