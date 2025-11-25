#!/usr/bin/env python3
"""
TalentLMS Employee Import Program
This program imports new employees into TalentLMS and optionally assigns them to courses.
"""

import requests
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from config import DOMAIN, API_KEY


class TalentLMSClient:
    """Client for interacting with TalentLMS API"""

    def __init__(self, domain: str, api_key: str):
        """
        Initialize the TalentLMS client

        Args:
            domain: Your TalentLMS domain (e.g., 'yourcompany.talentlms.com')
            api_key: Your TalentLMS API key
        """
        self.domain = domain.replace('https://', '').replace('http://', '')
        self.base_url = f"https://{self.domain}/api/v1"
        self.api_key = api_key

    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """
        Make an authenticated request to TalentLMS API

        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request payload

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=(self.api_key, ''),
                data=data
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            raise

    def create_user(self, first_name: str, last_name: str, email: str,
                    login: str, password: Optional[str] = None,
                    user_type: Optional[str] = None) -> Dict:
        """
        Create a new user in TalentLMS

        Args:
            first_name: User's first name
            last_name: User's last name
            email: User's email address
            login: Username for login
            password: Password (optional, TalentLMS will generate if not provided)
            user_type: User type (Learner, Instructor, Administrator - optional, defaults to Learner if not provided)

        Returns:
            Created user dictionary
        """
        data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'login': login
        }

        if password:
            data['password'] = password

        if user_type:
            data['user_type'] = user_type

        return self._make_request('/usersignup', method='POST', data=data)

    def add_user_to_course(self, user_id: int, course_id: int, role: str = "learner") -> Dict:
        """
        Enroll a user in a course

        Args:
            user_id: The user's ID
            course_id: The course ID
            role: Role in the course (learner or instructor)

        Returns:
            Response dictionary
        """
        data = {
            'user_id': user_id,
            'course_id': course_id,
            'role': role
        }

        return self._make_request('/addusertocourse', method='POST', data=data)

    def get_courses(self) -> List[Dict]:
        """
        Get all courses

        Returns:
            List of course dictionaries
        """
        return self._make_request('/courses')

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Check if a user exists by email

        Args:
            email: Email to search for

        Returns:
            User dictionary if found, None otherwise
        """
        try:
            return self._make_request(f'/users/email:{email}')
        except requests.exceptions.HTTPError as e:
            # 404 is expected when user doesn't exist
            if e.response.status_code == 404:
                return None
            # Re-raise other HTTP errors
            raise
        except:
            return None


class EmployeeImporter:
    """Handles importing employees into TalentLMS"""

    def __init__(self, client: TalentLMSClient):
        self.client = client
        self.import_log = []

    def import_employee(self, employee: Dict, courses_to_assign: Optional[List[int]] = None) -> Dict:
        """
        Import a single employee

        Args:
            employee: Dictionary with employee data (first_name, last_name, email, login)
            courses_to_assign: Optional list of course IDs to enroll the user in

        Returns:
            Dictionary with import result
        """
        result = {
            'email': employee.get('email'),
            'status': 'pending',
            'user_id': None,
            'errors': [],
            'courses_assigned': []
        }

        try:
            # Check if user already exists
            existing_user = self.client.get_user_by_email(employee['email'])

            if existing_user:
                result['status'] = 'skipped'
                result['user_id'] = existing_user.get('id')
                result['errors'].append('User already exists')
                print(f"  ⚠ User {employee['email']} already exists (ID: {result['user_id']})")
            else:
                # Create new user
                new_user = self.client.create_user(
                    first_name=employee['first_name'],
                    last_name=employee['last_name'],
                    email=employee['email'],
                    login=employee.get('login', employee['email']),
                    password=employee.get('password'),
                    user_type=employee.get('user_type')
                )

                result['user_id'] = new_user.get('id')
                result['status'] = 'success'
                print(f"  ✓ Created user {employee['email']} (ID: {result['user_id']})")

            # Assign courses if specified
            if courses_to_assign and result['user_id']:
                for course_id in courses_to_assign:
                    try:
                        self.client.add_user_to_course(result['user_id'], course_id)
                        result['courses_assigned'].append(course_id)
                        print(f"    → Enrolled in course {course_id}")
                    except Exception as e:
                        result['errors'].append(f"Failed to assign course {course_id}: {str(e)}")

        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            print(f"  ✗ Failed to import {employee['email']}: {str(e)}")

        self.import_log.append(result)
        return result

    def import_from_csv(self, csv_file_path: str, courses_to_assign: Optional[List[int]] = None) -> Dict:
        """
        Import employees from a CSV file

        Args:
            csv_file_path: Path to CSV file with employee data
            courses_to_assign: Optional list of course IDs to assign to all imported users

        Returns:
            Summary dictionary
        """
        print(f"\nImporting employees from {csv_file_path}...")
        print("="*60)

        summary = {
            'total': 0,
            'success': 0,
            'skipped': 0,
            'failed': 0
        }

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    summary['total'] += 1
                    print(f"\n[{summary['total']}] Processing {row.get('email', 'N/A')}...")

                    result = self.import_employee(row, courses_to_assign)

                    if result['status'] == 'success':
                        summary['success'] += 1
                    elif result['status'] == 'skipped':
                        summary['skipped'] += 1
                    else:
                        summary['failed'] += 1

        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_file_path}")
        except Exception as e:
            print(f"Error reading CSV: {e}")

        return summary

    def import_from_list(self, employees: List[Dict], courses_to_assign: Optional[List[int]] = None) -> Dict:
        """
        Import employees from a list of dictionaries

        Args:
            employees: List of employee dictionaries
            courses_to_assign: Optional list of course IDs to assign

        Returns:
            Summary dictionary
        """
        print(f"\nImporting {len(employees)} employees...")
        print("="*60)

        summary = {
            'total': len(employees),
            'success': 0,
            'skipped': 0,
            'failed': 0
        }

        for i, employee in enumerate(employees, 1):
            print(f"\n[{i}/{len(employees)}] Processing {employee.get('email', 'N/A')}...")

            result = self.import_employee(employee, courses_to_assign)

            if result['status'] == 'success':
                summary['success'] += 1
            elif result['status'] == 'skipped':
                summary['skipped'] += 1
            else:
                summary['failed'] += 1

        return summary

    def save_import_log(self, output_file: str = None):
        """
        Save import log to JSON file in import_logs/YYYYMMDD/
        """
        from pathlib import Path
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        log_dir = Path("import_logs") / date_str
        log_dir.mkdir(parents=True, exist_ok=True)
        if not output_file:
            output_file = str(log_dir / f"import_log_{time_str}.json")
        else:
            output_file = str(log_dir / output_file)
        output_file_str = str(output_file)
        with open(output_file_str, 'w', encoding='utf-8') as f:
            json.dump(self.import_log, f, indent=2)
        print(f"\nImport log saved to {output_file_str}")


def print_summary(summary: Dict):
    """Print import summary"""
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Total Employees:    {summary['total']}")
    print(f"Successfully Added: {summary['success']}")
    print(f"Skipped (Existing): {summary['skipped']}")
    print(f"Failed:             {summary['failed']}")
    print("="*60)


def main():
    """Main program execution"""

    # Initialize client and importer
    client = TalentLMSClient(DOMAIN, API_KEY)
    importer = EmployeeImporter(client)

    # Example 1: Import from a list of employees
    sample_employees = [
        {
            'first_name': 'Test',
            'last_name': '1',
            'email': 'test.1@example.com',
            'login': 'test.1',
            'password': 'TempPass123!'
        },
        {
            'first_name': 'Test',
            'last_name': '2',
            'email': 'test.2@example.com',
            'login': 'test.2',
            'password': 'TempPass123!'
        },
        {
            'first_name': 'Test',
            'last_name': '3',
            'email': 'test.3@example.com',
            'login': 'test.3',
            'password': 'TempPass123!'
        }
    ]

    # Optional: Specify course IDs to automatically enroll users
    # courses_to_assign = [123, 456]  # Replace with actual course IDs
    courses_to_assign = None

    try:
        # Import employees
        summary = importer.import_from_list(sample_employees, courses_to_assign)

        # Print summary
        print_summary(summary)

        # Save log
        importer.save_import_log()

        # Example 2: Import from CSV (uncomment to use)
        # csv_file_path = "employees.csv"
        # summary = importer.import_from_csv(csv_file_path, courses_to_assign)
        # print_summary(summary)
        # importer.save_import_log()

    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        print("\nPlease ensure:")
        print("1. Your domain and API key are correct")
        print("2. Your TalentLMS account has API access enabled")
        print("3. You have permission to create users")


if __name__ == "__main__":
    main()
