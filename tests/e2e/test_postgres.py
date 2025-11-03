from enum import auto
from typing import Annotated

import pytest
from psycopg.errors import InvalidTextRepresentation

from embar.column.pg import EmbarEnum, EnumCol, Jsonb, PgEnum, Text, Varchar
from embar.config import EmbarConfig
from embar.constraint import Index
from embar.db.pg import Db as PgDb
from embar.query.selection import Selection
from embar.table import Table


@pytest.mark.asyncio
async def test_postgres_jsonb(pg_db: PgDb):
    db = pg_db

    class TableWithJsonB(Table):
        data: Jsonb = Jsonb()

    db.migrate([TableWithJsonB]).run()

    name = "bob"
    data = TableWithJsonB(data={"name": name})
    await db.insert(TableWithJsonB).values(data)

    # fmt: off
    res = (
        db.select(TableWithJsonB.all())
        .fromm(TableWithJsonB)
        .run()
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


def test_postgres_index(pg_db: PgDb):
    table_name = "table_with_index"

    class TableWithIndex(Table):
        embar_config: EmbarConfig = EmbarConfig(
            table_name=table_name, constraints=[Index("table_index").on(lambda: TableWithIndex.id)]
        )

        id: Text = Text()

    db = pg_db
    db.migrate([TableWithIndex]).run()

    class IndexResults(Selection):
        indexname: Annotated[str, str]

    # breakpoint()
    # fmt: off
    res = (
        # this is a rare instance where we don't want to interpolate {TableWithIndex} because that will
        # wrap it "" rather than ''
        db.sql(t"SELECT indexname FROM pg_indexes WHERE tablename = 'table_with_index';")
        .model(IndexResults)
        .run()
    )
    # fmt: off

    assert len(res) == 1


@pytest.mark.asyncio
async def test_postgres_enum(pg_db: PgDb):
    db = pg_db

    class StatusEnum(EmbarEnum):
        PENDING = auto()
        DONE = auto()

    class StatusPgEnum(PgEnum[StatusEnum]):
        name: str = "status_enum"
        enum: type[StatusEnum] = StatusEnum

    class TableWithStatus(Table):
        status: EnumCol[StatusEnum] = EnumCol(StatusPgEnum)

    db.migrate([TableWithStatus], enums=[StatusPgEnum]).run()

    good_row = TableWithStatus(status="DONE")
    await db.insert(TableWithStatus).values(good_row)
    # fmt: off
    res = (
        db.select(TableWithStatus.all())
        .fromm(TableWithStatus)
        .run()
    )
    # fmt: on
    assert len(res) == 1
    got = res[0]
    assert got.status == "DONE"

    bad_row = TableWithStatus(status="foo")
    with pytest.raises(InvalidTextRepresentation):
        await db.insert(TableWithStatus).values(bad_row)
