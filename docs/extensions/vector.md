# Vector

Embar supports [pgvector](https://github.com/pgvector/pgvector), the open-source vector similarity search extension for PostgreSQL.

Before using vector columns, you must install and activate the extension:

```sql
CREATE EXTENSION vector;
```

## Creating a Vector Column

Use `Vector` to store embeddings with a fixed dimension:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.column.common import Integer
from embar.column.pg import Vector
from embar.db.pg import AsyncPgDb
from embar.table import Table

class Document(Table):
    id: Integer = Integer()
    embedding: Vector = Vector(3)  # 3-dimensional vector

async def get_db():
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    db = AsyncPgDb(conn)
    await db.migrate([Document])
    return db

async def setup():
    db = await get_db()
    # Insert some documents with embeddings
    await db.insert(Document).values(Document(id=1, embedding=[1.0, 0.0, 0.0]))
    await db.insert(Document).values(Document(id=2, embedding=[0.0, 1.0, 0.0]))
    await db.insert(Document).values(Document(id=3, embedding=[0.0, 0.0, 1.0]))

asyncio.run(setup())
```

## L2 Distance

Use `L2Distance` for Euclidean distance searches. This uses the `<->` operator.

### Order By L2 Distance

Find documents ordered by distance to a query vector:

```{.python continuation}
from embar.query.vector import L2Distance

async def order_by_l2():
    db = await get_db()
    query_vector = [1.0, 0.5, 0.0]
    docs = await (
        db.select(Document.all())
        .from_(Document)
        .order_by(L2Distance(Document.embedding, query_vector))
    )
    print([d.id for d in docs])

asyncio.run(order_by_l2())
```

### Filter By L2 Distance

Find documents within a distance threshold:

```{.python continuation}
from embar.query.where import Lt

async def filter_by_l2():
    db = await get_db()
    query_vector = [1.0, 0.0, 0.0]
    docs = await (
        db.select(Document.all())
        .from_(Document)
        .where(Lt(L2Distance(Document.embedding, query_vector), 0.5))
    )
    print([d.id for d in docs])

asyncio.run(filter_by_l2())
```

## Cosine Distance

Use `CosineDistance` for cosine similarity searches. This uses the `<=>` operator.

### Order By Cosine Distance

```{.python continuation}
from embar.query.vector import CosineDistance

async def order_by_cosine():
    db = await get_db()
    query_vector = [1.0, 0.5, 0.0]
    docs = await (
        db.select(Document.all())
        .from_(Document)
        .order_by(CosineDistance(Document.embedding, query_vector))
    )
    print([d.id for d in docs])

asyncio.run(order_by_cosine())
```
