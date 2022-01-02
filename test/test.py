from __future__ import print_function, unicode_literals

try:
    import coverage

    cov = coverage.coverage()
except ImportError:
    class DummyCoverage(object):
        def start(self):
            pass

        def stop(self):
            pass

        def save(self):
            pass

        def report(self, *a, **k):
            pass


    cov = DummyCoverage()

cov.start()
import sys, os, doctest, unittest, inspect, itertools, json, re, argparse

HERE = os.path.abspath(os.path.dirname(__file__))
DOTDOT = os.path.abspath(os.path.join(HERE, '..'))

MATERIAL_PATH = os.path.join(HERE, 'Material')

sys.path.insert(0, os.path.join(DOTDOT, 'src'))
import json_delta as ujson_delta


def gather_material(dr=MATERIAL_PATH):
    files = set(os.listdir(dr))
    i = 0
    for f in files.copy():
        if re.search(
                r'^(?:(?:case|diff|target)_\d{2}.json|udiff_\d{2}.patch)$', f
        ) is None:
            files.discard(f)
    while True:
        out = i
        if not files:
            break
        for frame in ('case_%02d.json', 'target_%02d.json',
                      'diff_%02d.json', 'udiff_%02d.patch'):
            if frame % i not in files:
                out = None
            files.discard(frame % i)
        if out is not None:
            yield out
        i += 1


def load_material(category, index):
    ext = 'patch' if category == 'udiff' else 'json'
    fn = os.path.join(
        MATERIAL_PATH,
        '{}_{:02d}.{}'.format(category, index, ext)
    )
    with open(fn) as f:
        return f.read()


MODULES = (
    ujson_delta,
    ujson_delta._diff,
    ujson_delta._udiff,
    ujson_delta._patch,
    ujson_delta._upatch,
    ujson_delta._util
)


class DocTestSuite(unittest.TestSuite):
    def __init__(self):
        return unittest.TestSuite.__init__(self,
                                           (doctest.DocTestSuite(mod) for mod in MODULES)
                                           )


class PerIndexCase(unittest.TestCase):
    def __init__(self, index):
        unittest.TestCase.__init__(self, 'runTest')
        self.index = index
        self.attrs = {type(self).__name__[:-4], self.index}

    def __str__(self):
        return '{}, case {}'.format(type(self).__name__, self.index)

    def setUp(self):
        for cat in self.cats:
            setattr(self, cat, load_material(cat, self.index))


class MinimalDiffCase(PerIndexCase):
    cats = ('case', 'target')

    def runTest(self):
        diff = ujson_delta.load_and_diff(self.case, self.target,
                                        minimal=True, verbose=True)
        self.assertEquals(
            json.loads(self.target), ujson_delta.patch(json.loads(self.case), diff)
        )


class NonMinimalDiffCase(PerIndexCase):
    cats = ('case', 'target')

    def runTest(self):
        diff = ujson_delta.load_and_diff(self.case, self.target,
                                        minimal=False, verbose=True)
        self.assertEquals(
            json.loads(self.target), ujson_delta.patch(json.loads(self.case), diff)
        )


class PatchCase(PerIndexCase):
    cats = ('case', 'target', 'diff')

    def runTest(self):
        self.assertEquals(
            json.loads(self.target),
            ujson_delta.load_and_patch(self.case, self.diff)
        )


class UdiffCase(PerIndexCase):
    cats = ('case', 'target')

    def runTest(self):
        udiff = '\n'.join(ujson_delta.load_and_udiff(self.case, self.target))
        self.assertEquals(
            json.loads(self.target), ujson_delta.upatch(
                json.loads(self.case), udiff
            )
        )


class UpatchCase(PerIndexCase):
    cats = ('case', 'target', 'udiff')

    def runTest(self):
        self.assertEquals(
            json.loads(self.target), ujson_delta.load_and_upatch(
                self.case, json.dumps(self.udiff)
            )
        )


class ReverseUpatchCase(PerIndexCase):
    cats = ('case', 'target', 'udiff')

    def runTest(self):
        self.assertEquals(
            json.loads(self.case), ujson_delta.load_and_upatch(
                self.target, json.dumps(self.udiff), reverse=True
            )
        )


INDICES = [x for x in gather_material()]
INDEX_CASES = [MinimalDiffCase, UdiffCase, NonMinimalDiffCase,
               PatchCase, UpatchCase, ReverseUpatchCase]


def desired_attr_sets(attr_args):
    out = set()
    for attrs in attr_args:
        attr_set = set()
        for attr in attrs:
            if re.search('^[A-Za-z-]+$', attr):
                attr_set.add(attr)
            elif re.search('^[0-9]+(?:,[0-9]+)*$', attr):
                attr_set.update((int(x) for x in attr.split(',')))
            else:
                mat = re.search('^([0-9]+)-([0-9]+)$', attr)
                if mat is not None:
                    attr_set.update(range(int(mat.group(1)), int(mat.group(2)) + 1))
        out.add(frozenset(attr_set))
    return out


def generate_test_cases(attr_check):
    for case_class, case_no in itertools.product(INDEX_CASES, INDICES):
        case = case_class(case_no)
        if case is not None and attr_check(case.attrs):
            yield case
    if attr_check({'doctest'}):
        for module in MODULES:
            yield doctest.DocTestSuite(module)


def check_attr_sets(case_attrs, attr_sets):
    if attr_sets == set():
        return True
    for attr_set in attr_sets:
        if attr_set.issubset(case_attrs):
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attribute', '-a', nargs='+',
                        action='append', default=[])
    parser.add_argument('--verbose', '-v', action='count', default=0)
    opts = parser.parse_args()
    attr_sets = desired_attr_sets(opts.attribute)
    attr_check = lambda attrs: check_attr_sets(attrs, attr_sets)
    suite = unittest.TestSuite(generate_test_cases(attr_check))
    unittest.TextTestRunner(descriptions=False,
                            verbosity=opts.verbose + 1).run(suite)


if __name__ == '__main__':
    main()
    cov.stop()
    cov.save()
    cov.report(MODULES)
