# pudl

A Drizzly ORM for Python

## Example
Set up your schemas and selection models:
```python
# schema.py
from pudl.table import Selection, TextColumn, Table, Text

class User(Table):
    _name = "user"
    id: TextColumn = Text(primary=True)
    email: TextColumn = Text("user_email", default="text", not_null=True)

class Message(Table):
    id: TextColumn = Text()
    user_id: TextColumn = Text().fk(lambda: User.id)
    content: TextColumn = Text()

class UserSel(Selection):
    id: str = User.id()

class MessageSel(Selection):
    user_name: str = User.email()
    message: str = Message.content()
```

And query your database:
```python
# main.py
from pudl.db import Db
from pudl.where import Eq, Like, Or

from . import schema
from .schema import User, Message, UserSel, MessageSel

user_id = "a"
user = User(id=user_id, email="john@foo.com")
message = Message(id="m1", user_id=user.id, content="Hello!")

db = Db(DATABASE_URL).connect()
db.migrates(schema)

db.insert(User).values(user).execute()
db.insert(Message).values(message).execute()

users = (
    db.select(UserSel)
    .fromm(User)
    .where(Or(
        Eq(User.id.info, "a"),
        Like(User.email.info, "john%")
    ))
    .limit(2)
    .execute()
)
print(users)

messages = (
    db.select(MessageSel)
    .fromm(Message)
    .left_join(User, Eq(User.id.info, Message.user_id.info))
    .limit(2)
    .execute()
)
print(messages)
```
