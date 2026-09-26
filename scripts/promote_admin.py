"""Promote an existing SkyBook account to administrator.

Usage:
    python scripts/promote_admin.py user@example.com

This script requires access to the same DATABASE_URL used by the application.
It does not create an account or contain a built-in administrator credential.
"""

import sys

from flight_booking.database import SessionLocal, UserModel


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/promote_admin.py user@example.com")
        return 2

    email = sys.argv[1].strip().lower()
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if not user:
            print("No account found for that email.")
            return 1
        user.role = "admin"
        db.commit()
        print(f"Promoted {user.email} to admin.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
