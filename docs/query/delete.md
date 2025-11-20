# Delete

Delete operations remove rows from your database. Embar provides a straightforward interface for deleting data with optional result retrieval.

## Basic Delete

To delete rows, use `.delete()` with a `.where()` clause to specify which rows to remove:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.column.common import Integer, Text
from embar.db.pg import AsyncPgDb
from embar.query.where import Eq
from embar.table import Table

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer()
    content: Text = Text()

async def get_db():
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate([Message])
    return db

async def basic():
    db = await get_db()
    await db.delete(Message).where(Eq(Message.id, 1))

asyncio.run(basic())
```

This generates:

```sql
DELETE FROM "message"
WHERE "message"."id" = %(p0)s
```

With parameters: `{'p0': 1}`

## Returning Deleted Data

Use `.returning()` to get back the deleted rows. This is useful when you need to know what was removed or to perform cleanup actions:

```{.python continuation}
async def returning():
    db = await get_db()
    message = Message(id=1, user_id=2, content="foo")
    await db.insert(Message).values(message)
    deleted = await db.delete(Message).where(Eq(Message.id, 1)).returning()

    # deleted is a list of Message instances
    assert deleted[0].id == message.id
    assert deleted[0].content == message.content

asyncio.run(returning())
```

This generates:

```sql
DELETE FROM "message"
WHERE "message"."id" = %(p0)s
RETURNING *
```

The `RETURNING *` clause tells the database to return all columns of the deleted rows.

## Where Clauses

The `.where()` method specifies which rows to delete. You can use simple conditions or combine multiple criteria:

```{.python continuation}
from embar.query.where import Eq, Gt, And, Or

async def where():
    db = await get_db()
    # Delete a specific row
    await db.delete(Message).where(Eq(Message.id, 1))

    # Delete multiple rows matching a condition
    await db.delete(Message).where(Gt(Message.id, 100))

    # Delete with multiple conditions
    await db.delete(Message).where(And(
        Eq(Message.user_id, 5),
        Gt(Message.id, 10)
    ))

    # Delete with OR logic
    await db.delete(Message).where(Or(
        Eq(Message.user_id, 5),
        Eq(Message.user_id, 10)
    ))

asyncio.run(where())
```

For more on where clauses, see [Where](where.md).

## Deleting Without Where

!!! warning
    Deleting without a where clause removes **all rows** from the table. Use with extreme caution.

```{.python continuation}
async def no_where():
    db = await get_db()

    # This deletes every row in the table
    await db.delete(Message)

asyncio.run(no_where())
```

This generates:

```sql
DELETE FROM "message"
```

Always double-check before running delete operations without where clauses. Consider using `.returning()` to see what will be deleted:

```{.python continuation}
# See what would be deleted
async def verify():
    db = await get_db()
    query = db.delete(Message).sql()
    print(query.sql)

    # Or return the deleted data to verify
    deleted = await db.delete(Message).where(Gt(Message.id, 100)).returning()
    print(f"Deleted {len(deleted)} rows")

asyncio.run(verify())
```

## Viewing the SQL

Inspect the generated query without executing it:

```{.python continuation}
async def view_sql():
    db = await get_db()
    query = db.delete(Message).where(Eq(Message.id, 1)).sql()

    print(query.sql)
    # DELETE FROM "message"
    # WHERE "message"."id" = %(p0)s

    print(query.params)
    # {'p0': 1}

asyncio.run(view_sql())
```

## Next Steps

- Learn about [Where](where.md) clauses for filtering
- See how to [Update](update.md) data
- Explore [Insert](insert.md) operations
