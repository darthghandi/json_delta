# -*- encoding: utf-8 -*-
from __future__ import print_function, unicode_literals

import random
import sys
import subprocess
import os
import ujson
import itertools
import unittest
import argparse
import re
import codecs
import traceback
from numbers import Number

HERE = os.path.abspath(os.path.dirname(__file__))
DOTDOT = os.path.abspath(os.path.join(HERE, '..'))

with open(os.path.join(HERE, 'local_binary_info.json')) as f:
    LOCAL_BINARY_INFO = ujson.load(f)

sys.path.insert(0, os.path.join(DOTDOT, 'src'))
print(sys.path)
from json_delta import _util as util

COMPACT_CASES = (0, 11, 12, 19)

UNICODE_POINTS = set(range(sys.maxunicode))
UNICODE_POINTS = UNICODE_POINTS - set(range(0xD800, 0xE000))  # Surrogates
UNICODE_POINTS = tuple(UNICODE_POINTS)

ENCODINGS = itertools.cycle(util.ENCODINGS)


class AgnosticNumeric(float):
    def __eq__(self, other):
        if not isinstance(other, Number):
            return False
        try:
            if float(self) == other:
                return True
            if float(self) == float(other):
                return True
            if int(self) == other:
                return True
        except:
            pass
        return False


test_dir = os.path.abspath(os.path.dirname(__file__))
cases = None
targets = None
diffs = None
udiffs = None
try:
    with open(os.path.join(test_dir, 'cases.json')) as f:
        cases = ujson.load(f)
    with open(os.path.join(test_dir, 'targets.json')) as f:
        targets = ujson.load(f)
    with open(os.path.join(test_dir, 'diffs.json')) as f:
        diffs = ujson.load(f)
    with open(os.path.join(test_dir, 'udiffs.json')) as f:
        udiffs = ujson.load(f)
except ValueError as ve:
    traceback.print_exc()
except Exception as e:
    traceback.print_exc()


class SubprocessTestCase(unittest.TestCase):
    multi_encodings = False

    def __init__(self, test_name, case_no=None):
        unittest.TestCase.__init__(self, test_name)
        assert test_name.startswith('test_'), test_name
        self.attrs = {self.package_name, test_name[5:].replace('_', '-')}
        if test_name.startswith('test_random'):
            self.attrs.add('random')
        else:
            self.attrs.add(case_no)
        if test_name.endswith('diff'):
            self.attrs.add('diff')
        if test_name[5] == 'u':
            self.attrs.add('u')
        self.test_name = test_name
        self.case_no = case_no

    def __str__(self):
        return ('{}, {}'.format(self.package_name, self.test_name)
                + (', case {}'.format(self.case_no)
                   if self.case_no is not None else ''))

    @classmethod
    def encode_input(cls, *args):
        encoding = next(ENCODINGS) if cls.multi_encodings else 'UTF-8'
        return util.compact_json_dumps(args).encode(encoding)

    @classmethod
    def is_abstract(cls):
        return not (hasattr(cls, 'binary') and hasattr(cls, 'commands'))

    @classmethod
    def determine_binary(cls):
        print(file=sys.stderr)
        if cls.__name__ in LOCAL_BINARY_INFO:
            cls.binary = LOCAL_BINARY_INFO[cls.__name__] or None
            if cls.binary is not None:
                print("{}: Binary `{}' specified locally; testing...".format(
                    cls.__name__, cls.binary
                ), file=sys.stderr)
        else:
            cls.binary = cls.binary_probe()

        if cls.binary is None:
            print('{}: Could not find binary. '.format(cls.__name__),
                  'Tests will be skipped.',
                  file=sys.stderr, sep=' ')

    @classmethod
    def setUpClass(cls, check=lambda ret: ret == 0):
        cls.determine_binary()
        cls.random_random_input = cls.encode_input(
            random_structure(), random_structure()
        )
        random_modified_case = random_structure()
        cls.random_modified_input = cls.encode_input(
            random_modified_case, modify_at_random(random_modified_case)
        )

        for input in ('random_modified_input',
                      'random_random_input'):
            data = getattr(cls, input)
            filename = '{}_{}.json'.format(cls.__name__, input)
            try:
                if os.path.exists(filename):
                    backup_filename = '{}~'.format(filename)
                    if os.path.exists(backup_filename):
                        os.remove(backup_filename)
                    os.rename(filename, backup_filename)
                with open(filename, 'wb') as f:
                    f.write(data)
            except:
                print("Warning: couldn't save `{}' to disk!".format(filename),
                      file=sys.stderr)

    @classmethod
    def binary_probe(cls):
        print("{}: Testing default binary `{}'".format(cls.__name__,
                                                       cls.binary),
              file=sys.stderr)
        probe = {'args': (cls.binary, '--version'),
                 'stdout': open(os.devnull, 'w'),
                 'stderr': open(os.devnull, 'w')}
        try:
            if subprocess.call(**probe) != 0:
                print("{}: No satisfactory response to `{} --version'".format(
                    cls.__name__, cls.binary
                ), file=sys.stderr)
                cls.binary = None
        except OSError:
            print("{}: An error occurred calling "
                  "`{} --version'".format(cls.__name__, cls.binary),
                  file=sys.stderr)
            cls.binary = None
        return cls.binary

    def run_cmd(self, cmd, stdin):
        if self.binary is None:
            raise unittest.SkipTest(
                'Cannot find binary for package {}'.format(self.package_name)
            )
        if cmd not in self.commands:
            raise unittest.SkipTest(
                'Package {} does not support the {} command'.format(
                    self.package_name, cmd
                )
            )
        arg_seq = [self.binary] + self.commands[cmd]
        worker = subprocess.Popen(arg_seq,
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        result, err = worker.communicate(stdin)
        self.assertEqual(err, '')
        if cmd == 'udiff':
            return result.decode('UTF-8')
        return ujson.loads(result.decode('UTF-8'), parse_float=AgnosticNumeric)

    def test_minimal_diff(self):
        diff = self.run_cmd(
            'minimal-diff',
            self.encode_input(cases[self.case_no], targets[self.case_no])
        )
        patched = self.run_cmd(
            'patch',
            self.encode_input(cases[self.case_no], diff)
        )
        self.assertEqual(patched, targets[self.case_no])

    def test_nonminimal_diff(self):
        diff = self.run_cmd(
            'nonminimal-diff',
            self.encode_input(cases[self.case_no], targets[self.case_no])
        )
        patched = self.run_cmd(
            'patch',
            self.encode_input(cases[self.case_no], diff))
        self.assertEqual(patched, targets[self.case_no])

    def test_patch(self):
        patched = self.run_cmd(
            'patch',
            self.encode_input(cases[self.case_no], diffs[self.case_no])
        )
        self.assertEqual(patched, targets[self.case_no])

    def test_udiff(self):
        diff = self.run_cmd(
            'udiff',
            self.encode_input(cases[self.case_no], targets[self.case_no])
        )
        patched = self.run_cmd(
            'patch',
            self.encode_input(cases[self.case_no], diff)
        )
        self.assertEqual(patched, targets[self.case_no])

    def test_upatch(self):
        patched = self.run_cmd(
            'upatch',
            self.encode_input(cases[self.case_no], udiffs[self.case_no])
        )
        self.assertEqual(patched, targets[self.case_no])

    def test_upatch_reverse(self):
        patched = self.run_cmd(
            'upatch-reverse',
            self.encode_input(targets[self.case_no], udiffs[self.case_no])
        )
        self.assertEqual(patched, cases[self.case_no])

    def test_compactness(self):
        if ('minimal-diff' not in self.commands
            and self.case_no in COMPACT_CASES):
            raise unittest.SkipTest(
                'Package {} diffs are not guaranteed compact.'.format(
                    self.package_name
                )
            )
        diff = self.run_cmd(
            'minimal-diff',
            self.encode_input(cases[self.case_no], targets[self.case_no])
        )
        self.assertLessEqual(
            len(util.compact_json_dumps(diff)),
            len(util.compact_json_dumps(diffs[self.case_no]))
        )

    def test_random_random(self):
        cmd = ('minimal-diff' if 'minimal-diff' in self.commands
               else 'nonminimal-diff')
        case, target = util.decode_json(self.random_random_input)
        diff = self.run_cmd(cmd, self.random_random_input)
        patched = self.run_cmd('patch', self.encode_input(case, diff))
        self.assertEqual(patched, target)

    def test_random_modified(self):
        cmd = ('minimal-diff' if 'minimal-diff' in self.commands
               else 'nonminimal-diff')
        case, target = util.decode_json(self.random_modified_input)
        diff = self.run_cmd(cmd, self.random_modified_input)
        patched = self.run_cmd('patch', self.encode_input(case, diff))
        self.assertEqual(patched, target)


class BasePythonCase(SubprocessTestCase):
    multi_encodings = True
    commands = {
        'minimal-diff': [os.path.join(DOTDOT, 'python', 'src', 'json_diff')],
        'nonminimal-diff': [os.path.join(DOTDOT, 'python', 'src', 'json_diff'),
                            '--fast'],
        'patch': [os.path.join(DOTDOT, 'python', 'src', 'json_patch')],
        'udiff': [os.path.join(DOTDOT, 'python', 'src', 'json_diff'), '-u'],
        'upatch': [os.path.join(DOTDOT, 'python', 'src', 'json_patch'), '-u'],
        'upatch-reverse': [os.path.join(DOTDOT, 'python', 'src', 'json_patch'),
                           '-uR']
    }

    def __init__(self, testMethod, case_no=None):
        super(BasePythonCase, self).__init__(testMethod, case_no)
        self.attrs.add('python')
        self.attrs.add(self.python_implementation.lower())

    @classmethod
    def check_python_version(cls):
        try:
            args = (cls.binary, '-c',
                    'import platform, sys; '
                    'sys.stdout.write(platform.python_version())')
            worker = subprocess.Popen(args, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
            version, err = worker.communicate()
            if err:
                return False

            args = (cls.binary, '-c',
                    'import platform, sys; '
                    'sys.stdout.write(platform.python_implementation())')
            worker = subprocess.Popen(args, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
            implementation, err = worker.communicate()
            if err:
                return False
        except OSError:
            return False
        return (version.startswith(cls.python_version)
                and implementation == cls.python_implementation)

    @classmethod
    def binary_probe(cls):
        tryouts = (cls.binary, '{}{}'.format(cls.binary, cls.python_version),
                   'python', 'python{}'.format(cls.python_version))
        for tryout in tryouts:
            cls.binary = tryout
            print(
                "{}: Let's see if calling `{}' will get us a "
                "{} {} interpreter...".format(
                    cls.__name__, cls.binary,
                    cls.python_implementation, cls.python_version
                ), file=sys.stderr
            )
            if cls.check_python_version():
                print("{}: Success!  Using `{}' as our binary.".format(
                    cls.__name__, cls.binary
                ), file=sys.stderr)
                return cls.binary
        cls.binary = None
        return cls.binary


class BasePython2Case(BasePythonCase):
    python_version = '2.7'
    commands = {cmd: ['-u'] + args
                for cmd, args in BasePythonCase.commands.items()}


class CPython2Case(BasePython2Case):
    package_name = 'python2'
    binary = 'python'
    python_implementation = 'CPython'


class CPython3Case(BasePythonCase):
    package_name = 'python3'
    binary = 'python'
    python_version = '3'
    python_implementation = 'CPython'


class JythonCase(BasePython2Case):
    package_name = 'jython'
    binary = 'jython'
    python_implementation = 'Jython'


class PyPy2Case(BasePython2Case):
    package_name = 'pypy2'
    binary = 'pypy'
    python_version = '2.7'
    python_implementation = 'PyPy'


class PyPy3Case(BasePythonCase):
    package_name = 'pypy3'
    binary = 'pypy'
    python_version = '3'
    python_implementation = 'PyPy'


class JavascriptCase(SubprocessTestCase):
    package_name = 'javascript'
    binary = 'node'
    commands = {
        'patch': [os.path.join(HERE, 'json_delta_test.js'), 'patch'],
        'minimal-diff': [os.path.join(HERE, 'json_delta_test.js'),
                         'minimal-diff'],
        'nonminimal-diff': [os.path.join(HERE, 'json_delta_test.js'),
                            'nonminimal-diff'],
    }


class RacketCase(SubprocessTestCase):
    package_name = 'racket'
    binary = 'racket'
    commands = {
        'patch': [os.path.join(HERE, 'patch.rkt')],
        'nonminimal-diff': [os.path.join(HERE, 'diff.rkt')]
    }


def get_test_material(idx):
    return cases[idx], targets[idx], diffs[idx], udiffs[idx]


def save_data():
    with codecs.open(os.path.join(test_dir, 'cases.json'),
                     'w', encoding='UTF-8') as f:
        ujson.dump(cases, f, ensure_ascii=False)
    with codecs.open(os.path.join(test_dir, 'targets.json'),
                     'w', encoding='UTF-8') as f:
        ujson.dump(targets, f, ensure_ascii=False)
    with codecs.open(os.path.join(test_dir, 'diffs.json'),
                     'w', encoding='UTF-8') as f:
        ujson.dump(diffs, f, ensure_ascii=False)
    with codecs.open(os.path.join(test_dir, 'udiffs.json'),
                     'w', encoding='UTF-8') as f:
        ujson.dump(udiffs, f, ensure_ascii=False)


def write_out_data(dest='Material'):
    if not os.path.exists(dest):
        os.makedirs(dest)
    for nm, i in itertools.product(('cases', 'targets', 'diffs'),
                                   range(len(cases))):
        with codecs.open(
                os.path.join(dest, '%s_%02d.json' % (nm[:-1], i)),
                'w', encoding=next(ENCODINGS)
        ) as f:
            if nm == 'diffs':
                ujson.dump(eval('%s[%d]' % (nm, i)), f, ensure_ascii=False)
            else:
                ujson.dump(eval('%s[%d]' % (nm, i)), f)

    for i, udiff in enumerate(udiffs):
        with codecs.open(os.path.join(dest, 'udiff_%02d.patch' % i),
                         'w', encoding=next(ENCODINGS)) as f:
            f.write(udiff)


def get_python_version(binary_name='python'):
    try:
        args = [binary_name, '-c',
                'import sys; sys.stdout.write(str(sys.version_info[0]))']
        worker = subprocess.Popen(args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        result, err = worker.communicate()
        if result in ('2', '3'):
            return result
    except OSError:
        pass


# def graph_struc_shape(struc, graph=None):
#     from pydot import Dot, Node, Edge
#
#     if graph is None:
#         graph = Dot()
#
#     labels = {dict: '{}', type(None): '∅', str: '“”', unicode: '“”',
#               list: '&#x5b;&#x5d;', tuple: '()', int: '0', float: '.0',
#               long: '0', bool: 'T∨F'}
#
#     def node_for_struc(struc, node_num=0):
#         n = Node(name='node{}'.format(node_num), label=labels[type(struc)])
#         graph.add_node(n)
#         node_num += 1
#         if isinstance(struc, dict):
#             for sub_struc in struc.values():
#                 sn, node_num = node_for_struc(sub_struc, node_num)
#                 graph.add_edge(Edge(n, sn))
#         elif isinstance(struc, list) or isinstance(struc, tuple):
#             for sub_struc in struc:
#                 sn, node_num = node_for_struc(sub_struc, node_num)
#                 graph.add_edge(Edge(n, sn))
#         return n, node_num
#
#     node_for_struc(struc)
#     return graph


def modify_at_random(struc, preserve_shape=True, preserve_types=False,
                     maxsize=15, *args, **kwargs):
    """Apply modifications randomly to the structure struc.

    Uses random_structure to generate values to modify, passing in
    args and kwargs.  If preserve_types is False, nodes in the
    structure may be replaced with nodes of a different type.  If
    preserve_shape is False, non-nested structures may be replaced
    with nested ones (and vice versa) and nodes may be added or
    deleted.
    """
    kwargs.update({'maxsize': maxsize})
    if type(struc) in util.TERMINALS:
        modify = random.choice((True, False))
        if modify:
            if preserve_types:
                rep_types = {type(struc)}
            elif preserve_shape:
                rep_types = set(util.TERMINALS)
            else:
                rep_types = set(util.SERIALIZABLE_TYPES)
                # rep_types.remove(tuple)
            struc = random_structure(rep_types, *args, **kwargs)
    else:
        if type(struc) is dict:
            out = struc.copy()
            keys = iter(struc)
        elif type(struc) in (list, tuple):
            out = [None] * len(struc)
            keys = range(len(struc))

        deletes = []
        for key in keys:
            delete = random.choice((True, False))
            if delete and not preserve_shape:
                deletes.append(key)
            else:
                out[key] = modify_at_random(
                    struc[key], preserve_shape, preserve_types, *args, **kwargs
                )

        for key in deletes:
            del out[key]

        if not preserve_shape:
            addchances = max(0, maxsize - len(out))
            for i in range(addchances):
                modify = random.choice((True, False))
                if modify:
                    if type(out) is dict:
                        key = random_structure({str, str}, *args, **kwargs)
                        while key not in out:
                            key = random_structure({str, str},
                                                   *args, **kwargs)
                        out[key] = random_structure(None, *args, **kwargs)
                    else:
                        out.append(random_structure(None, *args, **kwargs))

        if type(struc) is tuple:
            struc = tuple(out)
        else:
            struc = out
    return struc


def random_structure(types=frozenset(util.SERIALIZABLE_TYPES),
                     maxsize=15, nesting=0, maxnest=4, minnest=4):
    """Generate random JSON-serializable structures.

    >>> import json
    >>> for i in range(20):
    ...     struc = random_structure()
    ...     foo = ujson.dumps(struc)
    >>>
    """
    assert minnest <= maxnest, (minnest, maxnest)
    out_types = set(types)
    maxint = min(maxsize, sys.maxint)
    maxsize = min(maxsize, sys.maxsize)
    if nesting >= maxnest:
        out_types = out_types.difference(util.NONTERMINALS)
    elif nesting < minnest and types.intersection(util.NONTERMINALS):
        out_types = out_types.intersection(util.NONTERMINALS)

    out_type = random.choice(list(out_types))

    if out_type is type(None):
        return None

    if out_type is tuple:
        out = []
    else:
        out = out_type()

    if out_type is bool:
        out = bool(random.randrange(2))
    elif out_type is int:
        out = random.randint(-maxint, maxint)
    elif out_type is float:
        base = (random.random() * 2 - 1)  # Random float between -1.0 and 1.0
        out = base * maxsize
    else:
        length = random.randint(0, maxsize)
        idx = 0
        while idx < length:
            minnest_satisfied = any((type(x) in util.NONTERMINALS
                                     for x in out))
            if out_type in (list, tuple):
                out.append(random_structure(
                    types, maxsize, nesting=nesting + 1,
                    minnest=(0 if minnest_satisfied else minnest),
                    maxnest=maxnest
                ))
            elif out_type is str:
                out += chr(random.randrange(128))
            elif out_type is dict:
                key = random_structure({str, str})
                while key in out:
                    key = random_structure({str, str})
                out[key] = random_structure(
                    types, maxsize, nesting=nesting + 1,
                    minnest=(0 if minnest_satisfied else minnest),
                    maxnest=maxnest
                )
            idx += 1

    if out_type is tuple:
        out = tuple(out)
    return out


def gen_profiling_material(dest=os.path.join(DOTDOT, 'python', 'test',
                                             'Material', 'Profiling')):
    for nesting, case_no in itertools.product(range(1, 21), range(20)):
        with codecs.open(os.path.join(
                dest, 'all_nesting_{:02d}_case_{:02d}.json'.format(nesting, case_no)
        ), 'w', encoding='UTF-8') as f:
            case = random_structure(minnest=nesting, maxnest=nesting)
            ujson.dump(case, f, ensure_ascii=False)
        with codecs.open(os.path.join(
                dest, 'all_nesting_{:02d}_target_{:02d}.json'.format(nesting, case_no)
        ), 'w', encoding='UTF-8') as f:
            ujson.dump(
                modify_at_random(case, minnest=nesting, maxnest=nesting), f, ensure_ascii=False
            )
        with codecs.open(os.path.join(
                dest, 'dict_nesting_{:02d}_case_{:02d}.json'.format(nesting, case_no)
        ), 'w', encoding='UTF-8') as f:
            case = random_structure({dict}.union(util.TERMINALS),
                                    minnest=nesting, maxnest=nesting)
            ujson.dump(case, f, ensure_ascii=False)
        with codecs.open(os.path.join(
                dest, 'dict_nesting_{:02d}_target_{:02d}.json'.format(nesting, case_no)
        ), 'w', encoding='UTF-8') as f:
            ujson.dump(
                modify_at_random(case, minnest=nesting, maxnest=nesting), f, ensure_ascii=False
            )
        with codecs.open(os.path.join(
                dest, 'list_nesting_{:02d}_case_{:02d}.json'.format(nesting, case_no)
        ), 'w', encoding='UTF-8') as f:
            case = random_structure({list}.union(util.TERMINALS),
                                    minnest=nesting, maxnest=nesting)
            ujson.dump(case, f, ensure_ascii=False)
        print('list_nesting_{:02d}_target_{:02d}.json'.format(nesting, case_no))
        with codecs.open(os.path.join(
                dest, 'list_nesting_{:02d}_target_{:02d}.json'.format(nesting, case_no)
        ), 'w', encoding='UTF-8') as f:
            ujson.dump(
                modify_at_random(case, minnest=nesting, maxnest=nesting), f, ensure_ascii=False
            )


def int_if_poss(i):
    try:
        return int(i)
    except ValueError:
        return i


def get_case_classes():
    return [v for k, v in globals().items()
            if (k.endswith('Case')
                and issubclass(v, SubprocessTestCase)
                and not v.is_abstract())]


CASE_CLASSES = get_case_classes()


def get_python_binaries():
    for c in CASE_CLASSES:
        if issubclass(c, BasePythonCase):
            c.determine_binary()
            if c.binary is not None:
                yield c.binary


def desired_attr_sets(attr_args):
    out = set()
    for attrs in attr_args:
        attr_set = set()
        for attr in attrs:
            if re.search('^[A-Za-z-]+[23]?$', attr):
                attr_set.add(attr)
            elif re.search('^[0-9]+(?:,[0-9]+)*$', attr):
                attr_set.update((int(x) for x in attr.split(',')))
            else:
                mat = re.search('^([0-9]+)-([0-9]+)$', attr)
                if mat is not None:
                    attr_set.update(range(int(mat.group(1)),
                                          int(mat.group(2)) + 1))
        out.add(frozenset(attr_set))
    return out


def generate_test_cases(attr_check):
    for case_class, case_no in itertools.product(CASE_CLASSES,
                                                 range(len(cases))):
        for test_name in dir(case_class):
            if test_name.startswith('test_random') and case_no == 0:
                case = case_class(test_name)
            elif (test_name.startswith('test_')
                  and not test_name.startswith('test_random')):
                case = case_class(test_name, case_no)
            else:
                case = None
            if case is not None and attr_check(case.attrs):
                yield case


def check_attr_sets(case_attrs, attr_sets):
    if attr_sets == set():
        return True
    for attr_set in attr_sets:
        if attr_set.issubset(case_attrs):
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python-binaries', action='store_true')
    parser.add_argument('--attribute', '-a', nargs='+',
                        action='append', default=[])
    parser.add_argument('--verbose', '-v', action='count', default=0)
    opts = parser.parse_args()
    if opts.python_binaries:
        print(*get_python_binaries(), sep='\n')
        return
    attr_sets = desired_attr_sets(opts.attribute)
    attr_check = lambda attrs: check_attr_sets(attrs, attr_sets)
    suite = unittest.TestSuite(generate_test_cases(attr_check))
    unittest.TextTestRunner(descriptions=False,
                            verbosity=opts.verbose + 1).run(suite)


if __name__ == '__main__':
    main()
