from __future__ import print_function, absolute_import, division
import sys
from contextlib import contextmanager
import numpy
from numba import numpy_support, types
from numba.compiler import compile_isolated
from numba import unittest_support as unittest
from numba.io_support import StringIO


@contextmanager
def swap_stdout():
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        yield
    finally:
        sys.stdout = old_stdout


def usecase1(arr1, arr2):
    """Base on https://github.com/numba/numba/issues/370

    Modified to add test-able side effect.
    """
    n1 = arr1.size
    n2 = arr2.size

    for i1 in range(n1):
        st1 = arr1[i1]
        for i2 in range(n2):
            st2 = arr2[i2]
            st2.row += st1.p * st2.p + st1.row - st1.col

        st1.p += st2.p
        st1.col -= st2.col


def usecase2(x, N):
    """
    Base on test1 of https://github.com/numba/numba/issues/381
    """
    for k in range(N):
        y = x[k]
        print(y.f1, y.s1, y.f2)


def usecase3(x, N):
    """
    Base on test2 of https://github.com/numba/numba/issues/381
    """
    for k in range(N):
        print(x.f1[k], x.s1[k], x.f2[k])


def usecase4(x, N):
    """
    Base on test3 of https://github.com/numba/numba/issues/381
    """
    for k in range(N):
        y = x[k]
        print(y.f1, x.s1[k], y.f2)


def usecase5(x, N):
    """
    Base on test4 of https://github.com/numba/numba/issues/381
    """
    for k in range(N):
        print(x[k].f1, x.s1[k], x[k].f2)


class TestRecordUsecase(unittest.TestCase):

    def setUp(self):
        fields = [('f1', '<f8'), ('s1', '|S3'), ('f2', '<f8')]
        self.unaligned_dtype = numpy.dtype(fields)
        self.aligned_dtype = numpy.dtype(fields, align=True)

    def test_usecase1(self):
        pyfunc = usecase1

        # This is an unaligned dtype
        mystruct_dt = numpy.dtype([('p', numpy.float64),
                           ('row', numpy.float64),
                           ('col', numpy.float64)])
        mystruct = numpy_support.from_dtype(mystruct_dt)

        cres = compile_isolated(pyfunc, (mystruct[:], mystruct[:]))
        cfunc = cres.entry_point

        st1 = numpy.recarray(3, dtype=mystruct_dt)
        st2 = numpy.recarray(3, dtype=mystruct_dt)

        st1.p = numpy.arange(st1.size) + 1
        st1.row = numpy.arange(st1.size) + 1
        st1.col = numpy.arange(st1.size) + 1

        st2.p = numpy.arange(st2.size) + 1
        st2.row = numpy.arange(st2.size) + 1
        st2.col = numpy.arange(st2.size) + 1

        expect1 = st1.copy()
        expect2 = st2.copy()

        got1 = expect1.copy()
        got2 = expect2.copy()

        pyfunc(expect1, expect2)
        cfunc(got1, got2)

        self.assertTrue(numpy.all(expect1 == got1))
        self.assertTrue(numpy.all(expect2 == got2))

    def _setup_usecase2to5(self, dtype):
        N = 5
        a = numpy.recarray(N, dtype=dtype)
        a.f1 = numpy.arange(N)
        a.f2 = numpy.arange(2, N + 2)
        a.s1 = numpy.array(['abc'] * a.shape[0], dtype='|S3')
        return a

    def _test_usecase2to5(self, pyfunc, dtype):
        array = self._setup_usecase2to5(dtype)
        record_type = numpy_support.from_dtype(dtype)
        cres = compile_isolated(pyfunc, (record_type[:], types.intp))
        cfunc = cres.entry_point

        with swap_stdout():
            pyfunc(array, len(array))
            expect = sys.stdout.getvalue()

        with swap_stdout():
            cfunc(array, len(array))
            got = sys.stdout.getvalue()

        self.assertEqual(expect, got)

    def test_usecase2(self):
        self._test_usecase2to5(usecase2, self.unaligned_dtype)
        self._test_usecase2to5(usecase2, self.aligned_dtype)

    def test_usecase3(self):
        self._test_usecase2to5(usecase3, self.unaligned_dtype)
        self._test_usecase2to5(usecase3, self.aligned_dtype)

    def test_usecase4(self):
        self._test_usecase2to5(usecase4, self.unaligned_dtype)
        self._test_usecase2to5(usecase4, self.aligned_dtype)

    def test_usecase5(self):
        self._test_usecase2to5(usecase5, self.unaligned_dtype)
        self._test_usecase2to5(usecase5, self.aligned_dtype)


if __name__ == '__main__':
    unittest.main()
