from dataclasses import dataclass
from typing import final

from pudl.column.common import Integer, Text
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
