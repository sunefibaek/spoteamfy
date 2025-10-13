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

## 4. Test Setup

```bash
python scripts/test_auth.py
```
