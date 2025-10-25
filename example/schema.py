from dataclasses import dataclass
from typing import Annotated, final

from pudl.column import Integer, Text
from pudl.selection import Selection
from pudl.table import Table


@dataclass
@final
class User(Table):
    _name = "user"
    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", default="text", not_null=True)


@dataclass
@final
class Message(Table):
    id: Integer = Integer()
    user_id: Integer = Integer().fk(lambda: User.id)
    content: Text = Text()


@dataclass
class UserSel(Selection):
    id: Annotated[int, User.id]


@dataclass
class MessageSel(Selection):
    user_name: Annotated[str, User.email]
    message: Annotated[str, Message.content]
