# Create client and apply migrations
# In production, you would (probably) use the `embar` CLI to generate and run migrations.
# This example uses the utility function to do it all in code.

import psycopg

from embar.db.pg import AsyncPgDb

from . import schema


async def setup_db():
    database_url = "postgres://pg:pw@localhost:3601/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)

    await db.migrates(schema)
    return db
