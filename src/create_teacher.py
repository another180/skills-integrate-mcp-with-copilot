"""Create a teacher account for the Mergington activities app."""

import argparse
import getpass
import hashlib
import json
import os
import secrets
from pathlib import Path

TEACHERS_FILE = Path(__file__).parent / "teachers.json"
PASSWORD_HASH_ITERATIONS = 600_000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="username assigned to the teacher")
    username = parser.parse_args().username
    if not username.strip() or username != username.strip():
        parser.error("username must not be empty or start/end with whitespace")

    password = getpass.getpass("Teacher password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password:
        parser.error("password must not be empty")
    if password != confirmation:
        parser.error("passwords do not match")

    try:
        with TEACHERS_FILE.open(encoding="utf-8") as teachers_file:
            data = json.load(teachers_file)
    except FileNotFoundError:
        data = {"teachers": []}

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, list) or any(
        not isinstance(teacher, dict)
        or not isinstance(teacher.get("username"), str)
        or not isinstance(teacher.get("password_hash"), str)
        for teacher in teachers
    ):
        parser.error(f"{TEACHERS_FILE} has an invalid format")
    if any(teacher["username"] == username for teacher in teachers):
        parser.error(f"teacher account {username!r} already exists")

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    ).hex()
    teachers.append(
        {
            "username": username,
            "password_hash": (
                f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt.hex()}$"
                f"{password_hash}"
            ),
        }
    )
    TEACHERS_FILE.write_text(
        json.dumps({"teachers": teachers}, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(TEACHERS_FILE, 0o600)
    print(f"Created teacher account {username!r} in {TEACHERS_FILE}")


if __name__ == "__main__":
    main()
