import json
import os
import tempfile

import pytest

from spoteamfy.src.cli import get_users_json_path, load_users_from_json


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
            "redirect_uri": "uri1"
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


def test_get_users_json_path_env(monkeypatch):
    monkeypatch.setenv("USERS_JSON_PATH", "/tmp/test_users.json")
    assert get_users_json_path() == "/tmp/test_users.json"


def test_get_users_json_path_cli():
    assert get_users_json_path("/tmp/cli_users.json") == "/tmp/cli_users.json"


def test_get_users_json_path_default(monkeypatch):
    monkeypatch.delenv("USERS_JSON_PATH", raising=False)
    assert get_users_json_path() == "./config/users.json"
