#!/usr/bin/env python3

import sys

from config import DOMAIN, API_KEY
from import_employees import TalentLMSClient


def main():
    if len(sys.argv) != 2:
        print("Usage: python delete_talentlms_user.py <user_email>")
        sys.exit(1)

    identifier = sys.argv[1].strip()
    client = TalentLMSClient(DOMAIN, API_KEY)

    print(f"Looking up user by email: {identifier} ...")
    user = client.get_user_by_email(identifier)

    if not user:
        print(f"✗ No TalentLMS user found with email: {identifier}")
        sys.exit(1)

    user_id = int(user["id"])
    full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    login = user.get("login")

    print("Found user:")
    print(f"  ID:    {user_id}")
    print(f"  Name:  {full_name}")
    print(f"  Login: {login}")
    print(f"  Email: {user.get('email')}")

    # If you want a safety prompt, uncomment this block:
    # confirm = input("Type 'delete' to permanently delete this user (and press Enter): ")
    # if confirm.lower() != "delete":
    #     print("Aborted.")
    #     sys.exit(0)

    print("\nDeleting user permanently from TalentLMS...")
    try:
        resp = client.delete_user(user_id=user_id, permanent=True)
        print("✓ Delete call succeeded.")
        print("Response:", resp)
        print(
            "\nNote: A permanent delete removes the user and their enrollments/"
            "course data from TalentLMS."
        )
    except Exception as e:
        print(f"✗ Delete failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
