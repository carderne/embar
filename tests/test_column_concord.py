"""
Tests that column annotations and field specifiers agree on type and nullability.

Static checks use `ty: ignore[error-name]` — the fact that ty does NOT complain
about the ignores confirms the code is correctly flagged as invalid.
"""

import pytest

from embar.column.base import ColumnBase
from embar.column.common import Integer, NullInteger, NullText, Text, integer, text
from embar.column.pg import NullVarchar, Varchar, varchar
from embar.table import Table

# ── Valid tables ──────────────────────────────────────────────────────────


class Required(Table):
    id: Integer = integer(primary=True)
    name: Text = text(not_null=True)


class WithDefaults(Table):
    id: Integer = integer(default=1)
    label: Text = text(default="x")
    tag: Varchar = varchar(default="v")


class Nullable(Table):
    email: NullText = text(default=None)
    age: NullInteger = integer(default=None)
    alias: NullVarchar = varchar(default=None)


class Mixed(Table):
    id: Integer = integer(primary=True)
    name: Text = text(not_null=True)
    email: NullText = text(default=None)
    label: Text = text(default="unlabeled")


# ── Constructor behaviour ────────────────────────────────────────────────


def test_required_fields_must_be_provided():
    with pytest.raises(TypeError, match="required fields"):
        Required(name="x")  # ty: ignore[missing-argument]


def test_defaults_make_fields_optional():
    row = WithDefaults()
    assert row.id == 1
    assert row.label == "x"
    assert row.tag == "v"


def test_nullable_defaults_to_none():
    row = Nullable()
    assert row.email is None
    assert row.age is None
    assert row.alias is None


def test_nullable_accepts_none():
    row = Nullable(email=None, age=None)
    assert row.email is None
    assert row.age is None


def test_nullable_accepts_value():
    row = Nullable(email="a@b.com", age=42)
    assert row.email == "a@b.com"
    assert row.age == 42


def test_mixed_table():
    row = Mixed(id=1, name="hi")
    assert row.email is None
    assert row.label == "unlabeled"


# ── Class-level access is ColumnBase ─────────────────────────────────────


def _wants_column(x: ColumnBase) -> None:
    pass


def test_class_access_is_column():
    _wants_column(Required.id)
    _wants_column(Required.name)
    _wants_column(Nullable.email)
    _wants_column(Nullable.age)
    _wants_column(Mixed.email)
    _wants_column(Mixed.label)


# ── Static type-checks (ty: ignore confirms the error is real) ───────────
# These lines are only validated by the type-checker, not executed.


def _static_checks_not_called() -> None:
    Required(name="x")  # ty: ignore[missing-argument]
    Required(id="oops", name="x")  # ty: ignore[invalid-argument-type]
    Required(id=1, name=None)  # ty: ignore[invalid-argument-type]


# ── Runtime validation: annotation vs specifier mismatches ───────────────


def test_wrong_base_type():
    with pytest.raises(TypeError, match="annotation type is Integer.*returns Text"):

        class T(Table):
            x: Integer = text()  # runtime-only: ty can't catch this


def test_wrong_base_type_reversed():
    with pytest.raises(TypeError, match="annotation type is Text.*returns Integer"):

        class T(Table):
            x: Text = integer()  # runtime-only: ty can't catch this


def test_nullable_ann_with_non_null_specifier():
    with pytest.raises(TypeError, match="annotation is nullable.*non-nullable"):

        class T(Table):
            x: NullText = text()


def test_non_null_ann_with_nullable_specifier():
    with pytest.raises(TypeError, match="annotation is non-nullable.*nullable"):

        class T(Table):
            x: Text = text(default=None)  # ty: ignore[invalid-assignment]


def test_null_type_param_mismatch():
    with pytest.raises(TypeError, match=r"Null\[int\].*py_type=str"):

        class T(Table):
            x: NullInteger = text(default=None)  # ty: ignore[invalid-assignment]


def test_nullable_ann_with_not_null_true():
    with pytest.raises(TypeError, match="annotation is nullable.*not_null=True"):

        class T(Table):
            x: NullText = text(default=None, not_null=True)
