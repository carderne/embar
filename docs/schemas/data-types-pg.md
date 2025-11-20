# Data Types (Postgres)

Embar provides comprehensive support for PostgreSQL data types. All types are imported from `embar.column.pg` and `embar.column.common`.

## Integer Types

### Integer

Standard integer type.

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

### SmallInt

Small integer type for values from -32768 to 32767.

```{.python continuation}
from embar.column.pg import SmallInt

class Product(Table):
    stock: SmallInt = SmallInt()
```

Generates:
```sql
"stock" SMALLINT
```

### BigInt

Large integer type for values beyond the standard integer range.

```{.python continuation}
from embar.column.pg import BigInt

class Analytics(Table):
    views: BigInt = BigInt()
```

Generates:
```sql
"views" BIGINT
```

## Serial Types

Serial types are auto-incrementing integers.

### Serial

Auto-incrementing integer.

```{.python continuation}
from embar.column.pg import Serial

class User(Table):
    id: Serial = Serial(primary=True)
```

Generates:
```sql
"id" SERIAL
```

### SmallSerial

Auto-incrementing small integer.

```{.python continuation}
from embar.column.pg import SmallSerial

class Tag(Table):
    id: SmallSerial = SmallSerial(primary=True)
```

Generates:
```sql
"id" SMALLSERIAL
```

### BigSerial

Auto-incrementing big integer.

```{.python continuation}
from embar.column.pg import BigSerial

class Event(Table):
    id: BigSerial = BigSerial(primary=True)
```

Generates:
```sql
"id" BIGSERIAL
```

## Text Types

### Text

Variable-length text with no limit.

```{.python continuation}
from embar.column.common import Text

class Post(Table):
    content: Text = Text()
```

Generates:
```sql
"content" TEXT
```

### Varchar

Variable-length text with optional length limit.

```{.python continuation}
from embar.column.pg import Varchar

class User(Table):
    username: Varchar = Varchar(length=50)
```

Generates:
```sql
"username" VARCHAR(50)
```

Without a length limit:

```{.python continuation}
class User(Table):
    bio: Varchar = Varchar()
```

Generates:
```sql
"bio" VARCHAR
```

### Char

Fixed-length character type.

```{.python continuation}
from embar.column.pg import Char

class Country(Table):
    code: Char = Char(length=2)
```

Generates:
```sql
"code" CHAR(2)
```

## Numeric Types

### Numeric

Arbitrary precision decimal type with configurable precision and scale.

```{.python continuation}
from embar.column.pg import Numeric

class Product(Table):
    price: Numeric = Numeric(precision=10, scale=2)
```

Generates:
```sql
"price" NUMERIC(10, 2)
```

With precision only:

```{.python continuation}
class Product(Table):
    score: Numeric = Numeric(precision=5)
```

Generates:
```sql
"score" NUMERIC(5)
```

### PgDecimal

Alias for Numeric (DECIMAL is an alias for NUMERIC in PostgreSQL).

```{.python continuation}
from embar.column.pg import PgDecimal

class Invoice(Table):
    total: PgDecimal = PgDecimal(precision=12, scale=2)
```

Generates:
```sql
"total" DECIMAL(12, 2)
```

### Float

Real floating point type.

```{.python continuation}
from embar.column.common import Float

class Measurement(Table):
    temperature: Float = Float()
```

Generates:
```sql
"temperature" REAL
```

### DoublePrecision

Double precision floating point type.

```{.python continuation}
from embar.column.pg import DoublePrecision

class Calculation(Table):
    result: DoublePrecision = DoublePrecision()
```

Generates:
```sql
"result" DOUBLE PRECISION
```

## Boolean

Boolean type for true/false values.

```{.python continuation}
from embar.column.pg import Boolean

class User(Table):
    active: Boolean = Boolean(default=True)
```

Generates:
```sql
"active" BOOLEAN
```

## JSON Types

### Json

JSON data stored as text.

```{.python continuation}
from embar.column.pg import Json

class Config(Table):
    settings: Json = Json()
```

Generates:
```sql
"settings" JSON
```

### Jsonb

Binary JSON with indexing support. Recommended over Json for most use cases.

```{.python continuation}
import asyncio

from embar.db.pg import AsyncPgDb
from embar.column.pg import Jsonb

class User(Table):
    metadata: Jsonb = Jsonb()

# Usage
async def main():
    db = AsyncPgDb(...)
    user = User(metadata={"theme": "dark", "language": "en"})
    await db.insert(User).values(user)
```

Generates:
```sql
"metadata" JSONB
```

## Date and Time Types

### Date

Calendar date (year, month, day).

```{.python continuation}
from datetime import date
from embar.column.pg import Date

class Event(Table):
    event_date: Date = Date()

# Usage
event = Event(event_date=date(2025, 1, 15))
```

Generates:
```sql
"event_date" DATE
```

### Time

Time of day without date.

```{.python continuation}
from datetime import time
from embar.column.pg import Time

class Schedule(Table):
    start_time: Time = Time()

# Usage
schedule = Schedule(start_time=time(9, 30))
```

Generates:
```sql
"start_time" TIME
```

### Timestamp

Date and time without timezone.

```{.python continuation}
from datetime import datetime
from embar.column.pg import Timestamp

class Post(Table):
    created_at: Timestamp = Timestamp()

# Usage
post = Post(created_at=datetime.now())
```

Generates:
```sql
"created_at" TIMESTAMP
```

### Interval

Time interval (duration).

```{.python continuation}
from datetime import timedelta
from embar.column.pg import Interval

class Task(Table):
    duration: Interval = Interval()

# Usage
task = Task(duration=timedelta(hours=2, minutes=30))
```

Generates:
```sql
"duration" INTERVAL
```

## Enum Types

PostgreSQL enums require defining both the enum type and the column type.

```{.python continuation}
from enum import auto
from embar.column.pg import EmbarEnum, EnumCol, PgEnum

class StatusEnum(EmbarEnum):
    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()

class StatusPgEnum(PgEnum[StatusEnum]):
    name: str = "status_enum"
    enum: type[StatusEnum] = StatusEnum

class Task(Table):
    status: EnumCol[StatusEnum] = EnumCol(StatusPgEnum)

# Usage
async def main():
    db = AsyncPgDb(...)
    task = Task(status="ACTIVE")
    await db.insert(Task).values(task)
```

The enum must be included in migrations:

```{.python continuation}
async def main():
    db = AsyncPgDb(...)
    await db.migrate([Task], enums=[StatusPgEnum])
```

Generates:
```sql
CREATE TYPE status_enum AS ENUM ('PENDING', 'ACTIVE', 'COMPLETED');
```

And for the column:
```sql
"status" status_enum
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
    created_at: Timestamp = Timestamp(default=datetime.now())
```

### Custom Column Name

```{.python continuation}
class User(Table):
    email: Text = Text("user_email")
```
