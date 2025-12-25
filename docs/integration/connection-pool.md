# Connection Pooling

Connection pooling allows you to reuse database connections across multiple operations, reducing the overhead of establishing new connections. This is particularly useful in web applications where many concurrent requests need database access.

## Usage

Pass a `ConnectionPool` (or `AsyncConnectionPool`) to `PgDb` instead of a raw connection:

```{.python continuation fixture:postgres_container}
from psycopg_pool import ConnectionPool
from pydantic import BaseModel
from typing import Annotated

from embar.column.common import Integer, Text
from embar.config import EmbarConfig
from embar.db.pg import PgDb
from embar.table import Table


class User(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="users")
    id: Integer = Integer(primary=True)
    name: Text = Text()


# Create a connection pool
pool = ConnectionPool("postgres://pg:pw@localhost:25432/db", open=True)

# Pass the pool to PgDb
db = PgDb(pool)

# Run migrations
db.migrate([User]).run()

# Insert a user
db.insert(User).values(User(id=1, name="Alice")).run()

# Query it back
class UserRead(BaseModel):
    id: Annotated[int, User.id]
    name: Annotated[str, User.name]

users = db.select(UserRead).from_(User).run()
print(users)
# [UserRead(id=1, name='Alice')]

# Clean up
pool.close()
```

## Unopened Pools

If you create a pool with `open=False`, it will be automatically opened on first use:

```python notest
pool = ConnectionPool("postgres://...", open=False)
db = PgDb(pool)
# Pool is opened automatically when the first query runs
```
