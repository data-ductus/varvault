import sqlite3
from typing import Dict

import varvault

# TODO Work in progress, but is it worth it? Redis is the better solution

def hash_dict(any_dict: dict) -> str:
    import hashlib

    return hashlib.md5(str(any_dict).encode()).hexdigest()


def serialize(value):
    if isinstance(value, str):
        return "'" + value + "'"
    elif isinstance(value, (bytes, int, list, tuple, dict, set, bool, type(None))):
        return str(value)
    else:
        print(
            f"Invalid type: {type(value)}, allowed types are: (bytes, int, tuple, list, dict, set, bool, NoneType)"
        )


def deserialize(value: str):
    import ast

    try:
        return ast.literal_eval(value)
    except ValueError:
        f"""Invalid value: {value} with type {type(value)}"""
    except SyntaxError:
        """Code injection detected."""


class SqliteResource(varvault.BaseResource):
    def __init__(self,
                 path,
                 mode=varvault.ResourceModes.READ,
                 table="varvault_table",
                 update_existing=True,):
        import os
        if not os.path.exists(path):
            open(path, 'w+')
        
        # local path to database file
        self.connection = sqlite3.connect(database=path)
        
        # mounted to a docker container with the path "root/db/[database file]"
        # volume required in docker-compose.yml file in the container directory before the container is created
        
        self.local_path = path
        self.cursor = self.connection.cursor()
        self.table = table
        self.update_existing = update_existing

        super().__init__(path=path, mode=mode)

    def create(self):
        return None

    @property
    def resource(self):
        return self.cursor

    @property
    def state(self) -> str:
        """Meant to return the state of the resource, such as a hash of the resource."""
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table} (key VARCHAR(255) PRIMARY KEY, value VARCHAR(255))")
        self.cursor.execute(f"SELECT * FROM {self.table}")
        d = {}
        for key, value in self.cursor.fetchall():
            value = serialization.deserialize(value)
            d.update({key: value})

        # useful for compatibility with other resources state property
        # does not store the new ordered dictionary
        d = sorted(d.items())

        return serialization.hash_dict(d)

    @property
    def path(self) -> str:
        """Meant to return the path to the database that stores the vault."""
        return self.local_path

    def writable(self, obj: Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        return True

    def exists(self) -> bool:
        """Meant to return a bool which says if the resource exists or not"""
        import os
        return os.path.exists(self.local_path)

    def do_write(self, vault: Dict):
        self.set(vault)

    def do_read(self) -> Dict:
        return self.get()

    def __del__(self):
        self.disconnect()

    def get(self):
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table} (key VARCHAR(255) PRIMARY KEY, value VARCHAR(255))")
        self.cursor.execute(f"SELECT * FROM {self.table}")

        d = {}

        for key, value in self.cursor.fetchall():
            value = serialization.deserialize(value)
            d.update({key: value})

        return d

    def set(self, dict: Dict):
        if self.mode == varvault.ResourceModes.READ.value:
            return

        elif self.mode == varvault.ResourceModes.WRITE.value:
            self.cursor.execute(f"DROP TABLE IF EXISTS {self.table}")

        self.cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table} (key VARCHAR(255) PRIMARY KEY, value VARCHAR(255))"
        )
        for key, value in dict.items():
            try:
                value = serialization.serialize(value)
                value = value.replace("'", '"')
                self.cursor.execute(
                    f"INSERT INTO {self.table} VALUES ('{key}', '{value}')"
                )
            except sqlite3.IntegrityError:
                if self.update_existing:
                    self.cursor.execute(
                        f"UPDATE {self.table} SET value=? WHERE key=?", (serialization.serialize(value), key)
                    )
        self.connection.commit()


    def disconnect(self):
        self.connection.commit()
        self.cursor.close()
        self.connection.close()