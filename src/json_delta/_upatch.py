from __future__ import print_function, unicode_literals
from copy import deepcopy
import json

from ._util import Basestring, key_tracker, in_array, nearest_of, follow_path
from ._diff import sort_stanzas
from . import _patch

def upatch(struc, udiff, reverse=False):
    '''Apply a patch of the form output by :py:func:`json_delta.udiff()` to the
    structure ``struc``.
    '''
    diff = reconstruct_diff(udiff, reverse)
    return _patch.patch(struc, diff)

def ellipsis_handler(jstring, point, key):
    '''Extends :py:func:`_util.key_tracker` to handle the ``...`` construction.'''
    if jstring[point] == '.':
        if point+3 < len(jstring) and jstring[point:point+3] == '...':
            point += 3
            if in_array(key) and jstring[point] == '(':
                increment = ''
                point += 1
                while point < len(jstring) and jstring[point] != ')':
                    assert jstring[point] in '0123456789'
                    increment += jstring[point]
                    point += 1
                key[-1] += int(increment) - 1
            elif in_array(key):
                key[-1] += 1
            point -= 1
        else:
            assert jstring[point-1] in '0123456789'
            assert jstring[point+1] in '0123456789'
    return (point, key)

def udiff_key_tracker(udiff, point=0, start_key=None):
    '''Find points within the udiff where the active keypath changes.'''
    for point, key in key_tracker(udiff, point, start_key, ellipsis_handler):
        yield point, key
                
def scrub_span(udiff, point, next_point, sigil):
    span = udiff[point:next_point-1]
    span = span.replace('\n{}'.format(sigil),'').strip('\r\n\t ')
    return span

def reconstruct_diff(udiff, reverse=False):
    '''Turn a udiff back into a JSON-format diff.

    Set ``reverse`` to ``True`` to generate a reverse diff (i.e. swap
    the significance of line-initial ``+`` and ``-``).

    Header lines (if present) are ignored:
    >>> udiff = """--- <stdin>
    ... +++ <stdin>
    ... -false
    ... +true"""
    >>> reconstruct_diff(udiff)
    [[[], True]]
    >>> reconstruct_diff(udiff, reverse=True)
    [[[], False]]
    '''
    del_sigil = '+' if reverse else '-'
    add_sigil = '-' if reverse else '+'
    deletes = []
    diff = []
    del_key = []
    add_key = []
    point = 0
    # dec = JSONDecoder()

    def scrub_span(point, next_point, sigil):
        span = udiff[point:next_point-1]
        span = span.replace('\n{}'.format(sigil),'').strip('\r\n\t ')
        return span

    def gen_stanzas(point, max_point, adding=True):
        point += 1
        key = add_key if adding else del_key
        sigil = add_sigil if adding else del_sigil

        def build_output():
            span = scrub_span(point, next_point, sigil)
            if span and adding:
                return (next_key, [list(key), json.loads(span)])
            elif span:
                return (next_key, [list(key)])
        
        next_key = top_key = key if (not key or key[-1] is not None) else None
        next_point = origin = point
        for p, next_key in udiff_key_tracker(udiff[origin:max_point], 0, key):
            next_point = origin + p
            if (not next_key or next_key[-1] is not None) and top_key is None:
                top_key = next_key
                point = next_point
            if ((not key or key[-1] is not None) and
                len(key) == len(top_key) == len(next_key)):
                out = build_output()
                if out is not None:
                    yield out
                point = next_point
            key = next_key
            
        next_point = max_point
        if (not key or key[-1] is not None) and len(key) == len(top_key):
            out = build_output()
            if out is not None:
                yield out

    if point + 3 <= len(udiff) and udiff[point:point+3] == '---':
        point = udiff[point:].find('\n') + point + 1
    if point + 3 <= len(udiff) and udiff[point:point+3] == '+++':
        point = udiff[point:].find('\n') + point + 1

    while point < len(udiff):
        if udiff[point] == ' ':
            if in_array(del_key):
                assert in_array(add_key)
                add_key = del_key = max(add_key, del_key)
            max_point = (nearest_of(udiff[point:], '\n{}'.format(del_sigil),
                                                   '\n{}'.format(add_sigil))
                         + point + 1)
            for p, del_key in udiff_key_tracker(udiff[point:max_point], 0, del_key):
                pass
            for p, add_key in udiff_key_tracker(udiff[point:max_point], 0, add_key):
                pass
        elif udiff[point] == del_sigil:
            max_point = (nearest_of(udiff[point:], '\n{}'.format(add_sigil), '\n ')
                         + point + 1)
            for del_key, stanza in gen_stanzas(point, max_point, False):
                deletes.append(stanza)
        else:
            assert udiff[point] == add_sigil
            max_point = (nearest_of(udiff[point:], '\n{}'.format(del_sigil), '\n ')
                         + point + 1)
            for add_key, stanza in gen_stanzas(point, max_point):
                diff.append(stanza)
        point = max_point
    keys_in_diff = [stanza[0] for stanza in diff]
    for stanza in diff:
        if in_array(stanza[0]) and [stanza[0]] not in deletes:
            stanza.append('i')
    diff.extend((d for d in deletes if d[0] not in keys_in_diff))
    return sort_stanzas(diff)
