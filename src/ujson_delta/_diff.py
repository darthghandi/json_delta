# -*- encoding: utf-8 -*-
# ujson_delta: a library for computing deltas between JSON-serializable
# structures.
# ujson_delta/_diff.py
#
# Copyright 2012‒2015 Philip J. Roberts <himself@phil-roberts.name>.
# BSD License applies; see the LICENSE file, or
# http://opensource.org/licenses/BSD-2-Clause
"""Functions for computing JSON-format diffs."""

from __future__ import print_function, unicode_literals
from ._util import compact_json_dumps, TERMINALS, NONTERMINALS, Basestring

import copy
import bisect
import sys

try:
    xrange(0)
except NameError:
    xrange = range


def diff(left_struc, right_struc, minimal=True, verbose=True, key=None):
    """Compose a sequence of diff stanzas sufficient to convert the
    structure ``left_struc`` into the structure ``right_struc``.  (The
    goal is to add 'necessary and' to 'sufficient' above!).

    Flags:
        ``verbose``: if this is set ``True`` (the default), a line of
        compression statistics will be printed to stderr.

        ``minimal``: if ``True``, the function will try harder to find
        the diff that encodes as the shortest possible JSON string, at
        the expense of using more of both memory and processor time
        (as alternatives are computed and compared).

    The parameter ``key`` is present because this function is mutually
    recursive with :py:func:`needle_diff` and :py:func:`keyset_diff`.
    If set to a list, it will be prefixed to every keypath in the
    output.

    """
    if key is None:
        key = []

    if structure_worth_investigating(left_struc, right_struc):
        common = commonality(left_struc, right_struc)
        if minimal:
            my_diff = needle_diff(left_struc, right_struc, key, minimal)
        elif common < 0.5:
            my_diff = this_level_diff(left_struc, right_struc, key, common)
        else:
            my_diff = keyset_diff(left_struc, right_struc, key, minimal)
    else:
        my_diff = this_level_diff(left_struc, right_struc, key, 0.0)

    if minimal:
        my_diff = min(my_diff, [[key[:], copy.copy(right_struc)]],
                      key=lambda x: len(compact_json_dumps(x)))

    if not key:
        if len(my_diff) > 1:
            my_diff = sort_stanzas(my_diff)
        if verbose:
            size = len(compact_json_dumps(right_struc))
            csize = float(len(compact_json_dumps(my_diff)))
            msg = ('Size of delta %.3f%% size of original '
                   '(original: %d chars, delta: %d chars)')
            print(msg % (((csize / size) * 100),
                         size,
                         int(csize)),
                  file=sys.stderr)
    return my_diff


def needle_diff(left_struc, right_struc, key, minimal=True):
    """Returns a diff between ``left_struc`` and ``right_struc``.

    If ``left_struc`` and ``right_struc`` are both serializable as
    arrays, this function will use Needleman-Wunsch sequence alignment
    to find a minimal diff between them.  Otherwise, the inputs are
    passed on to :func:`keyset_diff`.

    This function probably shouldn't be called directly.  Instead, use
    :func:`diff`, which is mutually recursive with this function and
    :func:`keyset_diff` anyway.

    """
    if type(left_struc) not in (list, tuple):
        return keyset_diff(left_struc, right_struc, key, minimal)
    assert type(right_struc) in (list, tuple)

    down_col = 0
    lastrow = [
        [[key + [sub_i]] for sub_i in range(i)]
        for i in range(len(left_struc), -1, -1)
        ]

    def modify_cand():
        """Build the candidate diff that involves (potentially) modifying an
        element."""
        if col_i + 1 < len(lastrow):
            return (lastrow[col_i + 1] +
                    diff(left_elem, right_elem, key=key + [left_i],
                         minimal=minimal, verbose=False))

    def delete_cand():
        """Build the candidate diff that involves deleting an element."""
        if row:
            return row[0] + [[key + [left_i]]]

    def append_cand():
        """Build the candidate diff that involves appending an element."""
        if col_i == down_col:
            return (lastrow[col_i] +
                    [[key + [append_key(lastrow[col_i], left_struc, key)],
                      right_elem]])

    for right_i, right_elem in enumerate(right_struc):
        first_left_i = min(right_i, len(left_struc) - 1)
        left_elems = left_struc[first_left_i:]
        row = []

        for left_i, left_elem in enumerate(left_elems, first_left_i):
            col_i = len(left_struc) - left_i - 1
            cands = [c for c in (modify_cand(), delete_cand(), append_cand())
                     if c is not None]
            winner = min(cands, key=lambda d: len(compact_json_dumps(d)))
            row.insert(0, winner)

        lastrow = row
    return winner


def append_key(stanzas, left_struc, keypath=None):
    """Get the appropriate key for appending to the sequence ``left_struc``.

    ``stanzas`` should be a diff, some of whose stanzas may modify a
    sequence ``left_struc`` that appears at path ``keypath``.  If any of
    the stanzas append to ``left_struc``, the return value is the
    largest index in ``left_struc`` they address, plus one.
    Otherwise, the return value is ``len(left_struc)`` (i.e. the index
    that a value would have if it was appended to ``left_struc``).

    >>> append_key([], [])
    0
    >>> append_key([[[2], 'Baz']], ['Foo', 'Bar'])
    3
    >>> append_key([[[2], 'Baz'], [['Quux', 0], 'Foo']], [], ['Quux'])
    1

    """
    if keypath is None:
        keypath = []
    addition_key = len(left_struc)
    for stanza in stanzas:
        prior_key = stanza[0]
        if (len(stanza) > 1
            and len(prior_key) == len(keypath) + 1
            and prior_key[-1] >= addition_key):
            addition_key = prior_key[-1] + 1
    return addition_key


def compute_keysets(left_seq, right_seq):
    """Compare the keys of ``left_seq`` vs. ``right_seq``.

    Determines which keys ``left_seq`` and ``right_seq`` have in
    common, and which are unique to each of the structures.  Arguments
    should be instances of the same basic type, which must be a
    non-terminal: i.e. list or dict.  If they are lists, the keys
    compared will be integer indices.

    Returns:
        Return value is a 3-tuple of sets ``({overlap}, {left_only},
        {right_only})``.  As their names suggest, ``overlap`` is a set
        of keys ``left_seq`` have in common, ``left_only`` represents
        keys only found in ``left_seq``, and ``right_only`` holds keys
        only found in ``right_seq``.

    Raises:
        AssertionError if ``left_seq`` is not an instance of
        ``type(right_seq)``, or if they are not of a non-terminal
        type.

    >>> compute_keysets({'foo': None}, {'bar': None}) == (set([]), {'foo'}, {'bar'})
    True
    >>> (compute_keysets({'foo': None, 'baz': None}, {'bar': None, 'baz': None})
    ...  == ({'baz'}, {'foo'}, {'bar'}))
    True
    >>> compute_keysets(['foo', 'baz'], ['bar', 'baz']) == ({0, 1}, set([]), set([]))
    True
    >>> compute_keysets(['foo'], ['bar', 'baz']) == ({0}, set([]), {1})
    True
    >>> compute_keysets([], ['bar', 'baz']) == (set([]), set([]), {0, 1})
    True
    """
    assert isinstance(left_seq, type(right_seq)), (left_seq, right_seq)
    assert type(left_seq) in NONTERMINALS, left_seq

    if type(left_seq) is dict:
        left_keyset = set(left_seq.keys())
        right_keyset = set(right_seq.keys())
    else:
        left_keyset = set(range(len(left_seq)))
        right_keyset = set(range(len(right_seq)))

    overlap = left_keyset.intersection(right_keyset)
    left_only = left_keyset - right_keyset
    right_only = right_keyset - left_keyset

    return overlap, left_only, right_only


def keyset_diff(left_struc, right_struc, key, minimal=True):
    """Return a diff between ``left_struc`` and ``right_struc``.

    It is assumed that ``left_struc`` and ``right_struc`` are both
    non-terminal types (serializable as arrays or objects).  Sequences
    are treated just like mappings by this function, so the diffs will
    be correct but not necessarily minimal.  For a minimal diff
    between two sequences, use :func:`needle_diff`.

    This function probably shouldn't be called directly.  Instead, use
    :func:`udiff`, which will call :func:`keyset_diff` if appropriate
    anyway.
    """
    out = []
    (overlap, left_only, right_only) = compute_keysets(left_struc, right_struc)
    out.extend([[key + [k]] for k in left_only])
    out.extend([[key + [k], right_struc[k]] for k in right_only])
    for k in overlap:
        sub_key = key + [k]
        out.extend(diff(left_struc[k], right_struc[k],
                        minimal, False, sub_key))
    return out


def this_level_diff(left_struc, right_struc, key=None, common=None):
    """Return a sequence of diff stanzas between the structures
    left_struc and right_struc, assuming that they are each at the
    key-path ``key`` within the overall structure.

    >>> (this_level_diff({'foo': 'bar', 'baz': 'quux'},
    ...                 {'foo': 'bar'})
    ...  == [[['baz']]])
    True
    >>> (this_level_diff({'foo': 'bar', 'baz': 'quux'},
    ...                 {'foo': 'bar'}, ['quordle'])
    ...  == [[['quordle', 'baz']]])
    True
    """
    out = []

    if key is None:
        key = []

    if common is None:
        common = commonality(left_struc, right_struc)

    if common:
        (overlap, left, right) = compute_keysets(left_struc, right_struc)
        for okey in overlap:
            if left_struc[okey] != right_struc[okey]:
                out.append([key[:] + [okey], right_struc[okey]])
        for okey in left:
            out.append([key[:] + [okey]])
        for okey in right:
            out.append([key[:] + [okey], right_struc[okey]])
        return out
    elif left_struc != right_struc:
        return [[key[:], right_struc]]
    else:
        return []


def structure_worth_investigating(left_struc, right_struc):
    """Test whether it is worth looking at the internal structure of
    `left_struc` and `right_struc` to see if they can be efficiently
    diffed.
    """
    if type(left_struc) is not type(right_struc):
        return False
    if type(left_struc) in TERMINALS:
        return False
    if len(left_struc) == 0 or len(right_struc) == 0:
        return False
    return True


def commonality(left_struc, right_struc):
    """Return a float between 0.0 and 1.0 representing the amount
    that the structures left_struc and right_struc have in common.

    It is assumed (and ``assert``ed!) that ``left_struc`` and
    ``right_struc`` are of the same type, and non-empty (check this
    using :func:`structure_worth_investigating`).  Return value is
    computed as the fraction (elements in common) / (total elements).
    """
    assert type(left_struc) is type(right_struc), (left_struc, right_struc)
    assert left_struc and right_struc, (left_struc, right_struc)
    if type(left_struc) is dict:
        (overlap, left, right) = compute_keysets(left_struc, right_struc)
        com = float(len(overlap))
        tot = len(overlap.union(left, right))
    else:
        assert type(left_struc) in (list, tuple), left_struc
        com = 0.0
        for elem in left_struc:
            if elem in right_struc:
                com += 1
        tot = max(len(left_struc), len(right_struc))

    return com / tot


def split_deletions(stanzas):
    """Split a diff into modifications and deletions.

    Return value is a 3-tuple of lists: the first is a list of
    stanzas from ``stanzas`` that modify JSON objects, the second is
    a list of stanzas that add or change elements in JSON arrays, and
    the second is a list of stanzas which delete elements from
    arrays.

    """
    objs = [x for x in stanzas if isinstance(x[0][-1], Basestring)]
    seqs = [x for x in stanzas if isinstance(x[0][-1], int)]
    assert len(objs) + len(seqs) == len(stanzas), stanzas
    seqs.sort(key=len)
    lengths = [len(x) for x in seqs]
    point = bisect.bisect_left(lengths, 2)
    return objs, seqs[point:], seqs[:point]


def sort_stanzas(stanzas):
    """Sort the stanzas in ``diff``.

    Object changes can occur in any order, but deletions from arrays
    have to happen last node first: ['foo', 'bar', 'baz'] -> ['foo',
    'bar'] -> ['foo'] -> []; and additions to arrays have to happen
    leftmost-node-first: [] -> ['foo'] -> ['foo', 'bar'] -> ['foo',
    'bar', 'baz'].

    Note that this will also sort changes to objects (dicts) so that
    they occur first of all, then modifications/additions on
    arrays, followed by deletions from arrays.

    """
    if len(stanzas) == 1:
        return stanzas
    # First we divide the stanzas using split_deletions():
    (objs, mods, dels) = split_deletions(stanzas)
    # Then we sort modifications of lists in ascending order of last key:
    mods.sort(key=lambda x: x[0][-1])
    # And deletions from lists in descending order of last key:
    dels.sort(key=lambda x: x[0][-1], reverse=True)
    # And recombine:
    return objs + mods + dels
