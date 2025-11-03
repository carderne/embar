"""Generate index.md and quickstart.md from README.md."""

import re
from pathlib import Path

import mkdocs_gen_files

root = Path(__file__).parent.parent
readme_path = root / "README.md"

# Read the README
with open(readme_path, "r") as f:
    content = f.read()

# Find the positions of the section markers
quickstart_match = re.search(r"^## Quickstart$", content, re.MULTILINE)
contributing_match = re.search(r"^## Contributing$", content, re.MULTILINE)

if not quickstart_match or not contributing_match:
    raise ValueError("Could not find '## Quickstart' or '## Contributing' sections in README.md")

quickstart_pos = quickstart_match.start()
contributing_pos = contributing_match.start()

# Split the content
index_content = content[:quickstart_pos].rstrip()
quickstart_content = content[quickstart_pos:contributing_pos].rstrip()

# Write index.md (everything before Quickstart)
with mkdocs_gen_files.open("index.md", "w") as f:
    f.write(index_content)


# Process quickstart content: upgrade heading levels by 1
# ## becomes #, ### becomes ##, etc.
# But only outside of code fences
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


quickstart_upgraded = upgrade_headings(quickstart_content)

# Write quickstart.md
with mkdocs_gen_files.open("quickstart.md", "w") as f:
    f.write(quickstart_upgraded)
