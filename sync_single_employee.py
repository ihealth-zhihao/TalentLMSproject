#!/usr/bin/env python3

"""
Single-employee sync script.

Usage:
    python sync_single_employee.py someone@ihealthlabs.com

Flow:
1. Fetch all workers from ADP.
2. Find the worker that matches the given identifier (prefer email).
3. Use that worker's info to:
   - Create a TalentLMS account if it doesn't exist.
   - Or print that they already have a TalentLMS account.
"""

import sys
from typing import Dict, List, Optional

from get_adp_employees import get_workers         
from import_employees import TalentLMSClient      
from config import DOMAIN, API_KEY      


# ------------- ADP helpers ------------- #

def get_all_workers() -> List[Dict]:
    """Call your existing get_workers() and return the list."""
    data = get_workers()  # should return {"workers": [...]}
    return data.get("workers", [])


def worker_work_email(worker: Dict) -> Optional[str]:
    """Get work email from ADP worker object."""
    bc = worker.get("businessCommunication", {}) or {}
    emails = bc.get("emails", []) or []
    if emails:
        return emails[0].get("emailUri")
    return None


def worker_personal_email(worker: Dict) -> Optional[str]:
    """Get personal email as fallback."""
    person = worker.get("person", {}) or {}
    comm = person.get("communication", {}) or {}
    emails = comm.get("emails", []) or []
    if emails:
        return emails[0].get("emailUri")
    return None


def worker_full_name(worker: Dict) -> str:
    """Return formatted legal name, or 'First Last'."""
    legal = (worker.get("person", {}) or {}).get("legalName", {}) or {}
    if "formattedName" in legal and legal["formattedName"]:
        return legal["formattedName"]
    first = legal.get("givenName", "") or ""
    last = legal.get("familyName1", "") or ""
    return f"{last}, {first}".strip(", ")


def worker_first_last(worker: Dict) -> (str, str):
    """Return first and last name separately from legalName."""
    legal = (worker.get("person", {}) or {}).get("legalName", {}) or {}
    first = legal.get("givenName") or ""
    last = legal.get("familyName1") or ""
    return first, last


def find_worker_by_identifier(workers: List[Dict], identifier: str) -> Optional[Dict]:
    """
    Try to locate a worker by:
      - work email
      - personal email
      - workerID.idValue
      - formattedName match (case-insensitive)
    """

    ident_lower = identifier.lower()

    # 1) Email match (work or personal) if identifier looks like an email
    if "@" in identifier:
        for w in workers:
            work_email = worker_work_email(w)
            personal_email = worker_personal_email(w)

            if work_email and work_email.lower() == ident_lower:
                return w
            if personal_email and personal_email.lower() == ident_lower:
                return w

    # 2) workerID (Associate ID) match
    for w in workers:
        worker_id = (w.get("workerID", {}) or {}).get("idValue")
        if worker_id and worker_id.lower() == ident_lower:
            return w

    # 3) formatted name match
    for w in workers:
        name = worker_full_name(w).lower()
        if name == ident_lower:
            return w

    # If nothing matched, return None
    return None


# ------------- TalentLMS sync ------------- #

def sync_single_employee(identifier: str) -> None:
    """
    Given an identifier (email / workerID / name), find the ADP worker
    and either create or confirm their TalentLMS account.
    """
    print(f"Identifier: {identifier}")
    print("Fetching workers from ADP...")
    workers = get_all_workers()
    print(f"Total workers fetched from ADP: {len(workers)}")

    worker = find_worker_by_identifier(workers, identifier)
    if not worker:
        print("No matching worker found in ADP.")
        return

    print(f"Found worker in ADP: {worker_full_name(worker)}")

    # Extract email (prefer work email, then personal)
    email = worker_work_email(worker) or worker_personal_email(worker)
    if not email:
        print("This worker has no email in ADP; cannot create TalentLMS account.")
        return

    first_name, last_name = worker_first_last(worker)
    if not first_name and not last_name:
        first_name = "Unknown"
        last_name = "User"

    print(f"Using email: {email}")
    print(f"Name for TalentLMS: {first_name} {last_name}")

    # TalentLMS client
    client = TalentLMSClient(DOMAIN, API_KEY)

    # Check if user already exists in TalentLMS
    print("Checking TalentLMS for existing user...")
    existing_user = client.get_user_by_email(email)

    if existing_user:
        print("User already exists in TalentLMS.")
        print(f"  TalentLMS User ID: {existing_user.get('id')}")
        print(f"  Name: {existing_user.get('first_name')} {existing_user.get('last_name')}")
        print(f"  Login: {existing_user.get('login')}")
        return

    # If not exists: create user
    print("User does not exist in TalentLMS. Creating...")

    # For MVP, we use email as login and let TalentLMS auto-generate a password.
    created = client.create_user(
        first_name=first_name,
        last_name=last_name,
        email=email,
        login=email,
        password="testpassword1",          # Dummy hardcoded password
        user_type="Learner",    # default role
    )

    print("Successfully created TalentLMS user:")
    print(f"  ID: {created.get('id')}")
    print(f"  Name: {created.get('first_name')} {created.get('last_name')}")
    print(f"  Login: {created.get('login')}")
    print(f"  Email: {created.get('email')}")


# ------------- CLI entrypoint ------------- #

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_single_employee.py <identifier>")
        print("  Example: python sync_single_employee.py someone@ihealthlabs.com")
        sys.exit(1)

    identifier = sys.argv[1]
    sync_single_employee(identifier)
