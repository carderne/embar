# pudl

A Drizzly ORM for Python

## Example
```python
from pudl.db import Database
from pudl.table import Selection, TextColumn, Table, Text

@dataclass
@final
class User(Table):
    _name = "user"
    id: TextColumn = Text()
    email: TextColumn = Text("user_email", default="text", not_null=True)

user = User(id="a", email="john@foo.com")

db = Database(DATABASE_URL).connect().migrate([User])

db.insert(User).values(user).execute()

@dataclass
class UserSel(Selection):
    id: str = User.id.sel()

results = (
    db.select(UserSel)
    .fromm(User)
    .where(User.id.info, "=", "a")
    .where(User.email.info, "LIKE", "john%")
    .limit(10)
    .execute()
)
print(results)

results = (
    db.select(SelectAll)
    .fromm(User)
    .execute()
)
print(results)
```
