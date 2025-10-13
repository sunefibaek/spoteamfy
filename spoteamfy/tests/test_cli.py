import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from spoteamfy.src.cli import (
    fetch_top_tracks,
    format_tracks_for_teams,
    get_users_json_path,
    load_users_from_json,
    post_to_teams,
)


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


def test_fetch_top_tracks():
    """Test fetching top tracks using spotipy."""
    # Mock spotipy client
    mock_client = Mock()
    mock_client.current_user_top_tracks.return_value = {
        "items": [
            {
                "name": "Test Song 1",
                "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
                "album": {"name": "Test Album"},
                "popularity": 85,
                "external_urls": {"spotify": "https://open.spotify.com/track/123"},
                "preview_url": "https://preview.url",
            },
            {
                "name": "Test Song 2",
                "artists": [{"name": "Artist 3"}],
                "album": {"name": "Another Album"},
                "popularity": 92,
                "external_urls": {"spotify": "https://open.spotify.com/track/456"},
                "preview_url": None,
            },
        ]
    }

    tracks = fetch_top_tracks(mock_client, num_tracks=2)

    assert len(tracks) == 2
    assert tracks[0]["name"] == "Test Song 1"
    assert tracks[0]["artist"] == "Artist 1, Artist 2"
    assert tracks[0]["album"] == "Test Album"
    assert tracks[0]["popularity"] == 85
    assert tracks[1]["name"] == "Test Song 2"
    assert tracks[1]["artist"] == "Artist 3"

    # Verify spotipy method was called with correct parameters
    mock_client.current_user_top_tracks.assert_called_once_with(
        limit=2, time_range="short_term"
    )


def test_fetch_top_tracks_limits_to_50():
    """Test that fetch_top_tracks limits requests to 50 tracks max."""
    mock_client = Mock()
    mock_client.current_user_top_tracks.return_value = {"items": []}

    fetch_top_tracks(mock_client, num_tracks=100)

    mock_client.current_user_top_tracks.assert_called_once_with(
        limit=50, time_range="short_term"  # Should be limited to 50
    )


def test_format_tracks_for_teams():
    """Test formatting tracks for Teams webhook."""
    tracks = [
        {
            "name": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "external_urls": "https://open.spotify.com/track/123",
        }
    ]

    message = format_tracks_for_teams("testuser", tracks)

    assert "testuser" in message["text"]
    assert "Test Song" in message["text"]
    assert "Test Artist" in message["text"]
    assert "Test Album" in message["text"]
    assert "https://open.spotify.com/track/123" in message["text"]


def test_format_tracks_for_teams_no_tracks():
    """Test formatting when no tracks are found."""
    message = format_tracks_for_teams("testuser", [])

    assert message["text"] == "No top tracks found for testuser"


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
    mock_post.side_effect = Exception("Network error")

    message = {"text": "Test message"}
    result = post_to_teams("https://webhook.url", message)

    assert result is False
