# Data Types (SQLite)

Embar provides support for SQLite data types. All types are imported from `embar.column.sqlite` and `embar.column.common`.

SQLite has a flexible type system. These column types provide the standard SQLite type affinities.

## Integer

Integer values.

```{.python continuation}
from embar.column.common import Integer
from embar.table import Table

class Product(Table):
    quantity: Integer = Integer()
```

Generates:
```sql
"quantity" INTEGER
```

## Text

Variable-length text.

```{.python continuation}
from embar.column.common import Text

class User(Table):
    email: Text = Text()
```

Generates:
```sql
"email" TEXT
```

## Float

Floating point values (stored as REAL in SQLite).

```{.python continuation}
from embar.column.common import Float

class Measurement(Table):
    temperature: Float = Float()
```

Generates:
```sql
"temperature" REAL
```

## Blob

Binary data storage.

```{.python continuation}
from embar.column.sqlite import Blob

class Document(Table):
    file_data: Blob = Blob()

# Usage
doc = Document(file_data=b"binary content here")
async def main():
    await db.insert(Document).values(doc)
```

Generates:
```sql
"file_data" BLOB
```

## Common Column Options

All column types support these options:

### Primary Key

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

### Custom Column Name

```{.python continuation}
class User(Table):
    email: Text = Text("user_email")
```
