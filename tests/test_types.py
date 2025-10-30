import pytest

from .schemas.schema import Message, User

# NOTE ABOUT pyright:ignore
# The fact that (based)pyright DOES NOT complain about the ignores
# tells us that they are valid ignores, and that the code is therefore invalid
# We're checking that the typechecker usefully shouts at the user for bad code


def test_fail_if_missing_table_fields():
    with pytest.raises(TypeError) as exc:
        # fmt: off
        User(
            email="",  # pyright:ignore[reportCallIssue]
        )
        # fmt: on
    error_str = str(exc.value)
    assert "required fields" in error_str
    assert "'id'" in error_str


def test_apply_table_defaults():
    # fmt: off
    message = Message(
        id=1,
        user_id=2,
    )
    # fmt: on
    assert message.content == "no message"
