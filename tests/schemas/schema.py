from embar.column.common import Integer, Text
from embar.config import TableConfig
from embar.table import Table


class User(Table):
    embar_config: TableConfig = TableConfig(table_name="users")

    id: Integer = Integer(primary=True)
    email: Text = Text("user_email", not_null=True)


class Message(Table):
    id: Integer = Integer()
    user_id: Integer = Integer().fk(lambda: User.id, "cascade")
    content: Text = Text(default="no message")
