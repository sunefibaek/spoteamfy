# src/cli.py
import json
import os
from typing import Dict, List

import click
from dotenv import load_dotenv


def load_users_from_json(json_path: str) -> List[Dict]:
    """
    Load user credentials from a JSON file.
    Each user must have: username, client_id, client_secret,
    redirect_uri, refresh_token.
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
    Determine the path to the users.json file.
    Priority: CLI argument > .env USERS_JSON_PATH > default ./config/users.json
    """
    load_dotenv()
    if cli_path:
        return cli_path
    env_path = os.getenv("USERS_JSON_PATH")
    if env_path:
        return env_path
    return "./config/users.json"


@click.command()
@click.option(
    "--num-tracks", default=5, help="Number of recent tracks to fetch per user."
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
    "--teams-webhook", required=True, help="Teams webhook URL for posting track info."
)
def main(num_tracks, users_json, teams_webhook):
    """CLI entry point for Spotify Teams utility."""
    users_json_path = get_users_json_path(users_json)
    click.echo(
        f"Fetching {num_tracks} tracks per user from "
        f"{users_json_path} and posting to Teams."
    )
    users = load_users_from_json(users_json_path)
    click.echo(f"Loaded user credentials for {len(users)} users.")
    # Implementation will follow in next steps


if __name__ == "__main__":
    main()
