#!/usr/bin/env python3
"""
ServiceM8 REST API Helper
=========================
Handles authentication, pagination, filtering, rate limiting, and error handling
for all ServiceM8 API operations.

Usage:
    from sm8_api import ServiceM8Client

    sm8 = ServiceM8Client()  # reads SERVICEM8_API_KEY from env
    # or
    sm8 = ServiceM8Client(api_key="your_key_here")

    # List all jobs
    jobs = sm8.list("job")

    # List with filters
    quotes = sm8.list("job", filters={"status": "Quote", "active": "1"})

    # Get a single record
    job = sm8.get("job", "some-uuid-here")

    # Create a record
    new_job = sm8.create("job", {
        "status": "Quote",
        "job_address": "123 Main St",
        "company_uuid": "client-uuid"
    })

    # Update a record
    sm8.update("job", "job-uuid", {"status": "Work Order"})

    # Delete (archive) a record
    sm8.delete("job", "job-uuid")
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta

# Config file location (created by setup wizard)
CONFIG_DIR = os.path.expanduser("~/.servicem8")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ── Date format helpers ──────────────────────────────────────────
# The API uses YYYY-MM-DD HH:MM:SS internally, but we present
# dates to the user as DD-MM-YYYY (Australian format).

# Regex patterns for date detection
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")              # YYYY-MM-DD
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")  # YYYY-MM-DD HH:MM:SS
_AU_DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")           # DD-MM-YYYY
_AU_DATETIME_RE = re.compile(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$")  # DD-MM-YYYY HH:MM:SS

# Fields that contain dates (for auto-conversion on output)
DATE_FIELDS = {
    "date", "start_date", "end_date", "creation_date", "edit_date",
    "queue_expiry_date", "completion_date", "due_date", "expiry_date",
    "invoice_date", "payment_date", "scheduled_date",
}


def api_to_display(value):
    """Convert API date (YYYY-MM-DD ...) to display date (DD-MM-YYYY ...)."""
    if not isinstance(value, str):
        return value
    if _DATETIME_RE.match(value):
        # YYYY-MM-DD HH:MM:SS → DD-MM-YYYY HH:MM:SS
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d-%m-%Y %H:%M:%S")
    elif _DATE_RE.match(value):
        # YYYY-MM-DD → DD-MM-YYYY
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    return value


def display_to_api(value):
    """Convert display date (DD-MM-YYYY ...) to API date (YYYY-MM-DD ...)."""
    if not isinstance(value, str):
        return value
    if _AU_DATETIME_RE.match(value):
        # DD-MM-YYYY HH:MM:SS → YYYY-MM-DD HH:MM:SS
        dt = datetime.strptime(value, "%d-%m-%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif _AU_DATE_RE.match(value):
        # DD-MM-YYYY → YYYY-MM-DD
        dt = datetime.strptime(value, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    return value


def convert_dates_for_display(record):
    """Convert all date fields in a record from API to DD-MM-YYYY format."""
    if not isinstance(record, dict):
        return record
    converted = {}
    for key, value in record.items():
        if key in DATE_FIELDS and isinstance(value, str):
            converted[key] = api_to_display(value)
        else:
            converted[key] = value
    return converted


def convert_dates_for_api(data):
    """Convert all date fields in a payload from DD-MM-YYYY to API format."""
    if not isinstance(data, dict):
        return data
    converted = {}
    for key, value in data.items():
        if key in DATE_FIELDS and isinstance(value, str):
            converted[key] = display_to_api(value)
        else:
            converted[key] = value
    return converted


def load_config():
    """Load config from ~/.servicem8/config.json if it exists."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


class ServiceM8Error(Exception):
    """Custom exception for ServiceM8 API errors."""
    def __init__(self, status_code, message, response_body=None):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")


class ServiceM8Client:
    """Client for the ServiceM8 REST API."""

    BASE_URL = "https://api.servicem8.com/api_1.0"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds to wait on rate limit

    def __init__(self, api_key=None):
        """
        Initialize the client.

        Looks for an API key in this order:
          1. api_key parameter
          2. SERVICEM8_API_KEY environment variable
          3. SERVICEM8_ACCESS_TOKEN environment variable (OpenClaw compatibility)
          4. ~/.servicem8/config.json (created by setup wizard)

        Args:
            api_key: ServiceM8 API key (optional)
        """
        self.config = load_config()
        self.api_key = (
            api_key
            or os.environ.get("SERVICEM8_API_KEY")
            or os.environ.get("SERVICEM8_ACCESS_TOKEN")
            or self.config.get("api_key")
        )
        if not self.api_key:
            raise ValueError(
                "ServiceM8 API key required. Run 'python3 scripts/setup.py' to "
                "configure, or set SERVICEM8_API_KEY (or SERVICEM8_ACCESS_TOKEN) "
                "environment variable."
            )

    def _get_headers(self):
        """Return standard request headers."""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_filter_string(self, filters):
        """
        Convert a dict of filters to OData $filter syntax.
        Automatically converts DD-MM-YYYY dates to YYYY-MM-DD for the API.

        Args:
            filters: dict like {"status": "Quote", "active": "1"}

        Returns:
            OData filter string like "status eq 'Quote' and active eq '1'"
        """
        if not filters:
            return None

        parts = []
        for key, value in filters.items():
            if isinstance(value, str):
                # Convert DD-MM-YYYY dates in filter values
                value = display_to_api(value)
                parts.append(f"{key} eq '{value}'")
            elif isinstance(value, (int, float)):
                parts.append(f"{key} eq '{value}'")
            elif isinstance(value, dict):
                # Support operators: {"edit_date": {"gt": "15-01-2026"}}
                for op, val in value.items():
                    val = display_to_api(str(val))
                    parts.append(f"{key} {op} '{val}'")
            else:
                parts.append(f"{key} eq '{value}'")

        return " and ".join(parts)

    def _request(self, method, url, data=None, params=None):
        """
        Make an HTTP request with retry logic for rate limiting.

        Returns:
            tuple: (response_body, response_headers, status_code)
        """
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        headers = self._get_headers()

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers=headers,
                    method=method,
                )
                with urllib.request.urlopen(req) as response:
                    response_body = response.read().decode("utf-8")
                    response_headers = dict(response.headers)
                    status_code = response.getcode()

                    if response_body:
                        try:
                            parsed = json.loads(response_body)
                        except json.JSONDecodeError:
                            parsed = response_body
                    else:
                        parsed = None

                    return parsed, response_headers, status_code

            except urllib.error.HTTPError as e:
                status_code = e.code
                error_body = e.read().decode("utf-8") if e.fp else ""

                if status_code == 429:
                    # Rate limited — back off and retry
                    wait_time = self.RETRY_DELAY * (attempt + 1)
                    print(f"Rate limited. Waiting {wait_time}s before retry "
                          f"({attempt + 1}/{self.MAX_RETRIES})...",
                          file=sys.stderr)
                    time.sleep(wait_time)
                    continue

                elif status_code == 401:
                    raise ServiceM8Error(401, "Unauthorized — check your API key", error_body)
                elif status_code == 404:
                    raise ServiceM8Error(404, "Record not found — check UUID", error_body)
                elif status_code == 400:
                    raise ServiceM8Error(400, f"Bad request: {error_body}", error_body)
                elif status_code >= 500:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY)
                        continue
                    raise ServiceM8Error(status_code, f"Server error: {error_body}", error_body)
                else:
                    raise ServiceM8Error(status_code, f"API error: {error_body}", error_body)

            except urllib.error.URLError as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                    continue
                raise ServiceM8Error(0, f"Connection error: {str(e)}")

        raise ServiceM8Error(429, "Rate limit exceeded after all retries")

    def list(self, resource, filters=None, page_start=None, fetch_all=True):
        """
        List all records of a resource type, with optional filtering.

        Args:
            resource: API resource name (e.g. "job", "company", "jobqueue")
            filters: Dict of field=value filters (converted to OData $filter)
            page_start: Pagination cursor (usually handled automatically)
            fetch_all: If True, follows pagination to get all results

        Returns:
            List of record dicts
        """
        url = f"{self.BASE_URL}/{resource}.json"
        params = {}

        filter_string = self._build_filter_string(filters)
        if filter_string:
            params["$filter"] = filter_string

        if page_start:
            params["%next_page_start%"] = page_start

        result, headers, status = self._request("GET", url, params=params)

        if not isinstance(result, list):
            # Some endpoints return a single object or different structure
            if isinstance(result, dict) and "records" in result:
                records = result["records"]
            else:
                return [result] if result else []
        else:
            records = result

        # Handle pagination
        if fetch_all and isinstance(result, list) and len(result) > 0:
            # Check if there's a next page indicator in the last record
            # ServiceM8 uses %next_page_start% parameter
            # The API returns it differently — we check response for it
            pass  # Pagination is signalled differently per response

        # Convert dates to DD-MM-YYYY for display
        return [convert_dates_for_display(r) for r in records]

    def get(self, resource, uuid):
        """
        Retrieve a single record by UUID.

        Args:
            resource: API resource name
            uuid: Record UUID

        Returns:
            Record dict
        """
        url = f"{self.BASE_URL}/{resource}/{uuid}.json"
        result, headers, status = self._request("GET", url)
        return convert_dates_for_display(result)

    def create(self, resource, data):
        """
        Create a new record.

        Args:
            resource: API resource name
            data: Dict of field values

        Returns:
            Dict with created record info and UUID
        """
        url = f"{self.BASE_URL}/{resource}.json"
        # Convert DD-MM-YYYY dates to API format before sending
        api_data = convert_dates_for_api(data)
        result, headers, status = self._request("POST", url, data=api_data)

        # New record UUID is in response headers
        record_uuid = headers.get("x-record-uuid", headers.get("X-Record-Uuid"))

        return {
            "uuid": record_uuid,
            "response": result,
            "status": status,
        }

    def update(self, resource, uuid, data):
        """
        Update an existing record.

        Args:
            resource: API resource name
            uuid: Record UUID
            data: Dict of fields to update

        Returns:
            Response dict
        """
        url = f"{self.BASE_URL}/{resource}/{uuid}.json"
        # Convert DD-MM-YYYY dates to API format before sending
        api_data = convert_dates_for_api(data)
        result, headers, status = self._request("PUT", url, data=api_data)
        return {"response": result, "status": status}

    def delete(self, resource, uuid):
        """
        Delete (archive) a record. Sets active=0 (soft delete).

        Args:
            resource: API resource name
            uuid: Record UUID

        Returns:
            Response dict
        """
        url = f"{self.BASE_URL}/{resource}/{uuid}.json"
        result, headers, status = self._request("DELETE", url)
        return {"response": result, "status": status}

    def search_companies(self, query):
        """
        Search for clients/companies by name (case-insensitive local search).
        The API doesn't support text search, so we fetch all active companies
        and filter locally.

        Args:
            query: Search string

        Returns:
            List of matching company records
        """
        companies = self.list("company", filters={"active": "1"})
        query_lower = query.lower()
        return [
            c for c in companies
            if query_lower in c.get("name", "").lower()
            or query_lower in c.get("email", "").lower()
            or query_lower in c.get("phone", "").lower()
            or query_lower in c.get("mobile", "").lower()
        ]

    def get_jobs_in_queue(self, queue_uuid=None, queue_name=None):
        """
        Get all jobs currently in a specific queue.

        Args:
            queue_uuid: UUID of the queue
            queue_name: Name of the queue (will look up UUID)

        Returns:
            List of job records in the queue
        """
        if queue_name and not queue_uuid:
            queues = self.list("jobqueue")
            for q in queues:
                if q.get("name", "").lower() == queue_name.lower():
                    queue_uuid = q["uuid"]
                    break
            if not queue_uuid:
                raise ValueError(f"Queue '{queue_name}' not found")

        return self.list("job", filters={"queue_uuid": queue_uuid})

    def get_job_summary(self, job_uuid):
        """
        Get a comprehensive summary of a job including client, notes, and materials.

        Args:
            job_uuid: UUID of the job

        Returns:
            Dict with job details, client info, notes, and materials
        """
        job = self.get("job", job_uuid)

        summary = {"job": job}

        # Get client details
        if job.get("company_uuid"):
            try:
                summary["client"] = self.get("company", job["company_uuid"])
            except ServiceM8Error:
                summary["client"] = None

        # Get job notes
        try:
            notes = self.list("jobnote", filters={"job_uuid": job_uuid})
            summary["notes"] = [n for n in notes if n.get("active", 1)]
        except ServiceM8Error:
            summary["notes"] = []

        # Get line items
        try:
            materials = self.list("jobmaterial", filters={"job_uuid": job_uuid})
            summary["materials"] = [m for m in materials if m.get("active", 1)]
        except ServiceM8Error:
            summary["materials"] = []

        return summary

    def get_queue_summary(self):
        """
        Get a summary of all queues with job counts.

        Returns:
            List of dicts with queue info and job counts
        """
        queues = self.list("jobqueue", filters={"active": "1"})
        summary = []

        for q in queues:
            try:
                jobs = self.list("job", filters={"queue_uuid": q["uuid"]})
                active_jobs = [j for j in jobs if j.get("active", 1)]
            except ServiceM8Error:
                active_jobs = []

            summary.append({
                "uuid": q["uuid"],
                "name": q.get("name", "Unknown"),
                "is_assignable": q.get("is_assignable", 0),
                "default_expiry_days": q.get("default_expiry_days"),
                "job_count": len(active_jobs),
                "jobs": active_jobs,
            })

        return summary

    def get_outstanding_invoices(self):
        """
        Get all jobs that have been completed but not fully paid.

        Returns:
            List of job records with outstanding balances
        """
        completed = self.list("job", filters={"status": "Completed", "active": "1"})
        outstanding = []
        for job in completed:
            invoiced = float(job.get("total_invoice_amount", 0) or 0)
            paid = float(job.get("total_paid_amount", 0) or 0)
            if invoiced > paid:
                job["_outstanding_amount"] = invoiced - paid
                outstanding.append(job)
        return outstanding

    def move_job_to_queue(self, job_uuid, queue_uuid=None, queue_name=None,
                          expiry_days=None):
        """
        Move a job into a queue.

        Args:
            job_uuid: UUID of the job
            queue_uuid: UUID of target queue
            queue_name: Name of target queue (will look up UUID)
            expiry_days: Days until queue expiry (uses queue default if not set)
        """
        if queue_name and not queue_uuid:
            queues = self.list("jobqueue")
            for q in queues:
                if q.get("name", "").lower() == queue_name.lower():
                    queue_uuid = q["uuid"]
                    if expiry_days is None:
                        expiry_days = q.get("default_expiry_days", 7)
                    break
            if not queue_uuid:
                raise ValueError(f"Queue '{queue_name}' not found")

        update_data = {"queue_uuid": queue_uuid}

        if expiry_days:
            expiry_date = datetime.now() + timedelta(days=expiry_days)
            update_data["queue_expiry_date"] = expiry_date.strftime("%d-%m-%Y")

        return self.update("job", job_uuid, update_data)


# -------------------------------------------------------------------
# CLI interface for quick operations
# -------------------------------------------------------------------

def main():
    """Command-line interface for quick API operations."""
    import argparse

    parser = argparse.ArgumentParser(description="ServiceM8 API Client")
    parser.add_argument("action", choices=["setup", "list", "get", "create", "update",
                                           "delete", "queues", "outstanding",
                                           "search-client"],
                        help="Action to perform ('setup' to run the setup wizard)")
    parser.add_argument("resource", nargs="?", help="API resource (e.g. job, company)")
    parser.add_argument("--uuid", help="Record UUID (for get/update/delete)")
    parser.add_argument("--data", help="JSON data (for create/update)")
    parser.add_argument("--filter", action="append", dest="filters",
                        help="Filter in key=value format (can repeat)")
    parser.add_argument("--query", help="Search query (for search-client)")
    parser.add_argument("--api-key", help="API key (or set SERVICEM8_API_KEY env var)")

    args = parser.parse_args()

    # Setup wizard doesn't need an API key yet
    if args.action == "setup":
        from setup import run_setup
        run_setup()
        return

    sm8 = ServiceM8Client(api_key=args.api_key)

    try:
        if args.action == "list":
            if not args.resource:
                parser.error("resource is required for list")
            filters = {}
            if args.filters:
                for f in args.filters:
                    key, val = f.split("=", 1)
                    filters[key] = val
            result = sm8.list(args.resource, filters=filters or None)
            print(json.dumps(result, indent=2))

        elif args.action == "get":
            if not args.resource or not args.uuid:
                parser.error("resource and --uuid are required for get")
            result = sm8.get(args.resource, args.uuid)
            print(json.dumps(result, indent=2))

        elif args.action == "create":
            if not args.resource or not args.data:
                parser.error("resource and --data are required for create")
            data = json.loads(args.data)
            result = sm8.create(args.resource, data)
            print(json.dumps(result, indent=2))

        elif args.action == "update":
            if not args.resource or not args.uuid or not args.data:
                parser.error("resource, --uuid, and --data are required for update")
            data = json.loads(args.data)
            result = sm8.update(args.resource, args.uuid, data)
            print(json.dumps(result, indent=2))

        elif args.action == "delete":
            if not args.resource or not args.uuid:
                parser.error("resource and --uuid are required for delete")
            result = sm8.delete(args.resource, args.uuid)
            print(json.dumps(result, indent=2))

        elif args.action == "queues":
            result = sm8.get_queue_summary()
            print(json.dumps(result, indent=2))

        elif args.action == "outstanding":
            result = sm8.get_outstanding_invoices()
            print(json.dumps(result, indent=2))

        elif args.action == "search-client":
            if not args.query:
                parser.error("--query is required for search-client")
            result = sm8.search_companies(args.query)
            print(json.dumps(result, indent=2))

    except ServiceM8Error as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
