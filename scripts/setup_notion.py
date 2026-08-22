"""Creates the three ProcureFlow Notion databases (Purchase Requests,
Approval Queue, Run Log) under a parent page, with the properties the
backend expects.

Usage:
    1. Create a Notion integration at https://www.notion.so/my-integrations
    2. Copy its "Internal Integration Secret" into NOTION_TOKEN in .env
    3. In Notion, create (or pick) a parent page and share it with the
       integration ("Add connections" -> your integration)
    4. Copy that page's ID into NOTION_PARENT_PAGE_ID below (or pass --parent-page-id)
    5. Run: python scripts/setup_notion.py
    6. Copy the printed database IDs into .env
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv  # noqa: E402
from notion_client import Client  # noqa: E402
from app.services.notion_service import setup_procureflow  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def build_client(token: str) -> Client:
    if not token:
        raise SystemExit("NOTION_TOKEN is not set. Add it to your environment or .env file.")
    return Client(auth=token)


def create_requests_db(client: Client, parent_page_id: str) -> str:
    db = client.databases.create(
        parent={"page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "ProcureFlow - Purchase Requests"}}],
        properties={
            "Request ID": {"title": {}},
            "Employee": {"rich_text": {}},
            "Email": {"rich_text": {}},
            "Department": {"select": {"options": []}},
            "Request": {"rich_text": {}},
            "Category": {"select": {"options": []}},
            "Quantity": {"number": {}},
            "Estimated Amount": {"number": {"format": "rupee"}},
            "Risk": {"select": {"options": [
                {"name": "Low", "color": "green"},
                {"name": "Medium", "color": "yellow"},
                {"name": "High", "color": "red"},
                {"name": "Unknown", "color": "gray"},
            ]}},
            "Priority": {"select": {"options": [
                {"name": "Low", "color": "gray"},
                {"name": "Medium", "color": "yellow"},
                {"name": "High", "color": "red"},
            ]}},
            "AI Confidence": {"number": {"format": "percent"}},
            "Status": {"select": {"options": [
                {"name": s, "color": c} for s, c in [
                    ("Received", "gray"), ("Processing", "blue"), ("Pending Approval", "yellow"),
                    ("Approved", "green"), ("Rejected", "red"), ("Auto-Processed", "blue"),
                    ("Completed", "green"), ("Failed", "red"), ("Needs Review", "orange"),
                ]
            ]}},
            "Approval Required": {"checkbox": {}},
            "Approver": {"rich_text": {}},
        },
    )
    return db["id"]


def create_approvals_db(client: Client, parent_page_id: str) -> str:
    db = client.databases.create(
        parent={"page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "ProcureFlow - Approval Queue"}}],
        properties={
            "Request ID": {"title": {}},
            "Employee": {"rich_text": {}},
            "Purchase": {"rich_text": {}},
            "Amount": {"number": {"format": "rupee"}},
            "Risk": {"select": {"options": [
                {"name": "Low", "color": "green"}, {"name": "Medium", "color": "yellow"}, {"name": "High", "color": "red"},
            ]}},
            "AI reasoning summary": {"rich_text": {}},
            "Recommended action": {"rich_text": {}},
            "Status": {"select": {"options": [
                {"name": "Pending", "color": "yellow"},
                {"name": "Approved", "color": "green"},
                {"name": "Rejected", "color": "red"},
                {"name": "Override", "color": "purple"},
            ]}},
        },
    )
    return db["id"]


def create_run_log_db(client: Client, parent_page_id: str) -> str:
    db = client.databases.create(
        parent={"page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "ProcureFlow - Run Log"}}],
        properties={
            "Run ID": {"title": {}},
            "Request ID": {"rich_text": {}},
            "Event": {"select": {"options": []}},
            "Status": {"select": {"options": [
                {"name": "SUCCESS", "color": "green"},
                {"name": "FAILURE", "color": "red"},
                {"name": "INFO", "color": "gray"},
            ]}},
            "Action": {"rich_text": {}},
            "Actor": {"rich_text": {}},
            "Reason": {"rich_text": {}},
            "Error": {"rich_text": {}},
            "External Action ID": {"rich_text": {}},
        },
    )
    return db["id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-page-id", default=os.environ.get("NOTION_PARENT_PAGE_ID", ""))
    args = parser.parse_args()

    token = os.environ.get("NOTION_TOKEN", "")
    if not args.parent_page_id:
        raise SystemExit("Pass --parent-page-id or set NOTION_PARENT_PAGE_ID")

    client = build_client(token)

    result = setup_procureflow(args.parent_page_id)
    print(f"ProcureFlow page: {result['procureflow_url'] or result['procureflow_page']}")
    print(f"NOTION_REQUESTS_DATABASE_ID={result['purchase_requests_database']['id']}")
    print(f"NOTION_APPROVALS_DATABASE_ID={result['approval_queue_database']['id']}")
    print(f"NOTION_RUN_LOG_DATABASE_ID={result['run_log_database']['id']}")
    print("\nCopy the three IDs above into your .env file, then restart the backend.")


if __name__ == "__main__":
    main()
