# pudl

A Drizzly ORM for Python

## Example
```python
from pudl.db import Database
from pudl.table import SelectAll, Selection, TextColumn, Table, Text
from pudl.where import And, Eq, Like


class User(Table):
    _name = "user"
    id: TextColumn = Text(primary=True)
    email: TextColumn = Text("user_email", default="text", not_null=True)


class Message(Table):
    id: TextColumn = Text()
    user_id: TextColumn = Text().fk(lambda: User.id.info)
    content: TextColumn = Text()


class UserSel(Selection):
    id: str = User.id.sel()


user_id = "a"
user = User(id=user_id, email="john@foo.com")
message = Message(id="1", user_id=user_id, content="Hello!")

db = Database(DATABASE_URL).connect().migrate([User, Message])

db.insert(User).values(user).execute()
db.insert(Message).values(message).execute()

users = (
    db.select(UserSel)
    .fromm(User)
    .where(And(
        Eq(User.id.info, "a"),
        Like(User.email.info, "john%")
    ))
    .limit(10)
    .execute()
)
print(users)

messages = (
    db.select(SelectAll)
    .fromm(Message)
    .limit(2)
    .execute()
)
print(messages)
```
