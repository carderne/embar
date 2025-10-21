from dataclasses import dataclass
import os

from pudl.db import Database
from pudl.table import TextColumn, table_config, Table, Text


DATABASE_URL = os.getenv("DATABASE_URL")


@table_config("users")
@dataclass
class User(Table):
    id: TextColumn = Text()
    email: TextColumn = Text("user_email", default="text", not_null=True)


def main():
    user = User(id="a", email="john@foo.com")

    assert DATABASE_URL is not None, "DATABASE_URL not set"
    db = Database(DATABASE_URL).connect().migrate(User)

    db.insert(User).values(user).execute()

    results = (
        db.select(User)
        .where(User.id.info, "=", "a")
        .where(User.email.info, "LIKE", "john%")
        .limit(10)
        .execute()
    )

    print(results)


if __name__ == "__main__":
    main()
