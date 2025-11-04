# Contributing

The usual process to make a contribution is to:

1. Check for existing related issues
2. Fork the repository and create a new branch
3. Make your changes
4. Make sure formatting, linting and tests passes.
5. Add tests if possible to cover the lines you added.
6. Commit, and send a Pull Request.

## Fork the repository
So that you have your own copy.

## Clone the repository

```bash
# replace 'carderne' with your own username if you made a fork
git clone git@github.com:carderne/embar.git
cd embar
git checkout -b add-my-contribution
```

## Setup uv
Install it if needed (full instructions [here](https://docs.astral.sh/uv/getting-started/installation/)):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then sync your local environment:
```bash
uv sync
```

## Run all code quality checks
This project uses [poethepoet](https://poethepoet.natn.io/index.html) for tasks/scripts.

You'll need Docker installed to run tests.

Format, lint, type-check, test:
```bash
uv run poe fmt
           lint
           check
           test

# or
uv run poe all
```

Or do this:
```bash
# Run this or put it in .zshrc/.bashrc/etc
alias poe="uv run poe"

# Then you can just:
poe test
```

## Open a PR
Push your changes to your branch on your fork, then open a PR against the main repository.
