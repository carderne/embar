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

Embar is a new ORM for Python, designed for simple SQL-esque queries and well-typed queries and results.

There seems to be a gap in the Python ORM market.
- [SQLAlchemy](https://www.sqlalchemy.org/) (and, by extension, [SQLModel](https://sqlmodel.tiangolo.com/)) is too complicated.
- [PonyORM](https://docs.ponyorm.org/) has no types
- Same for [PugSQL](https://pugsql.org/)
- [TortoiseORM](https://github.com/tortoise/tortoise-orm) is probably appealing if you like [Django](https://www.djangoproject.com/)/[ActiveRecord](https://en.wikipedia.org/wiki/Active_record_pattern)
- [Piccolo](https://github.com/piccolo-orm/piccolo) looks interesting...
- [ormar](https://github.com/collerek/ormar) too...

Embar is inspired by [Drizzle](https://orm.drizzle.team/).

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
```python continuation
# main.py
import sqlite3
from embar.db.sqlite import Db as SqliteDb

conn = sqlite3.connect(":memory:")
db = SqliteDb(conn)
db.migrate([User, Message])
```

### Insert some data
```python continuation
user = User(id=1, email="foo@bar.com")
message = Message(id=1, user_id=user.id, content="Hello!")

db.insert(User).value(user).run()
db.insert(Message).value(message).run()
```

### Query some data
With join, where and group by.
```python continuation
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
```python continuation
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
