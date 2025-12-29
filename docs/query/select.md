# Select

Select operations retrieve data from your database. Embar provides a fluent interface for building SELECT queries with full type safety.

## Basic Select

Setup.
```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.column.common import Integer, Text
from embar.db.pg import AsyncPgDb
from embar.table import Table

class User(Table):
    id: Integer = Integer(primary=True)
    email: Text = Text()

async def get_db(tables: list[Table] = None):
    if tables is None:
        tables = [User]
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate(tables)
    return db
```


Select all columns from a table using `.all()`:

```{.python continuation fixture:postgres_container}
async def basic():
    db = await get_db()
    users = await db.select(User.all()).from_(User)
    # [User(id=1, email="alice@example.com"), User(id=2, email="bob@example.com")]

asyncio.run(basic())
```

This generates:

```sql
SELECT "user"."id", "user"."email" FROM "user"
```

## Selecting Specific Columns

Define a custom model to select only specific columns:

```{.python continuation}
from typing import Annotated
from pydantic import BaseModel

class UserEmail(BaseModel):
    email: Annotated[str, User.email]

async def columns():
    db = await get_db()
    users = await db.select(UserEmail).from_(User)
    # [UserEmail(email="alice@example.com"), UserEmail(email="bob@example.com")]

asyncio.run(columns())
```

This generates:

```sql
SELECT "user"."email" AS "email" FROM "user"
```

The `Annotated` type tells Embar which table column maps to each field in your result model.

## Where Clauses

Filter results with `.where()`:

```{.python continuation}
from embar.query.where import Eq

async def where():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .where(Eq(User.id, 1))
    )

asyncio.run(where())
```

This generates:

```sql
SELECT "user"."id", "user"."email" FROM "user" WHERE "user"."id" = %(p0)s
```

Where clauses can be combined with `And`, `Or`, and other operators. See [Where](where.md) for details.

## Joins

Join related tables using `.left_join()`, `.right_join()`, `.inner_join()`, `.full_join()`, or `.cross_join()`:

```{.python continuation}
from embar.query.where import Eq

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()

class UserWithMessages(BaseModel):
    id: Annotated[int, User.id]
    email: Annotated[str, User.email]

async def joins():
    db = await get_db([User, Message])
    users = await (
        db.select(UserWithMessages)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
    )

asyncio.run(joins())
```

This generates:

```sql
SELECT "user"."id" AS "id", "user"."email" AS "email"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
```

For more on joins and nested data, see [Joins](joins.md).

## Selecting Nested Arrays

Use `.many()` to select arrays of values or full nested objects:

```{.python continuation}
class UserWithMessages(BaseModel):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]

async def arrays():
    db = await get_db([User, Message])
    users = await (
        db.select(UserWithMessages)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
    )
    # [UserWithMessages(id=1, messages=["Hello!", "How are you?"])]

asyncio.run(arrays())
```

Or select full nested objects:

```{.python continuation}
class UserWithFullMessages(BaseModel):
    id: Annotated[int, User.id]
    messages: Annotated[list[Message], Message.many()]

async def nested():
    db = await get_db([User, Message])
    users = await (
        db.select(UserWithFullMessages)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
    )
    # [UserWithFullMessages(
    #     id=1,
    #     messages=[
    #         Message(id=1, user_id=1, content="Hello!"),
    #         Message(id=2, user_id=1, content="How are you?")
    #     ]
    # )]

asyncio.run(nested())
```

## Distinct

Select distinct rows using `select_distinct()`:

```{.python continuation}
async def distinct():
    db = await get_db()
    users = await db.select_distinct(User.all()).from_(User)

asyncio.run(distinct())
```

This generates:

```sql
SELECT DISTINCT "user"."id", "user"."email" FROM "user"
```

## Group By

Group results with `.group_by()`:

```{.python continuation}
class UserMessageCount(BaseModel):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]

async def group_by():
    db = await get_db([User, Message])
    users = await (
        db.select(UserMessageCount)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
    )

asyncio.run(group_by())
```

This generates:

```sql
SELECT "user"."id" AS "id", json_agg("message"."content") AS "messages"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
GROUP BY "user"."id"
```

## Having

Filter grouped results with `.having()`:

```{.python continuation}
from embar.query.where import Gt
from embar.sql import Sql

class UserWithCount(BaseModel):
    id: Annotated[int, User.id]
    message_count: Annotated[int, Sql(t"COUNT({Message.id})")]

async def having():
    db = await get_db([User, Message])
    users = await (
        db.select(UserWithCount)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
        .having(Gt(User.id, 2))
    )

asyncio.run(having())
```

This generates:

```sql
SELECT "user"."id" AS "id", COUNT("message"."id") AS "message_count"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
GROUP BY "user"."id"
HAVING COUNT("message"."id") > %(p0)s
```

The `HAVING` clause filters groups after aggregation, while `WHERE` filters rows before grouping.

## Order By

Sort results with `.order_by()`:

```{.python continuation}
from embar.query.order_by import Asc, Desc

async def order_by():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .order_by(Desc(User.id))
    )

asyncio.run(order_by())
```

This generates:

```sql
SELECT "user"."id", "user"."email" FROM "user" ORDER BY "user"."id" DESC
```

You can order by multiple columns:

```{.python continuation}
async def order_multi():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .order_by(Asc(User.email), Desc(User.id))
    )

asyncio.run(order_multi())
```

Control null ordering:

```{.python continuation}
async def nulls():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .order_by(Asc(User.email, nulls="last"))
    )

asyncio.run(nulls())
```

This generates:

```sql
SELECT "user"."id", "user"."email" FROM "user" ORDER BY "user"."email" ASC NULLS LAST
```

## Limit and Offset

Paginate results with `.limit()` and `.offset()`:

```{.python continuation}
async def limit():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .limit(10)
        .offset(20)
    )

asyncio.run(limit())
```

This generates:

```sql
SELECT "user"."id", "user"."email" FROM "user" LIMIT 10 OFFSET 20
```

## Aggregations

Use raw SQL for aggregations:

```{.python continuation}
from embar.sql import Sql

class UserStats(BaseModel):
    total: Annotated[int, Sql(t"COUNT(*)::int")]
    avg_id: Annotated[float | None, Sql(t"AVG({User.id})::float")]

async def aggregation():
    db = await get_db()
    stats = await db.select(UserStats).from_(User)
    # [UserStats(total=100, avg_id=50.5)]

asyncio.run(aggregation())
```

Common aggregations include `COUNT()`, `SUM()`, `AVG()`, `MIN()`, and `MAX()`.

## Viewing the SQL

Inspect the generated query without executing it:

```{.python continuation}
async def raw_sql():
    db = await get_db()
    query = (
        db.select(User.all())
        .from_(User)
        .where(Eq(User.id, 1))
        .sql()
    )

    print(query.sql)
    # SELECT "user"."id", "user"."email" FROM "user" WHERE "user"."id" = %(p0)s

    print(query.params)
    # {'p0': 1}

asyncio.run(raw_sql())
```

## Next Steps

- Learn about [Where](where.md) clauses for filtering
- Explore [Joins](joins.md) for working with related tables
- See how to [Insert](insert.md) data
