# Relations

Foreign keys define relationships between tables. In Embar, you create foreign keys using the `.fk()` method on any column type.

## Basic Foreign Key

Use the `.fk()` method to reference a column in another table:

```{.python continuation}
from embar.column.common import Integer, Text
from embar.table import Table

class User(Table):
    id: Integer = Integer(primary=True)
    email: Text = Text()

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()
```

The lambda syntax (`lambda: User.id`) is required because `User` might not be defined yet when Python evaluates the `Message` class body.

This generates:

```sql
"user_id" INTEGER REFERENCES "user"("id")
```

## On Delete Behavior

You can specify what happens when the referenced row is deleted using the `on_delete` parameter:

```{.python continuation}
class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(
        lambda: User.id,
        on_delete="cascade"
    )
    content: Text = Text()
```

### Available Options

The `on_delete` parameter accepts these string literals:

- `"cascade"`: Delete this row when the referenced row is deleted
- `"set null"`: Set this column to NULL when the referenced row is deleted
- `"restrict"`: Prevent deletion of the referenced row if this row exists
- `"no action"`: Same as restrict (default SQL behavior)
- `"set default"`: Set this column to its default value when the referenced row is deleted

### Cascade Example

When a user is deleted, all their messages are deleted:

```{.python continuation}
class Message(Table):
    user_id: Integer = Integer().fk(
        lambda: User.id,
        on_delete="cascade"
    )
```

Generates:

```sql
"user_id" INTEGER REFERENCES "user"("id") ON DELETE cascade
```

### Set Null Example

When a user is deleted, the foreign key is set to NULL:

```{.python continuation}
class Message(Table):
    user_id: Integer = Integer().fk(
        lambda: User.id,
        on_delete="set null"
    )
```

Make sure the column allows NULL values (don't use `not_null=True`).

Generates:

```sql
"user_id" INTEGER REFERENCES "user"("id") ON DELETE set null
```

## Multi-Level Relations

You can chain foreign keys across multiple tables:

```{.python continuation}
class Organization(Table):
    id: Integer = Integer(primary=True)
    name: Text = Text()

class User(Table):
    id: Integer = Integer(primary=True)
    org_id: Integer = Integer().fk(lambda: Organization.id)
    email: Text = Text()

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id, on_delete="cascade")
    content: Text = Text()
```

## Composite Constraints

For more complex relationships, combine foreign keys with other column options:

```{.python continuation}
class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer(not_null=True).fk(
        lambda: User.id,
        on_delete="cascade"
    )
    content: Text = Text(not_null=True)
```

This ensures every message must have a user, and messages are deleted when their user is deleted.

## Working with Foreign Keys

When querying, use joins to fetch related data:

```{.python continuation}
from typing import Annotated
from pydantic import BaseModel
from embar.db.pg import AsyncPgDb
from embar.query.where import Eq

class UserWithMessages(BaseModel):
    email: Annotated[str, User.email]
    messages: Annotated[list[str], Message.content.many()]

async def main():
    db = AsyncPgDb(...)
    users = await (
        db.select(UserWithMessages)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .group_by(User.id)
    )
```

For more on querying related data, see [Joins](../query/joins.md).

## Next Steps

- Learn about [Constraints](constraints.md) like indexes and unique constraints
- Explore [Joins](../query/joins.md) for querying related data
