"""Tests for non-pydantic (plain class / plain dataclass) model support."""

from typing import Annotated

import pytest

from embar.column.common import Integer, Text, integer, text
from embar.config import EmbarConfig
from embar.db.pg import PgDb
from embar.model import (
    SelectAllDataclass,
    SelectAllPydantic,
    generate_dataclass_model,
    generate_pydantic_model,
    load_dataclass,
    upgrade_model_nested_fields,
)
from embar.table import Table

# ---------------------------------------------------------------------------
# Test schema
# ---------------------------------------------------------------------------


class Author(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="authors")
    id: Integer = integer(primary=True)
    name: Text = text()


class Book(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="books")
    id: Integer = integer(primary=True)
    title: Text = text()
    author_id: Integer = integer(fk=lambda: Author.id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_dummy() -> PgDb:
    return PgDb(None)  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Table.all() tests
# ---------------------------------------------------------------------------


def test_table_all_default_returns_dataclass():
    """Table.all() with no args returns SelectAllDataclass by default."""
    assert Author.all() is SelectAllDataclass


def test_table_all_use_pydantic_false_returns_dataclass():
    """Table.all(use_pydantic=False) explicitly returns SelectAllDataclass."""
    assert Author.all(use_pydantic=False) is SelectAllDataclass


def test_table_all_use_pydantic_true_returns_pydantic():
    """Table.all(use_pydantic=True) returns SelectAllPydantic."""
    assert Author.all(use_pydantic=True) is SelectAllPydantic


# ---------------------------------------------------------------------------
# generate_dataclass_model tests
# ---------------------------------------------------------------------------


def test_generate_dataclass_model_creates_dataclass():
    """generate_dataclass_model returns a plain dataclass with the right fields."""
    dc = generate_dataclass_model(Author)
    assert hasattr(dc, "__dataclass_fields__")
    assert "id" in dc.__dataclass_fields__
    assert "name" in dc.__dataclass_fields__


def test_generate_pydantic_model_creates_pydantic():
    """generate_pydantic_model returns a Pydantic BaseModel with the right fields."""
    from pydantic import BaseModel

    m = generate_pydantic_model(Author)
    assert issubclass(m, BaseModel)
    assert "id" in m.model_fields
    assert "name" in m.model_fields


# ---------------------------------------------------------------------------
# load_dataclass tests
# ---------------------------------------------------------------------------


def test_load_dataclass_simple():
    """load_dataclass populates plain dataclass fields from row dicts."""
    dc = generate_dataclass_model(Author)
    rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    results = load_dataclass(dc, rows)
    assert len(results) == 2
    assert results[0].id == 1
    assert results[0].name == "Alice"
    assert results[1].id == 2
    assert results[1].name == "Bob"


def test_load_dataclass_missing_field_becomes_none():
    """load_dataclass sets missing fields to None rather than raising."""
    dc = generate_dataclass_model(Author)
    rows = [{"id": 42}]
    results = load_dataclass(dc, rows)
    assert results[0].id == 42
    assert results[0].name is None


# ---------------------------------------------------------------------------
# Plain (non-pydantic) model in SELECT query — SQL generation
# ---------------------------------------------------------------------------


def test_select_plain_model_sql_generation(db_dummy: PgDb):
    """A plain class with Annotated fields can drive SQL generation."""
    db = db_dummy

    class AuthorSel:
        id: Annotated[int, Author.id]
        name: Annotated[str, Author.name]

    query = db.select(AuthorSel).from_(Author)
    sql_result = query.sql()

    assert '"authors"."id" AS "id"' in sql_result.sql
    assert '"authors"."name" AS "name"' in sql_result.sql
    assert "FROM" in sql_result.sql


def test_select_all_dataclass_sql_generation(db_dummy: PgDb):
    """SelectAllDataclass (default Table.all()) drives correct SQL generation."""
    db = db_dummy

    query = db.select(Author.all()).from_(Author)
    sql_result = query.sql()

    assert '"authors"."id" AS "id"' in sql_result.sql
    assert '"authors"."name" AS "name"' in sql_result.sql


def test_select_all_pydantic_sql_generation(db_dummy: PgDb):
    """SelectAllPydantic (Table.all(use_pydantic=True)) drives correct SQL generation."""
    db = db_dummy

    query = db.select(Author.all(use_pydantic=True)).from_(Author)
    sql_result = query.sql()

    assert '"authors"."id" AS "id"' in sql_result.sql
    assert '"authors"."name" AS "name"' in sql_result.sql


# ---------------------------------------------------------------------------
# upgrade_model_nested_fields with plain dataclass
# ---------------------------------------------------------------------------


def test_upgrade_nested_fields_plain_dataclass_no_nesting():
    """upgrade_model_nested_fields on a plain dataclass with no nested tables is a no-op."""
    dc = generate_dataclass_model(Author)
    upgraded = upgrade_model_nested_fields(dc, use_pydantic=False)
    assert hasattr(upgraded, "__dataclass_fields__")
    assert "id" in upgraded.__dataclass_fields__
    assert "name" in upgraded.__dataclass_fields__


def test_upgrade_nested_fields_pydantic_no_nesting():
    """upgrade_model_nested_fields on a Pydantic model with no nesting is a no-op."""
    from pydantic import BaseModel

    m = generate_pydantic_model(Author)
    upgraded = upgrade_model_nested_fields(m, use_pydantic=True)
    assert issubclass(upgraded, BaseModel)
    assert "id" in upgraded.model_fields
    assert "name" in upgraded.model_fields


# ---------------------------------------------------------------------------
# Data round-trip: generate model then load data
# ---------------------------------------------------------------------------


def test_dataclass_model_round_trip():
    """Generating a dataclass model then loading data produces correct objects."""
    dc = generate_dataclass_model(Book)
    rows = [{"id": 10, "title": "Dune", "author_id": 5}]
    results = load_dataclass(dc, rows)
    assert results[0].id == 10
    assert results[0].title == "Dune"
    assert results[0].author_id == 5


# ---------------------------------------------------------------------------
# Plain class model with nested ManyTable — SQL generation
# ---------------------------------------------------------------------------


def test_select_with_nested_many_sql(db_dummy: PgDb):
    """A plain class model with a nested ManyTable annotation generates correct SQL."""
    from embar.query.where import Eq

    db = db_dummy

    class AuthorWithBooks:
        id: Annotated[int, Author.id]
        books: Annotated[list[Book], Book.many()]

    query = db.select(AuthorWithBooks).from_(Author).left_join(Book, Eq(Author.id, Book.author_id))
    # We just verify the sql() call doesn't blow up and has the table reference
    sql_result = query.sql()
    assert '"authors"."id" AS "id"' in sql_result.sql


# ---------------------------------------------------------------------------
# E2E: load data via SQLite with plain dataclass model
# ---------------------------------------------------------------------------


def test_e2e_plain_model_sqlite():
    """End-to-end test: insert and select using SQLite and a plain dataclass model."""
    import sqlite3

    from embar.db.sqlite import SqliteDb

    conn = sqlite3.connect(":memory:")
    db = SqliteDb(conn)
    db.migrate([Author]).run()

    author = Author(id=1, name="Alice")
    db.insert(Author).values(author).run()

    # Select with plain dataclass model (SelectAllDataclass)
    results = db.select(Author.all()).from_(Author).run()

    assert len(results) == 1
    row = results[0]
    # Should have the right field values
    assert row.id == 1
    assert row.name == "Alice"


def test_e2e_pydantic_model_sqlite():
    """End-to-end test: select using SQLite and SelectAllPydantic."""
    import sqlite3

    from embar.db.sqlite import SqliteDb

    conn = sqlite3.connect(":memory:")
    db = SqliteDb(conn)
    db.migrate([Author]).run()

    author = Author(id=2, name="Bob")
    db.insert(Author).values(author).run()

    results = db.select(Author.all(use_pydantic=True)).from_(Author).run()

    assert len(results) == 1
    row = results[0]
    assert row.id == 2
    assert row.name == "Bob"


def test_e2e_plain_class_model_sqlite():
    """End-to-end test: select using a user-defined plain class (not Table, not BaseModel)."""
    import sqlite3

    from embar.db.sqlite import SqliteDb

    conn = sqlite3.connect(":memory:")
    db = SqliteDb(conn)
    db.migrate([Author]).run()

    author = Author(id=3, name="Carol")
    db.insert(Author).values(author).run()

    class AuthorSel:
        id: Annotated[int, Author.id]
        name: Annotated[str, Author.name]

    results = db.select(AuthorSel).from_(Author).run()

    assert len(results) == 1
    row = results[0]
    assert row.id == 3
    assert row.name == "Carol"


def test_e2e_nested_many_plain_model_sqlite():
    """End-to-end: nested ManyTable with plain class model loads correctly via SQLite."""
    import sqlite3

    from embar.db.sqlite import SqliteDb
    from embar.query.where import Eq

    conn = sqlite3.connect(":memory:")
    db = SqliteDb(conn)
    db.migrate([Author, Book]).run()

    author = Author(id=1, name="Alice")
    book = Book(id=1, title="Dune", author_id=1)
    db.insert(Author).values(author).run()
    db.insert(Book).values(book).run()

    class AuthorWithBooks:
        id: Annotated[int, Author.id]
        name: Annotated[str, Author.name]
        books: Annotated[list[Book], Book.many()]

    results = (
        db.select(AuthorWithBooks)
        .from_(Author)
        .left_join(Book, Eq(Author.id, Book.author_id))
        .group_by(Author.id)
        .run()
    )

    assert len(results) == 1
    row = results[0]
    assert row.id == 1
    assert row.name == "Alice"
    nested = row.books
    assert len(nested) == 1
    assert nested[0].title == "Dune"
    assert nested[0].id == 1
