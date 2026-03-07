# Public API Type Issues (ty compatibility)

These are the ty errors that affect **users of the library** — i.e., errors that appear when downstream code calls the public API. Each section includes a proposed fix.

---

## Issue 1: `run()` overloads fail when db is a union type — 60 errors

### How it appears in the public API

Any user who writes a function accepting `SqliteDb | PgDb` (or any union of db types) and calls `.run()` gets a `no-matching-overload` error:

```python
def my_func(db: SqliteDb | PgDb):
    db.insert(User).values(user).run()          # ❌ no-matching-overload
    db.select(UserSel).from_(User).run()        # ❌ no-matching-overload
    db.update(Message).set(data).where(...).run()  # ❌ no-matching-overload
    db.delete(User).run()                        # ❌ no-matching-overload
    db.migrate([User]).run()                     # ❌ no-matching-overload
```

This also affects `db.sql(t"...").run()` and `.returning().run()`.

### Root cause

All `run()` methods use self-type overloads to distinguish sync vs async:

```python
class InsertQueryReady[T: Table, Db: AllDbBase]:
    @overload
    def run(self: InsertQueryReady[T, DbBase]) -> None: ...
    @overload
    def run(self: InsertQueryReady[T, AsyncDbBase]) -> InsertQueryReady[T, Db]: ...
    def run(self) -> InsertQueryReady[T, Db] | None: ...
```

When the `Db` type parameter is a union like `SqliteDb | PgDb`, ty creates a union of overloaded methods and then can't match either variant to the call. This is ty bug [#1169](https://github.com/astral-sh/ty/issues/1169).

### Proposed fix: Remove self-type Db narrowing from `run()` overloads

**Key insight:** The overloads that narrow on `Db` (sync vs async) are the problem. But overloads that narrow on *other* type parameters (like `M` vs `SelectAll`) work fine, because those don't create a union-of-overloaded-methods situation — the `M` parameter is already resolved by the time `run()` is called.

The fix is:
1. **Remove** overloads that narrow on `Db` (the sync/async distinction)
2. **Keep** overloads that narrow on `M` (the `SelectAll` vs model distinction)

For the sync/async split: `__await__` already handles async. The `run()` method is sync-only. For `Migration` and `DbSql`, where `await x.run()` is used, `run()` returns `Self` (which has `__await__`).

**Changes required (implementation only, no external API change):**

| Class | Current `run()` | Proposed `run()` |
|-------|----------------|-----------------|
| `InsertQueryReady` | 2 overloads (Db narrowing) → `None \| Self` | `run() -> None` |
| `InsertQueryReturning` | 2 overloads (Db narrowing) → `list[T] \| Self` | `run() -> list[T]` |
| `SelectQueryReady` | 3 overloads (M + Db narrowing) → `Sequence[T\|M] \| Self` | 2 overloads (M narrowing only) → `Sequence[T]` or `Sequence[M]` |
| `UpdateQueryReady` | 2 overloads (Db narrowing) → `None \| Self` | `run() -> None` |
| `UpdateQueryReturning` | 2 overloads (Db narrowing) → `list[T] \| Self` | `run() -> list[T]` |
| `DeleteQueryReady` | 2 overloads (Db narrowing) → `None \| Self` | `run() -> None` |
| `DeleteQueryReturning` | 2 overloads (Db narrowing) → `list[T] \| Self` | `run() -> list[T]` |
| `Migration` | 2 overloads (Db narrowing) → `None \| Self` | `run() -> Self` |
| `DbSql` | 2 overloads (Db narrowing) → `None \| Self` | `run() -> Self` |
| `DbSqlReturning` | 2 overloads (Db narrowing) → `Sequence[M] \| Self` | `run() -> Sequence[M]` |

### `SelectQueryReady` — preserving the `M` vs `SelectAll` distinction

The current `SelectQueryReady.run()` has three overloads:

```python
@overload
def run(self: SelectQueryReady[SelectAll, T, DbBase]) -> Sequence[T]: ...
@overload
def run(self: SelectQueryReady[M, T, DbBase]) -> Sequence[M]: ...
@overload
def run(self: SelectQueryReady[M, T, AsyncDbBase]) -> SelectQueryReady[M, T, Db]: ...
```

The fix keeps the `SelectAll` vs `M` distinction but drops the `Db` narrowing:

```python
@overload
def run(self: SelectQueryReady[SelectAll, T, Db]) -> Sequence[T]: ...
@overload
def run(self) -> Sequence[M]: ...
def run(self) -> Sequence[M | T]:
    ...
```

This works because the overloads narrow on `M` (is it `SelectAll` or a user model?), not on `Db`. ty handles this correctly — it checks whether the concrete `M` is `SelectAll`, and if so picks the first overload; otherwise the fallback.

**Verified return types** (all correct, zero errors):

| Call site | Inferred return type |
|-----------|---------------------|
| `SelectQueryReady[str, User, SqliteDb \| PgDb].run()` | `Sequence[str]` ✅ |
| `SelectQueryReady[SelectAll, User, SqliteDb \| PgDb].run()` | `Sequence[User]` ✅ |
| `SelectQueryReady[str, User, PgDb].run()` | `Sequence[str]` ✅ |
| `SelectQueryReady[SelectAll, User, PgDb].run()` | `Sequence[User]` ✅ |
| `InsertQueryReady[User, SqliteDb \| PgDb].run()` | `None` ✅ |
| `InsertQueryReturning[User, SqliteDb \| PgDb].run()` | `list[User]` ✅ |
| `Migration[SqliteDb \| PgDb].run()` | `Migration[SqliteDb \| PgDb]` (Self) ✅ |
| `await Migration[AsyncPgDb].run()` | `None` (via `__await__`) ✅ |
| `await SelectQueryReady[str, User, AsyncPgDb]` | `Sequence[str]` ✅ |
| `await SelectQueryReady[SelectAll, User, AsyncPgDb]` | `Sequence[User]` ✅ |

### Behavioral notes

- **Sync callers:** Return types are identical or better than before. `SelectQueryReady` preserves the `M` vs `SelectAll` distinction.
- **Async callers using `await query`:** No change — `__await__` is unchanged.
- **Async callers using `await query.run()`:** Only `Migration` and `DbSql` support this (returning `Self`). For other query types, `run()` now returns `None` or the result — if an async user accidentally calls `.run()`, they get a clear type rather than a silently-wrong awaitable.
- **`Migration` and `DbSql`:** `run() -> Self` means sync callers get a `Migration` object back. They can ignore it — this is a minor change but matches the `await db.migrate([...]).run()` pattern used in tests.

---

## Issue 2: `Eq(User.id, Message.user_id)` — descriptor subclass generic inference — 6 errors

### How it appears in the public API

When comparing two columns in `Eq`, `Ne`, `Gt`, `Gte`, `Lt`, `Lte` (the six comparison operators):

```python
Eq(User.id, Message.user_id)           # ❌ Expected Column[int | Integer], found Integer
Eq(User.id, Message.user_id)           # ❌ (same)
```

But Column + literal value works fine:

```python
Eq(User.id, 1)                         # ✅ works
Eq(User.email, "foo%")                 # ✅ works
Like(User.email, "foo%")               # ✅ works
```

### Root cause

`User.id` returns `Integer` (via the `__get__` descriptor returning `Self`). `Integer` IS `Column[int]`, but when ty tries to solve `T` in `Column[T] | ClauseBase`, it creates the spurious union `Column[int | Integer]` instead of solving `T = int`.

This only affects the case where *both* arguments are column descriptors, because ty can infer `T` from a literal value but gets confused when both sides are subclass instances.

### Proposed fix: Use overloads to separate Column+Column from Column+value

**Change the signature from:**
```python
class Eq[T: PyType](ClauseBase):
    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T): ...
```

**To:**
```python
class Eq(ClauseBase):
    @overload
    def __init__[T: PyType](self, left: Column[T], right: Column[T]) -> None: ...
    @overload
    def __init__[T: PyType](self, left: Column[T], right: T) -> None: ...
    @overload
    def __init__(self, left: ClauseBase, right: ColumnBase | PyType) -> None: ...
    def __init__(self, left: Column[Any] | ClauseBase, right: Column[Any] | PyType) -> None: ...
```

**Key changes:**
1. The class is no longer generic (`Eq` instead of `Eq[T: PyType]`). The generic `T` moves to the overload level.
2. Three overloads handle: Column+Column (same type), Column+value (type-safe), and ClauseBase+anything (for composed clauses).

**API impact:** Minor — `Eq` loses its class-level type parameter. But users never write `Eq[int](...)` explicitly; the type parameter was always inferred. The class was only generic for the purpose of the `__init__` constraint.

**Type safety verified:**
- `Eq(User.id, Message.user_id)` ✅ — Column[int] + Column[int]
- `Eq(User.id, 1)` ✅ — Column[int] + int
- `Eq(User.email, "foo%")` ✅ — Column[str] + str
- `Eq(User.id, User.email)` ❌ correctly rejected — Column[int] + Column[str]
- `Eq(User.id, "wrong")` ❌ correctly rejected — Column[int] + str
- `Eq(User.email, 42)` ❌ correctly rejected — Column[str] + int

Different `Column[int]` subclasses (e.g., `Integer` + `SmallInt`) work correctly.

**Applies to:** `Eq`, `Ne`, `Gt`, `Gte`, `Lt`, `Lte` (6 classes with `Column[T] | ClauseBase, Column[T] | T` pattern).

**Not needed for:** `Like`, `Ilike`, `NotLike`, `Between`, `NotBetween`, `InArray`, `NotInArray` — these only take `Column[T]` on the left with a value on the right, so ty can infer `T` from the value argument.

---

## Issue 3: `ManyColumn[Self](self)` — Self vs typevar bound — 1 error

### How it appears in the public API

This is internal to `Column.many()` but affects any user calling it:

```python
class MyModel(BaseModel):
    values: Annotated[list[str], MyTable.my_col.many()]  # calls Column.many() internally
```

The error is in `src/embar/column/common.py:132`:
```python
def many(self) -> ManyColumn[Self]:
    return ManyColumn[Self](self)
    #                 ^^^^ Expected `T@Column`, found `Self@many`
```

### Root cause

When explicitly parameterizing `ManyColumn[Self]`, ty doesn't recognize that `Self` (in the context of `Column.many()`) satisfies the bound `T: ColumnBase` on `ManyColumn[T: ColumnBase]`.

### Proposed fix: Drop explicit type parameter

**Change from:**
```python
return ManyColumn[Self](self)
```

**To:**
```python
return ManyColumn(self)
```

Let ty infer the type parameter from the constructor argument. Verified: ty infers `ManyColumn[Integer]` (correct) when called as `User.id.many()`.

**API impact:** None — the return type annotation `-> ManyColumn[Self]` is unchanged, only the implementation.

---

## Issue 4: `InArray`/`NotInArray` — `list[T]` vs `list[PyType]` invariance — 2 errors

### How it appears in the public API

This is internal to `InArray.__init__` but affects any user creating an `InArray`:

```python
InArray(User.id, [1, 2, 3])  # works at call site, but ty errors on the class itself
```

The error is in the class body, not at the call site — but it means the module itself can't be imported without ty warnings.

### Root cause

```python
class InArray[T: PyType](ClauseBase):
    values: list[PyType]              # attribute typed as list[PyType]

    def __init__(self, column: Column[T], values: list[T]):
        self.values = values          # ❌ list[T] not assignable to list[PyType]
```

`list` is invariant, so `list[int]` is not `list[PyType]` even though `int` is a `PyType`.

### Proposed fix: Change attribute type to `list[T]`

```python
class InArray[T: PyType](ClauseBase):
    values: list[T]                   # Changed from list[PyType]
```

**API impact:** None — the `values` attribute is only used internally in `.sql()`. The public constructor signature is unchanged.

**Applies to:** `InArray` and `NotInArray` (2 classes).

---

## Summary

| Issue | Errors | Fix | API impact |
|-------|--------|-----|------------|
| 1. `run()` overloads on union self | 60 | Remove Db-narrowing overloads; keep M-narrowing overloads on select | None for sync callers. `Migration`/`DbSql` `run()` returns `Self` instead of `None`. |
| 2. `Eq(Col, Col)` descriptor inference | 6 | Overloaded `__init__` | Minor — `Eq` et al. lose class-level type param (never used explicitly by callers) |
| 3. `ManyColumn[Self](self)` | 1 | Drop explicit `[Self]` | None |
| 4. `list[T]` invariance | 2 | Change attribute type | None |
| **Total** | **69** | | |

All 69 errors can be fixed with implementation changes. The only external-facing differences are:

1. **`run()` on insert/update/delete** returns `None` instead of `Self` when called on an async db. This is actually better — it fails clearly rather than returning a no-op awaitable.
2. **`run()` on `Migration`/`DbSql`** returns `Self` always (instead of `None` for sync). Sync callers just ignore the return value.
3. **`run()` on select** preserves the `SelectAll` vs `M` distinction via overloads that narrow on `M` (not `Db`). Return types are `Sequence[T]` for `SelectAll` and `Sequence[M]` for a model — identical to the current behavior.
4. **`Eq`, `Ne`, `Gt`, `Gte`, `Lt`, `Lte`** lose their class-level `[T: PyType]` type parameter but keep the same constructor behavior via overloads. Type safety is preserved.
