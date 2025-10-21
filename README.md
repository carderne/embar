# pudl

A Drizzly ORM for Python

## Example
```python
from pudl.db import Database
from pudl.table import TextColumn, table_config, Table, Text

@table_config("user")
@dataclass
class User(Table):
    id: TextColumn = Text()
    email: TextColumn = Text("user_email", default="text", not_null=True)

user = User(id="a", email="john@foo.com")

db = Database(DATABASE_URL).connect().migrate(User)

db.insert(User).values(user).execute()

results = (
    db.select(User)
    .where(User.id.info, "=", "a")
    .where(User.email.info, "LIKE", "john%")
    .limit(10)
    .execute()
)

print(results)
```
