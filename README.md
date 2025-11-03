# Embar

<div align="center">
  <img src="https://github.com/user-attachments/assets/b8146626-3e64-424d-bb34-374d63a75d5b" alt="Embar logo" width="70" role="img">
  <p>A Python ORM with types</p>
</div>

----

<div align="center">
<a href="https://github.com/carderne/embar">
<img alt="GitHub badge" src="https://img.shields.io/badge/Github-Embar-blue?logo=github">
</a>
</div>

Embar is a new ORM for Python with the following goals:
- Type safety: your type checker should know what arguments are valid, and what is being returned from any call.
- Type hints: your LSP should be able to guide you towards the query you want to write.
- SQL-esque: you should be able to write queries simply by knowing SQL and your data model.
- You should be able to actually just write SQL when you need to.

These are mostly inspired by [Drizzle](https://orm.drizzle.team/).
The Python ecosystem deserves something with similar DX.

Embar supports three database clients:

- SQLite 3 via the Python standard library
- Postgres via psycopg3
- Postgres via async psycopg3

The async psycopg3 client is recommended. The others are provided mostly for testing and experimenting locally.

**Embar uses [Template strings](https://docs.python.org/3.14/library/string.templatelib.html#template-strings) and so only supports Python 3.14.**

**Embar is pre-alpha and ready for experimentation but not production use.**

**Documentation: [embar.rdrn.me](https://embar.rdrn.me)**


## Quickstart

### Install

```bash
uv add embar
```

### Set up database models

```python
# schema.py
from embar.column.common import Integer, Text
from embar.config import TableConfig
from embar.table import Table

class User(Table):
    embar_config = TableConfig(table_name="users")

    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", default="text", not_null=True)

class Message(Table):
    id: Integer = Integer()
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()
```

### Create client and apply migrations

```{.python continuation}
# main.py
import sqlite3
from embar.db.sqlite import Db as SqliteDb

conn = sqlite3.connect(":memory:")
db = SqliteDb(conn)
db.migrate([User, Message])
```

### Insert some data

```{.python continuation}
user = User(id=1, email="foo@bar.com")
message = Message(id=1, user_id=user.id, content="Hello!")

db.insert(User).values(user).run()
db.insert(Message).values(message).run()
```

### Query some data

With join, where and group by.

```{.python continuation}
from typing import Annotated
from embar.query.selection import Selection
from embar.query.where import Eq, Like, Or

class UserSel(Selection):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]

users = (
    db.select(UserSel)
    .fromm(User)
    .left_join(Message, Eq(User.id, Message.user_id))
    .where(Or(
        Eq(User.id, 1),
        Like(User.email, "foo%")
    ))
    .group_by(User.id)
    .run()
)
# [ UserSel(id=1, messages=['Hello!']) ]
```

### Query some more data

This time with fully nested child tables, and some raw SQL.

```{.python continuation}
from datetime import datetime
from embar.sql import Sql

class UserHydrated(Selection):
    email: Annotated[str, User.email]
    messages: Annotated[list[Message], Message.many()]
    date: Annotated[datetime, Sql(t"CURRENT_TIMESTAMP")]

users = (
    db.select(UserHydrated)
    .fromm(User)
    .left_join(Message, Eq(User.id, Message.user_id))
    .group_by(User.id)
    .limit(2)
    .run()
)
# [UserHydrated(
#      email='foo@bar.com',
#      messages=[Message(content='Hello!', id=1, user_id=1)],
#      date: datetime(2025, 10, 26, ...)
# )]
```

### See the SQL

Every query produces exactly one... query.
And you can always see what's happening under the hood with the `.sql()` method:

```{.python continuation}
users_query = (
    db.select(UserHydrated)
    .fromm(User)
    .left_join(Message, Eq(User.id, Message.user_id))
    .group_by(User.id)
    .sql()
)
users_query.sql
# SELECT 
#     "users"."user_email" AS "email",
#     json_group_array(json_object(
#         'id', "message"."id",
#         'user_id', "message"."user_id",
#         'content', "message"."content"
#     )) AS "messages",
#     CURRENT_TIMESTAMP AS "date"
# FROM "users"
# LEFT JOIN "message" ON "users"."id" = "message"."user_id"
# GROUP BY "users"."id"
```

### Update a row

Unfortunately this requires another model to be defined, as Python doesn't have a `Partial[]` type.

```{.python continuation}
from typing import TypedDict

class MessageUpdate(TypedDict, total=False):
    id: int
    user_id: int
    content: str

(
    db.update(Message)
    .set(MessageUpdate(content="Goodbye"))
    .where(Eq(Message.id, 1))
    .run()
)
```

### Add indexes

```{.python continuation}
from embar.constraint import Index

class Message(Table):
    embar_config: TableConfig = TableConfig(
        constraints=[Index("message_idx").on(lambda: Message.user_id)]
    )
    user_id: Integer = Integer().fk(lambda: User.id)
```

### Run raw SQL

```{.python continuation}
db.sql(t"DELETE FROM {Message}").run()
```

Or with a return:

```{.python continuation}
class UserId(Selection):
    id: Annotated[int, int]

res = (
    db.sql(t"SELECT * FROM {User}")
    .model(UserId)
    .run()
)
# [UserId(id=1)]
```

## Contributing

Install [uv](https://docs.astral.sh/uv/getting-started/installation/).

Then:

```bash
uv sync
```

This project uses [poethepoet](https://poethepoet.natn.io/index.html) for tasks/scripts.

You'll need Docker installed to run tests.

Format, lint, type-check, test:

```bash
uv run poe fmt
           lint
           check
           test

# or
uv run poe all
```

Or do this:

```bash
# Run this or put it in .zshrc/.bashrc/etc
alias poe="uv run poe"

# Then you can just:
poe test
```

## Other ORMs to consider

There seems to be a gap in the Python ORM market.
- [SQLAlchemy](https://www.sqlalchemy.org/) (and, by extension, [SQLModel](https://sqlmodel.tiangolo.com/)) is probably great if you're familiar with it, but too complicated for people who don't live in it
- [PonyORM](https://docs.ponyorm.org/) has no types
- [PugSQL](https://pugsql.org/) has no types
- [TortoiseORM](https://github.com/tortoise/tortoise-orm) is probably appealing if you like [Django](https://www.djangoproject.com/)/[ActiveRecord](https://en.wikipedia.org/wiki/Active_record_pattern)
- [Piccolo](https://github.com/piccolo-orm/piccolo) is cool but not very type-safe (functions accept Any, return dicts)
- [ormar](https://github.com/collerek/ormar) is not very type-safe and still based on SQLAlchemy
