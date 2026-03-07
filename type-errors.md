# ty Type Errors Report

**ty version:** 0.0.21 (c1ad9f281 2026-03-06)  
**Total diagnostics:** 99 (97 errors + 2 warnings)

## Summary by Rule

| Rule | Count | ty bug? |
|------|-------|---------|
| `no-matching-overload` | 66 | ✅ Mostly — 60 are false positives, 6 are correct (psycopg `LiteralString`) |
| `invalid-argument-type` | 23 | ✅ Mostly — 13 are false positives, 10 are correct/expected |
| `unresolved-import` | 6 | ❌ No — genuinely missing code |
| `invalid-assignment` | 2 | ✅ Likely yes |
| `possibly-missing-attribute` (warning) | 2 | ✅ Yes (same root cause as typevar bound issue) |

**False positives caused by ty bugs: ~77/99 (78%)**  
**Correct errors that need suppression or code fixes: ~22/99 (22%)**

---

## Category 1: Overloaded `run()` fails on union db types — 60 errors

**Rule:** `no-matching-overload`  
**Files:** `test_insert.py` (20), `test_transactions.py` (17), `test_sync_async.py` (7), `conftest.py` (6), `test_postgres.py` (6), `test_select.py` (2), `test_update.py` (2)

### Pattern

The ORM uses overloads on `self` to distinguish sync vs async behavior:

```python
class InsertQueryReady[T: Table, Db: AllDbBase]:
    @overload
    def run(self: InsertQueryReady[T, DbBase]) -> None: ...
    @overload
    def run(self: InsertQueryReady[T, AsyncDbBase]) -> InsertQueryReady[T, Db]: ...
    def run(self) -> InsertQueryReady[T, Db] | None: ...
```

Tests use a parametrized fixture `db: SqliteDb | PgDb` (both are `DbBase` subclasses). When `db.insert(User).values(user).run()` is called, ty resolves the `.run()` method to a **union of two overloaded methods**:

```
(Overload[() -> None, () -> InsertQueryReady[User, SqliteDb]])
| (Overload[() -> None, () -> InsertQueryReady[User, PgDb]])
```

ty then reports **both** union variants as "incompatible with this call site", even though the `() -> None` overload in each variant should clearly match. The same pattern affects `SelectQueryReady.run()`, `UpdateQueryReady.run()`, `Migration.run()`, and `DeleteQueryReady.run()`.

### Root Cause

ty doesn't correctly resolve overloads that narrow on `self` type when the receiver is a union. It needs to distribute the union across each variant, try the overloads independently, and then merge the results.

### Relevant ty Issues

- **[#1169](https://github.com/astral-sh/ty/issues/1169)** — "Incorrect handling of bound methods that are overloaded on the type of `self`" — **directly describes this bug**
- **[#2657](https://github.com/astral-sh/ty/issues/2657)** — "Expand unions in order to solve generic overloads more precisely" — the underlying type-solving limitation

---

## Category 2: psycopg `str` vs `LiteralString` — 14 errors

**Rules:** `no-matching-overload` (6) + `invalid-argument-type` (8)  
**File:** `src/embar/db/pg.py`

### Pattern

psycopg's `cursor.execute()` and `cursor.executemany()` use overloads to distinguish:
- `QueryNoTemplate` = `LiteralString | bytes | SQL | Composed` (first overload, with params)
- `Template` (second overload, without params)

The codebase passes dynamic `str` values to these methods. All 14 call sites already have `# ty: ignore[invalid-argument-type]` comments because pyright had the same error.

**Subgroup A — f-string execute calls (6 `no-matching-overload`):**
```python
cursor.execute(f"TRUNCATE TABLE {table_names} CASCADE")  # ty: ignore[invalid-argument-type]
```
An f-string is `str`, not `LiteralString`, so it doesn't match the first overload. And it's not a `Template`, so it doesn't match the second.

**Subgroup B — `query.sql` execute calls (4 `invalid-argument-type`):**
```python
conn.execute(query.sql, query.params)  # ty: ignore[invalid-argument-type]
```

**Subgroup C — `query.sql` executemany calls (4 `invalid-argument-type`):**
```python
cur.executemany(query.sql, params)  # ty: ignore[invalid-argument-type]
```

### Root Cause

**Not a ty bug.** This is correct type checking — psycopg intentionally uses `LiteralString` to prevent SQL injection. The code already suppresses these in pyright. They just need equivalent `# ty: ignore[...]` comments.

---

## Category 3: TypeVar bound method calls on generic union — 8 diagnostics

**Rules:** `invalid-argument-type` (6) + `possibly-missing-attribute` warning (2)  
**File:** `src/embar/db/pg.py`

### Pattern

```python
class ConnectionWrapper[C: Connection | ConnectionPool]:
    conn_or_pool: C

    def close(self):
        self.conn_or_pool.close()
        # Error: "Argument type C@ConnectionWrapper does not satisfy upper bound
        #         Connection[...] of type variable Self"

    def __enter__(self) -> Connection:
        if isinstance(self.conn_or_pool, Connection):
            return self.conn_or_pool
        self.conn_or_pool.open()
        # Error: "Argument type C@ConnectionWrapper does not satisfy upper bound
        #         ConnectionPool[...] of type variable Self"
```

Both `Connection` and `ConnectionPool` have `.close()` methods, so calling `.close()` on `C: Connection | ConnectionPool` should be valid. ty fails because it can't properly call methods through a typevar's upper bound when the bound is a union.

**Breakdown:** `.close()` errors × 4 (2 in sync wrapper, 2 in async wrapper — each one doubled because ty reports it separately for each union variant), `.open()` errors × 2 (sync + async), plus 2 `possibly-missing-attribute` warnings for `.open()`.

### Relevant ty Issues

- **[#1503](https://github.com/astral-sh/ty/issues/1503)** — "Method call on constrained typevar emits invalid-argument-type" — exact same pattern
- **[#2585](https://github.com/astral-sh/ty/issues/2585)** — "False positive on calls to bound methods of classes when using a typevar bound to a union" — exact same pattern

---

## Category 4: Generic subclass inference with descriptors — 8 errors

**Rule:** `invalid-argument-type` (`__init__`)  
**Files:** `example/app/app.py` (3), `tests/e2e/test_select.py` (3), `tests/conftest.py` (1), `src/embar/tools/commands.py` (1)

### Subgroup A: `Eq(User.id, Message.user_id)` — 6 errors

```python
class Column[T: PyType]:
    @overload
    def __get__(self, obj: None, owner: type) -> Self: ...

class Integer(Column[int]): ...

class Eq[T: PyType]:
    def __init__(self, left: Column[T] | ClauseBase, right: Column[T] | T): ...
```

When calling `Eq(User.id, Message.user_id)`:
- `User.id` is class access → descriptor `__get__` returns `Self` → `Integer`
- `Integer` IS `Column[int]`, so `T` should be inferred as `int`
- But ty reports: **`Expected Column[int | Integer] | ClauseBase, found Integer`**

ty incorrectly includes `Integer` (the subclass) in the type parameter alongside `int`, producing `Column[int | Integer]` instead of just solving `T = int`.

### Subgroup B: `PgDb(None)` — 2 errors

```python
db = PgDb(None)  # ty: ignore[invalid-argument-type]
```

These are **genuine type errors** (passing `None` where a `Connection | ConnectionPool` is expected). The code already suppresses them in pyright. They need `# ty: ignore[...]` too.

### Relevant ty Issues

- **[#623](https://github.com/astral-sh/ty/issues/623)** — "Improve typevar solving" — ty doesn't solve typevars as precisely as pyright/mypy

---

## Category 5: `Self` not satisfying typevar bound — 1 error

**Rule:** `invalid-argument-type`  
**File:** `src/embar/column/common.py:132`

### Pattern

```python
@dataclass
class ManyColumn[T: ColumnBase]:
    of: T

class Column[T: PyType](ColumnBase):
    def many(self) -> ManyColumn[Self]:
        return ManyColumn[Self](self)
        #                       ^^^^ Expected `T@Column`, found `Self@many`
```

`self` inside `Column.many()` has type `Self` (bound to a `Column[T]` subclass). `ManyColumn.__init__` takes `of: T` where `T: ColumnBase`. Since `Column` inherits from `ColumnBase`, `Self` should satisfy the bound. ty doesn't recognize this.

---

## Category 6: `list[T]` not assignable to `list[PyType]` — 2 errors

**Rule:** `invalid-assignment`  
**File:** `src/embar/query/where.py`

### Pattern

```python
class InArray[T: PyType](ClauseBase):
    values: list[PyType]

    def __init__(self, column: Column[T], values: list[T]):
        self.values = values
        # Error: list[T@InArray] not assignable to list[PyType]
```

Since `list` is invariant, `list[T]` is technically not a subtype of `list[PyType]` even when `T: PyType`. However, pyright allows this because `T` is bounded by `PyType` and the assignment is safe in practice (you can't insert non-`T` items into the list through the `list[PyType]` reference without other errors). ty is stricter here.

### Possible Fix

Change the attribute type to `list[T]` instead of `list[PyType]`, or use `Sequence[PyType]` (covariant).

---

## Category 7: Unresolved imports — 6 errors

**Rule:** `unresolved-import`  
**Files:** `src/embar/tools/commands.py` (3), `src/embar/tools/migrate.py` (3)

### Missing items

| Import | Status |
|--------|--------|
| `embar.tools.llm` (entire module) | Deleted in commit `ddedd4a` |
| `embar.tools.utils.get_api_key` | Doesn't exist in `utils.py` |
| `embar.tools.fmt.format_migration_output` | Doesn't exist in `fmt.py` |
| `embar.tools.models.MigrationDiff` | Doesn't exist in `models.py` |
| `embar.tools.models.TableMatch` | Doesn't exist in `models.py` |

### Root Cause

**These are genuine issues** — the imports reference code that was deleted/never created. They would fail at runtime if the code paths were hit. **Not ty bugs.**

---

## Summary Table

| # | Category | Errors | ty Bug? | Key GitHub Issue(s) |
|---|----------|--------|---------|-------------------|
| 1 | Overloaded `run()` on union `self` | 60 | ✅ Yes | [#1169](https://github.com/astral-sh/ty/issues/1169), [#2657](https://github.com/astral-sh/ty/issues/2657) |
| 2 | `str` → `LiteralString` (psycopg) | 14 | ❌ Correct (needs `ty: ignore`) | N/A |
| 3 | TypeVar bound method calls on union | 8 | ✅ Yes | [#1503](https://github.com/astral-sh/ty/issues/1503), [#2585](https://github.com/astral-sh/ty/issues/2585) |
| 4a | Descriptor subclass generic inference | 6 | ✅ Yes | [#623](https://github.com/astral-sh/ty/issues/623) |
| 4b | `PgDb(None)` suppressed | 2 | ❌ Correct (needs `ty: ignore`) | N/A |
| 5 | `Self` vs typevar bound | 1 | ✅ Yes | — |
| 6 | `list[T]` vs `list[PyType]` (invariance) | 2 | ⚠️ Debatable | — |
| 7 | Genuinely missing imports | 6 | ❌ Real bugs | N/A |
| | **Total** | **99** | | |

### Actionable Items

1. **Wait for ty fixes** on #1169 + #2657 (60 errors), #1503 + #2585 (8 errors), #623 (6 errors) — **74 errors blocked on ty**
2. **Existing `# ty: ignore[...]` comments** are already in place on 16 lines (14 psycopg + 2 `PgDb(None)`)
3. **Fix broken imports** in `tools/commands.py` and `tools/migrate.py` — 6 errors from deleted code
4. **Optionally fix** `InArray`/`NotInArray` by changing `values: list[PyType]` → `values: list[T]` (2 errors)
5. **Optionally fix** `ManyColumn[Self](self)` — may resolve once ty improves `Self` handling (1 error)
