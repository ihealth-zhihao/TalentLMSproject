#!/usr/bin/env python3
"""
Quick test: print TalentLMS mandatory registration fields.
"""

import requests
import json
from config import DOMAIN, API_KEY


class TalentLMSClient:
    def __init__(self, domain, api_key):
        self.domain = domain.replace("https://", "").replace("http://", "")
        self.base_url = f"https://{self.domain}/api/v1"
        self.api_key = api_key

    def _make_request(self, endpoint):
        url = f"{self.base_url}{endpoint}"
        r = requests.get(url, auth=(self.api_key, ""))
        r.raise_for_status()
        return r.json()

    def show_required_fields(self):
        """Print required custom registration fields."""
        fields = self._make_request("/getcustomregistrationfields")
        required = [f for f in fields if f.get("mandatory") == "yes"]

        if not required:
            print("✓ No mandatory custom registration fields found.")
            return

        print("Mandatory custom registration fields:\n")
        for f in required:
            print(f"- {f['key']} ({f['name']}) — type: {f['type']}")
            if f.get("dropdown_values"):
                print(f"   allowed: {f['dropdown_values']}")
        print("\nKeys to include in your CSV or payload:")
        print(", ".join(f["key"] for f in required))


if __name__ == "__main__":
    client = TalentLMSClient(DOMAIN, API_KEY)
    client.show_required_fields()
