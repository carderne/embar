# Raw SQL

Sometimes you need to write raw SQL. Embar provides template strings for safe SQL interpolation while maintaining type safety.

## Template Strings

Use Python's template strings with the `t` prefix to write raw SQL:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.column.common import Integer, Text
from embar.db.pg import AsyncPgDb
from embar.table import Table

class User(Table):
    id: Integer = Integer(primary=True)
    status: Text = Text()
    email: Text = Text()

async def get_db(tables: list[Table] = None):
    if tables is None:
        tables = [User]
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate(tables)
    return db

async def example():
    db = await get_db()
    await db.sql(t"DELETE FROM {User}")

asyncio.run(example())
```

This generates:

```sql
DELETE FROM "user"
```

The `{User}` interpolation is replaced with the properly quoted table name.

Table names are automatically escaped and quoted according to your database dialect.


## Column Name Interpolation

Reference columns directly in your raw SQL:

```{.python continuation}
async def col():
    db = await get_db()
    await db.sql(t"SELECT {User.email} FROM {User}")

asyncio.run(col())
```

This generates:

```sql
SELECT "user"."email" FROM "user"
```

Both the table and column are properly escaped and quoted.

## Queries Without Return Values

Use `db.sql()` for queries that don't return data:

```{.python continuation}
async def noreturn():
    db = await get_db()
    # Delete
    await db.sql(t"DELETE FROM {User} WHERE id > 100")

    # Update
    await db.sql(t"UPDATE {User} SET {User.status} = 'inactive' WHERE {User.email} LIKE 'foo.com'")

    # Truncate
    await db.sql(t"TRUNCATE TABLE {User} CASCADE")

asyncio.run(noreturn())
```

## Queries That Return Data

Use `.model()` to specify a return type for queries that fetch data:

```{.python continuation}
from typing import Annotated
from pydantic import BaseModel

class UserId(BaseModel):
    id: Annotated[int, int]

async def returning():
    db = await get_db()

    users = await db.sql(t"SELECT id FROM {User} WHERE email LIKE '%@gmail.com'").model(UserId)
    # [UserId(id=1), UserId(id=2), UserId(id=3)]

asyncio.run(returning())
```

This generates:

```sql
SELECT id FROM "user" WHERE email LIKE '%@gmail.com'
```

The returned data is parsed into the model you provide.

## Complex Return Types

Models can have multiple fields:

```{.python continuation}
class UserEmail(BaseModel):
    id: Annotated[int, int]
    email: Annotated[str, str]

async def complex():
    db = await get_db()
    users = await db.sql(t"SELECT id, email FROM {User} ORDER BY id DESC LIMIT 10").model(UserEmail)

asyncio.run(complex())
```

Or even nested types:

```{.python continuation}
from datetime import datetime

class MessageWithUser(BaseModel):
    content: Annotated[str, str]
    user_email: Annotated[str, str]
    created_at: Annotated[datetime, datetime]

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()

async def nested():
    db = await get_db([User, Message])
    messages = await (
        db.sql(t"""
            SELECT m.content, u.email as user_email, CURRENT_TIMESTAMP as created_at
            FROM {Message} m
            JOIN {User} u ON m.user_id = u.id
            WHERE m.content LIKE '%important%'
        """)
        .model(MessageWithUser)
    )

asyncio.run(nested())
```

## Raw SQL in Select Queries

Use the `Sql()` class to include raw SQL within select queries:

```{.python continuation}
from embar.sql import Sql
from embar.query.where import Eq

class UserWithCount(BaseModel):
    id: Annotated[int, User.id]
    email: Annotated[str, User.email]
    message_count: Annotated[int, Sql(t"COUNT({Message.id})")]

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()

async def select():
    db = await get_db([User, Message])
    users = await (
        db.select(UserWithCount)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
    )

asyncio.run(select())
```

This generates:

```sql
SELECT
    "user"."id" AS "id",
    "user"."email" AS "email",
    COUNT("message"."id") AS "message_count"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
GROUP BY "user"."id"
```

The raw SQL is inserted directly into the SELECT clause.

## Database-Specific Functions

Use raw SQL for database-specific functionality:

```{.python continuation}
class UserWithTimestamp(BaseModel):
    email: Annotated[str, User.email]
    now: Annotated[datetime, Sql(t"CURRENT_TIMESTAMP")]

async def timestamp():
    db = await get_db()
    users = await db.select(UserWithTimestamp).from_(User)

asyncio.run(timestamp())
```

Or for Postgres-specific features:

```{.python continuation}
# JSON operations
class UserWithJsonField(BaseModel):
    email: Annotated[str, User.email]
    metadata: Annotated[dict, Sql(t"jsonb_build_object('status', 'active')")]

# Array aggregation
class UserWithTags(BaseModel):
    email: Annotated[str, User.email]
    tags: Annotated[list[str], Sql(t"array_agg({Tag.name})")]
```

## Mixing Raw SQL with Query Builders

Combine raw SQL with query builders for complex scenarios:

```{.python continuation}
from embar.query.where import Gt

class UserStats(BaseModel):
    id: Annotated[int, User.id]
    email: Annotated[str, User.email]
    score: Annotated[float, Sql(t"RANDOM() * 100")]

async def mix():
    db = await get_db()
    users = await (
        db.select(UserStats)
        .from_(User)
        .where(Gt(User.id, 10))
        .limit(5)
    )

asyncio.run(mix())
```

This lets you use raw SQL where needed while maintaining type safety and parameterization for the rest of the query.

## Viewing the SQL

Inspect raw SQL queries before execution:

```{.python continuation}
async def raw_sql():
    db = await get_db()
    query = db.sql(t"DELETE FROM {User} WHERE id > 100").sql()

    print(query)
    # DELETE FROM "user" WHERE id > 100

asyncio.run(raw_sql())
```

For queries with models:

```{.python continuation}
async def with_models():
    db = await get_db()
    query = (
        db.sql(t"SELECT id, email FROM {User} WHERE id < 10")
        .model(UserEmail)
        .sql()
    )

    print(query)
    # SELECT id, email FROM "user" WHERE id < 10

asyncio.run(with_models())
```

## Next Steps

- See how to build complex queries with [Select](select.md)
- Learn about parameterized filtering with [Where](where.md)
- Explore type-safe [Joins](joins.md)
