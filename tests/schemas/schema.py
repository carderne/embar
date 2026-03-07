from typing import TypedDict

from embar.column.common import Integer, Text, integer, text
from embar.config import EmbarConfig
from embar.table import Table


class User(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="users")

    id: Integer = integer(primary=True)
    email: Text = text("user_email", not_null=True)


class UserUpdate(TypedDict, total=False):
    id: int
    email: str


class Message(Table):
    id: Integer = integer()
    user_id: Integer = integer(fk=lambda: User.id, on_delete="cascade")
    content: Text = text(default="no message")


class MessageUpdate(TypedDict, total=False):
    id: int
    user_id: int
    content: str
