#!/usr/bin/env python3
"""
Script to fetch Spotify access tokens using spotipy.
This script handles both getting initial refresh tokens and refreshing access tokens.
"""

import json
import os
import sys
from typing import Dict, Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "spoteamfy", "src"))


def get_initial_auth_for_user(
    username: str, client_id: str, client_secret: str, redirect_uri: str
) -> Optional[Dict]:
    """Get initial authorization for a user using Authorization Code Flow.

    This will open a browser and require user interaction.

    Args:
        username: The username for display purposes.
        client_id: Spotify app client ID.
        client_secret: Spotify app client secret.
        redirect_uri: Redirect URI configured in Spotify app.

    Returns:
        Token info dictionary containing access_token, refresh_token, expires_at,
        and scope if successful, None otherwise.
    """
    # Updated scope to include all required permissions
    scope = """
        user-top-read
        playlist-modify-public
        playlist-modify-private
        user-read-recently-played
    """

    # Create SpotifyOAuth object
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        show_dialog=True,  # Force show dialog even if user previously authorized
        cache_path=None,  # Don't use file-based cache
    )

    print(f"Getting authorization for user: {username}")

    # Get authorization URL
    auth_url = sp_oauth.get_authorize_url()
    print("Please go to this URL to authorize the application:")
    print(f"{auth_url}")

    # Get the redirect URL from user input
    redirect_response = input("\nPaste the full redirect URL here: ").strip()

    try:
        # Extract code from redirect URL
        code = sp_oauth.parse_response_code(redirect_response)
        if code:
            token_info = sp_oauth.get_access_token(code, as_dict=False)

            # Convert to dict format for compatibility
            if isinstance(token_info, str):
                # If it returns just the token string, we need to get the full
                # token info.
                # Use get_cached_token to get the full token info
                full_token_info = sp_oauth.get_cached_token()
                if full_token_info:
                    token_info = full_token_info
                else:
                    print("Failed to get full token info")
                    return None

            if token_info and isinstance(token_info, dict):
                print("\n=== SUCCESS ===")
                print(f"Access Token: {token_info['access_token'][:20]}...")
                print(f"Refresh Token: {token_info['refresh_token']}")
                print(f"Expires at: {token_info['expires_at']}")
                print(f"Scope: {token_info['scope']}")

                return token_info
            else:
                print("Failed to get token info")
                return None
        else:
            print("Failed to extract authorization code from URL")
            return None
    except Exception as e:
        print(f"Error during authorization: {e}")
        return None


def refresh_access_token(
    client_id: str, client_secret: str, refresh_token: str
) -> Optional[Dict]:
    """Refresh an access token using a refresh token.

    Args:
        client_id: Spotify app client ID.
        client_secret: Spotify app client secret.
        refresh_token: Valid refresh token to use for getting new access token.

    Returns:
        Refreshed token info dictionary if successful, None otherwise.
    """
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8080/callback",  # Dummy URI for refresh
        cache_path=None,
    )

    try:
        # Create a token info dict with the refresh token
        # token_info = {
        #     "refresh_token": refresh_token,
        #     "access_token": "dummy",  # Will be refreshed
        #     "expires_at": 0,  # Expired, will trigger refresh
        # }

        # Refresh the token
        refreshed_token_info = sp_oauth.refresh_access_token(refresh_token)

        if refreshed_token_info:
            print("Access token refreshed successfully!")
            print(f"New Access Token: {refreshed_token_info['access_token'][:20]}...")
            print(f"Expires at: {refreshed_token_info['expires_at']}")

            return refreshed_token_info
        else:
            print("Failed to refresh access token")
            return None

    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None


def test_access_token(access_token: str) -> bool:
    """Test if an access token works by making a simple API call.

    Args:
        access_token: Access token to test.

    Returns:
        True if the token is valid and works, False otherwise.
    """
    try:
        sp = spotipy.Spotify(auth=access_token)
        user_info = sp.current_user()
        print(
            f"Token test successful! User: {user_info['display_name']}"
            f"(ID: {user_info['id']})"
        )
        return True
    except Exception as e:
        print(f"Token test failed: {e}")
        return False


def get_client_credentials_token(client_id: str, client_secret: str) -> Optional[str]:
    """Get an access token using Client Credentials Flow (app-only, no user context).

    This is useful for app-only requests but won't work for user-specific data.

    Args:
        client_id: Spotify app client ID.
        client_secret: Spotify app client secret.

    Returns:
        Access token string if successful, None otherwise.
    """
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id, client_secret=client_secret
        )

        # sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

        # Test the connection
        # results = sp.search(q="test", type="track", limit=1)

        print("Client Credentials token obtained successfully!")
        print(
            "Note: This token can only be used for app-only requests, "
            "not user-specific data."
        )

        return client_credentials_manager.get_access_token()

    except Exception as e:
        print(f"Error getting Client Credentials token: {e}")
        return None


def main() -> None:
    """Main function to handle token operations.

    Provides an interactive menu for managing Spotify API tokens including
    getting initial authorization, refreshing tokens, testing tokens, and
    obtaining client credentials tokens.
    """

    # Load users.json
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "users.json")

    try:
        with open(config_path, "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {config_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing users.json: {e}")
        return

    print("=== Spotify Token Manager ===")
    print("1. Get initial authorization (new refresh token)")
    print("2. Refresh existing access token")
    print("3. Test access token")
    print("4. Get Client Credentials token (app-only)")

    choice = input("\nSelect an option (1-4): ").strip()

    if choice in ["1", "2", "3"]:
        # List available users
        print("\nAvailable users:")
        for i, user in enumerate(users):
            print(f"{i + 1}. {user['username']}")

        try:
            selection = input("\nEnter the number of the user: ")
            user_index = int(selection) - 1
            if user_index < 0 or user_index >= len(users):
                print("Invalid selection")
                return
        except ValueError:
            print("Invalid input")
            return

        selected_user = users[user_index]
        username = selected_user["username"]
        client_id = selected_user["client_id"]
        client_secret = selected_user["client_secret"]
        redirect_uri = selected_user["redirect_uri"]
        refresh_token = selected_user.get("refresh_token", "")

        # Validate credentials
        if client_id.startswith("SPOTIFY_CLIENT_ID") or client_secret.startswith(
            "SPOTIFY_CLIENT_SECRET"
        ):
            print(
                "Error: Please update users.json with real "
                "Spotify client credentials first"
            )
            return

    if choice == "1":
        # Get initial authorization
        token_info = get_initial_auth_for_user(
            username, client_id, client_secret, redirect_uri
        )
        if token_info:
            print("\nUpdate users.json with this refresh token:")
            print(f"Replace '{refresh_token}' with '{token_info['refresh_token']}'")

    elif choice == "2":
        # Refresh existing token
        if not refresh_token or refresh_token.startswith("SPOTIFY_REFRESH_TOKEN"):
            print(
                "Error: No valid refresh token found. "
                "Use option 1 to get initial authorization first."
            )
            return

        token_info = refresh_access_token(client_id, client_secret, refresh_token)
        if token_info:
            print("You can now use this access token for API calls.")

    elif choice == "3":
        # Test access token
        access_token = input("Enter the access token to test: ").strip()
        test_access_token(access_token)

    elif choice == "4":
        # Get Client Credentials token
        if len(users) > 0:
            user = users[0]  # Use first user's credentials
            client_id = user["client_id"]
            client_secret = user["client_secret"]

            if client_id.startswith("SPOTIFY_CLIENT_ID") or client_secret.startswith(
                "SPOTIFY_CLIENT_SECRET"
            ):
                print(
                    "Error: Please update users.json with real "
                    "Spotify client credentials first"
                )
                return

            token_info = get_client_credentials_token(client_id, client_secret)
            if token_info:
                print(f"Access Token: {token_info['access_token'][:20]}...")
        else:
            print("No users found in config")

    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
