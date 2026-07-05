# VersionCheck 🚀

A lightweight, elegant python script to quickly monitor installed CLI tools and compare their local versions against the latest GitHub releases. Designed to be fast, beautiful, and completely portable.

![Preview of output](https://img.shields.io/badge/status-beautiful-brightgreen)

## Features

- **No Installation Required:** Leverages [`uv`](https://github.com/astral-sh/uv) to automatically manage dependencies in an ephemeral sandbox.
- **Remote Execution Ready:** Can be piped over SSH to check versions on any remote machine without transferring files.
- **Smart Parsing:** Uses regex to extract clean version numbers directly from standard terminal output commands and GitHub tags.
- **Custom Version Sources:** Supports querying versions from custom API endpoints (e.g. auto-updater APIs) when standard GitHub Releases are not available.
- **Self-Updating:** Automatically monitors its own GitHub repository and updates itself (`git pull origin main`) when a new release is available!
- **Persistent Logging:** Silently records all status checks, prompts, and background app installation outputs into an ANSI-stripped, timestamped `logs/versioncheck.log` file.
- **Compact & Visual:** Employs emojis and ANSI colors to highlight what actually requires your attention.
- **Compact Mode (Telegram/EvaClaw):** Provides a specialized, narrow, non-aligned format (`-c` or `--compact`) specifically designed to look beautiful in Telegram messaging and AI execution blocks.

## Example Output

### Desktop Mode
```text
🔍 Checking software versions...
------------------------------------------------
✔️  VersionCheck    : 0.1.9 (Up to date)
✔️  Antigravity CLI : 1.0.16 (Up to date)
✔️  Antigravity IDE : 2.1.1 (Up to date)
✔️  Antigravity 2   : 2.2.1 (Up to date)
🚀  OpenCode        : 1.15.12 -> 1.17.13
✔️  Qwen            : 0.14.5 -> 0.19.6 (Ignored)
```

### Compact Mode (`-c` / `--compact`)
```text
🔍 Checking versions...
✔️ VersionCheck › 0.1.9
✔️ agy CLI › 1.0.16
✔️ agy IDE › 2.1.1
✔️ agy 2 › 2.2.1
🆙 OpenCode › 1.15.12->1.17.13
✔️ Qwen › 0.14.5->0.19.6 (Ign)
```

## Installation

### Classic (via Git)
Clone the repository directly and run it:
```bash
git clone https://github.com/OleksiyM/versioncheck.git
cd versioncheck
uv run check_versions.py
```

### Direct Download
Download the latest stable release from the [GitHub Releases page](https://github.com/OleksiyM/versioncheck/releases). Extract the archive, and you are ready to go!

## Quickstart

### Prerequisites
Make sure you have [uv](https://docs.astral.sh/uv/) installed.

### Usage

Run the script normally:
```bash
uv run check_versions.py
```

**Command-line Arguments:**
- `-h`, `--help`: Show the help message and exit.
- `--version`: Display the current script version (dynamically read from `pyproject.toml`).
- `-y`, `--yes`: Auto-approve all pending updates without prompting `[Y/n]`. Example: `uv run check_versions.py -y`
- `-i`, `--info`: Show versions only, skip all updates and prompts. Example: `uv run check_versions.py -i`
- `-c`, `--compact`: Render layout in a compact format without spacing alignment (ideal for Telegram/EvaClaw). Example: `uv run check_versions.py -c -i`

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
        show_message=True,      # If True, prints a prepared message at the end for Eva
        version_url="https://api.example.com/version" # Custom URL to query version from instead of GitHub Releases
    ),
```

### Update Logic Flags
- **`ignore_update`**: Use this when you want to know an update exists but don't want to be prompted to install it. It simply marks the update as `(Ignored)`.
- **`auto_update` & `update_cmd`**: If `auto_update` is set to `True` and an `update_cmd` is provided, the script will prompt you `Update Your App? [Y/n]` after checking all versions. Pressing Enter will run the command directly in your shell.
- **`show_message`**: Specifically designed for AI assistants (like Eva). When an update is detected, it generates a convenient copy-paste block asking the assistant to check the changelog before proceeding with the update.
- **`version_url`**: Useful for applications that do not release on GitHub or use their own private/public update channels. The script will fetch this URL and parse the version via Regex.

The script will automatically grab the terminal output, scrape the version via Regex, pull the latest release from the GitHub API, compare them, and execute the configured logic.

## License

MIT License. Feel free to fork, expand, and use it everywhere!
