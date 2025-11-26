import requests
from config import DOMAIN, API_KEY    


def list_courses():
    url = f"https://{DOMAIN}/api/v1/courses"
    
    resp = requests.get(url, auth=(API_KEY, ""))  # API key as username, empty password
    resp.raise_for_status()
    
    courses = resp.json()
    print("\n=== TalentLMS Courses ===\n")
    
    for c in courses:
        cid = c.get("id")
        name = c.get("name")
        code = c.get("code") or "-"
        print(f"ID: {cid:<5} | Code: {code:<10} | Name: {name}")
    
    print("\nTotal courses:", len(courses))


if __name__ == "__main__":
    list_courses()
