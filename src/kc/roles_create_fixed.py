import sys

from kc.cli import main


def entrypoint() -> None:
    sys.argv = [
        "kc",
        "roles",
        "create",
        "--realm",
        "master",
        "--name",
        "example-role",
    ]
    main()


if __name__ == "__main__":
    entrypoint()
