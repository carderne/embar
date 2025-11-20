# Schema Basics

Schemas in Embar are defined as Python classes that inherit from `Table`. Each column is defined as a class variable with a type annotation.

## Defining a Table

The simplest table definition:

```{.python continuation}
from embar.column.common import Integer, Text
from embar.table import Table

class User(Table):
    id: Integer = Integer()
    email: Text = Text()
```

This creates a table called `user` with two columns: `id` and `email`.

## Table Naming

By default, Embar generates table names from your class name by converting from PascalCase to snake_case:

```{.python continuation}
class UserProfile(Table):
    id: Integer = Integer()

# Table name will be "user_profile"
```

You can override this with an explicit table name:

```{.python continuation}
from embar.config import EmbarConfig

class UserProfile(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="users")

    id: Integer = Integer()
```

## Column Naming

Like table names, column names are auto-generated from the field name:

```{.python continuation}
class User(Table):
    user_id: Integer = Integer()
    # Column name will be "user_id"
```

You can provide an explicit name as the first argument:

```{.python continuation}
class User(Table):
    id: Integer = Integer("user_id")
    # Field name is "id", column name is "user_id"
```

This is useful when you want shorter field names in Python but more explicit column names in the database.

## Column Types

Embar provides several column types. The most common ones are:

- `Integer`: Integer values
- `Text`: Text/string values
- `Float`: Floating point values

For the full list of available types:

- [Postgres data types](data-types-pg.md)
- [Sqlite data types](data-types-sqlite.md)

## Basic Column Configuration

Columns accept several configuration options:

### Primary Keys

```{.python continuation}
class User(Table):
    id: Integer = Integer(primary=True)
```

### Not Null

```{.python continuation}
class User(Table):
    email: Text = Text(not_null=True)
```

### Default Values

```{.python continuation}
class User(Table):
    status: Text = Text(default="active")
```

When creating a new row, fields with defaults can be omitted:

```{.python continuation}
user = User()
# status will be "active"
```

### Combining Options

```{.python continuation}
class User(Table):
    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", not_null=True)
    status: Text = Text(default="active", not_null=True)
```

## Foreign Keys

Foreign keys reference columns in other tables:

```{.python continuation}
class User(Table):
    id: Integer = Integer(primary=True)

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id)
```

The lambda is required because `User` might not be defined yet when `Message` is being created.

You can specify `on_delete` behavior:

```{.python continuation}
class Message(Table):
    user_id: Integer = Integer().fk(
        lambda: User.id,
        on_delete="cascade"
    )
```

## A Complete Example

```{.python continuation}
from embar.column.common import Integer, Text
from embar.config import EmbarConfig
from embar.table import Table

class User(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="users")

    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", not_null=True)
    name: Text = Text(default="Anonymous")

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer(not_null=True).fk(lambda: User.id)
    content: Text = Text(not_null=True)
```

## Next Steps

- Learn about [Relations](relations.md) for working with related data
- Add [Constraints](constraints.md) like indexes and unique constraints
- Explore the full list of [Postgres data types](data-types-pg.md) or [Sqlite data types](data-types-sqlite.md)
