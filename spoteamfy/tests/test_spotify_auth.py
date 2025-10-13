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
    assert "Missing or empty refresh_token" in str(exc.value)


def test_authenticate_user_placeholder_refresh_token():
    """Test that placeholder refresh tokens are detected and rejected."""
    creds = {
        "client_id": "id",
        "client_secret": "secret",
        "redirect_uri": "uri",
        "refresh_token": "SPOTIFY_REFRESH_TOKEN_1",
        "username": "user",
    }
    with pytest.raises(SpotifyAuthError) as exc:
        authenticate_user(creds)
    assert "Refresh token is a placeholder" in str(exc.value)


def test_authenticate_user_spotify_oauth_error(monkeypatch):
    """Test handling of SpotifyOauthError during token refresh."""
    from spotipy.oauth2 import SpotifyOauthError

    class DummyOAuth:
        def __init__(self, client_id, client_secret, redirect_uri, scope, cache_path):
            pass

        def refresh_access_token(self, refresh_token):
            raise SpotifyOauthError("OAuth error")

    monkeypatch.setattr("spoteamfy.src.spotify_auth.SpotifyOAuth", DummyOAuth)

    creds = {
        "client_id": "id",
        "client_secret": "secret",
        "redirect_uri": "uri",
        "refresh_token": "valid_token",
        "username": "user",
    }

    with pytest.raises(SpotifyAuthError) as exc:
        authenticate_user(creds)
    assert "Authentication failed for user user" in str(exc.value)


def test_authenticate_user_key_error():
    """Test handling of missing required credential fields."""
    creds = {
        "client_secret": "secret",
        "redirect_uri": "uri",
        "refresh_token": "token",
        "username": "user",
        # missing client_id
    }

    with pytest.raises(SpotifyAuthError) as exc:
        authenticate_user(creds)
    assert "Missing required credential field for user user" in str(exc.value)
