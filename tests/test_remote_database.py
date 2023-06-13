from commons import *
import redis_classes
from redis import exceptions as redis_exceptions
import sqlite_classes

class Keyring(varvault.Keyring):
    string_value = varvault.Key("string_value", valid_type=str)
    int_value = varvault.Key("int_value", valid_type=int)
    list_value = varvault.Key("list_value", valid_type=list)
    none_value = varvault.Key("none_value", valid_type=type(None), can_be_none=True)

class TestRedisVault:

    test_values  = "not valid", 177, [1, "2", 3, 4, 5], None # tuple of test values
    db = 4 # db index for testing (default: 0)

    @classmethod
    def setup_class(cls):
        pass

    def test_connection_refused(self):
        bogon_ip_address = "198.51.100.0"
        undefined_port = 0b_1111_1111_1111_1111
        db = 1337
        failed_vault = varvault.create(keyring=Keyring, resource=redis_classes.RedisResource(host=bogon_ip_address, port=undefined_port, db=db))

        assert len(failed_vault.items()) == 0

    def test_write(self):
        vault = varvault.create(keyring=Keyring, resource=redis_classes.RedisResource(mode="w", db=4))

        @vault.manual(output=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
        def _set():
            return self.test_values

        _set()

        result = vault.resource.read()

        assert Keyring.string_value in result and result[Keyring.string_value] == self.test_values[0]
        assert Keyring.int_value in result and result[Keyring.int_value] == self.test_values[1]
        assert Keyring.list_value in result and result[Keyring.list_value] == self.test_values[2]
        assert Keyring.none_value in result and result[Keyring.none_value] == self.test_values[3]

    # def test_append(self):
    #     vault = varvault.create(keyring=nextring, resource=redis_classes.RedisResource(mode="a", db=4))

    #     @vault.manual(output=(nextring.string_value, nextring.int_value, nextring.list_value, nextring.none_value, nextring.other_value))
    #     def _set():
    #         return self.test_values

    #     _set()

    #     result = vault.resource.read()

    #     assert Keyring.string_value in result and result[Keyring.string_value] == self.test_values[0]
    #     assert Keyring.int_value in result and result[Keyring.int_value] == self.test_values[1]
    #     assert Keyring.list_value in result and result[Keyring.list_value] == self.test_values[2]
    #     assert Keyring.none_value in result and result[Keyring.none_value] == self.test_values[3]

    def test_read(self):
        vault = varvault.create(keyring=Keyring, resource=redis_classes.RedisResource(mode="r", db=self.db))

        @vault.manual(input=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
        def _get(string_value = None, int_value=None, list_value=None, none_value=not None):
            assert string_value == self.test_values[0]
            assert int_value == self.test_values[1]
            assert list_value == self.test_values[2]
            assert none_value == self.test_values[3]

        _get()

    def test_connection_refused(self):
        bogon_ip_address = "198.51.100.1"
        undefined_port = 0b_1111_1111_1111_1111
        db = 1337
        
        try:
            res = redis_classes.RedisResource(host=bogon_ip_address, port=undefined_port, db=db)
        except BaseException:
            res = None
        
        assert res is None

class TestSqliteVault:

    test_values = ('tested_string', 0xF00DBA11, [2, 3, 5, 7, "eleven"], None)

    # create with mode='r'
    # create with mode='w'
    # create with mode='a'

    # set an empty dict
    # set with a type that is not dict

    def test_operational_error(self, ):
        just_wrong = "operational_error.operational_error"
        failed_vault = varvault.create(keyring=Keyring, resource=sqlite_classes.SqliteResource(path=just_wrong))

        assert len(failed_vault.items()) == 0

    def test_write(self):
        full_path = os.path.expanduser("~") + "/repos/varvault/varvault.db"

        vault = varvault.create(keyring=Keyring, resource=sqlite_classes.SqliteResource(path=full_path, mode="w"))

        @vault.manual(output=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
        def _set():
            return self.test_values

        _set()

        result = vault.resource.read()

        assert Keyring.string_value in result and result[Keyring.string_value] == self.test_values[0]
        assert Keyring.int_value in result and result[Keyring.int_value] == self.test_values[1]
        assert Keyring.list_value in result and result[Keyring.list_value] == self.test_values[2]
        assert Keyring.none_value in result and result[Keyring.none_value] == self.test_values[3]

    # def test_append(self):
    #     vault = varvault.create(keyring=Keyring, resource=sqlite_classes.SqliteResource(mode="a", db=4))

    #     @vault.manual(output=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
    #     def _set():
    #         return "valid", 1, [1, 2, 3, 4, 5], None

    #     _set()

    #     result = vault.resource.read()

    #     assert Keyring.string_value in result and result[Keyring.string_value] == self.test_values[0]
    #     assert Keyring.int_value in result and result[Keyring.int_value] == self.test_values[1]
    #     assert Keyring.list_value in result and result[Keyring.list_value] == self.test_values[2]
    #     assert Keyring.none_value in result and result[Keyring.none_value] == self.test_values[3]

    def test_read(self):
        vault = varvault.create(keyring=Keyring, resource=sqlite_classes.SqliteResource(path= os.path.expanduser("~") + "/repos/varvault/varvault.db", mode="r"))

        @vault.manual(input=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
        def _get(string_value=None, int_value=None, list_value=None, none_value=not None):
            assert string_value == self.test_values[0]
            assert int_value == self.test_values[1]
            assert list_value == self.test_values[2]
            assert none_value == self.test_values[3]

        _get()

    def test_file_not_found(self):
        import os
        path_to_fail = os.path.expanduser("~") + "/repos/varvault/failed_vault.db"
        try:
            os.remove(path_to_fail)
        except IsADirectoryError:
            pass
        except OSError:
            pass
        failed_vault = varvault.create(keyring=Keyring, resource=sqlite_classes.SqliteResource(path=path_to_fail))

        assert len(failed_vault.items()) == 0

def test_state():
    test_values = ('tested_string', 0xF00DBA11, [2, 3, 5, 7, "eleven"], None)


    json = varvault.create(keyring=Keyring, resource=varvault.JsonResource(path=os.path.expanduser("~") + "/repos/varvault/compare.json", mode='w'))

    @json.manual(output=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
    def _middle_set():
        return test_values

    _middle_set()

    redis = varvault.create(keyring=Keyring, resource=redis_classes.RedisResource(db=7, mode='w'))

    @redis.manual(output=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
    def _left_set():
        return test_values

    _left_set()

    sqlite = varvault.create(keyring=Keyring, resource=sqlite_classes.SqliteResource(path=os.path.expanduser("~") + "/repos/varvault/compare.db", mode='w'))

    @sqlite.manual(output=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
    def _right_set():
        return test_values

    _right_set()

    # @middle.manual(input=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
    # def _middle_get(string_value=None, int_value=None, list_value=None, none_value=not None):
    #     return test_values

    # _middle_get()


    # @left.manual(input=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
    # def _left_get(string_value=None, int_value=None, list_value=None, none_value=not None):
    #     return test_values

    # _left_get()

    # @left.manual(input=(Keyring.string_value, Keyring.int_value, Keyring.list_value, Keyring.none_value))
    # def _right_get(string_value=None, int_value=None, list_value=None, none_value=not None):
    #     return test_values

    # _right_get()
    # d = sorted(redis.resource.read().items())
    # dd = sorted(json.resource.read().items())
    # ddd = sorted(sqlite.resource.read().items())

    l = redis.resource.state
    import hashlib
    m = json.resource.state # not ordered
    m = hashlib.md5(str(sorted(json.resource.read().items())).encode()).hexdigest()
    r = sqlite.resource.state
    assert l == m == r

def suite_of_tests(include_slow_tests=True):

    if include_slow_tests:
        broken = TestRedisVault()
        broken.test_connection_refused()
        del broken

    tr = TestRedisVault()

    tr.test_write()
    # tr.test_append()
    tr.test_read()

    if include_slow_tests:
        broken = TestSqliteVault()
        broken.test_file_not_found()
        del broken

    ts = TestSqliteVault()

    ts.test_write() # without .db
    ts.test_write() # with .db
    # ts.test_append()
    ts.test_read()


if __name__ == "__main__":
    include_all_tests = False
    suite_of_tests(include_all_tests)
    test_state()

