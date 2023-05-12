import varvault
import redis


# creates a RedisResource that attempts to establishes a connection based on the IP:port provided
# not used by anything, but maybe still useful
class DepreciatedRedisResource(varvault.BaseResource):
    # RedisResource begins
    def __init__(
        self,
        IPaddress="localhost",
        port: int = 6379,
        db: int = 0,
        mode="a",
        canWriteIfExists=True,
    ):
        pool = redis.ConnectionPool(host=IPaddress, port=port, db=db)
        self.redis_client = redis.Redis(connection_pool=pool)

        self.hasWriteAccess = bool()
        self.canWriteIfExists = canWriteIfExists

        # diffrent usage modes for RedisResource
        if mode == "r":
            # only allow GET requests
            self.hasWriteAccess = False
            self.canWriteIfExists = False

        if mode == "w":
            # clear database and run SET command for every key in Keyring
            if not self.redis_client.flushdb():
                raise Exception("__init__.py, RedisResource: Could not clear database")
            self.hasWriteAccess = True
            print("flushing server: done!")

        if mode == "a":
            pass
            # self.redis_client.exists()

        super().__init__("", "w")

        self.host = pool.connection_kwargs["host"]
        self.port = pool.connection_kwargs["port"]
        self.file_io = None

    def getDict(self):
        d = dict()
        keys = self.redis_client.keys("*")
        values = self.redis_client.mget(keys)

        for key, value in zip(keys, values):
            d.update({key.decode(): value.decode()})
        return d

    def setup_connection(self, IPAddress="localhost", port=6379):
        import socket

        try:
            pool = redis.ConnectionPool(host=IPAddress, port=port, db=0)
            self.redis_client = redis.Redis(connection_pool=pool)
            self.redis_client.reset()
        except redis.exceptions.ConnectionError:
            print("Failed to connect to Redis server.")
        except socket.gaierror:
            print("Invalid IP address or hostname.")
        except Exception as e:
            print(f"Error: {e}")

    def getVar(self, __name) -> bytes | None:
        return self.redis_client.get(__name)

    def setVar(self, __name, __value) -> bool | None:
        if not (self.redis_client.get(__name) is None):
            print(
                "__init__.py, setVar() NOTE: you need write-access to write to an existing key-value pair"
            )
            return None
        return self.redis_client.set(__name, __value)

    # delete variables if their name is in names
    def delVar(self, __names) -> bool:
        return self.redis_client.delete(__names)

    # extra funcitons that shouldn't be needed to work properly
    # WARNING: they are currently broken

    # # get variables from keys
    # def getVarsFromKeyNames(self, __keys) -> bool | None:
    #     return [bytes(item).decode('UTF-8') for item in self.redis_client.mget(__keys)]

    # def getPair(self, __hash_name, __key) -> bool | None:
    #     return self.redis_client.hget(__hash_name, __key)

    # def setPair(self, __hash_name, __key, __value) -> int:
    #     return self.redis_client.hset(__hash_name, __key, __value)

    # def getSubList(self, __name, __start=0, __end=-1) -> list[bytes]:
    #     return self.redis_client.lrange(__name, __start, __end)

    # def pushVars(self, __name, __values) -> int:
    #     return self.redis_client.rpush(__name, __values)

    # cleanup redis client
    def close(self):
        try:
            self.redis_client.close()
        except redis.exceptions as e:
            print(f"Error: {e}")
        except Exception as any:
            print(f"Error: {any}")

    # RedisResource ends

    # baseResource begins
    @property
    def state(self):
        """Returns the state of the vault, which is the checksum of the redis server content as a dictionary"""
        result = self.getDict().items()
        import hashlib

        hash_md5 = hashlib.md5()
        if result:
            hash_md5.update("{\n".encode())
            for key, value in result:
                hash_md5.update(
                    bytes(key.encode()) + b": " + bytes(value.encode()) + b",\n"
                )
            hash_md5.update("}".encode())
        else:
            hash_md5.update(b"{}")
        return hash_md5.hexdigest()

    @property
    def resource(self):
        """Meant to return the resource that stores the vault in some database such as a file."""
        return NotImplementedError()

    def create_resource(self):
        """Meant to create the resource to store the vault in a database."""
        if not self.redis_client.ping():
            self.setup_connection(self.host, self.port)

    @property
    def path(self):
        """Meant to return the path to the database that stores the vault."""
        return self.host, self.port

    def writable(self, obj: varvault.Dict) -> bool:
        import socket

        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        try:
            if not self.redis_client.ping():
                return False

        except redis.exceptions.ConnectionError:
            print("Failed to connect to Redis server.")
        except socket.gaierror:
            print("Invalid IP address or hostname.")
        except Exception as e:
            print(f"Error: {e}")

    def exists(self) -> bool:
        """Meant to return a bool which says if the server is connected"""
        return self.redis_client.ping()

    def do_write(self, vault: dict) -> None:
        f"""write from {vault} to redis"""
        for key, value in vault.items():
            if not self.setVar(key, value):
                print(f"Warning: key {key} failed to be set to {value}")
            else:
                # continue
                print(
                    f"__init__.py, RedisResource, do_write(): Note: key {key} set to {value}"
                )

    def do_read(self):
        return self.getDict()

    # baseResouce ends


class KeyRing(varvault.Keyring):
    arg1 = varvault.Key("arg1", valid_type=int)
    arg2 = varvault.Key("arg2", valid_type=str)
    arg3 = varvault.Key("arg3", valid_type=list, can_be_none=False)


def serialize(value: str):
    # if want to ignore the type add single quotes around the value
    return str(value)


def deserialize(value: str):
    if type(value) == bytes:
        value = value.decode()
    if value is None:
        return value
    try:
        return eval(value)
    except SyntaxError:
        if isinstance(value, str):
            return value
    except NameError:
        if isinstance(value, str):
            return value
    raise Exception


# Download database

# convert to JsonResource

# edit data

# Upload database


class RedisResource(varvault.BaseResource):
    def __init__(self, path="localhost6379", mode=varvault.ResourceModes.WRITE):
        self.connect()
        super().__init__("path", mode)

    def __del__(self):
        self.disconnect()

    def connect(self, host: str = "localhost", port: int = 6379, db: int = 0):
        pool = redis.ConnectionPool(host=host, port=port, db=db)
        self.redis_client = redis.Redis(connection_pool=pool)

    def get(self) -> dict:
        d = {}
        keys = self.redis_client.keys("*")
        values = self.redis_client.mget(keys)

        for key, value in zip(keys, values):
            value = deserialize(value)
            d.update({key.decode(): value})
        return d

    def set(self, d: varvault.Dict):
        if self.mode == varvault.ResourceModes.READ:
            return
        for key, value in d.items():
            value = serialize(value)
            self.redis_client.set(key, value)

    def disconnect(self):
        self.redis_client.close()

    def create(self):
        return None

    def resource(self):
        """Meant to return the resource that stores the vault in some database such as a file."""
        return None

    def state(self):
        """Meant to return the state of the resource, such as a hash of the resource."""
        import hashlib

        hash_md5 = hashlib.md5()
        for key, value in self.get().items():
            hash_md5.update(key + value)
        return hash_md5.hexdigest()

    def create_resource(self):
        """this is handled by the constructor instead."""
        return None

    def path(self):
        """Meant to return the path to the database that stores the vault."""
        return "localhost:6379"

    def writable(self, obj: varvault.Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        return True

    def exists(self) -> bool:
        """Meant to return a bool which says if the resource exists or not"""
        return True

    def do_write(self, vault: dict):
        if self.mode == varvault.ResourceModes.READ:
            return

        # flushdb first if write is True
        elif self.mode == varvault.ResourceModes.WRITE:
            self.redis_client.flushdb()

        # APPEND
        self.set(vault)

    def do_read(self):
        self.get()


class KeyRing(varvault.Keyring):
    arg1 = varvault.Key("arg1", valid_type=int)
    arg2 = varvault.Key("arg2", valid_type=int)


redisResource_vault = varvault.create(keyring=KeyRing, resource=RedisResource())


@redisResource_vault.vaulter(return_keys=[KeyRing.arg1, KeyRing.arg2])
def create_args(arg1, arg2):
    return arg1, arg2


@redisResource_vault.vaulter(input_keys=[KeyRing.arg1, KeyRing.arg2])
def use_args(arg1=varvault.AssignedByVault, arg2=varvault.AssignedByVault):
    print(KeyRing.arg1, arg1, KeyRing.arg2, arg2)


# everything is a string
# https://stackoverflow.com/questions/32274113/difference-between-storing-integers-and-strings-in-redis
if __name__ == "__main__":
    create_args(98, 33)

    use_args()
