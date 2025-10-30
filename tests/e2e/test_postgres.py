from embar.column.pg import Jsonb
from embar.db.pg import Db as PgDb
from embar.query.selection import SelectAll
from embar.table import Table


class TableWithJsonB(Table):
    data: Jsonb = Jsonb()


def test_postgres_jsonb(pg_db: PgDb):
    db = pg_db
    db.migrate([TableWithJsonB])

    name = "bob"
    data = TableWithJsonB(data={"name": name})
    db.insert(TableWithJsonB).value(data).execute()

    # fmt: off
    res = (
        db.select(SelectAll)
        .fromm(TableWithJsonB)
        .execute()
    )
    # fmt: on
    assert len(res) == 1
    got = res[0]
    assert got.data["name"] == name
