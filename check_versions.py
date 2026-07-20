# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
# ]
# ///

import sys
import subprocess
import requests
import re
import argparse
import tomllib
import time
import json
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
                return data.get("project", {}).get("version", "0.2.0")
    except Exception:
        pass
    return "0.2.0"

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
    version_url: str = ""           # Custom URL to fetch version from (instead of GitHub releases)
    short_name: str = ""            # Short name for compact/Telegram layout

# List of applications to monitor. You can easily expand this list.
APPS = [
    AppConfig(
        name="VersionCheck",
        command=["uv", "run", str(Path(__file__).resolve()), "--version"],
        github_repo="OleksiyM/versioncheck",
        auto_update=True,
        update_cmd="git pull origin main"
    ),
    AppConfig(
        name="Antigravity CLI",
        short_name="agy CLI",
        command=["agy", "--version"],
        github_repo="google-antigravity/antigravity-cli",
        version_url="https://antigravity-cli-auto-updater-974169037036.us-central1.run.app",
        auto_update=True,
        update_cmd="agy update"
    ),
    AppConfig(
        name="Antigravity IDE",
        short_name="agy IDE",
        command=["agy-ide", "--version"],
        github_repo="google-antigravity/antigravity-ide",
        version_url="https://antigravity-ide-auto-updater-974169037036.us-central1.run.app",
        ignore_update=True
    ),
    AppConfig(
        name="Antigravity 2",
        short_name="agy 2",
        command=[],  # No direct version command, custom parser reads app.asar
        github_repo="",
        version_url="https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/manifest/latest-x64-linux.yml",
        version_regex=r"version:\s*(\d+\.\d+(?:\.\d+[a-zA-Z0-9\-]*)?)",
        ignore_update=True
    ),
    AppConfig(
        name="OpenCode",
        command=["opencode", "--version"],
        github_repo="anomalyco/opencode",
        auto_update=True,
        update_cmd="opencode upgrade"
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
    AppConfig(
        name="Grok",
        command=["grok", "--version"],
        github_repo="xai-org/grok-build",
        version_url="https://x.ai/cli/stable",
        auto_update=True,
        update_cmd="curl -fsSL https://x.ai/cli/install.sh | bash"
    ),
]

def get_local_version(app: AppConfig) -> Optional[str]:
    """Retrieves the local version of the application using its CLI command."""
    if app.name == "Antigravity IDE":
        # Custom logic to read internal version from package.json or product.json
        # Prefer product.json ideVersion because that's what the update server reports (e.g. 2.1.1)
        paths = [
            "/usr/share/antigravity-ide/resources/app/product.json",
            "/usr/share/antigravity-ide/resources/app/package.json",
            "/Applications/Antigravity IDE.app/Contents/Resources/app/product.json",
            "/Applications/Antigravity IDE.app/Contents/Resources/app/package.json",
            str(Path.home() / "Applications/AntigravityIDE/resources/app/product.json"),
            str(Path.home() / "Applications/AntigravityIDE/resources/app/package.json"),
            str(Path.home() / "Applications/Antigravity IDE.app/Contents/Resources/app/product.json"),
            str(Path.home() / "Applications/Antigravity IDE.app/Contents/Resources/app/package.json"),
        ]
        for p in paths:
            path = Path(p)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Prefer ideVersion first (from product.json) so it yields 2.1.1, else fallback to version
                        val = data.get("ideVersion") or data.get("version")
                        if val:
                            return val
                except Exception:
                    pass

    if app.name == "Antigravity 2":
        # Custom logic to extract version from app.asar binary
        paths = [
            "/usr/share/antigravity/resources/app.asar",
            "/Applications/Antigravity.app/Contents/Resources/app.asar",
            str(Path.home() / "Applications/Antigravity/resources/app.asar"),
            str(Path.home() / "Applications/Antigravity.app/Contents/Resources/app.asar"),
        ]
        for p in paths:
            path = Path(p)
            if path.exists():
                try:
                    # The main package.json is usually stored in the file data payload (farther in the file),
                    # not the header, because package.json is packaged as a file.
                    # Reading the whole file is safe as it's around 170MB, but to be fast and memory efficient,
                    # we can search for the byte sequence of the package.json content.
                    with open(path, "rb") as f:
                        data = f.read()
                    
                    # Look for the exact byte block of package.json:
                    # "name": "antigravity" and "version": "..."
                    # Find instances of b'"version"'
                    idx = 0
                    while True:
                        idx = data.find(b'"version"', idx)
                        if idx == -1:
                            break
                        # Read 300 bytes around it and check if it's the main package.json
                        chunk = data[idx:idx+300].decode("utf-8", errors="ignore")
                        if "antigravity" in chunk and "description" in chunk:
                            # Extract version
                            match = re.search(r'"version"\s*:\s*"([^"]+)"', chunk)
                            if match:
                                return match.group(1)
                        idx += 9
                except Exception:
                    pass
        return None

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
            if "--compact" in sys.argv or "-c" in sys.argv:
                cprint(f"❌ {app.short_name or app.name} › parse error")
            else:
                cprint(f"❌ {app.name:<15} : Local version parse error")
            return None
            
    except FileNotFoundError:
        if "--compact" in sys.argv or "-c" in sys.argv:
            cprint(f"❌ {app.short_name or app.name} › not found")
        else:
            cprint(f"❌ {app.name:<15} : Command not found ({app.command[0]})")
        return None
    except subprocess.TimeoutExpired:
        if "--compact" in sys.argv or "-c" in sys.argv:
            cprint(f"❌ {app.short_name or app.name} › timeout")
        else:
            cprint(f"❌ {app.name:<15} : Local check timeout")
        return None
    except Exception as e:
        if "--compact" in sys.argv or "-c" in sys.argv:
            cprint(f"❌ {app.short_name or app.name} › failed")
        else:
            cprint(f"❌ {app.name:<15} : Local check failed")
        return None

def get_github_version(app: AppConfig) -> Optional[str]:
    """Retrieves the latest version of the application from GitHub Releases API or a custom URL."""
    url = app.version_url if app.version_url else f"https://api.github.com/repos/{app.github_repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "VersionChecker-Script/1.0"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        
        if response.status_code == 404:
            source_name = "Custom URL" if app.version_url else "GitHub repo"
            if "--compact" in sys.argv or "-c" in sys.argv:
                cprint(f"❌ {app.short_name or app.name} › not found")
            else:
                cprint(f"❌ {app.name:<15} : {source_name} not found")
            return None
            
        response.raise_for_status()
        
        if app.version_url:
            # Custom parsing for raw text response
            text = response.text
            match = re.search(app.version_regex, text)
            if match:
                return match.group(1)
            else:
                if "--compact" in sys.argv or "-c" in sys.argv:
                    cprint(f"❌ {app.short_name or app.name} › parse error")
                else:
                    cprint(f"❌ {app.name:<15} : Custom URL version parse error")
                return None
        else:
            data = response.json()
            tag = data.get("tag_name", "")
            
            # Parse the tag using regex to ensure we just compare numeric version parts
            match = re.search(app.version_regex, tag)
            if match:
                return match.group(1)
            else:
                if "--compact" in sys.argv or "-c" in sys.argv:
                    cprint(f"❌ {app.short_name or app.name} › parse error")
                else:
                    cprint(f"❌ {app.name:<15} : GitHub version parse error")
                return None
            
    except requests.exceptions.Timeout:
        if "--compact" in sys.argv or "-c" in sys.argv:
            cprint(f"❌ {app.short_name or app.name} › API timeout")
        else:
            cprint(f"❌ {app.name:<15} : API/URL request timeout")
        return None
    except requests.exceptions.RequestException as e:
        if "--compact" in sys.argv or "-c" in sys.argv:
            cprint(f"❌ {app.short_name or app.name} › API error")
        else:
            cprint(f"❌ {app.name:<15} : API/URL request failed")
        return None

def main():
    script_version = get_script_version()
    parser = argparse.ArgumentParser(
        description="A compact and elegant script to compare local CLI tool versions against the latest GitHub releases."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {script_version}", help="Show the version of this script and exit")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve all updates without prompting")
    parser.add_argument("-i", "--info", action="store_true", help="Show versions only, skip all updates and prompts")
    parser.add_argument("-c", "--compact", action="store_true", help="Compact output format (ideal for Telegram/EvaClaw)")
    args = parser.parse_args()

    # Configure styling based on compact mode
    # "✔️  VersionCheck    : 0.1.8 (Up to " -> 15 chars for name, 2 chars for emoji, 2 spaces, colon, spaces.
    # Total width target is around 32-35 chars
    name_w = 12 if args.compact else 15

    if not args.compact:
        cprint(f"\n{Colors.BOLD}🔍 Checking software versions...{Colors.RESET}\n{Colors.GRAY}{'-'*48}{Colors.RESET}")
    else:
        cprint(f"{Colors.BOLD}🔍 Checking versions...{Colors.RESET}")
    
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
            
        # Determine name to display based on compact flag
        app_name = app.short_name if (args.compact and app.short_name) else app.name

        if args.compact:
            # Compact rendering: No alignment spaces, single emoji space, streamlined output
            if local_version == github_version:
                cprint(f"✔️ {app_name} › {Colors.GRAY}{local_version}{Colors.RESET}")
            else:
                if app.ignore_update:
                    cprint(f"✔️ {app_name} › {Colors.GRAY}{local_version}->{github_version} (Ign){Colors.RESET}")
                else:
                    cprint(f"🆙 {app_name} › {local_version}->{Colors.GREEN}{github_version}{Colors.RESET}")
            updates.append({
                "app": app,
                "local": local_version,
                "github": github_version
            }) if not (local_version == github_version or app.ignore_update) else None
        else:
            # Normal desktop rendering
            sep = " :"
            if local_version == github_version:
                # Gray text for up-to-date
                cprint(f"✔️  {app_name:<15}{sep} {Colors.GRAY}{local_version} (Up to date){Colors.RESET}")
            else:
                if app.ignore_update:
                    # Show the update exists, but mark as ignored and skip further actions
                    cprint(f"✔️  {app_name:<15}{sep} {Colors.GRAY}{local_version} -> {github_version} (Ignored){Colors.RESET}")
                    continue
                    
                # Green text for new available version
                cprint(f"🚀  {app_name:<15}{sep} {local_version} -> {Colors.GREEN}{github_version}{Colors.RESET}")
                updates.append({
                    "app": app,
                    "local": local_version,
                    "github": github_version
                })

    if not args.compact:
        cprint(f"{Colors.GRAY}{'-' * 48}{Colors.RESET}\n")

    if args.info:
        return

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
