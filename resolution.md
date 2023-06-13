# Patches

## RedisResource

The Constructor has a `host='localhost'` and `port=6379` parameters that can be changed to match the host and port of the `redis server` the user would like to connect to.

There is no instance of a database in redis. Instead commands are executed directly inside the dictionary that is a dictonary. Switch between databases with the -n flag which is be convension `0`.

The following functions has been overridden from `BaseResource` in `RedisResource`:

* read
* write
* exists
* state

## SqliteResource

### SQL injections

The `execute` method from the `sqlite` module is safe from SQL_injections.

The following functions has been overridden from `BaseResource` in `SqliteResource`:

* read
* write
* exists
* state
* path

The constructor wants the `path` to the `varvault.db` and with the help of the docker-compose.yml will make sure the docker container has a refrence to the database file created by sqlite.

## General

### Code Injections

Desirialization uses literal_eval, from the `ast` module instead of eval to avoid malicious code execution.

### Resource Modes

* w: deletes the content of the enitre remote database and updates the values from the `KeyRing` provided.

* r: only allows read to be performed for this vault.

## Fixes

Thesis discarded and files moved into tests/
Changed filename and variable name from `camelCase` to `snake_case`.
