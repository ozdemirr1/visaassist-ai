"""Create an administrator account, or reset a user's password (ADR 0004).

Registration through the API always creates applicants, so administrators are created here.
The password is asked for on the terminal, never passed as an argument.

    uv run python -m app.users.create_admin --email admin@example.com
    uv run python -m app.users.create_admin --email someone@example.com --reset-password
"""

import argparse
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.auth import service
from app.db import get_engine


def _ask_password() -> str:
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat: "):
        raise service.WeakPassword("The two passwords differ.")
    return password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="set a new password for an existing account and end its sessions",
    )
    args = parser.parse_args(argv)

    try:
        email = service.normalise_email(args.email)
        password = _ask_password()
        with Session(get_engine()) as session, session.begin():
            if args.reset_password:
                user = session.scalar(select(models.User).where(models.User.email == email))
                if user is None:
                    print(f"No account for {email}.", file=sys.stderr)
                    return 1
                service.set_password(session, user, password)
                print(f"Password of {email} changed; all its sessions ended.")
            else:
                service.create_user(session, email, password, role="admin")
                print(f"Administrator {email} created.")
    except service.AuthError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
