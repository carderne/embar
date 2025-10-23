# pudl

A Drizzly ORM for Python

## Example
```python
from pudl.db import Database
from pudl.table import Selection, TextColumn, Table, Text
from pudl.where import Eq, Like, Or

# Table schemas
class User(Table):
    _name = "user"
    id: TextColumn = Text(primary=True)
    email: TextColumn = Text("user_email", default="text", not_null=True)


class Message(Table):
    id: TextColumn = Text()
    user_id: TextColumn = Text().fk(lambda: User.id.info)
    content: TextColumn = Text()

# DB connection
db = Database(DATABASE_URL).connect().migrate([User, Message])

# Insert some data
user = User(id="a", email="john@foo.com")
message = Message(id="m1", user_id=user.id, content="Hello!")

db.insert(User).values(user).execute()
db.insert(Message).values(message).execute()

# Select users with condition
class UserSel(Selection):
    id: str = User.id.sel
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

# Select messages with a join
class MessageSel(Selection):
    user_name: str = User.email.sel
    message: str = Message.content.sel
messages = (
    db.select(MessageSel)
    .fromm(Message)
    .left_join(User, Eq(User.id.info, Message.user_id.info))
    .limit(2)
    .execute()
)
print(messages)
```
