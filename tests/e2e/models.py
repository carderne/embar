from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from pudl.selection import Selection
from pudl.sql import sql

from .schema import User, Message


@dataclass
class UserSel(Selection):
    id: Annotated[int, User.id]
    messages: Annotated[list[str], Message.content.many()]


@dataclass
class UserFullMessages(Selection):
    email: Annotated[str, User.email]
    messages: Annotated[list[Message], Message.many()]
    date: Annotated[datetime, sql(t"CURRENT_TIMESTAMP")]


@dataclass
class MessageSel(Selection):
    user: Annotated[User, User]
    message: Annotated[str, Message.content]
