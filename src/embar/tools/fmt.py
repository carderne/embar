def red_bold(text: str) -> str:
    """Return text in red and bold for terminal."""
    return f"\033[1;31m{text}\033[0m"


def green(text: str) -> str:
    """Return text in green for terminal."""
    return f"\033[32m{text}\033[0m"


def yellow(text: str) -> str:
    """Return text in yellow for terminal."""
    return f"\033[33m{text}\033[0m"
