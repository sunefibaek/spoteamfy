# Spoteamfy

A Python CLI tool that fetches recently played Spotify tracks and posts them as rich adaptive cards to Microsoft Teams channels.

## Features

- Fetches recently played tracks from Spotify
- Displays album cover art from the most recent track
- Creates interactive adaptive cards for Teams
- Supports multiple Spotify users
- Clickable Spotify links for each track

## Quick Start

1. **Configure credentials** in `config/users.json`
2. **Set webhook URL** in `.env` file: `WEBHOOK_URL=https://your-teams-webhook`
3. **Run the CLI**:
   ```bash
   python -m spoteamfy.src.cli --num-tracks 5
   ```

See the [CLI guide](cli.md) for detailed usage instructions.
