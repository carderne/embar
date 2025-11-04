"""Generate index.md and quickstart.md from README.md."""

import re
from pathlib import Path

import mkdocs_gen_files


def main():
    root = Path(__file__).parent.parent
    readme_path = root / "README.md"

    # Read the README
    with open(readme_path, "r") as f:
        content = f.read()

    content = content.replace("```python continuation", "```python")

    # Find the positions of the section markers
    quickstart_match = re.search(r"^## Quickstart$", content, re.MULTILINE)
    migrations_match = re.search(r"^## Migrations$", content, re.MULTILINE)
    contributing_match = re.search(r"^## Contributing$", content, re.MULTILINE)

    if not quickstart_match or not migrations_match or not contributing_match:
        raise ValueError("Could not find '## Quickstart', '## Migrations', or '## Contributing' sections in README.md")

    quickstart_pos = quickstart_match.start()
    migrations_pos = migrations_match.start()
    contributing_pos = contributing_match.start()

    # Split the content
    index_content = content[:quickstart_pos].rstrip()
    quickstart_content = content[quickstart_pos:migrations_pos].rstrip()
    migrations_content = content[migrations_pos:contributing_pos].rstrip()

    with mkdocs_gen_files.open("index.md", "w") as f:
        f.write(index_content)

    quickstart_upgraded = upgrade_headings(quickstart_content)
    with mkdocs_gen_files.open("quickstart.md", "w") as f:
        f.write(quickstart_upgraded)

    migrations_upgraded = upgrade_headings(migrations_content)
    with mkdocs_gen_files.open("migrations.md", "w") as f:
        f.write(migrations_upgraded)


def upgrade_headings(content: str) -> str:
    lines = content.split("\n")
    result: list[str] = []
    in_code_fence = False

    for line in lines:
        # Check if we're entering/exiting a code fence
        if line.startswith("```"):
            in_code_fence = not in_code_fence
            result.append(line)
            continue

        # Only upgrade headings outside of code fences
        if not in_code_fence and line.startswith("##"):
            # Count the number of # at the start
            match = re.match(r"^(#{2,})( .+)$", line)
            if match:
                hashes = match.group(1)
                rest = match.group(2)
                # Remove one # to upgrade the level
                if len(hashes) > 1:
                    line = hashes[:-1] + rest
                else:
                    # ## becomes #
                    line = "#" + rest

        result.append(line)

    return "\n".join(result)


main()
