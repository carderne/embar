from typing import TypedDict

from embar.column.common import Integer, Text
from embar.config import EmbarConfig
from embar.table import Table


class User(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="users")

    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", not_null=True)
    username: Text = Text()  # NEW: Adding username column
    created_at: Text = Text(default="now()")  # NEW: Adding created_at with default


class UserUpdate(TypedDict, total=False):
    id: int
    email: str
    username: str
    created_at: str


class Message(Table):
    id: Integer = Integer()
    user_id: Integer = Integer().fk(lambda: User.id, "cascade")
    content: Text = Text(default="no message")


class MessageUpdate(TypedDict, total=False):
    id: int
    user_id: int
    content: str
