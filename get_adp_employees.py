import requests
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
        url = f"https://api.adp.com/hr/v2/workers?offset={offset}&limit={limit}"
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

if __name__ == "__main__":
    employees_data = get_workers()
    workers = employees_data.get("workers", [])
    total_employees = len(workers)
    active_count = 0
    terminated_count = 0
    active_roles_set = set()
    for emp in workers:
        status = emp.get("workerStatus", {}).get("statusCode", {}).get("codeValue", "Unknown")
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
    print(f"Active employee roles:")
    for role in sorted(active_roles_set):
        print(f"  - {role}")