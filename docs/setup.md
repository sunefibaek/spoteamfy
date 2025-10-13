# Spoteamfy Setup Guide

Quick setup to get Spotify tokens and configure users for the Teams utility.

## 1. Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Create a new app
3. Copy your **Client ID** and **Client Secret**
4. Add redirect URI: `http://127.0.0.1:8080/callback`

## 2. Configure users.json

Edit `config/users.json`:

```json
[
  {
    "username": "your-name",
    "client_id": "your-spotify-client-id",
    "client_secret": "your-spotify-client-secret",
    "redirect_uri": "http://127.0.0.1:8080/callback",
    "refresh_token": "PLACEHOLDER_WILL_BE_REPLACED"
  }
]
```

## 3. Get Refresh Token

Run the token script:
```bash
python scripts/get_access_token.py
```

1. Select option **1** (Get initial authorization)
2. Choose your user
3. Open the Spotify URL in your browser
4. Authorize the app
5. Copy the full redirect URL and paste it back
6. Update your `refresh_token` in users.json with the returned value

## 4. Set Environment Variables (Optional)

Create a `.env` file for easier testing:
```bash
WEBHOOK_URL=https://your-teams-webhook-url
USERS_JSON_PATH=/path/to/your/users.json  # Optional, defaults to ./config/users.json
```

## 5. Test Setup

Validate authentication:
```bash
python scripts/auth_validator.py username
```

## 6. Run the CLI

With webhook in .env:
```bash
python spoteamfy/src/cli.py --num-tracks 5
```

Or specify webhook directly:
```bash
python spoteamfy/src/cli.py --teams-webhook "YOUR_WEBHOOK_URL" --num-tracks 5
```

That's it! The utility will fetch recently played tracks and post them to Teams.
