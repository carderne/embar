# Without Pydantic

Pydantic is an optional dependency. If you don't need validation or coercion,
you can skip it entirely — embar will load query results into plain Python
objects instead.

Install without pydantic:

```bash
uv add embar
```

Install with pydantic:

```bash
uv add "embar[pydantic]"
```

## Define your schema

Table definitions are identical regardless of whether pydantic is installed.

```python
import sqlite3
from typing import Annotated

from embar.column.common import Integer, Text, integer, text
from embar.config import EmbarConfig
from embar.db.sqlite import SqliteDb
from embar.table import Table


class User(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="users")
    id: Integer = integer(primary=True)
    email: Text = text("user_email", not_null=True)


class Message(Table):
    id: Integer = integer()
    user_id: Integer = integer(fk=lambda: User.id)
    content: Text = text()


conn = sqlite3.connect(":memory:")
db = SqliteDb(conn)
db.migrate([User, Message]).run()
```

## Insert and select all columns

Pass `use_pydantic=False` to get plain dataclass objects back with no validation.
`Table.all()` defaults to `use_pydantic=True`; opt out explicitly:

```{.python continuation}
user = User(id=1, email="alice@example.com")
message = Message(id=1, user_id=1, content="Hello!")
db.insert(User).values(user).run()
db.insert(Message).values(message).run()

results = db.select(User.all(use_pydantic=False)).from_(User).run()
assert results[0].id == 1
assert results[0].email == "alice@example.com"
```

## Query with a plain model class

Define a plain class with `Annotated` fields — no `BaseModel` required.
embar reads the annotations to build the SQL and to load results:

```{.python continuation}
from embar.query.where import Eq


class UserSel:
    id: Annotated[int, User.id]
    email: Annotated[str, User.email]


results = db.select(UserSel).from_(User).where(Eq(User.id, 1)).run()
assert results[0].email == "alice@example.com"
```

## Nested results

Nested tables work the same way — the plain loader parses the JSON
produced by the DB and builds the nested objects recursively:

```{.python continuation}
class UserWithMessages:
    id: Annotated[int, User.id]
    messages: Annotated[list[Message], Message.many()]


results = (
    db.select(UserWithMessages)
    .from_(User)
    .left_join(Message, Eq(User.id, Message.user_id))
    .group_by(User.id)
    .run()
)
assert results[0].messages[0].content == "Hello!"
```

## Insert with returning

`.returning()` also accepts `use_pydantic=False`.
This example uses a table with no custom column names so the returned fields map directly:

```{.python continuation}
class Tag(Table):
    id: Integer = integer(primary=True)
    name: Text = text()


db.migrate([Tag]).run()

tag = Tag(id=1, name="python")
inserted = db.insert(Tag).values(tag).returning(use_pydantic=False).run()
assert inserted[0].name == "python"
```

## What you give up

Without pydantic:

- No type coercion — values are stored as-is from the database driver.
- No field validators or `BeforeValidator` transforms.
- No `ValidationError` on bad data — invalid values pass through silently.

If you need any of these, install `embar[pydantic]` and use the default
`use_pydantic=True` (or omit the argument entirely).
