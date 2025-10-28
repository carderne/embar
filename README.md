# Pudl

<div align="center">
  <img src="https://raw.githubusercontent.com/carderne/pudl/refs/heads/main/docs/assets/logo.svg?token=GHSAT0AAAAAACLGWZ4ZYBJDLTZCWPWHOY4A2IA4ARA" alt="Pudl logo" width="100" role="img">
  <p>A Python ORM with types</p>
</div>

----

<div align="center">
<a href="https://github.com/carderne/pudl">
<img alt="GitHub badge" src="https://img.shields.io/badge/Github-Pudl-blue?logo=github">
</a>
</div>

Pudl is a new ORM for Python, designed for simple SQL-esque queries and well-typed queries and results.

There seems to be a gap in the Python ORM market.
- [SQLAlchemy](https://www.sqlalchemy.org/) (and, by extension, [SQLModel](https://sqlmodel.tiangolo.com/)) is too complicated.
- [PonyORM](https://docs.ponyorm.org/) has no types
- Same for [PugSQL](https://pugsql.org/)
- [TortoiseORM](https://github.com/tortoise/tortoise-orm) is probably appealing if you like [Django](https://www.djangoproject.com/)/[ActiveRecord](https://en.wikipedia.org/wiki/Active_record_pattern)
- [Piccolo](https://github.com/piccolo-orm/piccolo) looks interesting...
- [ormar](https://github.com/collerek/ormar) too...

Pudl is inspired by [Drizzle](https://orm.drizzle.team/).

## Quickstart
Install:
```bash
uv add pudl  # TODO not published to PyPI yet!
```

Set up your database models:
```python
# schema.py
from dataclasses import dataclass
from typing import final
from pudl.column.common import Integer, Text
from pudl.table import Table

@dataclass
@final
class User(Table):
    _name = "user"
    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", default="text", not_null=True)

@dataclass
@final
class Message(Table):
    id: Integer = Integer()
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()
```

Then create a database client, apply migrations and insert some data:
```python continuation
# main.py
import sqlite3
from pudl.db.sqlite import Db as SqliteDb

conn = sqlite3.connect(":memory:")
db = SqliteDb(conn)
db.migrate([User, Message])
user = User(id=1, email="foo@bar.com")
message = Message(id=1, user_id=user.id, content="Hello!")

db.insert(User).value(user).execute()
db.insert(Message).value(message).execute()
```

Now you're ready to query some data!
```python continuation
from typing import Annotated
from pudl.query.selection import Selection
from pudl.query.where import Eq, Like, Or

@dataclass
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
    .execute()
)
# [ UserSel(id=1, messages=['Hello!']) ]
```

And what about a fully nested object and some SQL templating:
```python continuation
from datetime import datetime
from pudl.sql import Sql

@dataclass
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
    .execute()
)
# [UserHydrated(
#      email='foo@bar.com',
#      messages=[Message(content='Hello!', id=1, user_id=1)],
#      date: datetime(2025, 10, 26, ...)
# )]
```

## Contributing
Install [uv](https://docs.astral.sh/uv/getting-started/installation/).

Then:
```bash
uv sync
```

This project uses [poethepoet](https://poethepoet.natn.io/index.html) for tasks/scripts.

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
