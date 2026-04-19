# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
# ]
# ///

import subprocess
import requests
import re
from dataclasses import dataclass
from typing import Optional

# Maximum execution time for commands and network requests
TIMEOUT_SECONDS = 10

@dataclass
class AppConfig:
    """Configuration for an application to check."""
    name: str
    command: list[str]
    github_repo: str
    # Regex to extract the version number (e.g., matching "0.14.5" from "v0.14.5")
    version_regex: str = r"(\d+\.\d+(?:\.\d+[a-zA-Z0-9\-]*)?)"

# List of applications to monitor. You can easily expand this list.
APPS = [
    AppConfig(
        name="Qwen",
        command=["qwen", "--version"],
        github_repo="QwenLM/qwen-code"
    ),
    AppConfig(
        name="OpenClaw",
        command=["openclaw", "--version"],
        github_repo="openclaw/openclaw"
    ),
    AppConfig(
        name="Gemini CLI",
        command=["gemini", "--version"],
        github_repo="google-gemini/gemini-cli"
    ),
    AppConfig(
        name="Codex",
        command=["codex", "--version"],
        github_repo="openai/codex"
    ),
    AppConfig(
        name="Claude Code",
        command=["claude", "--version"],
        github_repo="anthropics/claude-code"
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
    print("\n🔍 Checking software versions...\n" + "-"*45)
    
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
            print(f"✔️  {app.name:<12} : \033[90m{local_version} (Up to date)\033[0m")
        else:
            # Green text for new available version
            print(f"🚀 {app.name:<12} : {local_version} -> \033[92m{github_version} (Update!)\033[0m")

    print("-"*45 + "\n")

if __name__ == "__main__":
    main()
