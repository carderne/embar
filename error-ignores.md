# Pyright → ty Error Ignore Migration

## Mapping

| Pyright Rule | ty Equivalent | Action |
|---|---|---|
| `reportArgumentType` | `invalid-argument-type` | Replace |
| `reportAssignmentType` | `invalid-assignment` | Replace |
| `reportCallIssue` | `missing-argument` | Replace (used for missing required args in constructor) |
| `reportGeneralTypeIssues` | `unresolved-attribute` | Replace (used for attribute access on possibly-wrong type) |
| `reportPrivateImportUsage` | *(no equivalent)* | Remove comment — ty does not flag private imports |
| `reportPrivateUsage` | *(no equivalent)* | Remove comment — ty does not flag private attribute/method access |
| `reportUnannotatedClassAttribute` | *(no equivalent)* | Remove comment — ty does not flag unannotated class attributes |
| `reportUninitializedInstanceVariable` | *(no equivalent)* | Remove comment — ty does not flag uninitialized instance variables |
| `reportUnusedClass` | *(no equivalent)* | Remove comment — ty does not flag unused classes |
| `reportUnusedParameter` | *(no equivalent)* | Remove comment — ty does not flag unused parameters |

## Files affected

- `docs/postgres-quickstart.md` — reportUnusedClass
- `example/app/app.py` — reportUnusedClass
- `scripts/gen_ref_pages.py` — reportPrivateImportUsage
- `src/embar/column/base.py` — reportUninitializedInstanceVariable (×3)
- `src/embar/db/_util.py` — reportPrivateUsage
- `src/embar/db/pg.py` — reportArgumentType (×14), reportPrivateUsage (×2)
- `src/embar/model.py` — reportPrivateUsage
- `src/embar/table.py` — reportUnannotatedClassAttribute, reportAssignmentType, reportGeneralTypeIssues (×2)
- `src/embar/tools/commands.py` — reportArgumentType
- `tests/conftest.py` — reportArgumentType
- `tests/e2e/test_migrations.py` — reportPrivateUsage (×4), reportUnusedParameter (×2)
- `tests/test_types.py` — reportCallIssue
