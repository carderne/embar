# TODO

## SELECT Query Missing Components

- [x] HAVING clause - Critical for filtering aggregated results (e.g., `HAVING COUNT(*) > 5`)
- [x] ORDER BY clause - Essential for sorting results
- [x] OFFSET clause - Complete pagination capabilities (LIMIT already exists)
- [x] DISTINCT/DISTINCT ON - Eliminate duplicate rows or get distinct values for specific columns
- [ ] Window functions - Support for `OVER (PARTITION BY ... ORDER BY ...)` clauses for advanced analytics
- [ ] UNION/INTERSECT/EXCEPT - Set operations to combine multiple SELECT queries
- [ ] Subqueries in WHERE/FROM - Use subqueries as data sources or in conditions
- [ ] CTEs (WITH clause) - Common Table Expressions support for complex queries
- [ ] FOR UPDATE/FOR SHARE - Row locking mechanisms for transactional queries
- [ ] Aggregate functions in SELECT - First-class support for `COUNT()`, `SUM()`, `AVG()`, etc.

## UPDATE Query Missing Components

- [x] RETURNING clause - Critical for getting updated values back (especially important in Postgres)
- [ ] FROM clause - Update based on joins with other tables (Postgres extension)
- [ ] ORDER BY + LIMIT - Update only a subset of matching rows (useful for batch processing)
- [ ] Multiple WHERE conditions chaining - Support for `.and_where()` or `.or_where()`
- [ ] Subqueries in WHERE - Update based on subquery results
- [ ] Computed values - Set columns to expressions like `col = col + 1` or `col = OTHER_TABLE.col`
- [ ] CTEs (WITH clause) - Support for complex updates

## INSERT Query Missing Components

- [x] RETURNING clause - Critical for getting generated IDs, timestamps, or other computed values back
- [x] ON CONFLICT (UPSERT) - Handle constraint violations gracefully (e.g., `ON CONFLICT DO UPDATE` or `DO NOTHING`)
- [ ] INSERT ... SELECT - Insert results from a SELECT query
- [ ] Default column values - Explicitly use `DEFAULT` for specific columns while setting others
- [ ] OVERRIDING SYSTEM VALUE - Insert into identity/serial columns explicitly
- [ ] Multiple value sets syntax - Single query with multiple value clauses
- [ ] CTEs (WITH clause) - Support for complex insert scenarios
