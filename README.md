# Embar

<div align="center">
  <img src="https://github.com/user-attachments/assets/b8146626-3e64-424d-bb34-374d63a75d5b" alt="Embar logo" width="70" role="img">
  <p>A Python ORM with types</p>
</div>

----

<div align="center">
<a href="https://github.com/carderne/embar">
<img alt="GitHub badge" src="https://img.shields.io/badge/Github-Embar-blue?logo=github">
<img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/carderne/9a3090c00e2e164bd197c5853245a7b1/raw/coverage.json" alt="Coverage">
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
- Postgres via [psycopg3](https://www.psycopg.org/psycopg3/docs/index.html)
- Postgres via [async psycopg3](https://www.psycopg.org/psycopg3/docs/advanced/async.html)

The async psycopg3 client is recommended. The others are provided mostly for testing and experimenting locally.

**Embar uses [Template strings](https://docs.python.org/3.14/library/string.templatelib.html#template-strings) and so only supports Python 3.14.**

**Embar is pre-alpha and ready for experimentation but not production use.**

**Documentation: [embar.rdrn.me](https://embar.rdrn.me)**

## Roadmap
- Improve the story around updates. Requires codegen.
- Create a drizzle-style `db.query.users.findMany({ where: ... })` alternative syntax. Requires codegen.
- Create a migration diffing engine.

## Quickstart

The quickstart uses the non-async sqlite client to make an easy example.

If you want to see a fully worked Postgres example, check out the [Postgres Quickstart](https://embar.rdrn.me/postgres-quickstart).

### Install

```bash
uv add embar
```

### Set up database models

```python
# schema.py
from embar.column.common import Integer, Text
from embar.config import EmbarConfig
from embar.table import Table

class User(Table):
    # If you don't provide a table name, it is generated from your class name
    embar_config: EmbarConfig = EmbarConfig(table_name="users")

    id: Integer = Integer(primary=True)
    # Columns will also generate their own name if not provided
    email: Text = Text("user_email", default="text", not_null=True)

class Message(Table):
    id: Integer = Integer()
    # Foreign key constraints are easy to add
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()
```

### Create client and apply migrations

In production, you would (probably) use the `embar` CLI to generate and run migrations.
This example uses the utility function to do it all in code.

```python continuation
# main.py
import sqlite3
from embar.db.sqlite import SqliteDb

conn = sqlite3.connect(":memory:")
db = SqliteDb(conn)
db.migrate([User, Message]).run()
```

### Insert some data

```python continuation
user = User(id=1, email="foo@bar.com")
message = Message(id=1, user_id=user.id, content="Hello!")

db.insert(User).values(user).run()

# you can return your inserted data if you want
msg_inserted = db.insert(Message).values(message).returning().run()
assert msg_inserted[0].content == message.content
```

### Query some data

With join, where and group by.

```python continuation
from typing import Annotated
from pydantic import BaseModel
from embar.query.where import Eq, Like, Or

class UserSel(BaseModel):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]

users = (
    db.select(UserSel)
    .from_(User)
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

```python continuation
from datetime import datetime
from embar.sql import Sql

class UserHydrated(BaseModel):
    email: Annotated[str, User.email]
    messages: Annotated[list[Message], Message.many()]
    date: Annotated[datetime, Sql(t"CURRENT_TIMESTAMP")]

users = (
    db.select(UserHydrated)
    .from_(User)
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

```python continuation
users_query = (
    db.select(UserHydrated)
    .from_(User)
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

```python continuation
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

### Delete some rows

And return the deleted data if you like.

```python continuation
deleted = db.delete(Message).returning().run()
assert len(deleted) == 1
```

### Add indexes

```python continuation
from embar.constraint import Index

class MessageIndexed(Table):
    embar_config: EmbarConfig = EmbarConfig(
        constraints=[Index("message_idx").on(lambda: MessageIndexed.user_id)]
    )
    user_id: Integer = Integer().fk(lambda: User.id)
```

### Run raw SQL

```python continuation
db.sql(t"DELETE FROM {Message}").run()
```

Or with a return:

```python continuation
class UserId(BaseModel):
    id: Annotated[int, int]

res = (
    db.sql(t"SELECT * FROM {User}")
    .model(UserId)
    .run()
)
# [UserId(id=1)]
```

## Migrations

Properly diffing migrations is not supported yet, but it's in the pipeline.

In the meantime, you have two options:

### Embar CLI (work in progress)

This uses which uses an LLM (and your `ANTHROPIC_API_KEY`) to generate vibe-diffs.
You should inspect these before running them.

You can see a working example at [example/](https://github.com/carderne/embar/tree/main/example).

First create a config file `embar.toml` in your app root:

```toml
dialect = "postgresql"
db_url = "postgresql://pg:pw@localhost:3601/db"
schema_path = "app.schema"
migrations_dir = "migrations"  # optional
```

#### Simple DDL output
If you just want to output the current schema as SQL (DDL), run:
```bash
embar schema
```

#### Migration files
Then to generate migrations, run the following and follow the prompts:

```bash
embar migrate
```

#### Push changes
Or to push directly to your db, run the following.
You will be prompted before each change.

```bash
embar push
```

### Or use an external schema management tool
Use the `migrate()` method shown in the quickstart to dump the current DDL to a `.sql` file.

Then use a schema management tool to manage updates.
Some options are:

- [Atlas](https://github.com/ariga/atlas)
- [sqldef](https://github.com/sqldef/sqldef)
- [sqitch](https://sqitch.org/)


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
