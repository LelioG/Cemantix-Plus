from __future__ import annotations


def test_bootstrap_daily(client):
    response = client.get("/api/v1/bootstrap")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["current_mode"] == "daily"
    assert payload["game"]["mode"] == "daily"
    assert payload["engine"]["name"] == "demo"
    assert payload["stats"]["played"] >= 1


def test_custom_game_full_flow(client):
    select_response = client.post(
        "/api/v1/game/select",
        json={"mode": "custom", "new_game": True, "custom_word": "amour"},
    )
    assert select_response.status_code == 200
    selected = select_response.get_json()
    assert selected["game"]["mode"] == "custom"

    guess_response = client.post("/api/v1/game/guess", json={"word": "mer"})
    assert guess_response.status_code == 200
    guess_payload = guess_response.get_json()
    assert guess_payload["ok"] is True
    assert guess_payload["game"]["guess_count"] == 1
    assert guess_payload["game"]["won"] is False

    hint_response = client.post("/api/v1/game/hint", json={})
    assert hint_response.status_code == 200
    hint_payload = hint_response.get_json()
    assert hint_payload["ok"] is True
    assert hint_payload["game"]["hints_used"] == 1
    assert len(hint_payload["game"]["hints"]) == 1

    win_response = client.post("/api/v1/game/guess", json={"word": "amour"})
    assert win_response.status_code == 200
    win_payload = win_response.get_json()
    assert win_payload["game"]["won"] is True
    assert win_payload["game"]["secret_word"] == "amour"

    leaderboard_response = client.get("/api/v1/leaderboard?mode=custom")
    assert leaderboard_response.status_code == 200
    leaderboard_payload = leaderboard_response.get_json()
    assert leaderboard_payload["leaderboard"]["entries"]
    assert leaderboard_payload["leaderboard"]["entries"][0]["attempts_count"] == 2


def test_profile_update_validation(client):
    bad_response = client.put("/api/v1/profile", json={"display_name": "x"})
    assert bad_response.status_code == 400

    good_response = client.put("/api/v1/profile", json={"display_name": "Lexi Test"})
    assert good_response.status_code == 200
    payload = good_response.get_json()
    assert payload["user"]["display_name"] == "Lexi Test"
