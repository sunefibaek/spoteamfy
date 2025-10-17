#!/usr/bin/env python3
"""
Simple authentication validation script for Spotify users.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "spoteamfy", "src"))

from spotify_auth import SpotifyAuthError, authenticate_user  # noqa: E402


def validate_user_auth(username):
    """Validate authentication for a specific user and fetch their profile info.

    Args:
        username: The username to validate authentication for.

    Returns:
        True if authentication is successful, False otherwise.
    """

    # Load users.json
    script_dir = Path(__file__).resolve().parent.parent
    config_path = script_dir / "config" / "users.json"

    try:
        with open(config_path, "r") as f:
            users = json.load(f)
    except Exception as e:
        print(f"Failed to load users from {config_path}: {e}")
        return False

    # Find the user
    user_creds = None
    for user in users:
        if user.get("username") == username:
            user_creds = user
            break

    if not user_creds:
        print(f"User '{username}' not found in users.json")
        print(f"Available users: {[u.get('username') for u in users]}")
        return False

    print(f"Testing authentication for user: {username}")
    print(f"Client ID: {user_creds['client_id']}")
    print(f"Redirect URI: {user_creds['redirect_uri']}")

    # Check if refresh token is still a placeholder
    if user_creds["refresh_token"].startswith("SPOTIFY_REFRESH_TOKEN"):
        print(f"❌ Refresh token is still a placeholder: {user_creds['refresh_token']}")
        print(
            "Please run 'python scripts/get_access_token.py' "
            "to get a real refresh token first."
        )
        return False

    try:
        # Authenticate using spotipy
        spotify_client = authenticate_user(user_creds)
        print("✅ Authentication successful!")

        # Test by getting user profile
        user_profile = spotify_client.current_user()
        print("✅ Profile retrieved successfully!")
        print(f"   Display Name: {user_profile.get('display_name', 'N/A')}")
        print(f"   Spotify ID: {user_profile.get('id', 'N/A')}")
        print(f"   Followers: {user_profile.get('followers', {}).get('total', 'N/A')}")
        print(f"   Country: {user_profile.get('country', 'N/A')}")

        # Test fetching recently played tracks
        print("\n🎵 Testing recently played tracks retrieval...")
        recent_tracks = spotify_client.current_user_recently_played(limit=3)

        if recent_tracks["items"]:
            print("✅ Recently played tracks retrieved successfully!")
            print(f"   Found {len(recent_tracks['items'])} tracks:")
            for i, item in enumerate(recent_tracks["items"][:3], 1):
                track = item["track"]
                artists = ", ".join([artist["name"] for artist in track["artists"]])
                print(f"   {i}. {track['name']} by {artists}")
        else:
            print(
                "⚠️  No recently played tracks found "
                "(this is normal if you haven't listened to music recently)"
            )

        return True

    except SpotifyAuthError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate Spotify authentication for a user"
    )
    parser.add_argument(
        "username",
        help="Username to test (must match a user in users.json)",
    )

    args = parser.parse_args()

    success = validate_user_auth(args.username)
    if success:
        print(
            "\n🎉 All tests passed! Your Spotify authentication is working correctly."
        )
    else:
        print("\n💥 Tests failed. Please check the errors above.")
