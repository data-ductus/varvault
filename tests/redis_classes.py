import json
from typing import Dict, Union, Literal

import ast
import redis
import varvault
import hashlib


def hash_dict(any_dict: dict) -> str:
    return hashlib.md5(str(any_dict).encode()).hexdigest()


def serialize(value):
    valid_types = (bytes, int, float, tuple, set, bool, type(None))
    if isinstance(value, str):
        return f"'{value}'"
    elif isinstance(value, (dict, list)):
        return json.dumps(value)
    elif isinstance(value, valid_types):
        return str(value)
    else:
        print(f"Invalid type: {type(value)}, allowed types are: {valid_types}")


def deserialize(value: str):
    try:
        return json.loads(value)
    except:
        # An exception was caught trying to load value as a JSON.
        # This means the value is not a complex structure like a list or a dict
        pass
    try:
        return ast.literal_eval(value)
    except:
        # An exception was caught trying to deserialize the value.
        # This usually isn't a problem and usually just means the string looks a bit special, e.g. a URL
        pass
    return value


class RedisResource(varvault.BaseResource):
    pool: redis.ConnectionPool
    redis_client: redis.Redis
    def __init__(self, host='localhost', port: int = 6379, db: int = 0, mode: Union[Literal["r", "w", "a", "r+", "w+", "a+"], varvault.ResourceModes] = "r"):

        self.pool = redis.ConnectionPool(host=host, port=port, db=db)
        self.redis_client = None
        try:
            self.create()
        except BaseException as e:
            if not self.MODE_MAPPING[mode].live_update:
                raise varvault.ResourceNotFoundError(f"Unable to create resource at {host}:{port} (mode is {mode})", self) from e

        super().__init__(path=f"{host}:{port}", mode=mode)

    def __del__(self):
        self.disconnect()

    def set(self, d: Dict):
        if self.mode == varvault.ResourceModes.READ.value:
            return
        for key, value in d.items():
            value = serialize(value)
            self.redis_client.set(key, value)

    def disconnect(self):
        self.redis_client.close()

    def create(self):
        self.redis_client = redis.Redis(connection_pool=self.pool)
        self.redis_client.ping()

    @property
    def resource(self) -> redis.Redis:
        """Meant to return the resource that stores the vault in some database such as a file."""
        return self.redis_client

    @property
    def state(self) -> str:
        """Meant to return the state of the resource, such as a hash of the resource."""
        d = sorted(self.read())

        return hash_dict(d)

    @property
    def path(self):
        """Meant to return the path to the database that stores the vault."""
        return self.raw_path

    def writable(self, obj: Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        return True

    def exists(self) -> bool:
        try:
            return self.redis_client.ping()
        except:
            return False

    def do_write(self, vault: dict):
        # cannot write on read-only
        if self.mode_properties.read_only:
            return

        # flushdb first if the resource can write
        elif self.mode_properties.write:
            self.redis_client.flushdb()

        if self.mode == varvault.ResourceModes.READ.value:
            return

        async def set(key, value):
            self.redis_client.set(key, serialize(value))
        varvault.concurrent_execution(set, vault.keys(), vault.values())

    def do_read(self):
        keys = self.redis_client.keys("*")
        values = self.redis_client.mget(keys)
        varvault.assert_and_raise(values is not None, varvault.ResourceNotFoundError("No values found in the database.", self))
        varvault.assert_and_raise(len(keys) == len(values), ValueError("Keys and values must be of equal length."))
        data = {}
        for key, value in zip(keys, values):
            key = key.decode()
            value = value.decode()
            value = deserialize(value)
            data.update({key: value})
        return data
