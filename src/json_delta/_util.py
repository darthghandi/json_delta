# -*- encoding: utf-8 -*-
# json_delta: a library for computing deltas between JSON-serializable
# structures.
# json_delta/_util.py
#
# Copyright 2012‒2015 Philip J. Roberts <himself@phil-roberts.name>.
# BSD License applies; see the LICENSE file, or
# http://opensource.org/licenses/BSD-2-Clause
'''
Utility functions and constants used by all submodules.
'''
from __future__ import print_function, unicode_literals

import ujson

try:
    Basestring = basestring
except NameError:
    Basestring = str

TERMINALS = (str, int, float, bool, type(None))
try:
    TERMINALS += (unicode, long)
except NameError:
    pass
NONTERMINALS = (list, dict)
SERIALIZABLE_TYPES = TERMINALS + NONTERMINALS

# ----------------------------------------------------------------------
# Utility functions

def uniquify(obj, key=lambda x: x):
    '''Remove duplicate elements from a list while preserving order.'''
    seen = set()
    seen_add = seen.add
    return [
        x for x in obj if (key(x) not in seen and not seen_add(key(x)))
    ]

def decode_json(file_or_str):
    '''Decode a JSON file-like object or string.

    The following doctest is probably pointless as documentation.  It is
    here so json_delta can claim 100% code coverage for its test suite!

    >>> try:
    ...     from StringIO import StringIO
    ... except ImportError:
    ...     from io import StringIO
    >>> foo = '[]'
    >>> decode_json(foo)
    []
    >>> decode_json(StringIO(foo))
    []
    '''
    if isinstance(file_or_str, Basestring):
        return ujson.loads(file_or_str)
    else:
        return ujson.load(file_or_str)

def _load_and_func(func, parm1=None, parm2=None, both=None, **flags):
    '''Decode JSON-serialized parameters and apply func to them.'''
    if (parm1 is not None) and (parm2 is not None):
        return func(decode_json(parm1), decode_json(parm2), **flags)
    else:
        assert (both is not None), (parm1, parm2, both)
        [parm1, parm2] = decode_json(both)
        return func(parm1, parm2, **flags)

def in_one_level(diff, key):
    '''Return the subset of ``diff`` whose key-paths begin with
    ``key``, expressed relative to the structure at ``[key]``
    (i.e. with the first element of each key-path stripped off).

    >>> diff = [ [['bar'], None],
    ...          [['baz', 3], 'cheese'],
    ...          [['baz', 4, 'quux'], 'foo'] ]
    >>> in_one_level(diff, 'baz') == [[[3], 'cheese'], [[4, 'quux'], 'foo']]
    True
    '''
    oper_stanzas = [stanza[:] for stanza in diff if stanza[0][0] == key]
    for stanza in oper_stanzas:
        stanza[0] = stanza[0][1:]
    return oper_stanzas

def compact_json_dumps(obj):
    '''Compute the most compact possible JSON representation of the
    serializable object ``obj``.

    >>> test = {
    ...             'foo': 'bar',
    ...             'baz':
    ...                ['quux', 'spam',
    ...       'eggs']
    ... }
    >>> compact_json_dumps(test) in (
    ...     '{"foo":"bar","baz":["quux","spam","eggs"]}',
    ...     '{"baz":["quux","spam","eggs"],"foo":"bar"}'
    ... )
    True
    >>>
    '''
    return ujson.dumps(obj, ensure_ascii=False)

def all_paths(struc):
    '''Generate key-paths to every node in ``struc``.

    Both terminal and non-terminal nodes are visited, like so:

    >>> paths = [x for x in all_paths({'foo': None, 'bar': ['baz', 'quux']})]
    >>> [] in paths # ([] is the path to struc itself.)
    True
    >>> ['foo'] in paths
    True
    >>> ['bar'] in paths
    True
    >>> ['bar', 0] in paths
    True
    >>> ['bar', 1] in paths
    True
    >>> len(paths)
    5
    '''
    yield []
    if isinstance(struc, dict):
        keys = struc.keys()
    elif isinstance(struc, list):
        keys = range(len(struc))
    else:
        return
    for key in keys:
        for subkey in all_paths(struc[key]):
            yield [key] + subkey

def follow_path(struc, path):
    '''Return the value found at the key-path ``path`` within ``struc``.'''
    if not path:
        return struc
    else:
        return follow_path(struc[path[0]], path[1:])

def check_diff_structure(diff):
    '''Return ``diff`` (or ``True``) if it is structured as a sequence
    of ``diff`` stanzas.  Otherwise return ``False``.

    ``[]`` is a valid diff, so if it is passed to this function, the
    return value is ``True``, so that the return value is always true
    in a Boolean context if ``diff`` is valid.

    >>> check_diff_structure('This is certainly not a diff!')
    False
    >>> check_diff_structure([])
    True
    >>> check_diff_structure([None])
    False
    >>> example_valid_diff = [[["foo", 6, 12815316313, "bar"], None]]
    >>> check_diff_structure(example_valid_diff) == example_valid_diff
    True
    >>> check_diff_structure([[["foo", 6, 12815316313, "bar"], None],
    ...                       [["foo", False], True]])
    False
    '''
    if diff == []:
        return True
    if not isinstance(diff, list):
        return False
    for stanza in diff:
        conditions = (lambda s: isinstance(s, list),
                      lambda s: isinstance(s[0], list),
                      lambda s: len(s) in (1, 2))
        for condition in conditions:
            if not condition(stanza):
                return False
        for key in stanza[0]:
            if not (type(key) is int or isinstance(key, Basestring)):
                # So, it turns out isinstance(False, int)
                # evaluates to True!
                return False
    return diff

def in_object(key):
    '''Should the keypath `key` point at a JSON object (`{}`)?'''
    return (key and (key[-1] is None
            or isinstance(key[-1], Basestring)))

def in_array(key):
    '''Should the keypath `key` point at a JSON array (`[]`)?'''
    return (key and isinstance(key[-1], int))

def nearest_of(string, *subs):
    '''Find the index of the substring in ``subs`` that occurs earliest in
    ``string``, or ``len(string)`` if none of them do.'''
    return min((string.find(x) if x in string else len(string) for x in subs))
        
def skip_string(jstring, point):
    '''Assuming ``jstring`` is a string, and ``jstring[point]`` is a ``"`` that
    starts a JSON string, return ``x`` such that ``jstring[x-1]`` is
    the ``"`` that terminates the string.
    '''
    assert jstring[point] == '"'
    point += 1
    while jstring[point] != '"' and jstring[point-1] != '\\':
        point += 1
    return point + 1

def key_tracker(jstring, point=0, start_key=None, special_handler=None):
    '''Generate points within ``jstring`` where the keypath changes.

    This function also identifies points within objects where a new
    ``key: value`` pair is expected, by yielding a pseudo-keypath with
    ``None`` as the final element.

    Parameters:
        * ``jstring``: The JSON string to search.
        
        * ``point``: The point to start at.
        
        * ``start_key``: The starting keypath.
        
        * ``special_handler``: A function for handling extensions to
          JSON syntax (e.g. :py:func:`_upatch.ellipsis_handler`, used
          to handle the ``...`` construction in udiffs).

    >>> next(key_tracker('{}'))
    (1, (None,))
    '''
    if start_key is None:
        key = []
    else:
        key = list(start_key)

    while point < len(jstring):
        if jstring[point] == '{':
            key.append(None)
            yield (point + 1, tuple(key))
        elif jstring[point] == '[':
            key.append(0)
            yield (point + 1, tuple(key))
        elif jstring[point] in ']}':
            key.pop()
            yield (point + 1, tuple(key))
        elif jstring[point] == ',':
            if in_object(key):
                key[-1] = None
            else:
                assert in_array(key)
                key[-1] += 1
            yield (point + 1, tuple(key))
        elif jstring[point] == '"':
            string_end = skip_string(jstring, point)
            if (key and key[-1] is None):
                key[-1] = ujson.loads(jstring[point:string_end])
                while (string_end < len(jstring)
                       and jstring[string_end] in ' \r\n\t:'):
                    string_end += 1
                yield (string_end, tuple(key))
            point = string_end - 1
        elif special_handler is not None:
            point, newkey = special_handler(jstring, point, key)
            if key != newkey:
                key = newkey
                yield (point, tuple(key))
        point += 1
