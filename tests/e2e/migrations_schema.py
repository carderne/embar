"""Test schema for migration e2e tests."""

from embar.column.common import Integer, Text, integer, text
from embar.table import Table


class TestUser(Table):
    id: Integer = integer(primary=True)
    name: Text = text(not_null=True)
