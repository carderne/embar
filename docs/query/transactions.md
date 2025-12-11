# Transactions

Transactions allow you to group multiple database operations into a single atomic unit. Either all operations succeed and are committed, or any failure causes all changes to be rolled back.

## Basic Usage

Use `db.transaction()` as a context manager to start a transaction:

```{.python fixture:postgres_container}
import asyncio
import psycopg

from embar.column.common import Integer, Text
from embar.db.pg import AsyncPgDb
from embar.table import Table

class Account(Table):
    id: Integer = Integer()
    name: Text = Text()

class Transfer(Table):
    id: Integer = Integer()
    from_account: Integer = Integer()
    to_account: Integer = Integer()
    amount: Integer = Integer()

async def get_db():
    database_url = "postgres://pg:pw@localhost:25432/db"
    conn = await psycopg.AsyncConnection.connect(database_url)
    db = AsyncPgDb(conn)
    await db.migrate([Account, Transfer])
    return db

async def basic():
    db = await get_db()

    async with db.transaction() as tx:
        account = Account(id=1, name="alice")
        await tx.insert(Account).values(account)

    # Changes are committed when the context manager exits successfully
    accounts = await db.select(Account.all()).from_(Account)
    assert any(a.id == 1 for a in accounts)

asyncio.run(basic())
```

Inside the transaction block, use `tx` (the transaction database object) for all operations. When the block exits normally, changes are committed automatically.

## Automatic Rollback on Errors

If an exception occurs inside the transaction block, all changes are automatically rolled back:

```{.python continuation}
async def rollback_on_error():
    db = await get_db()

    try:
        async with db.transaction() as tx:
            account = Account(id=100, name="bob")
            await tx.insert(Account).values(account)

            # This raises an exception
            raise ValueError("Something went wrong")
    except ValueError:
        pass

    # The insert was rolled back
    accounts = await db.select(Account.all()).from_(Account)
    assert not any(a.id == 100 for a in accounts)

asyncio.run(rollback_on_error())
```

## Multiple Operations

Transactions are useful when you need multiple related operations to succeed or fail together:

```{.python continuation}
async def transfer_funds():
    db = await get_db()

    async with db.transaction() as tx:
        # Create accounts and record transfer atomically
        await tx.insert(Account).values(Account(id=200, name="sender"))
        await tx.insert(Account).values(Account(id=201, name="receiver"))

        transfer = Transfer(id=1, from_account=200, to_account=201, amount=100)
        await tx.insert(Transfer).values(transfer)

    # All operations committed together
    transfers = await db.select(Transfer.all()).from_(Transfer)
    assert any(t.from_account == 200 for t in transfers)

asyncio.run(transfer_funds())
```

## Next Steps

- Learn about [Raw SQL](raw-sql.md) for custom queries
- See how to [Insert](insert.md) data
- Explore [Select](select.md) queries
