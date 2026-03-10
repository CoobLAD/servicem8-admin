# ServiceM8 Skill

```
   _____                 _           __  ______
  / ___/___  ______   __(_)_______  /  |/  ( __ )
  \__ \/ _ \/ ___/ | / / / ___/ _ \/ /|_/ / __  |
 ___/ /  __/ /   | |/ / / /__/  __/ /  / / /_/ /
/____/\___/_/    |___/_/\___/\___/_/  /_/\____/
   _____ __   _ ____
  / ___// /__(_) / /
  \__ \/ //_/ / / /
 ___/ / ,< / / / /
/____/_/|_/_/_/_/

                                        By Coob.
```

A Claude AI skill for managing a [ServiceM8](https://www.servicem8.com/) field service business via the REST API. Built for trades — electricians, plumbers, builders, and anyone running jobs through ServiceM8.

## Features

- **Job Management** — Create, update, search, and filter jobs by status, queue, client, or date
- **Client Management** — Search clients, create new ones, view job history
- **Queue Management** — List queues, view job counts, move jobs between queues, track expiry dates
- **Scheduling & Dispatch** — Create bookings, view the schedule, check staff availability, log time
- **Quoting & Invoicing** — Add line items, track outstanding invoices, record payments
- **Materials** — Manage your product catalogue and add items to jobs
- **Staff** — List staff, check workloads, view activity
- **Job Notes** — Add notes to the job diary, view history
- **Reporting** — Outstanding invoices, queue summaries, staff utilisation
- **Australian Date Format** — All dates display as DD-MM-YYYY, automatically converted to/from the API

## Installation

### Clone the repo

```bash
git clone https://github.com/CoobLAD/servicem8-admin.git
cd servicem8-admin
```

### Run the setup wizard

```bash
python3 scripts/setup.py
```

The wizard will prompt for your API key, test the connection, show your business details, and save the config to `~/.servicem8/`.

---

### Platform-Specific Setup

<details>
<summary><strong>Claude Code (Terminal)</strong></summary>

Install as a skill directly:

```bash
git clone https://github.com/CoobLAD/servicem8-admin.git
cd servicem8-admin
python3 scripts/setup.py
```

Then point Claude Code at the skill directory, or copy the `SKILL.md`, `scripts/`, and `references/` folders into your project's skill path.

</details>

<details>
<summary><strong>Claude Desktop (MCP)</strong></summary>

ServiceM8 has an official MCP server. Add it to your Claude Desktop config at `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "servicem8": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.servicem8.com"],
      "env": {
        "SERVICEM8_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Alternatively, use this repo's Python client as a local tool by pointing your agent at `scripts/sm8_api.py`.

</details>

<details>
<summary><strong>Python Projects / Custom Agents</strong></summary>

Use the API client as a standalone library — zero dependencies, just Python 3.6+:

```bash
git clone https://github.com/CoobLAD/servicem8-admin.git
```

```python
import sys
sys.path.insert(0, "servicem8-admin/scripts")
from sm8_api import ServiceM8Client

sm8 = ServiceM8Client(api_key="your_key_here")

# List all jobs
jobs = sm8.list("job")

# Search clients
clients = sm8.search_companies("smith")

# Get queue summary
queues = sm8.get_queue_summary()
```

Or set the env variable and skip passing the key:

```bash
export SERVICEM8_API_KEY="your_key_here"
```

</details>

<details>
<summary><strong>LangChain / CrewAI / AutoGen / Other Frameworks</strong></summary>

Import the client and wrap it as a tool for your framework:

```python
from sm8_api import ServiceM8Client

sm8 = ServiceM8Client()

# Example: LangChain tool
from langchain.tools import tool

@tool
def list_jobs(status: str = None) -> str:
    """List ServiceM8 jobs, optionally filtered by status."""
    filters = {"status": status} if status else None
    jobs = sm8.list("job", filters=filters)
    return str(jobs)

@tool
def search_clients(query: str) -> str:
    """Search ServiceM8 clients by name, email, or phone."""
    return str(sm8.search_companies(query))

@tool
def get_queue_summary() -> str:
    """Get all job queues with job counts."""
    return str(sm8.get_queue_summary())
```

The client handles auth, pagination, rate limiting, and date conversion — just wrap and go.

</details>

<details>
<summary><strong>CLI Only (No AI Agent)</strong></summary>

Use the built-in command-line interface directly:

```bash
git clone https://github.com/CoobLAD/servicem8-admin.git
cd servicem8-admin
python3 scripts/setup.py          # One-time config

python3 scripts/sm8_api.py list job
python3 scripts/sm8_api.py queues
python3 scripts/sm8_api.py search-client --query "smith"
python3 scripts/sm8_api.py outstanding
```

</details>

---

### Using It

Once configured, just talk to your AI agent naturally:

- *"List all jobs in the Pending Quotes queue"*
- *"Create a new job for John Smith at 42 Main St, quote for switchboard upgrade"*
- *"What invoices are outstanding?"*
- *"Schedule that job for Monday morning with Dave"*
- *"Move job #1234 to the Parts on Order queue"*

## Getting Your API Key

1. Log in to your [ServiceM8 online dashboard](https://go.servicem8.com/)
2. Go to **Settings → API & Webhooks**
3. Click **Generate API Key**
4. Copy the key and use it in the setup wizard

## Project Structure

```
servicem8-admin/
├── SKILL.md                    # Main skill instructions for Claude
├── scripts/
│   ├── setup.py                # Interactive setup wizard
│   └── sm8_api.py              # API client library & CLI tool
└── references/
    └── endpoints.md            # Full API endpoint reference
```

## CLI Reference

Full list of commands:

```bash
python3 scripts/sm8_api.py setup                          # Run setup wizard
python3 scripts/sm8_api.py list job                        # List all jobs
python3 scripts/sm8_api.py list job --filter status=Quote  # Filter by status
python3 scripts/sm8_api.py list company                    # List all clients
python3 scripts/sm8_api.py get job --uuid "uuid-here"      # Get a specific job
python3 scripts/sm8_api.py create job --data '{"status": "Quote", "job_address": "123 Main St"}'
python3 scripts/sm8_api.py update job --uuid "uuid" --data '{"status": "Work Order"}'
python3 scripts/sm8_api.py delete job --uuid "uuid"        # Archive a job
python3 scripts/sm8_api.py queues                          # Queue summary + job counts
python3 scripts/sm8_api.py outstanding                     # Unpaid invoices
python3 scripts/sm8_api.py search-client --query "smith"   # Search clients
```

## Date Format

All dates use **DD-MM-YYYY** format (Australian standard). The client automatically converts to/from the API's internal YYYY-MM-DD format — you never need to think about it.

```python
# These just work
sm8.create("jobactivity", {"start_date": "15-03-2026 08:00:00"})
jobs = sm8.list("job", filters={"edit_date": {"gt": "01-01-2026"}})
```

## API Rate Limits

- 60 requests per minute (per app, per account)
- 20,000 requests per day
- The client automatically backs off and retries on rate limit errors

## Requirements

- Python 3.6+
- No external dependencies (uses only stdlib)
- A ServiceM8 account with an API key

## License

MIT

## Author

**Coob**
