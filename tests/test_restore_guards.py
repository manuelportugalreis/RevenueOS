import pytest

from revenueos.restore_drill import validate_target


@pytest.mark.parametrize(
    "url,target",
    [
        ("postgresql+psycopg://u@remote.example/db", "revenueos_restore_check_demo"),
        ("postgresql+psycopg://u@127.0.0.1/db", "revenueos_test"),
        (
            "postgresql+psycopg://u@127.0.0.1/revenueos_restore_check_demo",
            "revenueos_restore_check_demo",
        ),
        ("postgresql+psycopg://u@127.0.0.1/db", "revenueos_restore_check_a;drop database x"),
    ],
)
def test_restore_rejects_remote_or_unsafe_targets(url: str, target: str) -> None:
    with pytest.raises(ValueError):
        validate_target(url, target)
