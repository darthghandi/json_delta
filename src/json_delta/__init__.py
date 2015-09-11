# -*- encoding: utf-8 -*-
# json_delta: a library for computing deltas between JSON-serializable
# structures.
# json_delta/__init__.py
#
# Copyright 2012‒2015 Philip J. Roberts <himself@phil-roberts.name>.
# BSD License applies; see the LICENSE file, or
# http://opensource.org/licenses/BSD-2-Clause
'''
This is the main “library” for json_delta’s functionality.  Functions
available within the namespace of this module are to be considered
part of json_delta’s stable API, subject to change only after a lot
of noisy announcements and gnashing of teeth.

The names of submodules begin with underscores because the same is not
true of them: the functionality behind the main entry points diff,
patch, udiff, upatch may be refactored at any time.

Requires Python 2.7 or newer (including Python 3).
'''
from __future__ import unicode_literals
import sys
import json

__VERSION__ = '1.1.3'

from ._diff   import diff
from ._patch  import patch
from ._udiff  import udiff
from ._upatch import upatch

from ._util import _load_and_func

def load_and_diff(left=None, right=None, both=None,
                  minimal=True, verbose=True):
    '''Apply :py:func:`diff` to strings or files representing
    JSON-serialized structures.

    Specify either ``left`` and ``right``, or ``both``, like so:

    >>> (load_and_diff('{"foo":"bar"}', '{"foo":"baz"}', verbose=False)
    ...  == [[["foo"],"baz"]])
    True
    >>> (load_and_diff(both='[{"foo":"bar"},{"foo":"baz"}]', verbose=False)
    ...  == [[["foo"],"baz"]])
    True

    ``left``, ``right`` and ``both`` may be either strings (instances
    of `basestring` in 2.7) or file-like objects.

    ``minimal`` and ``verbose`` are passed through to :py:func:`diff`,
    which see.

    A call to this function with string arguments is strictly
    equivalent to calling ``diff(json.loads(left), json.loads(right),
    minimal=minimal, verbose=verbose)`` or ``diff(*json.loads(both),
    minimal=minimal, verbose=verbose)``, as appropriate.
    '''
    return _load_and_func(diff, left, right, both,
                          minimal=minimal, verbose=verbose)

def load_and_patch(struc=None, stanzas=None, both=None, in_place=True):
    '''Apply :py:func:`patch` to strings or files representing
    JSON-serialized structures.

    Specify either ``struc`` and ``stanzas``, or ``both``, like so:

    >>> (load_and_patch('{"foo":"bar"}', '[[["foo"],"baz"]]') ==
    ...  {"foo": "baz"})
    True
    >>> (load_and_patch(both='[{"foo":"bar"},[[["foo"],"baz"]]]') ==
    ...  {"foo": "baz"})
    True

    ``struc``, ``stanzas`` and ``both`` may be either strings (instances
    of `basestring` in 2.7) or file-like objects.

    ``in_place`` is passed through to :py:func:`patch`, which see.

    A call to this function with string arguments is strictly
    equivalent to calling ``patch(json.loads(struc), json.loads(stanzas),
    in_place=in_place)`` or ``patch(*json.loads(both),
    in_place=in_place)``, as appropriate.
    '''
    return _load_and_func(patch, struc, stanzas, both, in_place=in_place)

def load_and_udiff(left=None, right=None, both=None,
                   stanzas=None, indent=0):
    '''Apply :py:func:`udiff` to strings representing JSON-serialized
    structures.

    Specify either ``left`` and ``right``, or ``both``, like so:

    >>> udiff = """ {
    ...  "foo":
    ... -  "bar"
    ... +  "baz"
    ...  }"""
    >>> test = load_and_udiff('{"foo":"bar"}', '{"foo":"baz"}')
    >>> '\\n'.join(test) == udiff
    True
    >>> test = load_and_udiff(both='[{"foo":"bar"},{"foo":"baz"}]')
    >>> '\\n'.join(test) == udiff
    True

    ``left``, ``right`` and ``both`` may be either strings (instances
    of `basestring` in 2.7) or file-like objects.

    ``stanzas`` and ``indent`` are passed through to :py:func:`udiff`,
    which see.

    A call to this function with string arguments is strictly
    equivalent to calling ``udiff(json.loads(left), json.loads(right),
    stanzas=stanzas, indent=indent)`` or ``udiff(*json.loads(both),
    stanzas=stanzas, indent=indent)``, as appropriate.
    '''
    return _load_and_func(udiff, left, right, both,
                          patch=stanzas, indent=indent)

def load_and_upatch(struc=None, json_udiff=None, both=None,
                    reverse=False, in_place=True):
    """Apply :py:func:`upatch` to strings representing JSON-serialized
    structures.

    Specify either ``struc`` and ``json_udiff``, or ``both``, like so:

    >>> struc = '{"foo":"bar"}'
    >>> json_udiff = r'" {\\n  \\"foo\\":\\n-  \\"bar\\"\\n+  \\"baz\\"\\n }"'
    >>> both = r'[{"foo":"baz"}," '\\
    ... r'{\\n  \\"foo\\":\\n-  \\"bar\\"\\n+  \\"baz\\"\\n }"]'
    >>> load_and_upatch(struc, json_udiff) == {"foo": "baz"}
    True
    >>> load_and_upatch(both=both, reverse=True) == {"foo": "bar"}
    True

    ``struc``, ``json_udiff`` and ``both`` may be either strings
    (instances of `basestring` in 2.7) or file-like objects.  Note
    that ``json_udiff`` is so named because it must be a
    JSON-serialized representation of the udiff string, not the udiff
    string itself.

    ``reverse`` is passed through to :py:func:`upatch`, which see.

    A call to this function with string arguments is strictly
    equivalent to calling ``upatch(json.loads(struc),
    json.loads(json_udiff), reverse=reverse, in_place=in_place)`` or
    ``upatch(*json.loads(both), reverse=reverse, in_place=in_place)``,
    as appropriate.

    """
    return _load_and_func(upatch, struc, json_udiff, both, reverse=reverse)
