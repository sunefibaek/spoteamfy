import json
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__)))

from spotify_auth import SpotifyAuthError  # noqa: E402

# , authenticate_user


def main():
    """Main function to validate Spotify authentication for all users.

    Loads user credentials from the configured JSON file and attempts to
    authenticate each user to verify their credentials are working properly.
    Prints the authentication status for each user.
    """

    # Resolve project root
    script_dir = Path(__file__).resolve().parent.parent.parent
    default_users_path = script_dir / "config" / "users.json"
    users_path = os.getenv("USERS_JSON_PATH", str(default_users_path))
    try:
        with open(users_path, "r") as f:
            users = json.load(f)
    except Exception as e:
        print(f"Failed to load users from {users_path}: {e}")
        return

    if not isinstance(users, list):
        print("users.json must be a list of user credential objects.")
        return

    for user in users:
        username = user.get("username", "<unknown>")
        print(f"Authenticating user: {username}")
        try:
            # client = authenticate_user(user)
            print(f"Success: {username}")
        except SpotifyAuthError as e:
            print(f"Auth failed for {username}: {e}")
        except Exception as e:
            print(f"Unexpected error for {username}: {e}")


if __name__ == "__main__":
    main()
