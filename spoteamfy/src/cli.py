# src/cli.py
import json
import os
from typing import Dict, List

import click
import requests
import spotipy
from dotenv import load_dotenv

from .spotify_auth import SpotifyAuthError, authenticate_user


def load_users_from_json(json_path: str) -> List[Dict]:
    """
    Loads user credentials from a JSON file.

    Args:
        json_path (str): Path to the JSON file containing user credentials.

    Returns:
        List[Dict]: List of user credential dictionaries.

    Raises:
        ValueError: If any user entry is missing required keys.
    """
    with open(json_path, "r") as f:
        users = json.load(f)
    required_keys = {
        "username",
        "client_id",
        "client_secret",
        "redirect_uri",
        "refresh_token",
    }
    for user in users:
        if not required_keys.issubset(user):
            raise ValueError(f"User entry missing required keys: {user}")
    return users


def get_users_json_path(cli_path: str = None) -> str:
    """
    Determines the path to the users.json file.

    Priority: CLI argument > .env USERS_JSON_PATH > default ./config/users.json

    Args:
        cli_path (str, optional): Path provided via CLI argument. Defaults to None.

    Returns:
        str: Path to the users.json file.
    """
    load_dotenv()
    if cli_path:
        return cli_path
    env_path = os.getenv("USERS_JSON_PATH")
    if env_path:
        return env_path
    return "./config/users.json"


def get_webhook_url(cli_webhook: str = None) -> str:
    """
    Determines the webhook URL to use.

    Priority: CLI argument > .env WEBHOOK_URL > raise error

    Args:
        cli_webhook (str, optional): Webhook URL provided via CLI argument.
        Defaults to None.

    Returns:
        str: Webhook URL.

    Raises:
        ValueError: If no webhook URL is provided.
    """
    load_dotenv()
    if cli_webhook:
        return cli_webhook
    env_webhook = os.getenv("WEBHOOK_URL")
    if env_webhook:
        return env_webhook
    raise ValueError(
        "No webhook URL provided. Use --teams-webhook or set WEBHOOK_URL in .env"
    )


def fetch_recently_played(
    spotify_client: spotipy.Spotify, num_tracks: int = 5
) -> List[Dict]:
    """
    Fetches recently played tracks for a user using spotipy.

    Args:
        spotify_client (spotipy.Spotify): Authenticated spotipy client.
        num_tracks (int, optional): Number of tracks to fetch (max 50). Defaults to 5.

    Returns:
        List[Dict]: List of track dictionaries with relevant information.

    Raises:
        Exception: If fetching recently played tracks fails.
    """
    try:
        # Use spotipy's current_user_recently_played method
        results = spotify_client.current_user_recently_played(
            limit=min(num_tracks, 20)  # Spotify API limit is 50
        )

        tracks = []
        # Remove duplicates while preserving order (same song played multiple times)
        seen_tracks = set()

        for item in results["items"]:
            track = item["track"]
            track_id = track["id"]

            # Skip if we've already seen this track (to avoid duplicates)
            if track_id not in seen_tracks:
                seen_tracks.add(track_id)

                track_info = {
                    "name": track["name"],
                    "artist": ", ".join(
                        [artist["name"] for artist in track["artists"]]
                    ),
                    "album": track["album"]["name"],
                    "popularity": track["popularity"],
                    "external_urls": track["external_urls"]["spotify"],
                    "preview_url": track["preview_url"],
                    "played_at": item["played_at"],  # When it was played
                    "album_cover_url": (
                        track["album"]["images"][0]["url"]
                        if track["album"].get("images")
                        else None
                    ),
                }
                tracks.append(track_info)

                # Stop when we have enough unique tracks
                if len(tracks) >= num_tracks:
                    break

        return tracks

    except Exception as e:
        raise Exception(f"Failed to fetch recently played tracks: {e}")


def format_adaptive_card_for_teams(username: str, tracks: List[Dict]) -> Dict:
    """
    Formats track information as an Adaptive Card for Teams,
    including album cover art of the most recent track.

    Args:
        username (str): Spotify username.
        tracks (List[Dict]): List of track dictionaries.

    Returns:
        Dict: Adaptive Card payload for Teams webhook.
    """
    card_body = []
    if tracks and tracks[0].get("album_cover_url"):
        card_body.append(
            {
                "type": "Image",
                "url": tracks[0]["album_cover_url"],
                "size": "Medium",
                "style": "Default",
            }
        )
    card_body.append(
        {
            "type": "TextBlock",
            "text": f"🎵 Recently Played Tracks for {username} 🎵",
            "weight": "Bolder",
            "size": "Medium",
        }
    )
    if not tracks:
        card_body.append(
            {
                "type": "TextBlock",
                "text": f"No recently played tracks found for {username}",
                "wrap": True,
            }
        )
    else:
        for i, track in enumerate(tracks, 1):
            text = (
                f"{i}. **{track['name']}** by {track['artist']}  #"
                f"\nAlbum: {track['album']}"
            )
            card_body.append({"type": "TextBlock", "text": text, "wrap": True})
            if track.get("external_urls"):
                card_body.append(
                    {
                        "type": "TextBlock",
                        "text": f"[Listen on Spotify]({track['external_urls']})",
                        "wrap": True,
                        "spacing": "None",
                    }
                )
    card_payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": card_body,
                },
            }
        ],
    }
    return card_payload


def post_to_teams(webhook_url: str, message: Dict) -> bool:
    """
    Posts a message to Microsoft Teams using a webhook.

    Args:
        webhook_url (str): Teams webhook URL.
        message (Dict): Message payload dictionary.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        response = requests.post(
            webhook_url, json=message, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        click.echo(f"Failed to post to Teams: {e}", err=True)
        return False


@click.command()
@click.option(
    "--num-tracks",
    default=5,
    help="Number of recently played tracks to fetch per user (max 50).",
)
@click.option(
    "--users-json",
    required=False,
    type=click.Path(exists=True),
    help=(
        "Path to JSON file with user credentials. "
        "Defaults to .env USERS_JSON_PATH or ./config/users.json."
    ),
)
@click.option(
    "--teams-webhook",
    required=False,
    help="Teams webhook URL for posting track info. Defaults to .env WEBHOOK_URL.",
)
@click.option(
    "--username",
    required=False,
    help="Only process the user with this username from the users JSON file.",
)
def main(num_tracks, users_json, teams_webhook, username):
    """
    CLI entry point for Spotify Teams utility.

    Args:
        num_tracks (int): Number of recently played tracks to fetch per user.
        users_json (str): Path to JSON file with user credentials.
        teams_webhook (str): Teams webhook URL for posting track info.
        username (str): Only process the user with this username.
    """
    users_json_path = get_users_json_path(users_json)

    try:
        webhook_url = get_webhook_url(teams_webhook)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return

    click.echo(
        f"Fetching {num_tracks} recently played tracks per user from "
        f"{users_json_path} and posting to Teams."
    )

    try:
        users = load_users_from_json(users_json_path)
        click.echo(f"Loaded user credentials for {len(users)} users.")
    except Exception as e:
        click.echo(f"Error loading users: {e}", err=True)
        return

    # Filter users by username if specified
    if username:
        filtered_users = [u for u in users if u.get("username") == username]
        if not filtered_users:
            click.echo(f"No user found with username '{username}'.", err=True)
            return
        users = filtered_users
        click.echo(f"Processing only user: {username}")

    successful_posts = 0
    failed_posts = 0

    for user in users:
        username_val = user.get("username", "<unknown>")
        click.echo(f"\nProcessing user: {username_val}")

        try:
            # Authenticate user using spotipy
            spotify_client = authenticate_user(user)
            click.echo(f"✓ Authentication successful for {username_val}")

            # Fetch recently played tracks
            tracks = fetch_recently_played(spotify_client, num_tracks)
            click.echo(
                f"✓ Fetched {len(tracks)} recently played tracks for {username_val}"
            )

            # Format Adaptive Card message for Teams
            message = format_adaptive_card_for_teams(username_val, tracks)

            # Post to Teams
            if post_to_teams(webhook_url, message):
                click.echo(f"✓ Posted tracks for {username_val} to Teams")
                successful_posts += 1
            else:
                click.echo(f"✗ Failed to post tracks for {username_val} to Teams")
                failed_posts += 1

        except SpotifyAuthError as e:
            click.echo(f"✗ Authentication failed for {username_val}: {e}", err=True)
            failed_posts += 1
        except Exception as e:
            click.echo(f"✗ Error processing {username_val}: {e}", err=True)
            failed_posts += 1

    # Summary
    click.echo("\n=== Summary ===")
    click.echo(f"Successful posts: {successful_posts}")
    click.echo(f"Failed posts: {failed_posts}")
    click.echo(f"Total users processed: {len(users)}")


if __name__ == "__main__":
    main()
