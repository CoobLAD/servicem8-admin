---
name: servicem8-admin
description: >
  Manage a ServiceM8 field service business via the REST API. Use this skill whenever the user
  mentions ServiceM8, jobs, clients, quoting, invoicing, scheduling, dispatch, job queues, staff,
  materials, job notes, forms, badges, or any field service management task. Triggers on phrases
  like "create a job", "check the schedule", "list pending quotes", "send invoice", "what's in the
  parts queue", "add a note to job", "look up client", "move job to queue", "list materials",
  "staff availability", "outstanding invoices", or any reference to their ServiceM8 account data.
  Also use when the user wants reports, summaries, or bulk operations across their ServiceM8 data.
---

# ServiceM8 Admin Agent

Interact with a ServiceM8 account via the REST API to manage jobs, clients, scheduling,
quoting, invoicing, queues, staff, materials, notes, and more.

## Setup & Authentication

### First-time setup (recommended)

Run the interactive setup wizard from the skill's scripts directory:

```bash
python3 scripts/setup.py
```

The wizard will:
1. Prompt for your ServiceM8 API key
2. Test the connection and display your account details
3. Check which endpoints your key can access
4. Save the key securely to `~/.servicem8/config.json`
5. Generate a sourceable `.env` file at `~/.servicem8/.env`

After setup, the API client automatically loads your key from the config file —
no environment variable needed.

### Manual setup (alternative)

If you prefer, set the API key as an environment variable:
```
export SERVICEM8_API_KEY=your_api_key_here
```

Or source the generated env file:
```
source ~/.servicem8/.env
```

**To generate an API key:**
1. Log in to ServiceM8 online dashboard
2. Go to Settings → API & Webhooks
3. Click 'Generate API Key'
4. Copy the key

**Base URL:** `https://api.servicem8.com/api_1.0/`

Every request includes these headers automatically:
```
X-API-Key: {api_key}
Content-Type: application/json
```

### Date Format

All dates are displayed and accepted in **DD-MM-YYYY** format (Australian standard).
The client automatically converts to/from the API's internal YYYY-MM-DD format.

Examples:
- `"15-03-2026"` → date
- `"15-03-2026 08:00:00"` → datetime

## Quick Start

Before making any API calls, read `references/endpoints.md` for the full endpoint reference
including field names, naming conventions, and filter syntax.

Use the helper script at `scripts/sm8_api.py` for all API operations. It handles auth,
pagination, filtering, error handling, and rate limiting automatically.

## Core Workflow

### 1. Understand the request
Map the user's natural language to the correct API resource. Key naming differences:

| User says         | API resource     | Endpoint                    |
|-------------------|------------------|-----------------------------|
| Client/Customer   | Company          | `/company.json`             |
| Job               | Job              | `/job.json`                 |
| Line item         | JobMaterial      | `/jobmaterial.json`         |
| Booking/Schedule  | JobActivity      | `/jobactivity.json`         |
| Quote/Invoice/Doc | Attachment       | `/attachment.json`          |
| Staff member      | Staff            | `/staff.json`               |
| Job queue         | JobQueue         | `/jobqueue.json`            |
| Job note          | JobNote          | `/jobnote.json`             |
| Material/Product  | Material         | `/material.json`            |
| Job contact       | JobContact       | `/jobcontact.json`          |
| Client contact    | CompanyContact   | `/companycontact.json`      |
| Category          | JobCategory      | `/jobcategory.json`         |
| Task              | Task             | `/task.json`                |
| Asset             | Asset            | `/asset.json`               |
| Location          | Location         | `/location.json`            |
| Form response     | FormResponse     | `/formresponse.json`        |

### 2. Execute the API call
Use `scripts/sm8_api.py` — never construct raw HTTP requests manually. The script handles:
- Auth headers
- Pagination (follows `%next_page_start%` automatically)
- Filtering via `$filter` query parameter
- Rate limit awareness (max 60/min, 20,000/day)
- Error handling with meaningful messages

### 3. Present results
Format API responses in a way that's useful to the user. For lists, summarise key fields.
For single records, show the important details. Always translate API field names back to
user-friendly terms (e.g. "Company" → "Client").

## Common Operations

### Jobs

**List jobs by status:**
```python
# Status values: Quote, Work Order, In Progress, Completed, Unsuccessful
jobs = sm8.list("job", filters={"status": "Quote"})
```

**Create a job:**
```python
job = sm8.create("job", {
    "status": "Quote",
    "job_address": "34 Pacific Drive, Fingal Bay NSW",
    "company_uuid": "uuid-of-client",
    "job_description": "Switchboard upgrade - 3 phase",
    "category_uuid": "uuid-of-category"
})
```

**Update a job:**
```python
sm8.update("job", job_uuid, {"status": "Work Order"})
```

### Clients (Companies)

**Search clients:**
```python
clients = sm8.list("company", filters={"active": 1})
# Then filter locally by name/address if needed
```

**Create a client:**
```python
client = sm8.create("company", {
    "name": "John Smith",
    "address": "34 Pacific Drive",
    "city": "Fingal Bay",
    "state": "NSW",
    "postcode": "2315",
    "phone": "0412345678",
    "email": "john@example.com"
})
```

### Queues

**List all queues:**
```python
queues = sm8.list("jobqueue")
```

**Get jobs in a specific queue:**
```python
# Jobs have a queue_uuid field when they're in a queue
jobs = sm8.list("job", filters={"queue_uuid": queue_uuid})
```

**Move a job to a queue:**
```python
sm8.update("job", job_uuid, {
    "queue_uuid": queue_uuid,
    "queue_expiry_date": "01-04-2026"  # When to flag for review
})
```

**Remove a job from a queue:**
```python
sm8.update("job", job_uuid, {"queue_uuid": ""})
```

### Scheduling (JobActivity)

**List upcoming bookings:**
```python
bookings = sm8.list("jobactivity", filters={"activity_was_scheduled": 1})
```

**Create a booking:**
```python
sm8.create("jobactivity", {
    "job_uuid": job_uuid,
    "staff_uuid": staff_uuid,
    "activity_was_scheduled": 1,
    "start_date": "15-03-2026 08:00:00",
    "end_date": "15-03-2026 12:00:00"
})
```

**Get recorded time (check-ins):**
```python
time_logs = sm8.list("jobactivity", filters={"activity_was_scheduled": 0})
```

### Materials & Line Items

**List materials catalogue:**
```python
materials = sm8.list("material")
```

**Add line item to a job:**
```python
sm8.create("jobmaterial", {
    "job_uuid": job_uuid,
    "material_uuid": material_uuid,  # optional, can be ad-hoc
    "name": "RCD Safety Switch",
    "cost": 45.00,
    "price": 85.00,
    "qty": 2,
    "tax_rate_uuid": tax_rate_uuid
})
```

### Job Notes & Diary

**Add a note:**
```python
sm8.create("jobnote", {
    "job_uuid": job_uuid,
    "note": "Client confirmed access via side gate. Dog on premises.",
    "staff_uuid": staff_uuid  # optional
})
```

**List notes for a job:**
```python
notes = sm8.list("jobnote", filters={"job_uuid": job_uuid})
```

### Staff

**List all staff:**
```python
staff = sm8.list("staff", filters={"active": 1})
```

### Badges

Badges are visual tags on job cards. They link to forms and automations.
```python
# Badges are managed via the job record's badges field
# or through the badges API for account-level badge definitions
```

## Reporting Patterns

For composite reports, make multiple API calls and aggregate in Python:

**Outstanding invoices:**
```python
jobs = sm8.list("job", filters={"status": "Completed"})
# Filter for those with total_invoice_amount > total_paid_amount
```

**Jobs per queue summary:**
```python
queues = sm8.list("jobqueue")
for q in queues:
    jobs = sm8.list("job", filters={"queue_uuid": q["uuid"]})
    print(f"{q['name']}: {len(jobs)} jobs")
```

**Staff workload:**
```python
activities = sm8.list("jobactivity", filters={"activity_was_scheduled": 1})
# Group by staff_uuid and date range
```

## Rate Limits

- **60 requests per minute** per application per account
- **20,000 requests per day** per application per account
- HTTP 429 response if exceeded
- The helper script automatically backs off on 429 responses

For bulk operations, batch requests and add delays. Use filtering to reduce the number
of records returned rather than fetching everything and filtering locally.

## Filtering

The API supports OData-style `$filter` query parameters:

```
$filter=status eq 'Quote'
$filter=edit_date gt '01-01-2026'
$filter=status eq 'Quote' and active eq '1'
```

Supported operators: `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `and`, `or`

The helper script accepts a Python dict and converts to filter syntax automatically.
DD-MM-YYYY dates in filter values are converted to the API's YYYY-MM-DD format.

## Pagination

Large result sets are paginated. The response includes a `%next_page_start%` value.
The helper script handles this automatically and returns all results.

## Error Handling

| Code | Meaning                    | Action                        |
|------|----------------------------|-------------------------------|
| 200  | Success                    | Process response              |
| 201  | Created                    | Record created, check headers |
| 400  | Bad request                | Check payload fields          |
| 401  | Unauthorized               | Check API key                 |
| 404  | Not found                  | Check UUID                    |
| 429  | Rate limited               | Back off and retry            |
| 500  | Server error               | Retry after delay             |

New record UUIDs are returned in the `x-record-uuid` response header on POST requests.

## Important Notes

- UUIDs are the primary identifiers for all records. Always use UUIDs, not display IDs.
- `generated_job_id` is the human-readable job number (e.g. "#1234") — useful for display.
- The `active` field is used for soft-deletes. Set `active: 0` to archive, `active: 1` to restore.
- Date fields use `DD-MM-YYYY HH:MM:SS` format (converted automatically to/from API format).
- All monetary values are in the account's default currency.
- When creating records, UUID is optional — the API generates one if not supplied.
