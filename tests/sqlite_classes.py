import sqlite3
import serialization
import varvault

class DepreciatedSqliteResource(varvault.BaseResource):
    def __init__(
        self,
        database: str = "test.db",
        port: int = 9771,
        configuration: str = "configuration",
    ):
        self.id = 1
        self.configuration = configuration
        self.connection = sqlite3.connect(database=database)
        self.cursor = self.connection.cursor()

        # create table with key/value pairs
        try:
            self.cursor.execute(
                """CREATE TABLE conf
                (id INTEGER PRIMARY KEY, name VARCHAR(255), value VARCHAR(255))"""
            )
        except sqlite3.OperationalError as o:
            print(o)

        # super().__init__(path=port)

    def get_var(self, __name):
        return self.cursor.execute(
            f"SELECT value FROM {self.configuration} WHERE name=?", (__name,)
        )

    def set_var(self, __name, __value):
        # self.cursor.execute()
        # if not len(self.c)
        self.cursor.execute(
            f"INSERT INTO {self.configuration} SET value=? WHERE name=?",
            (__name, __value),
        )
        self.id += 1
        self.connection.commit()

    def get_dict(self):
        self.cursor.execute(f"SELECT * FROM {self.configuration}")
        d = {}
        ls = self.cursor.fetchall()
        for row in ls:
            id, key, value = str(row).split("|")
            d[key] = value

        return d

    def __del__(self):
        self.cursor.close()

    def test_run(self):
        connection = sqlite3.connect("test.db")

        cur = connection.cursor()

        cur.execute(
            """CREATE TABLE example_table
                    (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)"""
        )
        cur.execute("INSERT INTO example_table VALUES (1, 'John Doe', 35)")
        cur.execute("INSERT INTO example_table VALUES (2, 'Jane Smith', 28)")
        cur.execute("INSERT INTO example_table VALUES (3, 'Bob Johnson', 42)")

        # Commit the changes to the database
        connection.commit()

        cur.execute("SELECT name FROM example_table WHERE id=?", (1,))
        name = cur.fetchone()[0]
        print(name)

        cur.execute("UPDATE example_table SET age=? WHERE name=?", (36, "John Doe"))
        cur.execute("SELECT * FROM example_table")
        rows = cur.fetchall()
        for row in rows:
            print(row)

        with open("example_table.sql", "w") as f:
            for line in connection.iterdump():
                f.write("%s\n" % line)

        connection.close()

    def resource(self):
        """Meant to return the resource that stores the vault in some database such as a file."""
        raise NotImplementedError()

    def state(self):
        """Meant to return the state of the resource, such as a hash of the resource."""
        import hashlib

        hash_md5 = hashlib.md5()
        with open(self.path, "rb") as f:
            for chunk in self.connection.iterdump():
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def path(self):
        """Meant to return the path to the database that stores the vault."""
        raise NotImplementedError()

    def writable(self, obj: varvault.Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        raise NotImplementedError()

    def exists(self) -> bool:
        """Meant to return a bool which says if the resource exists or not"""
        return bool("Not implemented")
        raise NotImplementedError()

    def do_write(self, vault: dict):
        pass

    def do_read(self):
        pass

# anslut till databasen
# kolla om databas namnet finns
# finns det inte så skapa filen
# finns den så anslut
# get tar in hela tabellen och converterar den till en dict
# set tar in en dict och skickar kommandon for varje nyckel-värde par
# för varje par så updateras motsvarande värde
# om det behöver finnas till att börja med så fixa det edge caset också

class SqliteResource(varvault.BaseResource):
    def __init__(
        self,
        path,
        mode=varvault.ResourceModes.READ,
        table="varvault_table",
        update_existing=True,
    ):
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

        import hashlib
        return hashlib.md5(str(d).encode()).hexdigest()

    @property
    def path(self) -> str:
        """Meant to return the path to the database that stores the vault."""
        return self.local_path

    def writable(self, obj: varvault.Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        return True

    def exists(self) -> bool:
        """Meant to return a bool which says if the resource exists or not"""
        import os
        return os.path.exists(self.local_path)

    def do_write(self, vault: varvault.Dict):
        self.set(vault)

    def do_read(self) -> varvault.Dict:
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

    def set(self, dict: varvault.Dict):
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