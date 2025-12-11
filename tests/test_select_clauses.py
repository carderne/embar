"""Tests for HAVING, ORDER BY, and OFFSET clauses."""

from typing import Annotated

from pydantic import BaseModel

from embar.db.pg import PgDb
from embar.model import SelectAll
from embar.query.order_by import Asc, Desc
from embar.query.where import Gt
from embar.sql import Sql

from .schemas.schema import Message, User


def test_order_by_bare_column(db_dummy: PgDb):
    """Test ORDER BY with bare column reference (defaults to ASC)."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .order_by(User.email)
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert '"users"."user_email"' in sql_result.sql


def test_order_by_asc(db_dummy: PgDb):
    """Test ORDER BY with Asc()."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .order_by(Asc(User.email))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert "ASC" in sql_result.sql
    assert '"users"."user_email"' in sql_result.sql


def test_order_by_desc(db_dummy: PgDb):
    """Test ORDER BY with Desc()."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .order_by(Desc(User.id))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert "DESC" in sql_result.sql
    assert '"users"."id"' in sql_result.sql


def test_order_by_multiple(db_dummy: PgDb):
    """Test ORDER BY with multiple columns in one call."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .order_by(Asc(User.email), Desc(User.id))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    # Check both columns are present in the ORDER BY clause
    assert '"users"."user_email" ASC' in sql_result.sql
    assert '"users"."id" DESC' in sql_result.sql


def test_order_by_chained(db_dummy: PgDb):
    """Test ORDER BY with multiple chained calls."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .order_by(Asc(User.email))
        .order_by(Desc(User.id))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert '"users"."user_email" ASC' in sql_result.sql
    assert '"users"."id" DESC' in sql_result.sql


def test_order_by_with_nulls_first(db_dummy: PgDb):
    """Test ORDER BY with NULLS FIRST."""
    db = db_dummy

    class MessageSel(BaseModel):
        id: Annotated[int, Message.id]
        content: Annotated[str, Message.content]

    # fmt: off
    query = (
        db.select(MessageSel)
        .from_(Message)
        .order_by(Asc(Message.content, nulls="first"))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert "NULLS FIRST" in sql_result.sql


def test_order_by_with_nulls_last(db_dummy: PgDb):
    """Test ORDER BY with NULLS LAST."""
    db = db_dummy

    class MessageSel(BaseModel):
        id: Annotated[int, Message.id]
        content: Annotated[str, Message.content]

    # fmt: off
    query = (
        db.select(MessageSel)
        .from_(Message)
        .order_by(Desc(Message.content, nulls="last"))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert "NULLS LAST" in sql_result.sql


def test_order_by_raw_sql(db_dummy: PgDb):
    """Test ORDER BY with raw SQL."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .order_by(Sql(t"{User.id} DESC"))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert '"users"."id" DESC' in sql_result.sql


def test_limit_with_offset(db_dummy: PgDb):
    """Test LIMIT with OFFSET for pagination."""
    db = db_dummy

    # fmt: off
    query = (
        db.select(SelectAll)
        .from_(User)
        .limit(5)
        .offset(10)
    )
    # fmt: on

    sql_result = query.sql()
    assert "LIMIT 5" in sql_result.sql
    assert "OFFSET 10" in sql_result.sql


def test_having_clause(db_dummy: PgDb):
    """Test HAVING clause with GROUP BY."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .group_by(User.id)
        .having(Gt(User.id, 0))
    )
    # fmt: on

    sql_result = query.sql()
    assert "GROUP BY" in sql_result.sql
    assert "HAVING" in sql_result.sql
    assert '"users"."id" >' in sql_result.sql


def test_full_query_with_many_clauses(db_dummy: PgDb):
    """Test a query with HAVING, ORDER BY, and OFFSET together."""
    db = db_dummy

    class UserSel(BaseModel):
        id: Annotated[int, User.id]
        email: Annotated[str, User.email]

    # fmt: off
    query = (
        db.select(UserSel)
        .from_(User)
        .where(Gt(User.id, 0))
        .group_by(User.id)
        .having(Gt(User.id, 0))
        .order_by(Desc(User.id))
        .limit(10)
        .offset(5)
    )
    # fmt: on

    sql_result = query.sql()

    # Verify all clauses are present
    assert "WHERE" in sql_result.sql
    assert "GROUP BY" in sql_result.sql
    assert "HAVING" in sql_result.sql
    assert "ORDER BY" in sql_result.sql
    assert "LIMIT 10" in sql_result.sql
    assert "OFFSET 5" in sql_result.sql

    # Verify correct SQL clause ordering
    sql_lower = sql_result.sql
    where_pos = sql_lower.find("WHERE")
    group_pos = sql_lower.find("GROUP BY")
    having_pos = sql_lower.find("HAVING")
    order_pos = sql_lower.find("ORDER BY")
    limit_pos = sql_lower.find("LIMIT")
    offset_pos = sql_lower.find("OFFSET")

    # SQL clause order should be: WHERE < GROUP BY < HAVING < ORDER BY < LIMIT < OFFSET
    assert where_pos < group_pos
    assert group_pos < having_pos
    assert having_pos < order_pos
    assert order_pos < limit_pos
    assert limit_pos < offset_pos
