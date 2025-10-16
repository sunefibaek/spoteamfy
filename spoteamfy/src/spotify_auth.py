from typing import Any, Dict

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError


class SpotifyAuthError(Exception):
    """Custom exception for Spotify authentication errors."""

    pass


def authenticate_user(user_credentials: Dict[str, Any]) -> spotipy.Spotify:
    """
    Authenticate a Spotify user using Spotipy and return a Spotipy client instance.

    Args:
        user_credentials (Dict[str, Any]): Dictionary containing user credentials.
            Must include 'client_id', 'client_secret', 'redirect_uri',
            and 'refresh_token'.

    Returns:
        spotipy.Spotify: Authenticated Spotipy client instance.

    Raises:
        SpotifyAuthError: If authentication fails due to missing credentials,
            invalid refresh token, or any other error during the authentication process.
    """
    try:
        # Updated scope to include user-top-read for getting top tracks
        scope = """
            user-read-recently-played
            user-top-read
            playlist-modify-public
            playlist-modify-private
        """

        sp_oauth = SpotifyOAuth(
            client_id=user_credentials["client_id"],
            client_secret=user_credentials["client_secret"],
            redirect_uri=user_credentials["redirect_uri"],
            scope=scope,
            cache_path=None,
        )

        # Use refresh_token if available
        if "refresh_token" in user_credentials and user_credentials["refresh_token"]:
            # Check if refresh_token is not a placeholder
            if user_credentials["refresh_token"].startswith("SPOTIFY_REFRESH_TOKEN"):
                raise SpotifyAuthError(
                    "Refresh token is a placeholder. "
                    "Use get_access_token.py script to get a real refresh token."
                )

            token_info = sp_oauth.refresh_access_token(
                user_credentials["refresh_token"]
            )
            access_token = token_info["access_token"]
            return spotipy.Spotify(auth=access_token)
        else:
            raise SpotifyAuthError(
                "Missing or empty refresh_token in user credentials."
            )

    except SpotifyOauthError as e:
        raise SpotifyAuthError(
            "Authentication failed for user "
            f"{user_credentials.get('username', '')}: {e}"
        )
    except KeyError as e:
        raise SpotifyAuthError(
            "Missing required credential field for user "
            f"{user_credentials.get('username', '')}: {e}"
        )
    except Exception as e:
        raise SpotifyAuthError(
            "Unexpected authentication error for user "
            f"{user_credentials.get('username', '')}: {e}"
        )
