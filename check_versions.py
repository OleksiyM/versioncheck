# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
# ]
# ///

import subprocess
import requests
import re
import argparse
import tomllib
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Maximum execution time for shell commands and network requests (GitHub API)
TIMEOUT_SECONDS = 10

class Colors:
    GRAY = "\033[90m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def get_script_version() -> str:
    """Reads the script version dynamically from pyproject.toml."""
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
    except Exception:
        pass
    return "unknown"

@dataclass
class AppConfig:
    """Configuration for an application to check."""
    name: str
    command: list[str]
    github_repo: str
    # Regex to extract the version number (e.g., matching "0.14.5" from "v0.14.5")
    version_regex: str = r"(\d+\.\d+(?:\.\d+[a-zA-Z0-9\-]*)?)"
    
    # Update logic settings
    ignore_update: bool = False     # If True, ignore updates for this app
    auto_update: bool = False       # If True, prompt to run the update command
    update_cmd: str = ""            # Command to run for updating the app
    show_message: bool = False      # If True, show the prepared message for Eva

# List of applications to monitor. You can easily expand this list.
APPS = [
    AppConfig(
        name="VersionCheck",
        command=["uv", "run", "check_versions.py", "--version"],
        github_repo="OleksiyM/versioncheck",
        auto_update=True,
        update_cmd="git pull origin main"
    ),
    AppConfig(
        name="Qwen",
        command=["qwen", "--version"],
        github_repo="QwenLM/qwen-code",
        ignore_update=True
    ),
    AppConfig(
        name="OpenClaw",
        command=["openclaw", "--version"],
        github_repo="openclaw/openclaw",
        show_message=True
    ),
    AppConfig(
        name="Gemini CLI",
        command=["gemini", "--version"],
        github_repo="google-gemini/gemini-cli"
    ),
    AppConfig(
        name="Codex",
        command=["codex", "--version"],
        github_repo="openai/codex",
        auto_update=True,
        update_cmd="npm install -g @openai/codex"
    ),
    AppConfig(
        name="Claude Code",
        command=["claude", "--version"],
        github_repo="anthropics/claude-code",
        auto_update=True,
        update_cmd="claude update"
    ),
]

def get_local_version(app: AppConfig) -> Optional[str]:
    """Retrieves the local version of the application using its CLI command."""
    try:
        result = subprocess.run(
            app.command, 
            capture_output=True, 
            text=True, 
            timeout=TIMEOUT_SECONDS
        )
        
        # Check both stdout and stderr (some apps print version to stderr)
        output = result.stdout.strip() or result.stderr.strip()
        
        # Attempt to parse version using regex
        match = re.search(app.version_regex, output)
        if match:
            return match.group(1)
        else:
            print(f"❌ {app.name:<12} : Local version parse error")
            return None
            
    except FileNotFoundError:
        print(f"❌ {app.name:<12} : Command not found ({app.command[0]})")
        return None
    except subprocess.TimeoutExpired:
        print(f"❌ {app.name:<12} : Local check timeout")
        return None
    except Exception as e:
        print(f"❌ {app.name:<12} : Local check failed")
        return None

def get_github_version(app: AppConfig) -> Optional[str]:
    """Retrieves the latest version of the application from GitHub Releases API."""
    url = f"https://api.github.com/repos/{app.github_repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "VersionChecker-Script/1.0"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        
        if response.status_code == 404:
            print(f"❌ {app.name:<12} : GitHub repo not found")
            return None
            
        response.raise_for_status()
        data = response.json()
        tag = data.get("tag_name", "")
        
        # Parse the tag using regex to ensure we just compare numeric version parts
        match = re.search(app.version_regex, tag)
        if match:
            return match.group(1)
        else:
            print(f"❌ {app.name:<12} : GitHub version parse error")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ {app.name:<12} : GitHub API timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ {app.name:<12} : GitHub API request failed")
        return None

def main():
    script_version = get_script_version()
    parser = argparse.ArgumentParser(
        description="A compact and elegant script to compare local CLI tool versions against the latest GitHub releases."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {script_version}")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve all updates without prompting")
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}🔍 Checking software versions...{Colors.RESET}\n{Colors.GRAY}{'-'*45}{Colors.RESET}")
    
    # Store apps that have updates as a list of dicts
    updates = []
    
    for app in APPS:
        local_version = get_local_version(app)
        # If we can't find the local version, skip checking GitHub to save API requests
        if not local_version:
            continue
            
        github_version = get_github_version(app)
        if not github_version:
            continue
            
        if local_version == github_version:
            # Gray text for up-to-date
            print(f"✔️  {app.name:<12} : {Colors.GRAY}{local_version} (Up to date){Colors.RESET}")
        else:
            if app.ignore_update:
                # Show the update exists, but mark as ignored and skip further actions
                print(f"✔️  {app.name:<12} : {Colors.GRAY}{local_version} -> {github_version} (Ignored){Colors.RESET}")
                continue
                
            # Green text for new available version
            print(f"🚀 {app.name:<12} : {local_version} -> {Colors.GREEN}{github_version} (Update!){Colors.RESET}")
            updates.append({
                "app": app,
                "local": local_version,
                "github": github_version
            })

    print(f"{Colors.GRAY}{'-' * 45}{Colors.RESET}\n")

    # Prompt to update apps that have auto_update enabled
    for info in updates:
        app = info["app"]
        if app.auto_update and app.update_cmd:
            if args.yes:
                ans = 'y'
            else:
                # Default Yes on Enter
                ans = input(f"Update {app.name}? [Y/n]: ").strip().lower()
                
            if ans in ('', 'y', 'yes'):
                print(f"⚙️  Updating {app.name}...")
                try:
                    start_time = time.time()
                    subprocess.run(app.update_cmd, shell=True, check=True)
                    duration = int(time.time() - start_time)
                    print(f"✅ {Colors.GREEN}Successfully updated {app.name} in {duration} sec!{Colors.RESET}\n")
                except subprocess.CalledProcessError:
                    print(f"❌ {Colors.RED}Failed to update {app.name}.{Colors.RESET}\n")
            else:
                print(f"⏩ Update for {app.name} skipped.\n")

    # Display custom messages for applications that require manual intervention
    for info in updates:
        app = info["app"]
        if app.show_message:
            msg = f"""Эва, у {app.name} обновление: {info['local']} -> {info['github']}.

Проверь что нового, есть ли блокеры все как обычно, если всё спокойно обнови {app.name}, если что-то тебя насторожило - не обновляй и расскажи что"""
            
            print(f"{Colors.YELLOW}💡 Message for Eva (copy this):{Colors.RESET}")
            print(f"{Colors.BLUE}╭{'─'*60}╮{Colors.RESET}")
            for line in msg.split('\n'):
                print(f"{Colors.BLUE}│{Colors.RESET} {line:<58} {Colors.BLUE}│{Colors.RESET}")
            print(f"{Colors.BLUE}╰{'─'*60}╯{Colors.RESET}\n")

if __name__ == "__main__":
    main()
