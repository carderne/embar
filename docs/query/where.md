# Where

Where clauses filter rows in your queries. Embar provides type-safe operators for comparisons, pattern matching, null checks, and logical combinations.

## Basic Comparison

Use `Eq` to check equality:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.column.common import Integer, Text
from embar.db.pg import AsyncPgDb
from embar.query.where import Eq
from embar.table import Table

class User(Table):
    id: Integer = Integer(primary=True)
    email: Text = Text()

async def get_db(tables: list[Table] = None):
    if tables is None:
        tables = [User]
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate(tables)
    return db

async def basic():
    db = await get_db()
    users = await db.select(User.all()).from_(User).where(Eq(User.id, 1))

asyncio.run(basic())
```

This generates:

```sql
SELECT "user"."id", "user"."email" FROM "user" WHERE "user"."id" = %(eq_id_0)s
```

With parameters: `{'eq_id_0': 1}`

## Comparison Operators

### Equality

Check if values are equal or not equal:

```{.python continuation}
from embar.query.where import Eq, Ne

async def equality():
    db = await get_db()
    # Equal
    await db.select(User.all()).from_(User).where(Eq(User.id, 1))

    # Not equal
    await db.select(User.all()).from_(User).where(Ne(User.id, 1))

asyncio.run(equality())
```

### Numeric Comparisons

Compare numeric values:

```{.python continuation}
from embar.query.where import Gt, Gte, Lt, Lte

async def numeric():
    db = await get_db()
    # Greater than
    await db.select(User.all()).from_(User).where(Gt(User.id, 10))

    # Greater than or equal
    await db.select(User.all()).from_(User).where(Gte(User.id, 10))

    # Less than
    await db.select(User.all()).from_(User).where(Lt(User.id, 100))

    # Less than or equal
    await db.select(User.all()).from_(User).where(Lte(User.id, 100))

asyncio.run(numeric())
```

This generates:

```sql
-- Greater than
WHERE "user"."id" > %(gt_id_0)s

-- Greater than or equal
WHERE "user"."id" >= %(gte_id_0)s

-- Less than
WHERE "user"."id" < %(lt_id_0)s

-- Less than or equal
WHERE "user"."id" <= %(lte_id_0)s
```

## Pattern Matching

### Like

Use `Like` for case-sensitive pattern matching:

```{.python continuation}
from embar.query.where import Like

async def like():
    db = await get_db()
    # Starts with "alice"
    await db.select(User.all()).from_(User).where(Like(User.email, "alice%"))

    # Ends with "@example.com"
    await db.select(User.all()).from_(User).where(Like(User.email, "%@example.com"))

    # Contains "test"
    await db.select(User.all()).from_(User).where(Like(User.email, "%test%"))

asyncio.run(like())
```

This generates:

```sql
WHERE "user"."email" LIKE %(like_email_0)s
```

### Case-Insensitive Like

Use `Ilike` for case-insensitive matching (Postgres only):

```{.python continuation}
from embar.query.where import Ilike

async def insensitive():
    db = await get_db()
    await db.select(User.all()).from_(User).where(Ilike(User.email, "ALICE%"))

asyncio.run(insensitive())
```

This generates:

```sql
WHERE "user"."email" ILIKE %(ilike_email_0)s
```

### Not Like

Use `NotLike` to exclude patterns:

```{.python continuation}
from embar.query.where import NotLike

async def notlike():
    db = await get_db()
    await db.select(User.all()).from_(User).where(NotLike(User.email, "%spam%"))

asyncio.run(notlike())
```

This generates:

```sql
WHERE "user"."email" NOT LIKE %(notlike_email_0)s
```

## Null Checks

Check for null or non-null values:

```{.python continuation}
from embar.query.where import IsNull, IsNotNull

async def null():
    db = await get_db()
    # Is null
    await db.select(User.all()).from_(User).where(IsNull(User.email))

    # Is not null
    await db.select(User.all()).from_(User).where(IsNotNull(User.email))

asyncio.run(null())
```

This generates:

```sql
-- Is null
WHERE "user"."email" IS NULL

-- Is not null
WHERE "user"."email" IS NOT NULL
```

## Array Operations

### In Array

Check if a value is in a list:

```{.python continuation}
from embar.query.where import InArray

async def array():
    db = await get_db()
    await db.select(User.all()).from_(User).where(InArray(User.id, [1, 2, 3]))

asyncio.run(array())
```

This generates:

```sql
WHERE "user"."id" = ANY(%(in_id_0)s)
```

With parameters: `{'in_id_0': [1, 2, 3]}`

### Not In Array

Check if a value is not in a list:

```{.python continuation}
from embar.query.where import NotInArray

async def not_in_array():
    db = await get_db()
    await db.select(User.all()).from_(User).where(NotInArray(User.id, [5, 10, 15]))

asyncio.run(not_in_array())
```

This generates:

```sql
WHERE "user"."id" != ALL(%(notin_id_0)s)
```

## Range Operations

### Between

Check if a value falls within a range (inclusive):

```{.python continuation}
from embar.query.where import Between

async def between():
    db = await get_db()
    await db.select(User.all()).from_(User).where(Between(User.id, 10, 20))

asyncio.run(between())
```

This generates:

```sql
WHERE "user"."id" BETWEEN %(between_lower_id_0)s AND %(between_upper_id_0)s
```

### Not Between

Check if a value is outside a range:

```{.python continuation}
from embar.query.where import NotBetween

async def not_between():
    db = await get_db()
    await db.select(User.all()).from_(User).where(NotBetween(User.id, 10, 20))

asyncio.run(not_between())
```

This generates:

```sql
WHERE "user"."id" NOT BETWEEN %(notbetween_lower_id_0)s AND %(notbetween_upper_id_0)s
```

## Logical Operators

### And

Combine multiple conditions where all must be true:

```{.python continuation}
from embar.query.where import And, Eq, Gt

async def op_and():
    db = await get_db()
    await (
        db.select(User.all())
        .from_(User)
        .where(And(
            Gt(User.id, 10),
            Like(User.email, "%@example.com")
        ))
    )

asyncio.run(op_and())
```

This generates:

```sql
WHERE "user"."id" > %(gt_id_0)s AND "user"."email" LIKE %(like_email_1)s
```

### Or

Combine multiple conditions where at least one must be true:

```{.python continuation}
from embar.query.where import Or, Eq

async def op_or():
    db = await get_db()
    await (
        db.select(User.all())
        .from_(User)
        .where(Or(
            Eq(User.id, 1),
            Eq(User.id, 2)
        ))
    )

asyncio.run(op_or())
```

This generates:

```sql
WHERE "user"."id" = %(eq_id_0)s OR "user"."id" = %(eq_id_1)s
```

### Not

Negate a condition:

```{.python continuation}
from embar.query.where import Not, Eq

async def op_not():
    db = await get_db()
    await db.select(User.all()).from_(User).where(Not(Eq(User.id, 1)))

asyncio.run(op_not())
```

This generates:

```sql
WHERE NOT ("user"."id" = %(eq_id_0)s)
```

### Complex Combinations

Nest logical operators for complex conditions:

```{.python continuation}
async def complex():
    db = await get_db()
    await (
        db.select(User.all())
        .from_(User)
        .where(Or(
            And(
                Gt(User.id, 10),
                Lt(User.id, 20)
            ),
            And(
                Gt(User.id, 50),
                Lt(User.id, 60)
            )
        ))
    )

asyncio.run(complex())
```

This generates:

```sql
WHERE ("user"."id" > %(gt_id_0)s AND "user"."id" < %(lt_id_1)s) OR
      ("user"."id" > %(gt_id_2)s AND "user"."id" < %(lt_id_3)s)
```

## Subqueries

### Exists

Check if a subquery returns any rows:

```{.python continuation}
from embar.query.where import Exists

class Message(Table):
    id: Integer = Integer(primary=True)
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()

async def exists():
    db = await get_db([User, Message])
    subquery = db.select(User.all()).from_(Message).where(Eq(Message.user_id, User.id))

    users = await (
        db.select(User.all())
        .from_(User)
        .where(Exists(subquery))
    )

asyncio.run(exists())
```

This generates:

```sql
SELECT "user"."id", "user"."email" FROM "user"
WHERE EXISTS (
    SELECT "message"."id", "message"."user_id", "message"."content"
    FROM "message"
    WHERE "message"."user_id" = "user"."id"
)
```

### Not Exists

Check if a subquery returns no rows:

```{.python continuation}
from embar.query.where import NotExists

async def notexists():
    db = await get_db()
    subquery = db.select(User.all()).from_(Message).where(Eq(Message.user_id, User.id))
    users = await (
        db.select(User.all())
        .from_(User)
        .where(NotExists(subquery))
    )

asyncio.run(notexists())
```

This generates:

```sql
WHERE NOT EXISTS (...)
```

## Comparing Columns

Compare two columns instead of a column and a value:

```{.python continuation}
class Order(Table):
    id: Integer = Integer(primary=True)
    created_at: Integer = Integer()
    updated_at: Integer = Integer()

async def compare():
    db = await get_db([Order])
    orders = await (
        db.select(Order.all())
        .from_(Order)
        .where(Gt(Order.updated_at, Order.created_at))
    )

asyncio.run(compare())
```

This generates:

```sql
WHERE "order"."updated_at" > "order"."created_at"
```

Notice there are no parameter bindings when comparing columns directly.

## Viewing the SQL

Inspect the generated where clause:

```{.python continuation}
async def raw_sql():
    db = await get_db()
    query = (
        db.select(User.all())
        .from_(User)
        .where(And(
            Gt(User.id, 10),
            Like(User.email, "%@example.com")
        ))
        .sql()
    )

    print(query.sql)
    # SELECT "user"."id", "user"."email" FROM "user"
    # WHERE "user"."id" > %(gt_id_0)s AND "user"."email" LIKE %(like_email_1)s

    print(query.params)
    # {'gt_id_0': 10, 'like_email_1': '%@example.com'}

asyncio.run(raw_sql())
```

## Next Steps

- See how where clauses work with [Select](select.md) queries
- Use where clauses in [Update](update.md) operations
- Filter rows in [Delete](delete.md) operations
