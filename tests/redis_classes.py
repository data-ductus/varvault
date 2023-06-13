import varvault
import serialization
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
        can_write_if_exists=True,
    ):
        pool = redis.ConnectionPool(host=IPaddress, port=port, db=db)
        self.redis_client = redis.Redis(connection_pool=pool)

        self.hasWriteAccess = bool()
        self.canWriteIfExists = can_write_if_exists

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

    def get_dict(self):
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

    def get_var(self, __name) -> bytes | None:
        return self.redis_client.get(__name)

    def set_var(self, __name, __value) -> bool | None:
        if not (self.redis_client.get(__name) is None):
            print(
                "__init__.py, set_var() NOTE: you need write-access to write to an existing key-value pair"
            )
            return None
        return self.redis_client.set(__name, __value)

    # delete variables if their name is in names
    def del_var(self, __names) -> bool:
        return self.redis_client.delete(__names)

    # extra funcitons that shouldn't be needed to work properly
    # WARNING: they are currently broken

    # # get variables from keys
    # def get_vars_from_key_names(self, __keys) -> bool | None:
    #     return [bytes(item).decode('UTF-8') for item in self.redis_client.mget(__keys)]

    # def get_pair(self, __hash_name, __key) -> bool | None:
    #     return self.redis_client.hget(__hash_name, __key)

    # def set_pair(self, __hash_name, __key, __value) -> int:
    #     return self.redis_client.hset(__hash_name, __key, __value)

    # def get_sub_list(self, __name, __start=0, __end=-1) -> list[bytes]:
    #     return self.redis_client.lrange(__name, __start, __end)

    # def push_vars(self, __name, __values) -> int:
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

    # BaseResource begins
    @property
    def state(self):
        """Returns the state of the vault, which is the checksum of the redis server content as a dictionary"""
        import hashlib

        hash_md5 = hashlib.md5()
        for key, value in self.get_dict().items():
            hash_md5.update(key + value)
        return hash_md5.hexdigest()

    @property
    def resource(self):
        """Meant to return the resource that stores the vault in some database such as a file."""
        return NotImplementedError()

    @property
    def path(self):
        """Meant to return the path to the database that stores the vault."""
        return self.host, self.port

    def writable(self, obj: varvault.Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        import socket

        try:
            if not self.redis_client.ping():
                return False
        except redis.exceptions.ConnectionError:
            print("Failed to connect to Redis server.")
        except socket.gaierror:
            print("Invalid IP address or hostname.")
        except Exception as e:
            print(f"Error: {e}")

        return True

    def exists(self) -> bool:
        """Meant to return a bool which says if the server is connected"""
        return self.redis_client.ping()

    def do_write(self, vault: dict) -> None:
        f"""write from {vault} to redis"""
        for key, value in vault.items():
            if not self.set_var(key, value):
                print(f"Warning: key {key} failed to be set to {value}")
            else:
                # continue
                print(
                    f"__init__.py, RedisResource, do_write(): Note: key {key} set to {value}"
                )

    def do_read(self):
        return self.get_dict()

    # BaseResouce ends

# Download database
# convert to JsonResource
# edit data
# Upload database


class RedisResource(varvault.BaseResource):
    def __init__(self, host='localhost', port: int=6379, db:int=0, mode=varvault.ResourceModes.READ):

        pool = redis.ConnectionPool(host=host, port=port, db=db)
        self.redis_client = redis.Redis(connection_pool=pool)
        
        try:
            # connection timeout is 20 seconds
            self.redis_client.ping()
        except BaseException as redis_connection_refused:
            print(redis_connection_refused)
            raise

        super().__init__(path="", mode=mode)

    def __del__(self):
        self.disconnect()


    def get(self) -> dict:
        d = {}
        keys = self.redis_client.keys("*")
        values = self.redis_client.mget(keys)
        assert values is not None

        for key, value in zip(keys, values, strict=True):
            key = key.decode()
            value = value.decode()
            value = serialization.deserialize(value)
            d.update({key: value})
        return d

    def set(self, d: varvault.Dict):
        if self.mode == varvault.ResourceModes.READ.value:
            return
        for key, value in d.items():
            value = serialization.serialize(value)
            self.redis_client.set(key, value)

    def disconnect(self):
        self.redis_client.close()

    def create(self):
        return None

    def resource(self):
        """Meant to return the resource that stores the vault in some database such as a file."""
        return None

    @property
    def state(self) -> str:
        """Meant to return the state of the resource, such as a hash of the resource."""
        d = sorted(self.get().items())

        import hashlib
        return hashlib.md5(str(d).encode()).hexdigest()

    # @property
    def path(self):
        """Meant to return the path to the database that stores the vault."""
        raise NotImplementedError()

    def writable(self, obj: varvault.Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        return True

    def exists(self) -> bool:
        return self.redis_client.ping()

    def do_write(self, vault: dict):
        if self.mode == varvault.ResourceModes.READ.value:
            return

        # flushdb first if write is True
        elif self.mode == varvault.ResourceModes.WRITE.value:
            self.redis_client.flushdb()

        # APPEND
        self.set(vault)


    def do_read(self):
        return self.get()
