import time

from commons import *


class TestThreadGroup:
    def test_thread_group(self):
        test = varvault.ThreadGroup()

        @test.register()
        def f1():
            time.sleep(0.1)
            pass

        @test.register()
        def f2():
            time.sleep(0.1)
            pass

        @test.register()
        def f3():
            time.sleep(0.1)
            pass

        @test.register()
        def f4():
            time.sleep(0.1)
            pass

        start = time.time()
        test.execute()
        time_spent = time.time() - start
        assert test.executed
        assert 0.01 < time_spent < 0.2, f"(Threaded) Time spent ({time_spent}) is not within the permitted interval"

    def test_multiple_functions(self):
        test = varvault.ThreadGroup()

        @test.register()
        def f1():
            pass

        def shouldnt_run():
            assert False, f"Function {shouldnt_run.__name__} ran anyway"

        test.execute()
        assert test.executed

    def test_args_and_kwargs(self):
        test = varvault.ThreadGroup()

        @test.register(1, 2, kw1=True, kw2=False)
        def f1(a1, a2, kw1=None, kw2=None):
            assert a1 == 1
            assert a2 == 2
            assert kw1 is True
            assert kw2 is False

        test.execute()

        assert test.executed

    def test_update_fn_args(self):
        test = varvault.ThreadGroup()

        @test.register()
        def f1(a1, a2, kw1=None):
            assert a1 == 1
            assert a2 == 2
            assert kw1 is True

        test.update_fn_args(f1, 1, 2, kw1=True)

        test.execute()
        assert test.executed

    def test_multiple_groups_run_only_one(self):
        test = varvault.ThreadGroup()
        dont_run = varvault.ThreadGroup()

        @test.register()
        def f1():
            pass

        @dont_run.register()
        def d1():
            assert False, f"Function {d1.__name__} ran anyway"

        test.execute()
        assert test.executed
        assert dont_run.executed is False

    def test_run_multiple_groups(self):
        first = varvault.ThreadGroup()
        second = varvault.ThreadGroup()

        @first.register()
        def f1():
            pass

        @first.register()
        def f2():
            pass

        @second.register()
        def s1():
            pass

        @second.register()
        def s2():
            pass

        first.execute()
        assert first.executed
        assert second.executed is False

        second.execute()
        assert second.executed

    def test_call_registered_function_normally(self):
        test = varvault.ThreadGroup()

        @test.register()
        def f1(_a1, _a2, *, _kw1=None):
            assert _a1 == 1
            assert _a2 == "2"
            assert _kw1 == 3.14
            return _a1, _a2, _kw1

        a1, a2, kw1 = f1(1, "2", _kw1=3.14)
        assert a1 == 1
        assert a2 == "2"
        assert kw1 == 3.14
        assert not test.executed

    def test_asdict(self):
        test = varvault.ThreadGroup()

        @test.register()
        def f1():
            time.sleep(0.1)
            return 1, 1.2

        @test.register()
        def f2():
            time.sleep(0.1)
            return 2

        @test.register()
        def f3():
            time.sleep(0.1)
            return 3

        @test.register()
        def f4():
            time.sleep(0.1)
            return 4

        r: varvault.ResultList = test.execute()
        assert f"{r.asdict()}" == "{'f1': [(1, 1.2)], 'f2': [2], 'f3': [3], 'f4': [4]}"

        functions = [varvault.create_function(f1), varvault.create_function(f1), varvault.create_function(f1), varvault.create_function(f2), varvault.create_function(f3), varvault.create_function(f4)]
        r: varvault.ResultList = varvault.threaded_execution(functions)
        assert f"{r.asdict()}" == "{'f1': [(1, 1.2), (1, 1.2), (1, 1.2)], 'f2': [2], 'f3': [3], 'f4': [4]}"
