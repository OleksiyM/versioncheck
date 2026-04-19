# VersionCheck 🚀

A lightweight, elegant python script to quickly monitor installed CLI tools and compare their local versions against the latest GitHub releases. Designed to be fast, beautiful, and completely portable.

![Preview of output](https://img.shields.io/badge/status-beautiful-brightgreen)

## Features

- **No Installation Required:** Leverages [`uv`](https://github.com/astral-sh/uv) to automatically manage dependencies in an ephemeral sandbox.
- **Remote Execution Ready:** Can be piped over SSH to check versions on any remote machine without transferring files.
- **Smart Parsing:** Uses regex to extract clean version numbers directly from standard terminal output commands and GitHub tags.
- **Compact & Visual:** Employs emojis and ANSI colors to highlight what actually requires your attention.

## Example Output

```text
🔍 Checking software versions...
---------------------------------------------
✔️  Qwen         : 0.14.5 (Up to date)
❌ OpenClaw     : Command not found (openclaw)
🚀 Gemini CLI   : 0.36.0 -> 0.38.2 (Update!)
🚀 Claude Code  : 2.1.104 -> 2.1.114 (Update!)
---------------------------------------------
```

## Quickstart

### Prerequisites
Make sure you have [uv](https://docs.astral.sh/uv/) installed.

### Local Execution
```bash
uv run check_versions.py
```

### Remote Execution (via SSH)
Execute the script entirely in RAM on your remote machine:
```bash
ssh user@remote_host "uv run -" < check_versions.py
```
*(If `uv` isn't installed remotely, you can also use `ssh user@remote_host "python3 -" < check_versions.py` as long as `requests` is installed globally).*

## Configuration

Adding new tools is simple. Just append a new `AppConfig` block inside the `APPS` list in `check_versions.py`:

```python
    AppConfig(
        name="Your App",
        command=["app-command", "--version"],
        github_repo="owner/repo"
    ),
```

The script will automatically grab the terminal output, scrape the version via Regex, pull the latest release from the GitHub API, and compare them.

## License

MIT License. Feel free to fork, expand, and use it everywhere!
