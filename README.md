# TalentLMS Data Retrieval Program

Quick project to retrieve and push user information from the TalentLMS API.

## Setup & Usage

### 1. Open a Terminal and Navigate to the Project Directory
```sh
cd /.../TalentLMSproject
```

### 2. Activate the Virtual Environment
```sh
source .venv/bin/activate
```

If you don't have a virtual environment yet, you can create one with:
```sh
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```sh
pip install requests
```

### 4. Run the Program
```sh
python get_talentlms_data.py
```

## Script Usage

### get_adp_info.py
Fetch worker stats and org chart from ADP.

```sh
# Print worker statistics (active/terminated counts, roles)
python get_adp_info.py --get_workers

# Print full org chart
python get_adp_info.py --org_chart

# Print org chart for specific manager (by email or name)
python get_adp_info.py --org_chart manager@company.com
```

### sync_single_employee.py
Create TalentLMS account for a single employee from ADP data.

```sh
# Sync by email, name, or worker ID
python sync_single_employee.py employee@company.com
```

### delete_talentlms_user.py
Permanently delete a TalentLMS user by email.

```sh
python delete_talentlms_user.py user@company.com
```

## Notes
- Make sure your API key and domain are set correctly in the script.
- If you add more dependencies, install them with `pip install <package>` while the venv is activated.
- To deactivate the virtual environment, simply run:
```sh
deactivate
```
