from embar.tools.models import MigrationDiff


def red_bold(text: str) -> str:
    """Return text in red and bold for terminal."""
    return f"\033[1;31m{text}\033[0m"


def green(text: str) -> str:
    """Return text in green for terminal."""
    return f"\033[32m{text}\033[0m"


def yellow(text: str) -> str:
    """Return text in yellow for terminal."""
    return f"\033[33m{text}\033[0m"


def format_migration_output(diffs: list[MigrationDiff]) -> str:
    """Format migration diffs as SQL with metadata comments."""
    output: list[str] = []
    output.append("-- Generated Migration SQL")
    output.append("-- =======================")
    output.append("")

    for i, diff in enumerate(diffs, 1):
        output.append(f"-- Migration {i}/{len(diffs)}")
        output.append(f"-- Table: {diff.table_name}")
        output.append(f"-- Type: {diff.match_type.upper()}")

        if diff.old_table_name and diff.new_table_name and diff.old_table_name != diff.new_table_name:
            output.append(f"-- Rename: {diff.old_table_name} -> {diff.new_table_name}")

        compat_status = "BACKWARD-COMPATIBLE" if diff.is_backward_compatible else "⚠️  NON-BACKWARD-COMPATIBLE"
        output.append(f"-- Compatibility: {compat_status}")
        output.append(f"-- Explanation: {diff.explanation}")
        output.append("")
        output.append(diff.sql)
        output.append("")
        output.append("")

    return "\n".join(output)
