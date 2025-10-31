from enum import auto

import pytest
from psycopg.errors import InvalidTextRepresentation

from embar.column.pg import EmbarEnum, EnumCol, Jsonb, PgEnum, Varchar
from embar.db.pg import Db as PgDb
from embar.query.selection import SelectAll
from embar.table import Table


def test_postgres_jsonb(pg_db: PgDb):
    db = pg_db

    class TableWithJsonB(Table):
        data: Jsonb = Jsonb()

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


def test_postgres_varchar():
    class TableWithVarchar(Table):
        status: Varchar = Varchar(length=10)

    ddl = TableWithVarchar.ddl()
    assert ddl == 'CREATE TABLE IF NOT EXISTS "table_with_varchar" ("status" VARCHAR(10));'


def test_postgres_enum(pg_db: PgDb):
    db = pg_db

    class StatusEnum(EmbarEnum):
        PENDING = auto()
        DONE = auto()

    class StatusPgEnum(PgEnum[StatusEnum]):
        name: str = "status_enum"
        enum: type[StatusEnum] = StatusEnum

    class TableWithStatus(Table):
        status: EnumCol[StatusEnum] = EnumCol(StatusPgEnum)

    db.migrate([TableWithStatus], enums=[StatusPgEnum])

    good_row = TableWithStatus(status="DONE")
    db.insert(TableWithStatus).value(good_row).execute()
    # fmt: off
    res = (
        db.select(SelectAll)
        .fromm(TableWithStatus)
        .execute()
    )
    # fmt: on
    assert len(res) == 1
    got = res[0]
    assert got.status == "DONE"

    bad_row = TableWithStatus(status="foo")
    with pytest.raises(InvalidTextRepresentation):
        db.insert(TableWithStatus).value(bad_row).execute()
