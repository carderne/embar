# Update

Update operations modify existing rows in your database. Embar provides a straightforward interface for updating data with full type safety.

## Basic Update

To update rows, use `.update()` with `.set()` and typically `.where()` to specify which rows to modify:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from typing import TypedDict
from embar.column.common import Integer, Text
from embar.db.pg import AsyncPgDb
from embar.query.where import Eq
from embar.table import Table

class Message(Table):
    id: Integer = Integer()
    user_id: Integer = Integer()
    content: Text = Text()

class MessageUpdate(TypedDict, total=False):
    id: int
    user_id: int
    content: str

async def get_db(tables: list[Table] = None):
    if tables is None:
        tables = [Message]
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate(tables)
    return db

async def basic():
    db = await get_db()
    await (
        db.update(Message)
        .set(MessageUpdate(content="Updated message"))
        .where(Eq(Message.id, 1))
    )

asyncio.run(basic())
```

This generates:

```sql
UPDATE "message" SET "content" = %(set_content_0)s
WHERE "message"."id" = %(p0)s
```

With parameters: `{'set_content_0': 'Updated message', 'p0': 1}`

## Partial Updates with TypedDict

Python doesn't have a built-in `Partial` type, so Embar uses `TypedDict` with `total=False` to enable partial updates. This lets you update only specific fields:

```{.python continuation}
class MessageUpdate(TypedDict, total=False):
    id: int
    user_id: int
    content: str

async def partial():
    db = await get_db()
    # Update only the content field
    await (
        db.update(Message)
        .set(MessageUpdate(content="New content"))
        .where(Eq(Message.id, 1))
    )

    # Update multiple fields
    await (
        db.update(Message)
        .set(MessageUpdate(content="New content", user_id=2))
        .where(Eq(Message.id, 1))
    )

asyncio.run(partial())
```

The `total=False` parameter means all fields are optional, allowing you to specify only the fields you want to update.

## Returning Updated Data

Use `.returning()` to get back the updated rows. This is useful when you need to see the final state of the data:

```{.python continuation}
async def returning():
    db = await get_db()

    message = Message(id=1, user_id=2, content="Hello")
    await db.insert(Message).values(message)

    updated = await (
        db.update(Message)
        .set(MessageUpdate(content="Updated message"))
        .returning()
    )

    # updated is a list of Message instances
    assert updated[0].content == "Updated message"

asyncio.run(returning())
```

This generates:

```sql
UPDATE "message" SET "content" = %(set_content_0)s
WHERE "message"."id" = %(p0)s
RETURNING *
```

The `RETURNING *` clause tells the database to return all columns of the updated rows.

## Where Clauses

The `.where()` method limits which rows are updated. Without it, all rows in the table would be modified:

```{.python continuation}
from embar.query.where import Eq, Gt, And

async def where():
    db = await get_db()
    # Update a specific row
    await (
        db.update(Message)
        .set(MessageUpdate(content="Updated"))
        .where(Eq(Message.id, 1))
    )

    # Update multiple rows matching a condition
    await (
        db.update(Message)
        .set(MessageUpdate(content="Archived"))
        .where(Gt(Message.id, 100))
    )

    # Update with multiple conditions
    await (
        db.update(Message)
        .set(MessageUpdate(content="Updated by user 5"))
        .where(And(
            Eq(Message.user_id, 5),
            Gt(Message.id, 10)
        ))
    )

asyncio.run(where())
```

For more on where clauses, see [Where](where.md).

## Updating Multiple Fields

Update as many fields as needed by including them in your TypedDict:

```{.python continuation}
async def multi():
    db = await get_db()
    await (
        db.update(Message)
        .set(MessageUpdate(
            content="Updated message",
            user_id=5
        ))
        .where(Eq(Message.id, 1))
    )

asyncio.run(multi())
```

This generates:

```sql
UPDATE "message" SET "content" = %(set_content_0)s, "user_id" = %(set_user_id_1)s
WHERE "message"."id" = %(p0)s
```

## Viewing the SQL

Inspect the generated query without executing it:

```{.python continuation}
async def raw_sql():
    db = await get_db()
    query = (
        db.update(Message)
        .set(MessageUpdate(content="Updated"))
        .where(Eq(Message.id, 1))
        .sql()
    )

    print(query.sql)
    # UPDATE "message" SET "content" = %(set_content_0)s
    # WHERE "message"."id" = %(p0)s

    print(query.params)
    # {'set_content_0': 'Updated', 'p0': 1}

asyncio.run(raw_sql())
```

## Next Steps

- Learn about [Where](where.md) clauses for filtering
- See how to [Delete](delete.md) data
- Explore [Select](select.md) operations
