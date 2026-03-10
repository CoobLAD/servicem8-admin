#!/usr/bin/env python3
"""
ServiceM8 Admin Skill — Setup Wizard
=====================================
Interactive setup that walks through API key configuration,
tests the connection, and saves a config file.

Run:
    python3 setup.py
"""

import json
import os
import sys
import urllib.request
import urllib.error

# Config lives next to the script, or in ~/.servicem8/
CONFIG_DIR = os.path.expanduser("~/.servicem8")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ENV_FILE = os.path.join(CONFIG_DIR, ".env")

BANNER = r"""
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
"""

STEP_DIVIDER = "──────────────────────────────────────────────────────"


def print_banner():
    print(BANNER)


def print_step(num, title):
    print(f"\n{STEP_DIVIDER}")
    print(f"  Step {num}: {title}")
    print(STEP_DIVIDER)


def test_api_key(api_key):
    """
    Test the API key by fetching account (vendor) info.
    Returns (success: bool, data: dict or error message)
    """
    url = "https://api.servicem8.com/api_1.0/vendor.json"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            # vendor endpoint returns a list with one item
            if isinstance(data, list) and len(data) > 0:
                return True, data[0]
            return True, data

    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Invalid API key — authentication failed."
        elif e.code == 403:
            return False, "Access denied — check your API key permissions."
        else:
            return False, f"HTTP error {e.code}: {e.read().decode('utf-8', errors='replace')}"
    except urllib.error.URLError as e:
        return False, f"Connection failed: {str(e.reason)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def test_scopes(api_key):
    """Test which API scopes/endpoints are accessible with this key."""
    endpoints = [
        ("Jobs",        "job"),
        ("Clients",     "company"),
        ("Staff",       "staff"),
        ("Queues",      "jobqueue"),
        ("Materials",   "material"),
        ("Categories",  "jobcategory"),
        ("Tasks",       "task"),
        ("Assets",      "asset"),
        ("Locations",   "location"),
    ]

    results = []
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for label, resource in endpoints:
        url = f"https://api.servicem8.com/api_1.0/{resource}.json"
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                count = len(data) if isinstance(data, list) else 1
                results.append((label, True, count))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                results.append((label, False, 0))
            else:
                results.append((label, False, 0))
        except Exception:
            results.append((label, False, 0))

    return results


def save_config(api_key, business_name=None):
    """Save config to ~/.servicem8/config.json and .env"""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Save JSON config
    config = {
        "api_key": api_key,
        "base_url": "https://api.servicem8.com/api_1.0",
        "date_format": "DD-MM-YYYY",
        "business_name": business_name or "",
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)  # Owner read/write only

    # Save .env file for shell usage
    with open(ENV_FILE, "w") as f:
        f.write(f'export SERVICEM8_API_KEY="{api_key}"\n')
    os.chmod(ENV_FILE, 0o600)

    return CONFIG_FILE, ENV_FILE


def prompt_input(message, default=None, secret=False):
    """Prompt user for input with optional default."""
    if default:
        display = f"{message} [{default}]: "
    else:
        display = f"{message}: "

    if secret:
        try:
            import getpass
            value = getpass.getpass(display)
        except (ImportError, EOFError):
            value = input(display)
    else:
        value = input(display)

    return value.strip() or default


def run_setup():
    """Run the interactive setup wizard."""
    print_banner()

    # ── Step 1: API Key ──
    print_step(1, "API Key")
    print()
    print("  You'll need a ServiceM8 API key from your account.")
    print("  To generate one:")
    print("    1. Log in to ServiceM8 online dashboard")
    print("    2. Go to Settings → API & Webhooks")
    print("    3. Click 'Generate API Key'")
    print("    4. Copy the key and paste it below")
    print()

    # Check for existing config
    existing_key = None
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                existing = json.load(f)
                existing_key = existing.get("api_key")
        except Exception:
            pass

    if existing_key:
        masked = existing_key[:8] + "..." + existing_key[-4:]
        print(f"  Existing key found: {masked}")
        use_existing = prompt_input("  Use existing key? (y/n)", default="y")
        if use_existing.lower() in ("y", "yes"):
            api_key = existing_key
        else:
            api_key = prompt_input("  Enter your API key", secret=True)
    else:
        api_key = prompt_input("  Enter your API key", secret=True)

    if not api_key:
        print("\n  ✗ No API key provided. Setup cancelled.")
        sys.exit(1)

    # ── Step 2: Test Connection ──
    print_step(2, "Testing Connection")
    print()
    print("  Connecting to ServiceM8...")

    success, result = test_api_key(api_key)

    if not success:
        print(f"\n  ✗ Connection failed: {result}")
        print("  Please check your API key and try again.")
        retry = prompt_input("\n  Try a different key? (y/n)", default="y")
        if retry.lower() in ("y", "yes"):
            api_key = prompt_input("  Enter your API key", secret=True)
            success, result = test_api_key(api_key)
            if not success:
                print(f"\n  ✗ Still failing: {result}")
                sys.exit(1)
        else:
            sys.exit(1)

    business_name = ""
    if isinstance(result, dict):
        business_name = result.get("name", "")
        address = result.get("address", "")
        city = result.get("city", "")
        state = result.get("state", "")
        email = result.get("email", "")

        print(f"\n  ✓ Connected successfully!")
        print(f"\n  Account Details:")
        print(f"    Business:  {business_name}")
        if address:
            print(f"    Address:   {address}, {city} {state}")
        if email:
            print(f"    Email:     {email}")

    # ── Step 3: Check Available Endpoints ──
    print_step(3, "Checking API Access")
    print()
    print("  Testing which endpoints your key can access...")
    print()

    scope_results = test_scopes(api_key)

    accessible = 0
    for label, ok, count in scope_results:
        if ok:
            print(f"    ✓ {label:<14} ({count} records)")
            accessible += 1
        else:
            print(f"    ✗ {label:<14} (no access)")

    print(f"\n  {accessible}/{len(scope_results)} endpoints accessible")

    if accessible == 0:
        print("\n  ⚠ No endpoints accessible. Your API key may have restricted permissions.")
        print("  The skill will still be saved, but you may need to generate a new key")
        print("  with broader permissions.")

    # ── Step 4: Save Config ──
    print_step(4, "Saving Configuration")
    print()

    config_path, env_path = save_config(api_key, business_name)

    print(f"  ✓ Config saved to:  {config_path}")
    print(f"  ✓ Env file saved to: {env_path}")
    print()
    print("  To load the API key in your shell, run:")
    print(f"    source {env_path}")
    print()
    print("  Or add it to your shell profile (~/.bashrc or ~/.zshrc):")
    print(f'    echo \'source {env_path}\' >> ~/.bashrc')

    # ── Done ──
    print(f"\n{STEP_DIVIDER}")
    print("  ✓ Setup complete!")
    print(STEP_DIVIDER)
    print()
    print("  Quick test commands:")
    print(f"    python3 scripts/sm8_api.py list job")
    print(f"    python3 scripts/sm8_api.py queues")
    print(f"    python3 scripts/sm8_api.py search-client --query \"smith\"")
    print()
    if business_name:
        print(f"  Ready to manage {business_name}. 🔧")
    else:
        print("  Ready to go. 🔧")
    print()


if __name__ == "__main__":
    run_setup()
