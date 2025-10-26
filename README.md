# pudl

A Drizzly ORM for Python

## Example
Set up your database schema:
```python
# schema.py
from dataclasses import dataclass
from typing import final

from pudl.column import Integer, Text
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
```python
# main.py
from pudl.db import Db

from . import schema
from .schema import User, Message

db = Db(DATABASE_URL).connect()
db.migrates(schema)
user_id = random.randint(0, 100)
user = User(id=user_id, email="john@foo.com")
message = Message(id=1, user_id=user.id, content="Hello!")

db.insert(User).value(user).execute()
db.insert(Message).value(message).execute()
```

Now you're ready to query some data!
```python
@dataclass
class UserSel(Selection):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]


users = (
    db.select(UserSel)
    .fromm(User)
    .left_join(Message, JEq(User.id, Message.user_id))
    .where(Or(
        Eq(User.id, 1),
        Like(User.email, "john%")
    ))
    .group_by(User.id)
    .execute()
)
# [ UserSel(id=0, messages=['Hello!']) ]
```

And what about a fully nested object and some SQL templating:
```python
@dataclass
class UserHydrated(Selection):
    email: Annotated[str, User.email]
    messages: Annotated[list[Message], Message.many()]
    date: Annotated[datetime, sql(t"now()")]


users = (
    db.select(UserFullMessages)
    .fromm(User)
    .left_join(Message, JEq(User.id, Message.user_id))
    .group_by(User.id)
    .limit(2)
    .execute()
)
# [UserHydrated(
#      email='john@foo.com',
#      messages=[Message(content='Hello!', id=1, user_id=0)],
#      date: datetime(2025, 10, 26, ...)
# )]
```
