import os
import sys
import tomllib

from embar.tools.models import MigrateConfig


def load_env_file():
    """Load environment variables from .env file if it exists."""
    # Try current directory first, then parent directory
    for env_path in [".env", "../.env"]:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
            break


def load_config(config_path: str | None = None) -> MigrateConfig:
    """Load and validate configuration from file."""
    if config_path is None:
        config_path = "embar.toml"

    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found.")
        sys.exit(1)

    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)

    try:
        return MigrateConfig(**config_data)
    except TypeError as e:
        print(f"Error: Invalid config format: {e}")
        sys.exit(1)
