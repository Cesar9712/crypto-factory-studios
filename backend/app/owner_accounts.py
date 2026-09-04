from __future__ import annotations

from typing import Callable


OWNER_ACCOUNTS = (
    {
        "seed_id": "usr_cfs_owner_01",
        "email": "owner1@cryptofactorystudios.app",
        "display_name": "CFS Platform Owner 1",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$+sAigTpPZnbji1SBMFKOcQ$bpKAEZlhb0BX4IwM4PK6e1560N1vdOwhKOTOlq7Zzz4",
        "creator_slug": "cfs-platform-owner-01",
    },
    {
        "seed_id": "usr_cfs_owner_02",
        "email": "owner2@cryptofactorystudios.app",
        "display_name": "CFS Platform Owner 2",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$ykzXrxetbv1V2wV4RXkzEA$HcgXt+roiD5avKmKZjClV6XfE7QUMQBucsHwrWF7O8Y",
        "creator_slug": "cfs-platform-owner-02",
    },
)


def ensure_platform_owner_accounts(db, now: Callable[[], int]) -> None:
    """Provision the two persistent platform-owner accounts without storing plaintext passwords.

    Existing accounts keep their current password hash so credentials can be rotated later
    without being reset by a restart. Their platform-owner role and unlimited internal creator
    access are intentionally restored on startup.
    """
    t = now()
    for account in OWNER_ACCOUNTS:
        existing = db.one("SELECT id FROM users WHERE email=?", (account["email"],))
        if existing:
            user_id = existing["id"]
            db.execute(
                "UPDATE users SET display_name=?,role='platform_owner',disabled=0,updated_at=? WHERE id=?",
                (account["display_name"], t, user_id),
            )
        else:
            user_id = account["seed_id"]
            db.execute(
                """INSERT INTO users(id,email,password_hash,display_name,role,disabled,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    user_id,
                    account["email"],
                    account["password_hash"],
                    account["display_name"],
                    "platform_owner",
                    0,
                    t,
                    t,
                ),
            )

        profile = db.one("SELECT user_id FROM creator_profiles WHERE user_id=?", (user_id,))
        if profile:
            db.execute(
                "UPDATE creator_profiles SET plan_id='internal_unlimited',billing_exempt=1 WHERE user_id=?",
                (user_id,),
            )
        else:
            db.execute(
                """INSERT INTO creator_profiles(user_id,slug,bio,trust_level,plan_id,billing_exempt,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    user_id,
                    account["creator_slug"],
                    "Crypto Factory Studios platform owner account.",
                    "TRUSTED",
                    "internal_unlimited",
                    1,
                    t,
                ),
            )


def platform_owner_accounts_ready(db) -> bool:
    for account in OWNER_ACCOUNTS:
        row = db.one(
            """SELECT u.id,u.role,u.disabled,cp.plan_id,cp.billing_exempt
               FROM users u LEFT JOIN creator_profiles cp ON cp.user_id=u.id
               WHERE u.email=?""",
            (account["email"],),
        )
        if not row:
            return False
        if row.get("role") != "platform_owner" or int(row.get("disabled") or 0) != 0:
            return False
        if row.get("plan_id") != "internal_unlimited" or int(row.get("billing_exempt") or 0) != 1:
            return False
    return True
