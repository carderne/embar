"""Tests for pgvector support (L2Distance)."""

from typing import Annotated

from pydantic import BaseModel

from embar.column.common import Integer
from embar.column.pg import Vector
from embar.config import EmbarConfig
from embar.db.pg import PgDb
from embar.query.vector import CosineDistance, L2Distance
from embar.query.where import Gt, Lt
from embar.table import Table


class Embedding(Table):
    embar_config: EmbarConfig = EmbarConfig(table_name="embeddings")

    id: Integer = Integer(primary=True)
    vec_a: Vector = Vector(3)
    vec_b: Vector = Vector(3)


def test_order_by_l2distance_with_literal(db_dummy: PgDb):
    """Test ORDER BY with L2Distance using a literal vector."""

    class EmbeddingSel(BaseModel):
        id: Annotated[int, Embedding.id]

    # fmt: off
    query = (
        db_dummy.select(EmbeddingSel)
        .from_(Embedding)
        .order_by(L2Distance(Embedding.vec_a, [1.0, 2.0, 3.0]))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert "<->" in sql_result.sql
    assert '"embeddings"."vec_a"' in sql_result.sql


def test_order_by_l2distance_with_column(db_dummy: PgDb):
    """Test ORDER BY with L2Distance comparing two vector columns."""

    class EmbeddingSel(BaseModel):
        id: Annotated[int, Embedding.id]

    # fmt: off
    query = (
        db_dummy.select(EmbeddingSel)
        .from_(Embedding)
        .order_by(L2Distance(Embedding.vec_a, Embedding.vec_b))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert "<->" in sql_result.sql
    assert '"embeddings"."vec_a"' in sql_result.sql
    assert '"embeddings"."vec_b"' in sql_result.sql


def test_where_l2distance_with_lt(db_dummy: PgDb):
    """Test WHERE clause filtering by L2Distance < threshold."""

    class EmbeddingSel(BaseModel):
        id: Annotated[int, Embedding.id]

    # fmt: off
    query = (
        db_dummy.select(EmbeddingSel)
        .from_(Embedding)
        .where(Lt(L2Distance(Embedding.vec_a, [1.0, 2.0, 3.0]), 0.5))
    )
    # fmt: on

    sql_result = query.sql()
    assert "WHERE" in sql_result.sql
    assert "<->" in sql_result.sql
    assert "<" in sql_result.sql
    assert '"embeddings"."vec_a"' in sql_result.sql


def test_where_l2distance_with_gt(db_dummy: PgDb):
    """Test WHERE clause filtering by L2Distance > threshold."""

    class EmbeddingSel(BaseModel):
        id: Annotated[int, Embedding.id]

    # fmt: off
    query = (
        db_dummy.select(EmbeddingSel)
        .from_(Embedding)
        .where(Gt(L2Distance(Embedding.vec_a, [1.0, 2.0, 3.0]), 0.5))
    )
    # fmt: on

    sql_result = query.sql()
    assert "WHERE" in sql_result.sql
    assert "<->" in sql_result.sql
    assert ">" in sql_result.sql
    assert '"embeddings"."vec_a"' in sql_result.sql


def test_order_by_cosine_distance_with_literal(db_dummy: PgDb):
    """Test ORDER BY with CosineDistance using a literal vector."""

    class EmbeddingSel(BaseModel):
        id: Annotated[int, Embedding.id]

    # fmt: off
    query = (
        db_dummy.select(EmbeddingSel)
        .from_(Embedding)
        .order_by(CosineDistance(Embedding.vec_a, [1.0, 2.0, 3.0]))
    )
    # fmt: on

    sql_result = query.sql()
    assert "ORDER BY" in sql_result.sql
    assert "<=>" in sql_result.sql
    assert '"embeddings"."vec_a"' in sql_result.sql
