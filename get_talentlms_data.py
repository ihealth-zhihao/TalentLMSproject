#!/usr/bin/env python3
"""
Simple TalentLMS Data Retrieval Program
This program demonstrates the ability to retrieve data from TalentLMS API
by fetching and displaying user information.
"""

import requests
import json
from typing import Dict, List, Optional
from config import DOMAIN, API_KEY


class TalentLMSClient:
    """Simple client for interacting with TalentLMS API"""

    def __init__(self, domain: str, api_key: str):
        """
        Initialize the TalentLMS client
        """
        self.domain = domain.replace('https://', '').replace('http://', '')
        self.base_url = f"https://{self.domain}/api/v1"
        self.api_key = api_key

    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """
        Make an authenticated request to TalentLMS API

        Args:
            endpoint: API endpoint (e.g., '/users')
            method: HTTP method (GET, POST, etc.)
            data: Request payload for POST requests

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=(self.api_key, ''),  # API key as username, empty password
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            raise

    def get_users(self) -> List[Dict]:
        """
        Retrieve all users from TalentLMS

        Returns:
            List of user dictionaries
        """
        result = self._make_request('/users')
        if isinstance(result, dict):
            return [result]
        return result

    def get_user_by_id(self, user_id: int) -> Dict:
        """
        Retrieve a specific user by ID

        Args:
            user_id: The user's ID

        Returns:
            User dictionary
        """
        return self._make_request(f'/users/id:{user_id}')


def display_users_summary(users: List[Dict]) -> None:
    """
    Display a summary of users retrieved from TalentLMS

    Args:
        users: List of user dictionaries
    """
    print(f"Total Users: {len(users)}\n")

    print(f"{'ID':<10} {'First Name':<15} {'Last Name':<15} {'Email':<25}")

    for user in users[:10]:  # Display first 10 users
        user_id = user.get('id', 'N/A')
        first_name = user.get('first_name', 'N/A')
        last_name = user.get('last_name', 'N/A')
        email = user.get('email', 'N/A')
        print(f"{user_id:<10} {first_name:<15} {last_name:<15} {email:<25}")

    if len(users) > 10:
        print(f"\n... and {len(users) - 10} more users")



def display_first_names(users: List[Dict]) -> None:
    """
    Display just the first names of all users

    Args:
        users: List of user dictionaries
    """
    print(f"User First Names")

    first_names = [user.get('first_name', 'Unknown') for user in users]

    for i, name in enumerate(first_names, 1):
        print(f"{i}. {name}")

    print(f"\nTotal: {len(first_names)} users")



def main():
    """Main program execution"""
    # Use credentials from config file
    # DOMAIN and API_KEY are imported
    client = TalentLMSClient(DOMAIN, API_KEY)

    try:
        # Retrieve all users
        print("\nFetching users from TalentLMS...")
        users = client.get_users()

        # Display users summary
        display_users_summary(users)

        # Display just first names
        display_first_names(users)

        # Optional: Get details of the first user
        if users:
            first_user_id = users[0].get('id')
            if isinstance(first_user_id, int):
                print(f"\nFetching detailed information for user ID {first_user_id}...")
                user_detail = client.get_user_by_id(first_user_id)
                print(f"\nDetailed User Information:")
                print(json.dumps(user_detail, indent=2))
            else:
                print("\nFirst user does not have a valid 'id'.")

        print("\n✓ Successfully retrieved data from TalentLMS!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease ensure:")
        print("1. Your domain is correct (e.g., 'yourcompany.talentlms.com')")
        print("2. Your API key is valid")
        print("3. Your TalentLMS account has API access enabled")


if __name__ == "__main__":
    main()
