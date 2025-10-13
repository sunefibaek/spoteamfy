#!/usr/bin/env python3
"""
Simple test script to validate Spotify authentication for a specific user.
"""

import json
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "spoteamfy", "src"))

from spotify_auth import SpotifyAuthError, authenticate_user  # noqa: E402


def test_user_auth(username="Sune"):
    """Test authentication for a specific user and fetch their profile info."""

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

        # Test fetching top tracks
        print("\n🎵 Testing top tracks retrieval...")
        top_tracks = spotify_client.current_user_top_tracks(
            limit=3, time_range="short_term"
        )

        if top_tracks["items"]:
            print("✅ Top tracks retrieved successfully!")
            print(f"   Found {len(top_tracks['items'])} tracks:")
            for i, track in enumerate(top_tracks["items"][:3], 1):
                artists = ", ".join([artist["name"] for artist in track["artists"]])
                print(f"   {i}. {track['name']} by {artists}")
        else:
            print(
                "⚠️  No top tracks found "
                "(this is normal if you haven't listened to much music recently)"
            )

        return True

    except SpotifyAuthError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_user_auth("Sune")
    if success:
        print("\n🎉 All tests passed! Your Spotify authentication is working correctly.")
    else:
        print("\n💥 Tests failed. Please check the errors above.")
