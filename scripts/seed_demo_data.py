"""Fires the three demo scenarios at a running ProcureFlow backend via
real HTTP requests (not direct function calls) so it exercises the same
path the frontend/webhook would use.

Usage:
    python scripts/seed_demo_data.py --base-url http://localhost:8000
"""
import argparse
import json
import time

import httpx

SCENARIOS = [
    {
        "label": "DEMO 1 - Automatic (low risk)",
        "payload": {
            "employee_name": "Rahul Sharma",
            "employee_email": "rahul.demo1@example.com",
            "department": "Engineering",
            "request_text": "I need 5 keyboards for the engineering team because our new interns are joining next week.",
        },
    },
    {
        "label": "DEMO 2 - Human approval (high risk)",
        "payload": {
            "employee_name": "Ananya Rao",
            "employee_email": "ananya.demo2@example.com",
            "department": "Data Science",
            "request_text": "We need 3 MacBook Pro laptops for the new data science team. They start Monday.",
        },
    },
    {
        "label": "DEMO 3 - Ambiguous (needs review)",
        "payload": {
            "employee_name": "Karan Mehta",
            "employee_email": "karan.demo3@example.com",
            "department": "Operations",
            "request_text": "I need something urgently for the team.",
        },
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    for scenario in SCENARIOS:
        print(f"\n=== {scenario['label']} ===")
        resp = httpx.post(f"{args.base_url}/api/requests", json=scenario["payload"], timeout=30)
        print(f"HTTP {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        time.sleep(1)

    print("\nDemo requests submitted. Check the Notion Approval Queue for DEMO 2's pending item.")


if __name__ == "__main__":
    main()
