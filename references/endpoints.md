# ServiceM8 REST API Endpoint Reference

Base URL: `https://api.servicem8.com/api_1.0/`

All endpoints support: GET (list/retrieve), POST (create), PUT (update), DELETE (archive).
- List: `GET /{resource}.json`
- Retrieve: `GET /{resource}/{uuid}.json`
- Create: `POST /{resource}.json`
- Update: `PUT /{resource}/{uuid}.json`
- Delete: `DELETE /{resource}/{uuid}.json`

---

## Jobs

**Endpoint:** `/job.json`
**Scope:** `read_jobs`, `manage_jobs`, `create_jobs`

Key fields:
- `uuid` — unique identifier
- `generated_job_id` — human-readable job number (e.g. "1234")
- `status` — Quote | Work Order | In Progress | Completed | Unsuccessful
- `job_address` — full street address
- `job_description` — description / scope of work
- `company_uuid` — linked client
- `category_uuid` — job category
- `queue_uuid` — current queue (empty if not queued)
- `queue_expiry_date` — when queued job should be flagged
- `total_invoice_amount` — total value
- `total_paid_amount` — amount paid
- `job_is_scheduled` — 1 if scheduled, 0 if not
- `date` — job date
- `badges` — comma-separated badge names
- `active` — 1 = active, 0 = archived
- `edit_date` — last modified timestamp
- `creation_date` — when created

---

## Companies (Clients)

**Endpoint:** `/company.json`
**Scope:** `read_customers`, `manage_customers`

Key fields:
- `uuid`
- `name` — client/company name
- `address`, `city`, `state`, `postcode`, `country`
- `phone`, `mobile`, `fax`
- `email`, `website`
- `billing_address`, `billing_city`, `billing_state`, `billing_postcode`
- `active`

---

## Company Contacts

**Endpoint:** `/companycontact.json`
**Scope:** `read_customer_contacts`, `manage_customer_contacts`

Key fields:
- `uuid`
- `company_uuid` — parent company
- `first`, `last` — name
- `email`, `phone`, `mobile`
- `type` — contact type
- `is_primary_contact` — 1/0

---

## Job Contacts

**Endpoint:** `/jobcontact.json`
**Scope:** `read_job_contacts`, `manage_job_contacts`

Key fields:
- `uuid`
- `job_uuid` — parent job
- `first`, `last`
- `email`, `phone`, `mobile`
- `type`
- `is_primary_contact`

---

## Job Activities (Schedule / Time)

**Endpoint:** `/jobactivity.json`
**Scope:** `read_schedule`, `manage_schedule`

Key fields:
- `uuid`
- `job_uuid` — linked job
- `staff_uuid` — assigned staff member
- `activity_was_scheduled` — 1 = booking, 0 = recorded time (check-in/out)
- `start_date`, `end_date` — datetime
- `duration_minutes`
- `active`

---

## Job Materials (Line Items)

**Endpoint:** `/jobmaterial.json`
**Scope:** `read_job_materials`, `manage_job_materials`

Key fields:
- `uuid`
- `job_uuid` — parent job
- `material_uuid` — linked catalogue item (optional)
- `name` — display name
- `description`
- `cost` — cost price
- `price` — sell price
- `qty` — quantity
- `tax_rate_uuid`
- `active`

---

## Materials (Product Catalogue)

**Endpoint:** `/material.json`
**Scope:** `read_inventory`, `manage_inventory`

Key fields:
- `uuid`
- `name`
- `description`
- `cost` — cost price
- `price` — sell price
- `supplier`
- `material_code` — SKU / part number
- `active`

---

## Staff

**Endpoint:** `/staff.json`
**Scope:** `read_staff`, `manage_staff`

Key fields:
- `uuid`
- `first`, `last` — name
- `email`, `mobile`
- `role` — role/position
- `active`
- `is_admin` — 1/0
- `colour` — calendar colour

---

## Job Queues

**Endpoint:** `/jobqueue.json`
**Scope:** `read_job_queues`, `manage_job_queues`

Key fields:
- `uuid`
- `name` — queue name
- `default_expiry_days` — default days before a job expires from queue
- `is_assignable` — 1 = assignable queue (requires staff), 0 = regular
- `active`

---

## Job Notes (Job Diary)

**Endpoint:** `/jobnote.json`
**Scope:** `read_job_notes`, `publish_job_notes`

Key fields:
- `uuid`
- `job_uuid` — parent job
- `note` — text content
- `staff_uuid` — who wrote it
- `creation_date`
- `active`

---

## Attachments (Photos, Docs in Job Diary)

**Endpoint:** `/attachment.json`
**Scope:** `read_job_attachments`, `publish_job_attachments`

Key fields:
- `uuid`
- `job_uuid`
- `attachment_name`
- `attachment_source` — e.g. "photo", "document"
- `file_type`
- `active`

File content: `GET /attachment/{uuid}.file`

---

## Job Categories

**Endpoint:** `/jobcategory.json`
**Scope:** `read_job_categories`, `manage_job_categories`

Key fields:
- `uuid`
- `name` — category name
- `active`

---

## Tasks

**Endpoint:** `/task.json`
**Scope:** `read_tasks`, `manage_tasks`

Key fields:
- `uuid`
- `name` — task name
- `description`
- `active`

---

## Assets

**Endpoint:** `/asset.json`
**Scope:** `read_assets`, `manage_assets`

Key fields:
- `uuid`
- `name`
- `company_uuid` — owner
- `serial_number`
- `model`
- `manufacturer`
- `active`

---

## Locations

**Endpoint:** `/location.json`
**Scope:** `read_locations`, `manage_locations`

Key fields:
- `uuid`
- `name`
- `address`, `city`, `state`, `postcode`
- `active`

---

## Forms & Form Responses

**Forms:** `/form.json`
**Form Responses:** `/formresponse.json`

Key fields (response):
- `uuid`
- `form_uuid` — which form
- `job_uuid` — which job
- `field_data` — JSON of question/answer pairs
- `staff_uuid` — who completed it
- `active`

---

## Vendor (Account Info)

**Endpoint:** `/vendor.json`
**Scope:** `vendor`

Returns info about the ServiceM8 account itself (business name, address, etc).

---

## Webhook Subscriptions

**Endpoint:** `https://api.servicem8.com/webhook_subscriptions`
**Requires:** OAuth 2.0 (not available with API key auth)

Used to subscribe to real-time change notifications on any object type.

---

## Messaging API

**SMS:** `POST https://api.servicem8.com/api_1.0/sms.json`
**Email:** `POST https://api.servicem8.com/api_1.0/email.json`
**Requires:** OAuth 2.0 with `publish_sms` / `publish_email` scopes

---

## Document Templates

**Endpoint:** `/documenttemplate.json`
**Scope:** `manage_templates`

Used to list, create, and manage document templates for quotes, invoices, work orders, etc.

---

## Custom Fields

**Endpoint:** `https://api.servicem8.com/api_1.0/customfielddefinition.json`
**Requires:** OAuth 2.0

Custom fields are prefixed with `customfield_` on the parent record.

---

## Filtering Syntax

Use `$filter` query parameter with OData-style expressions:

```
GET /job.json?$filter=status eq 'Quote'
GET /job.json?$filter=status eq 'Quote' and active eq '1'
GET /job.json?$filter=edit_date gt '2026-01-01'
GET /company.json?$filter=active eq '1'
```

Note: The API expects dates in YYYY-MM-DD format internally. The sm8_api.py client
automatically converts DD-MM-YYYY dates in filter values to the correct format.

Operators: `eq`, `ne`, `gt`, `ge`, `lt`, `le`
Logical: `and`, `or`

String values must be wrapped in single quotes.

---

## Pagination

Responses may include `%next_page_start%` for paginated results.
Pass this value as a query parameter to get the next page:

```
GET /job.json?%next_page_start%=value_from_previous_response
```

---

## Rate Limits

- 60 requests per minute (per app, per account)
- 20,000 requests per day (per app, per account)
- HTTP 429 with message "Number of allowed API requests per minute exceeded"
- Throttling is per-application per-account
