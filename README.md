# pudl

A Drizzly ORM for Python

## Example
Set up your schemas and selection models:
```python
# schema.py
from pudl.column import Integer, Text
from pudl.selection import Selection
from pudl.table import Table

@dataclass
class User(Table):
    _name = "user"
    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", default="text", not_null=True)

@dataclass
class Message(Table):
    id: Integer = Integer()
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()

@dataclass
class UserSel(Selection):
    id: Annotated[int, User.id]

@dataclass
class MessageSel(Selection):
    user_name: Annotated[str, User.email]
    message: Annotated[str, Message.content]
```

And query your database:
```python
# main.py
from pudl.db import Db
from pudl.where import Eq, JEq, Like, Or

from . import schema
from .schema import User, Message, UserSel, MessageSel

user = User(id=100, email="john@foo.com")
message = Message(id=1, user_id=user.id, content="Hello!")

db = Db(DATABASE_URL).connect()
db.migrates(schema)

db.insert(User).values(user).execute()
db.insert(Message).values(message).execute()

users = (
    db.select(UserSel)
    .fromm(User)
    .where(Or(
        Eq(User.id, 1),
        Like(User.email, "john%")
    ))
    .limit(2)
    .execute()
)
print(users)

messages = (
    db.select(MessageSel)
    .fromm(Message)
    .left_join(User, JEq(User.id, Message.user_id))
    .limit(2)
    .execute()
)
print(messages)
```
