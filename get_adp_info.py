import requests
import argparse
from config import CLIENT_ID, CLIENT_SECRET

ADP_TOKEN_URL = "https://api.adp.com/auth/oauth/v2/token"
ADP_WORKERS_URL = "https://api.adp.com/hr/v2/workers"

CERT = ("adp_integration.crt", "adp_integration.key")  # mTLS


def get_adp_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    resp = requests.post(
        ADP_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        cert=CERT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_workers():
    token = get_adp_token()
    all_workers = []
    offset = 0
    limit = 50

    while True:
        url = f"{ADP_WORKERS_URL}?offset={offset}&limit={limit}"
        resp = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            cert=CERT,
        )
        resp.raise_for_status()
        data = resp.json()
        workers = data.get("workers", [])
        all_workers.extend(workers)
        if len(workers) < limit:
            break
        offset += limit

    return {"workers": all_workers}


def print_worker_stats():
    employees_data = get_workers()
    workers = employees_data.get("workers", [])
    total_employees = len(workers)
    active_count = 0
    terminated_count = 0
    active_roles_set = set()

    for emp in workers:
        status = (
            emp.get("workerStatus", {})
            .get("statusCode", {})
            .get("codeValue", "Unknown")
        )
        if status == "Active":
            active_count += 1
            assignments = emp.get("workAssignments", [])
            job_title = "Unknown"
            if assignments:
                job_title = assignments[0].get("jobTitle") or "Unknown"
            active_roles_set.add(job_title)
        elif status == "Terminated":
            terminated_count += 1

    print(f"Total employees: {total_employees}")
    print(f"Active employees: {active_count}")
    print(f"Terminated employees: {terminated_count}")
    print(f"Unique active roles: {len(active_roles_set)}")
    print("Active employee roles:")
    for role in sorted(active_roles_set):
        print(f"  - {role}")


def _extract_manager_id_from_assignment(work_assignment):
    """
    Try to get a manager's associateOID (or positionID fallback) from a single workAssignment.
    Handles both dict and list shapes that ADP might return for `reportsTo`.
    """
    reports_to = work_assignment.get("reportsTo")
    if not reports_to:
        return None

    # If reports_to is a list, take the first element
    if isinstance(reports_to, list):
        if not reports_to:
            return None
        reports_to = reports_to[0] or {}

    # Now we expect reports_to to be a dict
    if not isinstance(reports_to, dict):
        return None

    person = reports_to.get("person")
    if isinstance(person, list):
        person = person[0] if person else {}
    if isinstance(person, dict):
        assoc = person.get("associateOID")
        if assoc:
            return assoc

    # Sometimes associateOID might be directly under reports_to
    assoc = reports_to.get("associateOID")
    if assoc:
        return assoc

    # Fallback: positionID-based hierarchy
    position = reports_to.get("positionID")
    if isinstance(position, dict):
        return position.get("idValue") or position.get("positionID")
    elif isinstance(position, str):
        return position

    return None


def _clean_email(raw):
    """Normalize email strings: strip mailto:, angle brackets, spaces, lower-case."""
    if not raw:
        return None
    s = str(raw).strip().lower()

    # Strip mailto:
    if s.startswith("mailto:"):
        s = s[len("mailto:"):]

    # Handle "Name <email@domain>" style
    if "<" in s and "@" in s and ">" in s:
        start = s.index("<") + 1
        end = s.index(">", start)
        inner = s[start:end].strip()
        if "@" in inner:
            s = inner.lower()

    return s


def extract_email(worker):
    """
    Try to pull a primary email from the worker object.
    Uses person.communication/communications.emails[*].emailUri, etc.
    """
    person = worker.get("person", {}) or {}

    # ADP often uses 'communications' (plural), but your tenant uses 'communication'
    comm = person.get("communications") or person.get("communication") or {}
    emails = comm.get("emails") or comm.get("email") or []

    # Normalize emails to a list
    if isinstance(emails, dict):
        emails = [emails]

    if isinstance(emails, list):
        for eobj in emails:
            if not isinstance(eobj, dict):
                continue
            raw = (
                eobj.get("emailUri")
                or eobj.get("uri")
                or eobj.get("email")
                or eobj.get("value")
            )
            cleaned = _clean_email(raw)
            if cleaned:
                return cleaned

    # Fallbacks if your tenant uses flatter fields
    for key in ("workEmail", "email", "emailAddress"):
        if key in worker:
            cleaned = _clean_email(worker[key])
            if cleaned:
                return cleaned

    for key in ("email", "emailAddress"):
        if key in person:
            cleaned = _clean_email(person[key])
            if cleaned:
                return cleaned

    return None


def find_worker_by_identifier(workers, identifier: str):
    """
    Try to locate a worker by an identifier, in this priority:
    1) ADP user/worker IDs (often configured as work emails)
    2) Full name / name fragment
    3) Primary personal email (via extract_email)
    4) Any other email-like string anywhere in the worker
    """
    target = identifier.strip().lower()

    def get_full_name(worker):
        person = worker.get("person", {}) or {}
        legal = person.get("legalName", {}) or {}
        first = (legal.get("givenName") or "").strip()
        last = (legal.get("familyName") or "").strip()
        return (first + " " + last).strip()

    def get_candidate_ids(worker):
        """
        Collect all ID-like fields that might be configured as the 'user id'
        (e.g., work email).
        """
        ids = []

        # Common ADP fields
        aoid = worker.get("associateOID")
        if aoid:
            ids.append(str(aoid))

        w_id = (worker.get("workerID") or {}).get("idValue")
        if w_id:
            ids.append(str(w_id))

        # Possible custom/user fields (depending on your tenant)
        for key in ("userId", "userID", "login", "username"):
            if key in worker:
                ids.append(str(worker[key]))

        return [i.strip().lower() for i in ids if i]

    def iter_strings_with_at(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from iter_strings_with_at(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from iter_strings_with_at(v)
        elif isinstance(obj, str):
            if "@" in obj:
                yield obj

    # 1) Try to match identifier against ID fields first
    for w in workers:
        for wid in get_candidate_ids(w):
            if wid == target:
                return w

    # 2) Try to match by full name / fragment
    for w in workers:
        full_name = get_full_name(w)
        if full_name and target in full_name.lower():
            return w

    # 3) Try to match by primary email
    for w in workers:
        primary_email = extract_email(w)
        if primary_email and target in primary_email.lower():
            return w

    # 4) Try to match by ANY email-like string inside the worker
    for w in workers:
        for s in iter_strings_with_at(w):
            cleaned = _clean_email(s) or s.strip().lower()
            if target in cleaned:
                return w

    return None


def build_org_hierarchy(workers):
    """
    Build a mapping of manager -> list of direct reports.
    Returns:
        manager_map: dict of manager_associateOID -> list of worker dicts
        worker_map: dict of associateOID -> worker dict
    """
    manager_map = {}
    worker_map = {}

    # First pass: index workers by associateOID or workerID.idValue
    for w in workers:
        aoid = w.get("associateOID") or (w.get("workerID") or {}).get("idValue")
        if not aoid:
            continue
        worker_map[aoid] = w

    # Second pass: connect each worker to their manager
    for w in workers:
        aoid = w.get("associateOID") or (w.get("workerID") or {}).get("idValue")
        if not aoid:
            continue

        work_assignments = w.get("workAssignments", []) or []
        manager_id = None
        if work_assignments:
            manager_id = _extract_manager_id_from_assignment(work_assignments[0])

        if manager_id:
            manager_map.setdefault(manager_id, []).append(w)
        else:
            # Top-level employees (no manager)
            manager_map.setdefault(None, []).append(w)

    return manager_map, worker_map


def print_org_tree(manager_map, worker_map, manager_id=None, indent=0):
    """Recursively print the org tree."""
    employees = manager_map.get(manager_id, [])
    for emp in employees:
        aoid = emp.get("associateOID") or (emp.get("workerID") or {}).get("idValue")
        name = emp.get("person", {}).get("legalName", {}).get("givenName", "Unknown")
        family = emp.get("person", {}).get("legalName", {}).get("familyName", "")
        full_name = f"{name} {family}".strip()

        title = "Unknown"
        wa = emp.get("workAssignments", [])
        if wa:
            title = wa[0].get("jobTitle") or "Unknown"

        print(" " * indent + f"- {full_name} ({title})")

        # Recurse into direct reports
        print_org_tree(manager_map, worker_map, aoid, indent + 4)


def print_org_chart(manager_identifier: str | None = None):
    """
    Fetches workers and prints org chart using ADP manager relationships.
    If manager_identifier is provided, only prints that manager's subtree.
    """
    print("Fetching workers from ADP...")
    data = get_workers()
    workers = data.get("workers", [])

    if not workers:
        print("No workers found.")
        return

    manager_map, worker_map = build_org_hierarchy(workers)

    # If an identifier is provided, only print that manager's subtree
    if manager_identifier:
        manager_worker = find_worker_by_identifier(workers, manager_identifier)
        if not manager_worker:
            print(f"Could not find any worker matching: {manager_identifier}")
            return

        manager_id = manager_worker.get("associateOID") or (
            manager_worker.get("workerID") or {}
        ).get("idValue")

        if not manager_id:
            print(
                f"Found worker matching {manager_identifier}, but they have no associateOID/workerID."
            )
            return

        # Print who we're scoping under
        person = manager_worker.get("person", {})
        legal_name = person.get("legalName", {}) or {}
        first = legal_name.get("givenName", "Unknown")
        last = legal_name.get("familyName", "")
        full_name = f"{first} {last}".strip()

        title = "Unknown"
        wa = manager_worker.get("workAssignments", []) or []
        if wa:
            title = wa[0].get("jobTitle") or "Unknown"

        print(
            f"\n=== ORG CHART UNDER {full_name} ({title}) [{manager_identifier}] ===\n"
        )
        print_org_tree(manager_map, worker_map, manager_id=manager_id, indent=0)
        print("\n=== END ORG CHART ===\n")
        return

    # Otherwise, print full org chart from the top
    print("\n=== FULL ORG CHART ===\n")
    print_org_tree(manager_map, worker_map, manager_id=None, indent=0)
    print("\n=== END ORG CHART ===\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ADP Integration Utility")
    parser.add_argument(
        "--get_workers",
        action="store_true",
        help="Print worker statistics (active/terminated, roles, etc.)",
    )
    parser.add_argument(
        "--org_chart",
        nargs="?",
        const=True,
        help=(
            "Print ADP org chart. Optionally pass a user ID "
            "(e.g., work email if configured that way) or name fragment "
            "to show only that manager's subtree."
        ),
    )

    args = parser.parse_args()

    if args.get_workers:
        print_worker_stats()
    elif args.org_chart:
        # If org_chart is a string, it's the identifier. If it's True, show full org chart
        if isinstance(args.org_chart, str):
            print_org_chart(manager_identifier=args.org_chart)
        else:
            print_org_chart()
    else:
        print("No action specified. Use --get_workers or --org_chart [identifier].")
