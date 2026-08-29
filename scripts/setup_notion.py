"""Creates the ProcureFlow Notion workspace (Control Center + 3 databases).

Usage:
    1. Create a Notion integration at https://www.notion.so/my-integrations
    2. Copy its "Internal Integration Secret" into NOTION_TOKEN in .env
    3. In Notion, create (or pick) a parent page and share it with the
       integration ("Add connections" -> your integration)
    4. Copy that page's ID into NOTION_PARENT_PAGE_ID (or pass --parent-page-id)
    5. Run: python scripts/setup_notion.py
    6. Copy the printed database IDs into .env and restart the backend
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.services.notion_service import setup_procureflow, NotionServiceError  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Bootstrap ProcureFlow Notion databases")
    parser.add_argument("--parent-page-id", default=os.environ.get("NOTION_PARENT_PAGE_ID", ""))
    args = parser.parse_args()

    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        raise SystemExit(
            "NOTION_TOKEN is not set.\n"
            "1. Create an integration at https://www.notion.so/my-integrations\n"
            "2. Add NOTION_TOKEN=<secret> to your .env file"
        )
    if not args.parent_page_id:
        raise SystemExit(
            "NOTION_PARENT_PAGE_ID is not set.\n"
            "Create a page in Notion, share it with your integration, "
            "then pass --parent-page-id or set NOTION_PARENT_PAGE_ID in .env"
        )

    print("Validating Notion token and parent page access...")
    try:
        result = setup_procureflow(args.parent_page_id)
    except NotionServiceError as exc:
        raise SystemExit(f"Setup failed: {exc}") from exc

    print("\n✓ ProcureFlow Control Center ready\n")
    print(f"Control Center URL: {result.get('procureflow_url') or result['procureflow_page']}")
    print(f"\nPurchase Requests: {result['purchase_requests_database']['url'] or result['purchase_requests_database']['id']}")
    print(f"Approval Queue:    {result['approval_queue_database']['url'] or result['approval_queue_database']['id']}")
    print(f"Run Log:           {result['run_log_database']['url'] or result['run_log_database']['id']}")
    print("\nAdd these lines to your .env file:\n")
    snippet = result.get("env_snippet", {})
    print(f"NOTION_REQUESTS_DATABASE_ID={snippet.get('NOTION_REQUESTS_DATABASE_ID', result['purchase_requests_database']['id'])}")
    print(f"NOTION_APPROVALS_DATABASE_ID={snippet.get('NOTION_APPROVALS_DATABASE_ID', result['approval_queue_database']['id'])}")
    print(f"NOTION_RUN_LOG_DATABASE_ID={snippet.get('NOTION_RUN_LOG_DATABASE_ID', result['run_log_database']['id'])}")
    print("\nRestart the backend, then open Integrations → Test Connection / Validate Schema.")


if __name__ == "__main__":
    main()
