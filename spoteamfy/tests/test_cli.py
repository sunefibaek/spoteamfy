import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest
import requests
from click.testing import CliRunner

from spoteamfy.src.cli import (
    fetch_recently_played,
    format_tracks_for_teams,
    get_users_json_path,
    get_webhook_url,
    load_users_from_json,
    main,
    post_to_teams,
)
from spoteamfy.src.spotify_auth import SpotifyAuthError


def test_load_users_from_json_valid():
    users = [
        {
            "username": "user1",
            "client_id": "id1",
            "client_secret": "secret1",
            "redirect_uri": "uri1",
            "refresh_token": "token1",
        },
        {
            "username": "user2",
            "client_id": "id2",
            "client_secret": "secret2",
            "redirect_uri": "uri2",
            "refresh_token": "token2",
        },
    ]
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        json.dump(users, f)
        f.flush()
        path = f.name
    loaded = load_users_from_json(path)
    assert loaded == users
    os.remove(path)


def test_load_users_from_json_missing_key():
    users = [
        {
            "username": "user1",
            "client_id": "id1",
            "client_secret": "secret1",
            "redirect_uri": "uri1",
            # missing refresh_token
        }
    ]
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        json.dump(users, f)
        f.flush()
        path = f.name
    try:
        with pytest.raises(ValueError):
            load_users_from_json(path)
    finally:
        os.remove(path)


def test_get_users_json_path_cli_priority():
    """Test that CLI path takes priority over env and default."""
    path = get_users_json_path("/custom/path.json")
    assert path == "/custom/path.json"


def test_get_users_json_path_env_fallback(monkeypatch):
    """Test that env variable is used when no CLI path provided."""
    monkeypatch.setenv("USERS_JSON_PATH", "/env/path.json")
    path = get_users_json_path()
    assert path == "/env/path.json"


def test_get_users_json_path_default(monkeypatch):
    """Test that default path is used when no CLI path or env set."""
    monkeypatch.delenv("USERS_JSON_PATH", raising=False)
    path = get_users_json_path()
    assert path == "./config/users.json"


def test_fetch_recently_played():
    """Test fetching recently played tracks using spotipy."""
    # Mock spotipy client
    mock_client = Mock()
    mock_client.current_user_recently_played.return_value = {
        "items": [
            {
                "track": {
                    "id": "track1",
                    "name": "Test Song 1",
                    "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
                    "album": {
                        "name": "Test Album",
                        "images": [
                            {"height": 640, "url": "https://example.com/large.jpg"},
                            {"height": 300, "url": "https://example.com/medium.jpg"},
                            {"height": 64, "url": "https://example.com/small.jpg"},
                        ],
                    },
                    "popularity": 85,
                    "external_urls": {"spotify": "https://open.spotify.com/track/123"},
                    "preview_url": "https://preview.url",
                },
                "played_at": "2023-01-01T12:00:00Z",
            },
            {
                "track": {
                    "id": "track2",
                    "name": "Test Song 2",
                    "artists": [{"name": "Artist 3"}],
                    "album": {
                        "name": "Another Album",
                        "images": [
                            {"height": 640, "url": "https://example.com/large2.jpg"},
                            {"height": 300, "url": "https://example.com/medium2.jpg"},
                        ],
                    },
                    "popularity": 92,
                    "external_urls": {"spotify": "https://open.spotify.com/track/456"},
                    "preview_url": None,
                },
                "played_at": "2023-01-01T11:30:00Z",
            },
        ]
    }

    tracks = fetch_recently_played(mock_client, num_tracks=2)

    assert len(tracks) == 2
    assert tracks[0]["name"] == "Test Song 1"
    assert tracks[0]["artist"] == "Artist 1, Artist 2"
    assert tracks[0]["album"] == "Test Album"
    assert tracks[0]["popularity"] == 85
    assert tracks[0]["played_at"] == "2023-01-01T12:00:00Z"
    assert tracks[0]["album_cover_url"] == "https://example.com/medium.jpg"  # New field
    assert tracks[1]["name"] == "Test Song 2"
    assert tracks[1]["artist"] == "Artist 3"
    assert (
        tracks[1]["album_cover_url"] == "https://example.com/medium2.jpg"
    )  # New field

    # Verify spotipy method was called with correct parameters
    mock_client.current_user_recently_played.assert_called_once_with(limit=2)


def test_fetch_recently_played_limits_to_50():
    """Test that fetch_recently_played limits requests to 50 tracks max."""
    mock_client = Mock()
    mock_client.current_user_recently_played.return_value = {"items": []}

    fetch_recently_played(mock_client, num_tracks=100)

    mock_client.current_user_recently_played.assert_called_once_with(limit=50)


def test_fetch_recently_played_removes_duplicates():
    """Test that fetch_recently_played removes duplicate tracks."""
    mock_client = Mock()
    mock_client.current_user_recently_played.return_value = {
        "items": [
            {
                "track": {
                    "id": "track1",
                    "name": "Test Song",
                    "artists": [{"name": "Artist 1"}],
                    "album": {
                        "name": "Test Album",
                        "images": [
                            {"height": 300, "url": "https://example.com/medium.jpg"}
                        ],
                    },
                    "popularity": 85,
                    "external_urls": {"spotify": "https://open.spotify.com/track/123"},
                    "preview_url": None,
                },
                "played_at": "2023-01-01T12:00:00Z",
            },
            {
                "track": {
                    "id": "track1",  # Same track ID - should be filtered out
                    "name": "Test Song",
                    "artists": [{"name": "Artist 1"}],
                    "album": {
                        "name": "Test Album",
                        "images": [
                            {"height": 300, "url": "https://example.com/medium.jpg"}
                        ],
                    },
                    "popularity": 85,
                    "external_urls": {"spotify": "https://open.spotify.com/track/123"},
                    "preview_url": None,
                },
                "played_at": "2023-01-01T11:30:00Z",
            },
            {
                "track": {
                    "id": "track2",
                    "name": "Different Song",
                    "artists": [{"name": "Artist 2"}],
                    "album": {
                        "name": "Different Album",
                        "images": [
                            {"height": 300, "url": "https://example.com/different.jpg"}
                        ],
                    },
                    "popularity": 75,
                    "external_urls": {"spotify": "https://open.spotify.com/track/456"},
                    "preview_url": None,
                },
                "played_at": "2023-01-01T11:00:00Z",
            },
        ]
    }

    tracks = fetch_recently_played(mock_client, num_tracks=3)

    # Should only return 2 unique tracks, not 3
    assert len(tracks) == 2
    assert tracks[0]["name"] == "Test Song"
    assert tracks[1]["name"] == "Different Song"


def test_format_tracks_for_teams():
    """Test formatting tracks for Teams webhook as adaptive card."""
    tracks = [
        {
            "name": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "external_urls": "https://open.spotify.com/track/123",
            "album_cover_url": "https://example.com/cover.jpg",
        }
    ]

    message = format_tracks_for_teams("testuser", tracks)

    # Check that it's an adaptive card format
    assert message["type"] == "message"
    assert "attachments" in message
    assert len(message["attachments"]) == 1

    attachment = message["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"

    card_content = attachment["content"]
    assert card_content["type"] == "AdaptiveCard"
    assert card_content["version"] == "1.3"

    # Convert the card body to a string to check for content
    card_body_str = str(card_content["body"])
    assert "testuser" in card_body_str
    assert "Test Song" in card_body_str
    assert "Test Artist" in card_body_str
    assert "Test Album" in card_body_str


def test_format_tracks_for_teams_no_tracks():
    """Test formatting when no tracks are found returns adaptive card."""
    message = format_tracks_for_teams("testuser", [])

    # Check that it's an adaptive card format
    assert message["type"] == "message"
    assert "attachments" in message
    assert len(message["attachments"]) == 1

    attachment = message["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"

    card_content = attachment["content"]
    assert card_content["type"] == "AdaptiveCard"

    # Check the no tracks message
    body = card_content["body"]
    assert len(body) == 1
    assert body[0]["type"] == "TextBlock"
    assert "No recently played tracks found for testuser" in body[0]["text"]


@patch("spoteamfy.src.cli.requests.post")
def test_post_to_teams_success(mock_post):
    """Test successful posting to Teams."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    message = {"text": "Test message"}
    result = post_to_teams("https://webhook.url", message)

    assert result is True
    mock_post.assert_called_once_with(
        "https://webhook.url",
        json=message,
        headers={"Content-Type": "application/json"},
    )


@patch("spoteamfy.src.cli.requests.post")
def test_post_to_teams_failure(mock_post):
    """Test failed posting to Teams."""
    mock_post.side_effect = requests.RequestException("Network error")

    message = {"text": "Test message"}

    # The function should catch the exception and return False
    result = post_to_teams("https://webhook.url", message)

    assert result is False


def test_get_webhook_url_cli_priority():
    """Test that CLI webhook URL takes priority."""
    url = get_webhook_url("https://cli.webhook.url")
    assert url == "https://cli.webhook.url"


def test_get_webhook_url_env_fallback(monkeypatch):
    """Test that env variable is used when no CLI webhook provided."""
    monkeypatch.setenv("WEBHOOK_URL", "https://env.webhook.url")
    url = get_webhook_url()
    assert url == "https://env.webhook.url"


def test_get_webhook_url_no_url_provided(monkeypatch):
    """Test that ValueError is raised when no webhook URL is provided."""
    # Mock os.getenv to always return None, completely isolating from environment
    monkeypatch.setattr("os.getenv", lambda key, default=None: None)

    with pytest.raises(ValueError) as exc:
        get_webhook_url()
    assert "No webhook URL provided" in str(exc.value)


def test_fetch_recently_played_exception():
    """Test fetch_recently_played handles API exceptions."""
    mock_client = Mock()
    mock_client.current_user_recently_played.side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc:
        fetch_recently_played(mock_client, num_tracks=5)
    assert "Failed to fetch recently played tracks" in str(exc.value)


@patch("spoteamfy.src.cli.authenticate_user")
@patch("spoteamfy.src.cli.fetch_recently_played")
@patch("spoteamfy.src.cli.format_tracks_for_teams")
@patch("spoteamfy.src.cli.post_to_teams")
@patch("spoteamfy.src.cli.load_users_from_json")
@patch("spoteamfy.src.cli.get_webhook_url")
def test_main_success_flow(
    mock_get_webhook,
    mock_load_users,
    mock_post_teams,
    mock_format_tracks,
    mock_fetch_tracks,
    mock_auth,
):
    """Test successful main CLI flow."""
    # Setup mocks
    mock_get_webhook.return_value = "https://webhook.url"
    mock_load_users.return_value = [
        {
            "username": "testuser",
            "client_id": "id1",
            "client_secret": "secret1",
            "redirect_uri": "uri1",
            "refresh_token": "token1",
        }
    ]
    mock_spotify_client = Mock()
    mock_auth.return_value = mock_spotify_client
    mock_fetch_tracks.return_value = [{"name": "Test Song"}]
    mock_format_tracks.return_value = {"text": "Test message"}
    mock_post_teams.return_value = True

    runner = CliRunner()
    result = runner.invoke(main, ["--num-tracks", "3"])

    assert result.exit_code == 0
    assert "Successful posts: 1" in result.output
    assert "Failed posts: 0" in result.output
    mock_auth.assert_called_once()
    mock_fetch_tracks.assert_called_once_with(mock_spotify_client, 3)
    mock_post_teams.assert_called_once()


@patch("spoteamfy.src.cli.get_webhook_url")
def test_main_webhook_url_error(mock_get_webhook):
    """Test main CLI when webhook URL is missing."""
    mock_get_webhook.side_effect = ValueError("No webhook URL provided")

    runner = CliRunner()
    result = runner.invoke(main)

    assert result.exit_code == 0  # Click doesn't exit with error by default
    assert "Error: No webhook URL provided" in result.output


@patch("spoteamfy.src.cli.get_webhook_url")
@patch("spoteamfy.src.cli.load_users_from_json")
def test_main_users_loading_error(mock_load_users, mock_get_webhook):
    """Test main CLI when users loading fails."""
    mock_get_webhook.return_value = "https://webhook.url"
    mock_load_users.side_effect = Exception("Failed to load users")

    runner = CliRunner()
    result = runner.invoke(main)

    assert result.exit_code == 0
    assert "Error loading users: Failed to load users" in result.output


@patch("spoteamfy.src.cli.authenticate_user")
@patch("spoteamfy.src.cli.load_users_from_json")
@patch("spoteamfy.src.cli.get_webhook_url")
def test_main_auth_error(mock_get_webhook, mock_load_users, mock_auth):
    """Test main CLI when authentication fails."""
    mock_get_webhook.return_value = "https://webhook.url"
    mock_load_users.return_value = [
        {
            "username": "testuser",
            "client_id": "id1",
            "client_secret": "secret1",
            "redirect_uri": "uri1",
            "refresh_token": "token1",
        }
    ]
    mock_auth.side_effect = SpotifyAuthError("Auth failed")

    runner = CliRunner()
    result = runner.invoke(main)

    assert result.exit_code == 0
    assert "Authentication failed for testuser: Auth failed" in result.output
    assert "Failed posts: 1" in result.output


@patch("spoteamfy.src.cli.authenticate_user")
@patch("spoteamfy.src.cli.fetch_recently_played")
@patch("spoteamfy.src.cli.load_users_from_json")
@patch("spoteamfy.src.cli.get_webhook_url")
def test_main_fetch_tracks_error(
    mock_get_webhook, mock_load_users, mock_fetch_tracks, mock_auth
):
    """Test main CLI when fetching tracks fails."""
    mock_get_webhook.return_value = "https://webhook.url"
    mock_load_users.return_value = [
        {
            "username": "testuser",
            "client_id": "id1",
            "client_secret": "secret1",
            "redirect_uri": "uri1",
            "refresh_token": "token1",
        }
    ]
    mock_spotify_client = Mock()
    mock_auth.return_value = mock_spotify_client
    mock_fetch_tracks.side_effect = Exception("Fetch failed")

    runner = CliRunner()
    result = runner.invoke(main)

    assert result.exit_code == 0
    assert "Error processing testuser: Fetch failed" in result.output
    assert "Failed posts: 1" in result.output


@patch("spoteamfy.src.cli.authenticate_user")
@patch("spoteamfy.src.cli.fetch_recently_played")
@patch("spoteamfy.src.cli.format_tracks_for_teams")
@patch("spoteamfy.src.cli.post_to_teams")
@patch("spoteamfy.src.cli.load_users_from_json")
@patch("spoteamfy.src.cli.get_webhook_url")
def test_main_post_teams_failure(
    mock_get_webhook,
    mock_load_users,
    mock_post_teams,
    mock_format_tracks,
    mock_fetch_tracks,
    mock_auth,
):
    """Test main CLI when posting to Teams fails."""
    mock_get_webhook.return_value = "https://webhook.url"
    mock_load_users.return_value = [
        {
            "username": "testuser",
            "client_id": "id1",
            "client_secret": "secret1",
            "redirect_uri": "uri1",
            "refresh_token": "token1",
        }
    ]
    mock_spotify_client = Mock()
    mock_auth.return_value = mock_spotify_client
    mock_fetch_tracks.return_value = [{"name": "Test Song"}]
    mock_format_tracks.return_value = {"text": "Test message"}
    mock_post_teams.return_value = False  # Simulate posting failure

    runner = CliRunner()
    result = runner.invoke(main)

    assert result.exit_code == 0
    assert "Failed to post tracks for testuser to Teams" in result.output
    assert "Failed posts: 1" in result.output


@patch("spoteamfy.src.cli.authenticate_user")
@patch("spoteamfy.src.cli.fetch_recently_played")
@patch("spoteamfy.src.cli.format_tracks_for_teams")
@patch("spoteamfy.src.cli.post_to_teams")
@patch("spoteamfy.src.cli.load_users_from_json")
@patch("spoteamfy.src.cli.get_webhook_url")
def test_main_multiple_users(
    mock_get_webhook,
    mock_load_users,
    mock_post_teams,
    mock_format_tracks,
    mock_fetch_tracks,
    mock_auth,
):
    """Test main CLI with multiple users."""
    mock_get_webhook.return_value = "https://webhook.url"
    mock_load_users.return_value = [
        {
            "username": "user1",
            "client_id": "id1",
            "client_secret": "secret1",
            "redirect_uri": "uri1",
            "refresh_token": "token1",
        },
        {
            "username": "user2",
            "client_id": "id2",
            "client_secret": "secret2",
            "redirect_uri": "uri2",
            "refresh_token": "token2",
        },
    ]
    mock_spotify_client = Mock()
    mock_auth.return_value = mock_spotify_client
    mock_fetch_tracks.return_value = [{"name": "Test Song"}]
    mock_format_tracks.return_value = {"text": "Test message"}
    mock_post_teams.return_value = True

    runner = CliRunner()
    result = runner.invoke(main)

    assert result.exit_code == 0
    assert "Successful posts: 2" in result.output
    assert "Total users processed: 2" in result.output
    assert mock_auth.call_count == 2
    assert mock_fetch_tracks.call_count == 2


def test_main_with_cli_options():
    """Test main CLI with custom options."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
        users = [
            {
                "username": "testuser",
                "client_id": "id1",
                "client_secret": "secret1",
                "redirect_uri": "uri1",
                "refresh_token": "token1",
            }
        ]
        json.dump(users, f)
        f.flush()
        users_path = f.name

    try:
        with (
            patch("spoteamfy.src.cli.authenticate_user") as mock_auth,
            patch("spoteamfy.src.cli.fetch_recently_played") as mock_fetch,
            patch("spoteamfy.src.cli.format_tracks_for_teams") as mock_format,
            patch("spoteamfy.src.cli.post_to_teams") as mock_post,
        ):

            mock_spotify_client = Mock()
            mock_auth.return_value = mock_spotify_client
            mock_fetch.return_value = [{"name": "Test Song"}]
            mock_format.return_value = {"text": "Test message"}
            mock_post.return_value = True

            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--num-tracks",
                    "10",
                    "--users-json",
                    users_path,
                    "--teams-webhook",
                    "https://custom.webhook.url",
                ],
            )

            assert result.exit_code == 0
            assert "Fetching 10 recently played tracks" in result.output
            mock_fetch.assert_called_once_with(mock_spotify_client, 10)

    finally:
        os.remove(users_path)
