import asyncio
from datetime import datetime
from typing import Annotated, TypedDict

from pydantic import BaseModel

from embar.column.pg import Integer
from embar.config import EmbarConfig
from embar.constraint import Index
from embar.query.where import Eq, Like, Or
from embar.sql import Sql
from embar.table import Table

from .db import setup_db
from .schema import Message, User


async def app():
    db = await setup_db()
    user = User(id=1, email="foo@bar.com")
    message = Message(id=1, user_id=user.id, content="Hello!")

    # Unlike with the sync example, we don't have to call run() everywhere.
    # We can await any full constructed query and get the result
    await db.insert(User).values(user)
    await db.insert(Message).values(message)

    # Query some data
    # With join, where and group by.
    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        messages: Annotated[list[str], Message.content.many()]

    users = await (
        db.select(UserSel)
        .from_(User)
        .left_join(Message, Eq(User.id, Message.user_id))
        .where(Or(Eq(User.id, 1), Like(User.email, "foo%")))
        .group_by(User.id)
    )
    print(users)
    # [ UserSel(id=1, messages=['Hello!']) ]

    # Query some more data
    # This time with fully nested child tables, and some raw SQL.
    class UserHydrated(BaseModel):
        email: Annotated[str, User.email]
        messages: Annotated[list[Message], Message.many()]
        date: Annotated[datetime, Sql(t"CURRENT_TIMESTAMP")]

    users = await (
        db.select(UserHydrated).from_(User).left_join(Message, Eq(User.id, Message.user_id)).group_by(User.id).limit(2)
    )
    print(users)
    # [UserHydrated(
    #      email='foo@bar.com',
    #      messages=[Message(content='Hello!', id=1, user_id=1)],
    #      date: datetime(2025, 10, 26, ...)
    # )]

    # See the SQL
    # Every query produces exactly one... query.
    # And you can always see what's happening under the hood with the `.sql()`
    # method:
    users_query = (
        db.select(UserHydrated).from_(User).left_join(Message, Eq(User.id, Message.user_id)).group_by(User.id).sql()
    )
    print(users_query.sql)
    # SELECT
    #     "users"."user_email" AS "email",
    #     json_group_array(json_object(
    #         'id', "message"."id",
    #         'user_id', "message"."user_id",
    #         'content', "message"."content"
    #     )) AS "messages",
    #     CURRENT_TIMESTAMP AS "date"
    # FROM "users"
    # LEFT JOIN "message" ON "users"."id" = "message"."user_id"
    # GROUP BY "users"."id"

    # Update a row
    # Unfortunately this requires another model to be defined,
    # as Python doesn't have a `Partial[]` type.
    class MessageUpdate(TypedDict, total=False):
        id: int
        user_id: int
        content: str

    await db.update(Message).set(MessageUpdate(content="Goodbye")).where(Eq(Message.id, 1))

    # Add indexes
    class MessageIndexed(Table):  # pyright:ignore[reportUnusedClass]
        embar_config: EmbarConfig = EmbarConfig(constraints=[Index("message_idx").on(lambda: Message.user_id)])
        user_id: Integer = Integer().fk(lambda: User.id)

    # Run raw SQL
    await db.sql(t"DELETE FROM {Message}")

    # Or with a return:
    class UserId(BaseModel):
        id: Annotated[int, int]

    res = await db.sql(t"SELECT * FROM {User}").model(UserId)
    print(res)
    # [UserId(id=1)]


asyncio.run(app())
