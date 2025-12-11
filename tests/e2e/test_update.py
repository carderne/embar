from typing import Annotated

from pydantic import BaseModel

from embar.db.pg import PgDb
from embar.db.sqlite import SqliteDb
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

    class MessageSel(BaseModel):
        content: Annotated[str, Message.content]

    res = (
        db.select(MessageSel)
        .from_(Message)
        .where(
            Eq(Message.id, 1),
        )
        .limit(1)
        .run()
    )

    assert len(res) == 1
    got = res[0]
    assert got.content == new_content
