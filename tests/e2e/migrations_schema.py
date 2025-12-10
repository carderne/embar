"""Test schema for migration e2e tests."""

from embar.column.common import Integer, Text
from embar.table import Table


class TestUser(Table):
    id: Integer = Integer(primary=True)
    name: Text = Text(not_null=True)
