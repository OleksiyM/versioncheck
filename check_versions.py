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

# Logging setup
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "versioncheck.log"

def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def cprint(msg: str, end: str = "\n"):
    """Prints to console and logs to file with timestamp."""
    print(msg, end=end)
    clean_msg = strip_ansi(msg)
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        if clean_msg.strip():
            for line in clean_msg.splitlines():
                f.write(f"{timestamp} {line}\n")
        else:
            f.write(f"{clean_msg}{end}")

def run_and_log_subprocess(cmd: str):
    """Runs a shell command, prints output in real-time, and logs it."""
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in process.stdout:
        print(line, end="")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('[%Y-%m-%d %H:%M:%S]')} [CMD] {strip_ansi(line)}")
    
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)

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
                return data.get("project", {}).get("version", "0.1.5")
    except Exception:
        pass
    return "0.1.5"

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
            cprint(f"❌ {app.name:<12} : Local version parse error")
            return None
            
    except FileNotFoundError:
        cprint(f"❌ {app.name:<12} : Command not found ({app.command[0]})")
        return None
    except subprocess.TimeoutExpired:
        cprint(f"❌ {app.name:<12} : Local check timeout")
        return None
    except Exception as e:
        cprint(f"❌ {app.name:<12} : Local check failed")
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
            cprint(f"❌ {app.name:<12} : GitHub repo not found")
            return None
            
        response.raise_for_status()
        data = response.json()
        tag = data.get("tag_name", "")
        
        # Parse the tag using regex to ensure we just compare numeric version parts
        match = re.search(app.version_regex, tag)
        if match:
            return match.group(1)
        else:
            cprint(f"❌ {app.name:<12} : GitHub version parse error")
            return None
            
    except requests.exceptions.Timeout:
        cprint(f"❌ {app.name:<12} : GitHub API timeout")
        return None
    except requests.exceptions.RequestException as e:
        cprint(f"❌ {app.name:<12} : GitHub API request failed")
        return None

def main():
    script_version = get_script_version()
    parser = argparse.ArgumentParser(
        description="A compact and elegant script to compare local CLI tool versions against the latest GitHub releases."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {script_version}")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve all updates without prompting")
    args = parser.parse_args()

    cprint(f"\n{Colors.BOLD}🔍 Checking software versions...{Colors.RESET}\n{Colors.GRAY}{'-'*45}{Colors.RESET}")
    
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
            cprint(f"✔️  {app.name:<12} : {Colors.GRAY}{local_version} (Up to date){Colors.RESET}")
        else:
            if app.ignore_update:
                # Show the update exists, but mark as ignored and skip further actions
                cprint(f"✔️  {app.name:<12} : {Colors.GRAY}{local_version} -> {github_version} (Ignored){Colors.RESET}")
                continue
                
            # Green text for new available version
            cprint(f"🚀 {app.name:<12} : {local_version} -> {Colors.GREEN}{github_version} (Update!){Colors.RESET}")
            updates.append({
                "app": app,
                "local": local_version,
                "github": github_version
            })

    cprint(f"{Colors.GRAY}{'-' * 45}{Colors.RESET}\n")

    # Prompt to update apps that have auto_update enabled
    for info in updates:
        app = info["app"]
        if app.auto_update and app.update_cmd:
            if args.yes:
                ans = 'y'
            else:
                # Default Yes on Enter
                ans = input(f"Update {app.name}? [Y/n]: ").strip().lower()
                # Log the user's input so it is recorded
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('[%Y-%m-%d %H:%M:%S]')} Update {app.name}? [Y/n]: {ans}\n")
                
            if ans in ('', 'y', 'yes'):
                cprint(f"⚙️  Updating {app.name}...")
                try:
                    start_time = time.time()
                    run_and_log_subprocess(app.update_cmd)
                    duration = int(time.time() - start_time)
                    cprint(f"✅ {Colors.GREEN}Successfully updated {app.name} in {duration} sec!{Colors.RESET}\n")
                except subprocess.CalledProcessError:
                    cprint(f"❌ {Colors.RED}Failed to update {app.name}.{Colors.RESET}\n")
            else:
                cprint(f"⏩ Update for {app.name} skipped.\n")

    # Display custom messages for applications that require manual intervention
    for info in updates:
        app = info["app"]
        if app.show_message:
            msg = f"Эва, у {app.name} обновление: {info['local']} -> {info['github']}. Проверь пожалуйста"
            cprint(f"{Colors.YELLOW}💡 Message for Eva (copy this):{Colors.RESET}")
            cprint(f"{Colors.BLUE}{msg}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
