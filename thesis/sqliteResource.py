import sqlite3
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

    def getVar(self, __name):
        return self.cursor.execute(
            f"SELECT value FROM {self.configuration} WHERE name=?", (__name,)
        )

    def setVar(self, __name, __value):
        # self.cursor.execute()
        # if not len(self.c)
        self.cursor.execute(
            f"INSERT INTO {self.configuration} SET value=? WHERE name=?",
            (__name, __value),
        )
        self.id += 1
        self.connection.commit()

    def getDict(self):
        self.cursor.execute(f"SELECT * FROM {self.configuration}")
        d = {}
        ls = self.cursor.fetchall()
        for row in ls:
            id, key, value = str(row).split("|")
            d[key] = value

        return d

    def __del__(self):
        self.cursor.close()

    def testRun(self):
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

    def create_resource(self):
        """Meant to create the resource to store the vault in a database."""
        raise NotImplementedError()

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
        # An XML file must have exactly one root. We assign the vault to the root self.KEY
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
        path="varvault.db",
        mode=varvault.ResourceModes.WRITE,
        table="varvault_table",
        is_updating_existing=True,
    ):
        self.connection = sqlite3.connect(database=path)
        self.database_file = path
        self.cursor = self.connection.cursor()
        self.table = table
        self.is_updating_existing = is_updating_existing

        super().__init__(path="Online Database", mode=mode)

    def Create(self):
        return None

    def resource(self):
        """Meant to return the resource that stores the vault in some database such as a file."""
        raise NotImplementedError()

    def state(self):
        """Meant to return the state of the resource, such as a hash of the resource."""
        import hashlib

        hash_md5 = hashlib.md5()
        for chunk in self.connection.iterdump():
            hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def create_resource(self):
        """Meant to create the resource to store the vault in a database."""
        raise NotImplementedError("This is done using SqliteHandler's Constructor")

    def path(self) -> str:
        """Meant to return the path to the database that stores the vault."""
        return self.database_file

    def writable(self, obj: varvault.Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        return True

    def exists(self) -> bool:
        """Meant to return a bool which says if the resource exists or not"""
        return True

    def do_write(self, vault: varvault.Dict):
        self.set(vault)

    def do_read(self):
        self.get()

    def __del__(self):
        self.disconnect()

    def get(self):
        self.cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table} (key VARCHAR(255) PRIMARY KEY, value VARCHAR(255))"
        )
        # if the table is found get it's content
        d = {}
        self.cursor.execute(f"SELECT * FROM {self.table}")
        broken_list = self.cursor.fetchall()
        for row in broken_list:
            _, key, value = row
            d[key] = value

        return d

    def set(self, dict: varvault.Dict):
        if self.mode == varvault.ResourceModes.READ:
            return

        elif self.mode == varvault.ResourceModes.WRITE:
            self.cursor.execute(f"DROP TABLE IF EXISTS {self.table}")

        # varvault.ResourceModes.APPEND
        self.cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table} (key VARCHAR(255) PRIMARY KEY, value VARCHAR(255))"
        )
        for key, value in dict.items():
            try:
                self.cursor.execute(
                    f"INSERT INTO {self.table} VALUES ('{key}', '{value}')"
                )
            except sqlite3.IntegrityError:
                if self.is_updating_existing:
                    self.cursor.execute(
                        f"UPDATE {self.table} SET value=? WHERE key=?", (value, key)
                    )
        self.connection.commit()

    def disconnect(self):
        self.connection.commit()
        self.cursor.close()
        self.connection.close()

    def testRun(self):
        connection = sqlite3.connect(database="test.db")

        cur = connection.cursor()

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


class KeyRing(varvault.Keyring):
    arg1 = varvault.Key("arg1", valid_type=str)
    arg2 = varvault.Key("arg2", valid_type=str)


sqliteHandler_vault = varvault.create(keyring=KeyRing, resource=SqliteResource())


@sqliteHandler_vault.vaulter(return_keys=[KeyRing.arg1, KeyRing.arg2])
def sql_create_args(arg1, arg2):
    return arg1, arg2


@sqliteHandler_vault.vaulter(input_keys=[KeyRing.arg1, KeyRing.arg2])
def sql_use_args(arg1=varvault.AssignedByVault, arg2=varvault.AssignedByVault):
    print(KeyRing.arg1, arg1, KeyRing.arg2, arg2)


if __name__ == "__main__":
    sql_create_args("9", "73483")
    sql_use_args()
