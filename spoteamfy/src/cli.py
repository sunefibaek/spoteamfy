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
    """Load user credentials from a JSON file.

    Each user must have: username, client_id, client_secret,
    redirect_uri, refresh_token.

    Args:
        json_path: Path to the JSON file containing user credentials.

    Returns:
        A list of dictionaries containing user credential information.

    Raises:
        ValueError: If a user entry is missing required keys.
        FileNotFoundError: If the JSON file cannot be found.
        json.JSONDecodeError: If the JSON file is malformed.
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
    """Determine the path to the users.json file.

    Priority: CLI argument > .env USERS_JSON_PATH > default ./config/users.json

    Args:
        cli_path: Optional path provided via CLI argument.

    Returns:
        The resolved path to the users.json file.
    """
    load_dotenv()
    if cli_path:
        return cli_path
    env_path = os.getenv("USERS_JSON_PATH")
    if env_path:
        return env_path
    return "./config/users.json"


def get_webhook_url(cli_webhook: str = None) -> str:
    """Determine the webhook URL to use.

    Priority: CLI argument > .env WEBHOOK_URL > raise error

    Args:
        cli_webhook: Optional webhook URL provided via CLI argument.

    Returns:
        The resolved webhook URL.

    Raises:
        ValueError: If no webhook URL is provided via CLI or environment variable.
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
    """Fetch recently played tracks for a user using spotipy.

    Args:
        spotify_client: Authenticated spotipy client.
        num_tracks: Number of tracks to fetch (max 50). Defaults to 5.

    Returns:
        A list of track dictionaries with relevant information including
        name, artist, album, popularity, external_urls, preview_url,
        and played_at timestamp.

    Raises:
        Exception: If the Spotify API request fails or returns invalid data.
    """
    try:
        # Use spotipy's current_user_recently_played method
        results = spotify_client.current_user_recently_played(
            limit=min(num_tracks, 50)  # Spotify API limit is 50
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
                }
                tracks.append(track_info)

                # Stop when we have enough unique tracks
                if len(tracks) >= num_tracks:
                    break

        return tracks

    except Exception as e:
        raise Exception(f"Failed to fetch recently played tracks: {e}")


def format_tracks_for_teams(username: str, tracks: List[Dict]) -> Dict:
    """Format track information for Teams webhook.

    Args:
        username: Spotify username to include in the message.
        tracks: List of track dictionaries to format.

    Returns:
        A Teams message payload dictionary with formatted track information.
        If no tracks are provided, returns a message indicating no tracks found.
    """
    if not tracks:
        return {"text": f"No recently played tracks found for {username}"}

    # Create a formatted message for Teams
    message_text = f"🎵 **Recently Played {len(tracks)} Tracks for {username}** 🎵\n\n"

    for i, track in enumerate(tracks, 1):
        message_text += f"{i}. **{track['name']}** by {track['artist']}\n"
        message_text += f"   Album: {track['album']}\n"
        if track["external_urls"]:
            message_text += f"   [Listen on Spotify]({track['external_urls']})\n"
        message_text += "\n"

    return {"text": message_text}


def post_to_teams(webhook_url: str, message: Dict) -> bool:
    """Post message to Microsoft Teams using webhook.

    Args:
        webhook_url: Teams webhook URL to post to.
        message: Message payload dictionary to send.

    Returns:
        True if the message was posted successfully, False otherwise.
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
def main(num_tracks, users_json, teams_webhook):
    """CLI entry point for Spotify Teams utility.

    Fetches recently played tracks from Spotify for configured users
    and posts formatted messages to Microsoft Teams via webhook.

    Args:
        num_tracks: Number of recently played tracks to fetch per user.
        users_json: Path to JSON file containing user credentials.
        teams_webhook: Teams webhook URL for posting messages.
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

    successful_posts = 0
    failed_posts = 0

    for user in users:
        username = user.get("username", "<unknown>")
        click.echo(f"\nProcessing user: {username}")

        try:
            # Authenticate user using spotipy
            spotify_client = authenticate_user(user)
            click.echo(f"✓ Authentication successful for {username}")

            # Fetch recently played tracks
            tracks = fetch_recently_played(spotify_client, num_tracks)
            click.echo(f"✓ Fetched {len(tracks)} recently played tracks for {username}")

            # Format message for Teams
            message = format_tracks_for_teams(username, tracks)

            # Post to Teams
            if post_to_teams(webhook_url, message):
                click.echo(f"✓ Posted tracks for {username} to Teams")
                successful_posts += 1
            else:
                click.echo(f"✗ Failed to post tracks for {username} to Teams")
                failed_posts += 1

        except SpotifyAuthError as e:
            click.echo(f"✗ Authentication failed for {username}: {e}", err=True)
            failed_posts += 1
        except Exception as e:
            click.echo(f"✗ Error processing {username}: {e}", err=True)
            failed_posts += 1

    # Summary
    click.echo("\n=== Summary ===")
    click.echo(f"Successful posts: {successful_posts}")
    click.echo(f"Failed posts: {failed_posts}")
    click.echo(f"Total users processed: {len(users)}")


if __name__ == "__main__":
    main()
