from dataclasses import dataclass
from typing import final

from pudl.table import Selection, TextColumn, Table, Text


@dataclass
@final
class User(Table):
    _name = "user"
    id: TextColumn = Text(primary=True)
    email: TextColumn = Text("user_email", default="text", not_null=True)


@dataclass
@final
class Message(Table):
    id: TextColumn = Text()
    user_id: TextColumn = Text().fk(lambda: User.id)
    content: TextColumn = Text()


@dataclass
class UserSel(Selection):
    id: str = User.id()


@dataclass
class MessageSel(Selection):
    user_name: str = User.email()
    message: str = Message.content()
