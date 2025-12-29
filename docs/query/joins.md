# Joins

Joins combine data from multiple tables in a single query. Embar supports all standard SQL join types with full type safety.

## Basic Join

Use `.left_join()` to include all rows from the left table and matching rows from the right table:

```{.python fixture:postgres_container}
import asyncio
import psycopg
from typing import Annotated
from pydantic import BaseModel

from embar.column.common import Integer, Text
from embar.db.pg import AsyncPgDb
from embar.query.where import Eq
from embar.table import Table

class User(Table):
    id: Integer = Integer(primary=True)
    email: Text = Text()

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()

class UserWithEmail(BaseModel):
    id: Annotated[int, User.id]
    email: Annotated[str, User.email]

async def get_db(tables: list[Table] = None):
    if tables is None:
        tables = [User, Message]
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate(tables)
    return db

async def basic():
    db = await get_db()
    users = await (
        db.select(UserWithEmail)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
    )

asyncio.run(basic())
```

This generates:

```sql
SELECT "user"."id" AS "id", "user"."email" AS "email"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
```

The join condition uses `Eq` to match the user's ID with the message's user_id foreign key.

## Join Types

### Left Join

Returns all rows from the left table and matched rows from the right table. If there's no match, right table columns are null.

```{.python continuation}
async def left_join():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
    )

asyncio.run(left_join())
```

This generates:

```sql
SELECT "user"."id", "user"."email"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
```

### Inner Join

Returns only rows where there is a match in both tables:

```{.python continuation}
async def inner_join():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .inner_join(Message, Eq(User.id, Message.user_id))
    )

asyncio.run(inner_join())
```

This generates:

```sql
SELECT "user"."id", "user"."email"
FROM "user"
INNER JOIN "message" ON "user"."id" = "message"."user_id"
```

### Right Join

Returns all rows from the right table and matched rows from the left table:

```{.python continuation}
async def right_join():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .right_join(Message, Eq(User.id, Message.user_id))
    )

asyncio.run(right_join())
```

This generates:

```sql
SELECT "user"."id", "user"."email"
FROM "user"
RIGHT JOIN "message" ON "user"."id" = "message"."user_id"
```

### Full Join

Returns all rows from both tables, matching where possible:

```{.python continuation}
async def full_join():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .full_join(Message, Eq(User.id, Message.user_id))
    )

asyncio.run(full_join())
```

This generates:

```sql
SELECT "user"."id", "user"."email"
FROM "user"
FULL OUTER JOIN "message" ON "user"."id" = "message"."user_id"
```

### Cross Join

Returns the Cartesian product of both tables. No join condition is needed:

```{.python continuation}
async def cross_join():
    db = await get_db()
    users = await (
        db.select(User.all())
        .from_(User)
        .cross_join(Message)
    )

asyncio.run(cross_join())
```

This generates:

```sql
SELECT "user"."id", "user"."email"
FROM "user"
CROSS JOIN "message"
```

## Join Conditions

Join conditions use the same operators as where clauses. The most common is `Eq`, but you can use any comparison operator.

### Basic Equality

```{.python continuation}
from embar.query.where import Eq

async def equality():
    db = await get_db()
    await (
        db.select(User.all())
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
    )

asyncio.run(equality())
```

### Other Operators

Use any where clause operator for join conditions:

```{.python continuation}
from embar.query.where import Gt, Lt, And

async def operators():
    db = await get_db()
    # Greater than
    await (
        db.select(User.all())
        .from_(User)
        .left_join(Message, Gt(User.id, Message.user_id))
    )

    # Multiple conditions
    await (
        db.select(User.all())
        .from_(User)
        .left_join(Message, And(
            Eq(User.id, Message.user_id),
            Gt(Message.id, 100)
        ))
    )

asyncio.run(operators())
```

See [Where](where.md) for all available operators.

## Selecting Nested Data

Use `.many()` to aggregate joined rows into arrays. This requires `.group_by()` to group results by the parent table.

### Array of Values

Select an array of values from the joined table:

```{.python continuation}
class UserWithMessages(BaseModel):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]

async def arrays():
    db = await get_db()
    users = await (
        db.select(UserWithMessages)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
    )
    # [UserWithMessages(id=1, messages=["Hello!", "How are you?"])]

asyncio.run(arrays())
```

This generates:

```sql
SELECT
    "user"."id" AS "id",
    json_agg("message"."content") AS "messages"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
GROUP BY "user"."id"
```

### Array of Objects

Select full nested objects from the joined table:

```{.python continuation}
class UserWithFullMessages(BaseModel):
    id: Annotated[int, User.id]
    email: Annotated[str, User.email]
    messages: Annotated[list[Message], Message.many()]

async def objects():
    db = await get_db()
    users = await (
        db.select(UserWithFullMessages)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
    )
    # [UserWithFullMessages(
    #     id=1,
    #     email="alice@example.com",
    #     messages=[
    #         Message(id=1, user_id=1, content="Hello!"),
    #         Message(id=2, user_id=1, content="How are you?")
    #     ]
    # )]

asyncio.run(objects())
```

This generates:

```sql
SELECT
    "user"."id" AS "id",
    "user"."email" AS "email",
    json_agg(json_build_object(
        'id', "message"."id",
        'user_id', "message"."user_id",
        'content', "message"."content"
    )) AS "messages"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
GROUP BY "user"."id"
```

The `.many()` suffix tells Embar to aggregate the joined rows into a JSON array. Without `.group_by()`, you'll get separate rows for each message.

## Multiple Joins

Chain multiple join calls to join more than two tables:

```{.python continuation}
class Comment(Table):
    id: Integer = Integer(primary=True)
    message_id: Integer = Integer().fk(lambda: Message.id)
    text: Text = Text()

class UserWithData(BaseModel):
    id: Annotated[int, User.id]
    email: Annotated[str, User.email]
    messages: Annotated[list[str], Message.content.many()]
    comments: Annotated[list[str], Comment.text.many()]

async def multiple():
    db = await get_db([User, Message, Comment])
    users = await (
        db.select(UserWithData)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .left_join(Comment, Eq(Message.id, Comment.message_id))
        .group_by(User.id)
    )

asyncio.run(multiple())
```

This generates:

```sql
SELECT
    "user"."id" AS "id",
    "user"."email" AS "email",
    json_agg("message"."content") AS "messages",
    json_agg("comment"."text") AS "comments"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
LEFT JOIN "comment" ON "message"."id" = "comment"."message_id"
GROUP BY "user"."id"
```

## Joins with Where Clauses

Combine joins with where clauses to filter results:

```{.python continuation}
from embar.query.where import Like

class UserFiltered(BaseModel):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]

async def join_where():
    db = await get_db()
    users = await (
        db.select(UserFiltered)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .where(Like(User.email, "%@example.com"))
        .group_by(User.id)
    )

asyncio.run(join_where())
```

This generates:

```sql
SELECT
    "user"."id" AS "id",
    json_agg("message"."content") AS "messages"
FROM "user"
LEFT JOIN "message" ON "user"."id" = "message"."user_id"
WHERE "user"."email" LIKE %(p0)s
GROUP BY "user"."id"
```

The where clause filters the joined results before aggregation.

## Single Nested Object

Use `.one()` to select a single nested object instead of an array:

```{.python continuation}
class MessageWithUser(BaseModel):
    content: Annotated[str, Message.content]
    user: Annotated[User, User.one()]

async def nested():
    db = await get_db()
    messages = await (
        db.select(MessageWithUser)
        .from_(Message)
        .left_join(User, Eq(User.id, Message.user_id))
    )
    # [MessageWithUser(
    #     content="Hello!",
    #     user=User(id=1, email="alice@example.com")
    # )]

asyncio.run(nested())
```

This generates:

```sql
SELECT
    "message"."content" AS "content",
    json_build_object(
        'id', "user"."id",
        'email', "user"."email"
    ) AS "user"
FROM "message"
LEFT JOIN "user" ON "user"."id" = "message"."user_id"
```

Use `.one()` when the relationship is many-to-one (each message has one user). Use `.many()` when the relationship is one-to-many (each user has many messages).

## Next Steps

- Learn about [Where](where.md) clauses for join conditions and filtering
- See [Select](select.md) for more query building options
- Understand [Relations](../schemas/relations.md) for defining table relationships
