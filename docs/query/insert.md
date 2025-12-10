# Insert

Insert operations in Embar are straightforward. You create a table row instance and insert it into the database.

## Basic Insert

Insert a single row:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.db.pg import AsyncPgDb
from embar.column.common import Integer, Text
from embar.table import Table

class User(Table):
    id: Integer = Integer()
    email: Text = Text()

async def get_db(tables: list[Table] = None):
    tables = tables if tables is not None else [User]
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate(tables)
    return db

async def basic():
    db = await get_db()
    user = User(id=1, email="alice@example.com")
    await db.insert(User).values(user)

asyncio.run(basic())
```

This generates:

```sql
INSERT INTO "user" ("id", "email") VALUES (%(id)s, %(email)s)
```

With parameters: `{'id': 1, 'email': 'alice@example.com'}`

## Inserting Multiple Rows

Pass multiple row instances to `.values()`:

```{.python continuation}
async def multiple():
    users = [
        User(id=10, email="alice@example.com"),
        User(id=11, email="bob@example.com"),
        User(id=12, email="charlie@example.com"),
    ]
    db = await get_db()
    await db.insert(User).values(*users)

asyncio.run(multiple())
```

This generates a single insert statement with multiple parameter sets:

```sql
INSERT INTO "user" ("id", "email") VALUES (%(id)s, %(email)s)
```

With parameters:
```{.python continuation}
[
    {'id': 10, 'email': 'alice@example.com'},
    {'id': 11, 'email': 'bob@example.com'},
    {'id': 12, 'email': 'charlie@example.com'},
]
```

## Returning Inserted Data

Use `.returning()` to get back the inserted rows. This is useful for retrieving auto-generated IDs or default values:

```{.python continuation}
async def returning():
    db = await get_db()
    user = User(id=20, email="alice@example.com")
    inserted = await db.insert(User).values(user).returning()

    # inserted is a list of User instances
    assert inserted[0].id == 20
    assert inserted[0].email == "alice@example.com"

asyncio.run(returning())
```

This generates:

```sql
INSERT INTO "user" ("id", "email") VALUES (%(id)s, %(email)s) RETURNING *
```

The `RETURNING *` clause tells the database to return all columns of the inserted row.

## Working with Defaults

Columns with default values can be omitted when creating instances:

```{.python continuation}
class UserStatus(Table):
    id: Integer = Integer()
    email: Text = Text(not_null=True)
    status: Text = Text(default="active")

user = UserStatus(id=30, email="alice@example.com")
# status will be set to "active" by the database

async def defaults():
    db = await get_db([UserStatus])
    inserted = await db.insert(UserStatus).values(user).returning()
    assert inserted[0].status == "active"

asyncio.run(defaults())
```

## Viewing the SQL

Use `.sql()` to inspect the generated query without executing it:

```{.python continuation}
async def view_sql():
    user = User(id=1, email="alice@example.com")
    query = db.insert(User).values(user).sql()

    print(query.sql)
    # INSERT INTO "user" ("id", "email") VALUES (%(id)s, %(email)s)

    print(query.many_params)
    # [{'id': 1, 'email': 'alice@example.com'}]
```

## Inserting with Foreign Keys

When inserting rows with foreign key relationships, insert the parent row first:

```{.python continuation}

class UserSimple(Table):
    id: Integer = Integer(primary=True)

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: UserSimple.id)
    content: Text = Text()

async def relations():
    db = await get_db([Message,UserSimple])
    user = UserSimple(id=40)
    await db.insert(UserSimple).values(user)

    message = Message(id=1, user_id=user.id, content="Hello!")
    await db.insert(Message).values(message)

asyncio.run(relations())
```

## On Conflict (Upsert)

Handle duplicate key conflicts with `on_conflict_do_nothing()` or `on_conflict_do_update()`.

### Do Nothing

Ignore rows that would cause a unique constraint violation:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.db.pg import AsyncPgDb
from embar.column.common import Integer, Text
from embar.table import Table

class Product(Table):
    id: Integer = Integer(primary=True)
    name: Text = Text()

async def get_db(tables: list[Table] = None):
    tables = tables if tables is not None else [Product]
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate(tables)
    return db

async def do_nothing():
    db = await get_db([Product])

    # Insert initial product (using on_conflict for idempotency)
    await db.insert(Product).values(Product(id=100, name="Widget")).on_conflict_do_nothing(("id",))

    # Attempt to insert duplicate - will be ignored
    await db.insert(Product).values(
        Product(id=100, name="Gadget")
    ).on_conflict_do_nothing(("id",))

asyncio.run(do_nothing())
```

This generates:

```sql
INSERT INTO "product" ("id", "name") VALUES (%(id)s, %(name)s)
ON CONFLICT (id) DO NOTHING
```

### Do Update

Update existing rows when a conflict occurs:

```{.python continuation}
async def do_update():
    db = await get_db([Product])

    # Insert initial product (using on_conflict for idempotency)
    await db.insert(Product).values(Product(id=101, name="Widget")).on_conflict_do_nothing(("id",))

    # Upsert - update name if id already exists
    await db.insert(Product).values(
        Product(id=101, name="Gadget")
    ).on_conflict_do_update(("id",), {"name": "Updated Widget"})

asyncio.run(do_update())
```

This generates:

```sql
INSERT INTO "product" ("id", "name") VALUES (%(id)s, %(name)s)
ON CONFLICT (id) DO UPDATE SET name = %(set_name_0)s
```

### With Returning

Combine with `.returning()` to get the result:

```{.python continuation}
async def upsert_returning():
    db = await get_db([Product])

    # Insert initial product (using on_conflict for idempotency)
    await db.insert(Product).values(Product(id=102, name="Widget")).on_conflict_do_nothing(("id",))

    result = await db.insert(Product).values(
        Product(id=102, name="Gadget")
    ).on_conflict_do_update(("id",), {"name": "Updated"}).returning()

    assert result[0].id == 102

asyncio.run(upsert_returning())
```

