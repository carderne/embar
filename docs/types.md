# Types and tests

Embar is designed from the ground up for type safety and useful type hints.

Right now, the best way to take advantage of this is to install [basedpyright](https://github.com/DetachHead/basedpyright).
It's a fork of [pyright](https://github.com/microsoft/pyright) that adds some extra features.

```bash
uv add --dev basedpyright
```

Then you should add something like this your `pyproject.toml`:

```toml
[tool.pyright]
venvPath = "."
venv = ".venv"
pythonVersion = "3.14"
strict = ["**/*.py"]
```

Once that is added, you can run `uv run pyright` in the root and it should work correctly.
