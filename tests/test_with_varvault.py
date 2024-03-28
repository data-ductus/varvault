import time
from commons import *


vault_file = f"{DIR}/vault.json"


class Keyring(varvault.Keyring):
    k1 = varvault.Key("k1", valid_type=str)
    k2 = varvault.Key("k2", valid_type=int)
    k3 = varvault.Key("k3", valid_type=float)


class TestWithVarvault:
    """
    varvault-lib works really well together with varvault since varvault essentially abstracts away input variables and return variables from functions,
    allowing for decoupled functions that works really well running in thread groups where functions do not have to be called with arguments.
    """
    def setup_method(self):
        try:
            os.remove(vault_file)
        except:
            pass

    def teardown_method(self):
        try:
            os.remove(vault_file)
        except:
            pass

    def test_with_varvault(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file, mode="w"))
        sleep = 0.5
        init = varvault.ThreadGroup()
        use = varvault.ThreadGroup()

        @init.register()
        @vault.manual(output=Keyring.k1)
        def set_k1():
            time.sleep(sleep)
            return "valid"

        @init.register()
        @vault.manual(output=Keyring.k2)
        def set_k2():
            time.sleep(sleep)
            return 1

        @init.register()
        @vault.manual(output=Keyring.k3)
        def set_k3():
            time.sleep(sleep)
            return 3.14

        @use.register()
        @vault.manual(input=Keyring.k1)
        def use_k1(k1=None):
            time.sleep(sleep)
            assert k1 == "valid"
            return k1

        @use.register()
        @vault.manual(input=Keyring.k2)
        def use_k2(k2=None):
            time.sleep(sleep)
            assert k2 == 1
            return k2

        @use.register()
        @vault.manual(input=Keyring.k3)
        def use_k3(k3=None):
            time.sleep(sleep)
            assert k3 == 3.14
            return k3

        start = time.time()
        init.execute()
        assert sleep - 0.2 < time.time() - start < sleep + 0.2, "Took too long to run. Concurrency seems broken"
        assert Keyring.k1 in vault and vault.get(Keyring.k1) == "valid"
        assert Keyring.k2 in vault and vault.get(Keyring.k2) == 1
        assert Keyring.k3 in vault and vault.get(Keyring.k3) == 3.14
        assert init.executed
        assert use.executed is False

        start = time.time()
        use.execute()
        assert sleep - 0.2 < time.time() - start < sleep + 0.2, "Took too long to run. Concurrency seems broken"
        results = use.get_results()
        assert f"{results}" == "[(function=use_k1; result=valid), (function=use_k2; result=1), (function=use_k3; result=3.14)]"

