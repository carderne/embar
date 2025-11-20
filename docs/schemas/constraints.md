# Constraints

Constraints are defined in the table's `embar_config` and passed as a list. They generate additional SQL statements when you run migrations.

## Indexes

Indexes improve query performance on frequently searched columns. Create them with the `Index` class:

```{.python}
from embar.column.common import Integer, Text
from embar.config import EmbarConfig
from embar.constraint import Index
from embar.table import Table

class User(Table):
    embar_config: EmbarConfig = EmbarConfig(
        constraints=[Index("email_idx").on(lambda: User.email)]
    )

    id: Integer = Integer(primary=True)
    email: Text = Text()
```

This generates:

```sql
CREATE INDEX "email_idx" ON "user"("email");
```

### Multi-Column Indexes

Pass multiple columns to `on()` for composite indexes:

```{.python continuation}
class User(Table):
    embar_config: EmbarConfig = EmbarConfig(
        constraints=[
            Index("name_email_idx").on(
                lambda: User.last_name,
                lambda: User.first_name
            )
        ]
    )

    id: Integer = Integer(primary=True)
    first_name: Text = Text()
    last_name: Text = Text()
```

This generates:

```sql
CREATE INDEX "name_email_idx" ON "user"("last_name", "first_name");
```

### Partial Indexes

Add a `where()` clause to create a partial index (Postgres and Sqlite):

```{.python continuation}
from embar.query.where import Eq

class User(Table):
    embar_config: EmbarConfig = EmbarConfig(
        constraints=[
            Index("active_users_idx")
                .on(lambda: User.email)
                .where(lambda: Eq(User.status, "active"))
        ]
    )

    id: Integer = Integer(primary=True)
    email: Text = Text()
    status: Text = Text()
```

This generates:

```sql
CREATE INDEX "active_users_idx" ON "user"("email") WHERE "status" = :p0;
```

Partial indexes are smaller and faster when you only need to index a subset of rows.

## Unique Constraints

Unique constraints ensure no duplicate values exist in a column. Use the `UniqueIndex` class:

```{.python continuation}
from embar.constraint import UniqueIndex

class User(Table):
    embar_config: EmbarConfig = EmbarConfig(
        constraints=[UniqueIndex("email_unique").on(lambda: User.email)]
    )

    id: Integer = Integer(primary=True)
    email: Text = Text()
```

This generates:

```sql
CREATE UNIQUE INDEX "email_unique" ON "user"("email");
```

### Multi-Column Unique Constraints

Create unique constraints across multiple columns:

```{.python continuation}
class User(Table):
    embar_config: EmbarConfig = EmbarConfig(
        constraints=[
            UniqueIndex("org_email_unique").on(
                lambda: User.org_id,
                lambda: User.email
            )
        ]
    )

    id: Integer = Integer(primary=True)
    org_id: Integer = Integer()
    email: Text = Text()
```

This ensures that each email is unique within an organization, but the same email can exist in different organizations.

This generates:

```sql
CREATE UNIQUE INDEX "org_email_unique" ON "user"("org_id", "email");
```

## Multiple Constraints

Add multiple constraints to a single table:

```{.python continuation}
class Message(Table):
    embar_config: EmbarConfig = EmbarConfig(
        constraints=[
            Index("user_idx").on(lambda: Message.user_id),
            Index("created_idx").on(lambda: Message.created_at),
            UniqueIndex("content_unique").on(lambda: Message.content)
        ]
    )

    id: Integer = Integer(primary=True)
    user_id: Integer = Integer()
    content: Text = Text()
    created_at: Integer = Integer()
```

This generates three separate SQL statements during migration.

## Applying Constraints

Constraints are created when you run migrations:

```{.python continuation fixture:postgres_container}
import psycopg
from embar.db.pg import PgDb

database_url = "postgres://pg:pw@localhost:25432/db"
conn = psycopg.Connection.connect(database_url)
db = PgDb(conn)
db.migrate([User, Message]).run()
```

The `migrate()` method generates both table creation and constraint creation SQL.

## Next Steps

- Learn about [Basic schemas](basics.md) for defining tables
- Explore [Relations](relations.md) for foreign keys
