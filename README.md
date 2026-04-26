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
✔️ Qwen         : 0.14.5 (Up to date)
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

Adding new tools is simple. Just append a new `AppConfig` block inside the `APPS` list in `check_versions.py`. The `AppConfig` supports flexible update strategies via several flags:

```python
    AppConfig(
        name="Your App",
        command=["app-command", "--version"],
        github_repo="owner/repo",
        
        # Optional settings for update logic:
        ignore_update=False,    # If True, shows the update in gray (Ignored) and skips any actions
        auto_update=True,       # If True, prompts the user to automatically run the update command
        update_cmd="npm update -g app", # The command to execute if auto_update is True
        show_message=True       # If True, prints a prepared message at the end for Eva
    ),
```

### Update Logic Flags
- **`ignore_update`**: Use this when you want to know an update exists but don't want to be prompted to install it. It simply marks the update as `(Ignored)`.
- **`auto_update` & `update_cmd`**: If `auto_update` is set to `True` and an `update_cmd` is provided, the script will prompt you `Update Your App? [Y/n]` after checking all versions. Pressing Enter will run the command directly in your shell.
- **`show_message`**: Specifically designed for AI assistants (like Eva). When an update is detected, it generates a convenient copy-paste block asking the assistant to check the changelog before proceeding with the update.

The script will automatically grab the terminal output, scrape the version via Regex, pull the latest release from the GitHub API, compare them, and execute the configured logic.

## License

MIT License. Feel free to fork, expand, and use it everywhere!
