import pytest

from spoteamfy.src.spotify_auth import SpotifyAuthError, authenticate_user


class DummySpotify:
    def __init__(self, auth):
        self.auth = auth


def test_authenticate_user_success(monkeypatch):
    # Patch SpotifyOAuth and spotipy.Spotify
    class DummyOAuth:
        def __init__(self, client_id, client_secret, redirect_uri, scope, cache_path):
            pass

        def refresh_access_token(self, refresh_token):
            return {"access_token": "dummy_token"}

    monkeypatch.setattr("spoteamfy.src.spotify_auth.SpotifyOAuth", DummyOAuth)
    monkeypatch.setattr("spoteamfy.src.spotify_auth.spotipy.Spotify", DummySpotify)
    creds = {
        "client_id": "id",
        "client_secret": "secret",
        "redirect_uri": "uri",
        "refresh_token": "refresh",
        "username": "user",
    }
    client = authenticate_user(creds)
    assert isinstance(client, DummySpotify)
    assert client.auth == "dummy_token"


def test_authenticate_user_missing_refresh_token():
    creds = {
        "client_id": "id",
        "client_secret": "secret",
        "redirect_uri": "uri",
        "username": "user",
    }
    with pytest.raises(SpotifyAuthError) as exc:
        authenticate_user(creds)
    assert "Missing refresh_token" in str(exc.value)
