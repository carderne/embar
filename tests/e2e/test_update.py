from typing import Annotated

from embar.db.pg import Db as PgDb
from embar.db.sqlite import Db as SqliteDb
from embar.query.selection import Selection
from embar.query.where import Eq

from ..schemas.schema import Message, MessageUpdate


def test_update_row(db_loaded: SqliteDb | PgDb):
    db = db_loaded

    new_content = "new content"
    # fmt: off
    (
        db.update(Message)
        .set(MessageUpdate(content=new_content))
        .where(Eq(Message.id, 1))
        .run()
    )
    # fmt: on

    class MessageSel(Selection):
        content: Annotated[str, Message.content]

    res = (
        db.select(MessageSel)
        .fromm(Message)
        .where(
            Eq(Message.id, 1),
        )
        .limit(1)
        .run()
    )

    assert len(res) == 1
    got = res[0]
    assert got.content == new_content
