# CLI

The Spoteamfy CLI fetches recently played tracks from Spotify for configured users and posts formatted adaptive cards to Microsoft Teams via webhook.

## Usage

```bash
python -m spoteamfy.src.cli [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--num-tracks` | INTEGER | 5 | Number of recently played tracks to fetch per user (max 50) |
| `--users-json` | PATH | `./config/users.json` | Path to JSON file with user credentials. Must exist. |
| `--teams-webhook` | TEXT | Environment variable | Teams webhook URL for posting track info |

## Configuration Priority

### Users JSON File
1. `--users-json` CLI argument
2. `USERS_JSON_PATH` environment variable
3. `./config/users.json` (default)

### Teams Webhook URL
1. `--teams-webhook` CLI argument
2. `WEBHOOK_URL` environment variable
3. Error if neither provided

## Examples

### Basic usage (uses defaults)
```bash
python -m spoteamfy.src.cli
```

### Fetch 10 tracks with custom webhook
```bash
python -m spoteamfy.src.cli --num-tracks 10 --teams-webhook "https://your-webhook-url"
```

### Custom users file
```bash
python -m spoteamfy.src.cli --users-json "/path/to/users.json" --num-tracks 3
```

## Environment Setup

Create a `.env` file in the project root:
```bash
USERS_JSON_PATH=./config/users.json
WEBHOOK_URL=https://your-teams-webhook-url
```

## Output

The CLI creates adaptive cards with:
- Album cover art from the most recent track
- Track list with clickable Spotify links
- User-friendly formatting for Teams channels

## Exit Codes

- `0` - Success (even if some posts fail)
- Errors are reported but don't cause exit code changes
