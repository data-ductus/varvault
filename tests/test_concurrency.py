from commons import *


class TestConcurrency:
    def test_simple_concurrency(self):
        def f1(a1):
            assert a1 == 1
            return a1

        def f2(a2):
            assert a2 == 2
            return a2

        def f3(a1, kw1=None):
            assert a1 == 1
            assert kw1 is True
            return a1, kw1

        functions = [varvault.create_function(f1, 1), varvault.create_function(f2, 2), varvault.create_function(f3, 1, kw1=True)]
        result = varvault.threaded_execution(functions)
        assert f"{result}" == "[(function=f1; result=1), (function=f2; result=2), (function=f3; result=(1, True))]"

    def test_concurrency_same_function_different_args(self):
        arg_values = [1, 2, 3, 4, 5]

        def f1(a1):
            assert a1 in arg_values, f"{a1} not in {arg_values}"
            return a1

        functions = [varvault.create_function(f1, arg_value) for arg_value in arg_values]
        result = varvault.threaded_execution(functions)
        assert f"{result}" == "[(function=f1; result=1), (function=f1; result=2), (function=f1; result=3), (function=f1; result=4), (function=f1; result=5)]"

    def test_extracting_results(self):
        def f1(a1):
            return a1

        def f2(a2):
            return a2

        functions = [varvault.create_function(f1, 1), varvault.create_function(f1, 2), varvault.create_function(f2, 3)]
        result = varvault.threaded_execution(functions)
        assert f"{result}" == "[(function=f1; result=1), (function=f1; result=2), (function=f2; result=3)]"
        f1_results = result.get(f1.__name__)
        assert f"{f1_results}" == "[(function=f1; result=1), (function=f1; result=2)]"
        f2_results = result.get(f2.__name__)
        assert f"{f2_results}" == "[(function=f2; result=3)]"
