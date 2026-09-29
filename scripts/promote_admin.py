"""One-time administrator promotion for the production database.

Run this from the Render service shell:

    python scripts/promote_admin.py

Security:
- The target account is fixed to the intended administrator email.
- A secret must be supplied through ADMIN_PROMOTION_TOKEN; it is never stored in source.
- A database marker makes the promotion one-time. After a successful run,
  subsequent executions refuse to make any role changes.
- The operation is transactional and does not create a user.
"""

import os
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, inspect, text
from sqlalchemy.exc import IntegrityError

from flight_booking.database import Base, SessionLocal, UserModel, engine


TARGET_EMAIL = "rahulramachandran3110@gmail.com"
PROMOTION_KEY = "initial_admin_promotion_v1"


class AdminPromotionAudit(Base):
    __tablename__ = "AdminPromotionAudit"

    promotion_key = Column(String(100), primary_key=True)
    user_id = Column(Integer, nullable=False)
    email = Column(String(255), nullable=False)
    promoted_at = Column(DateTime, nullable=False)


def main() -> int:
    token = os.getenv("ADMIN_PROMOTION_TOKEN")
    if not token or len(token) < 24:
        print("ADMIN_PROMOTION_TOKEN is required and must be at least 24 characters.")
        return 2

    # Keep the target and action out of any HTTP endpoint. This script is intended
    # to be run manually from a privileged Render shell exactly once.
    expected_confirmation = os.getenv("ADMIN_PROMOTION_CONFIRM")
    if expected_confirmation != "PROMOTE_INITIAL_ADMIN":
        print("Set ADMIN_PROMOTION_CONFIRM=PROMOTE_INITIAL_ADMIN before running.")
        return 2

    # The token proves that the person intentionally configured this one-time
    # operation. It is not printed or persisted.
    if not secrets.compare_digest(token, os.getenv("ADMIN_PROMOTION_TOKEN", "")):
        return 2

    db = SessionLocal()
    try:
        # The audit table is created only when this one-time administrative tool
        # is explicitly executed; it is not part of normal application startup.
        AdminPromotionAudit.__table__.create(bind=engine, checkfirst=True)

        used = (
            db.query(AdminPromotionAudit)
            .filter(AdminPromotionAudit.promotion_key == PROMOTION_KEY)
            .first()
        )
        if used:
            print("This one-time admin promotion has already been used.")
            return 3

        user = (
            db.query(UserModel)
            .filter(UserModel.email == TARGET_EMAIL)
            .first()
        )
        if not user:
            print(f"Target account not found: {TARGET_EMAIL}")
            return 1

        if user.role == "admin":
            print(f"{TARGET_EMAIL} is already an admin; no change made.")
            return 0

        old_role = user.role
        user.role = "admin"
        db.add(
            AdminPromotionAudit(
                promotion_key=PROMOTION_KEY,
                user_id=user.user_id,
                email=user.email,
                promoted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            print("The one-time promotion was already claimed by another run.")
            return 3

        print(f"Promoted {TARGET_EMAIL}: {old_role} -> admin.")
        print("One-time admin promotion completed successfully.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
