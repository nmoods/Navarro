"""API tests: auth, authorization/isolation, project + editor flow, signed media, upload security."""

from __future__ import annotations

import io
import uuid

import pytest
from PIL import Image

from tests.conftest import drain, register


def _email() -> str:
    return f"{uuid.uuid4().hex[:10]}@example.com"


# ---- authentication ------------------------------------------------------------------------------------
def test_register_login_refresh_rotation_and_reuse_detection(client) -> None:  # type: ignore[no-untyped-def]
    email = _email()
    headers = register(client, email)
    assert client.get("/api/v1/auth/me", headers=headers).json()["email"] == email
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Sup3r-secret-pass"})
    assert login.status_code == 200
    old_cookie = client.cookies.get("rf_refresh")
    assert client.post("/api/v1/auth/refresh").status_code == 403  # CSRF header required
    refreshed = client.post("/api/v1/auth/refresh", headers={"X-Requested-With": "reelforge"})
    assert refreshed.status_code == 200 and refreshed.json()["access_token"]
    # replaying the rotated (old) refresh token revokes the whole token family
    new_cookie = client.cookies.get("rf_refresh")
    assert new_cookie and new_cookie != old_cookie
    client.cookies.clear()
    replay = client.post("/api/v1/auth/refresh", headers={"X-Requested-With": "reelforge", "Cookie": f"rf_refresh={old_cookie}"})
    assert replay.status_code == 401
    # ...and the legitimately rotated token is now revoked too (family revocation)
    client.cookies.clear()
    after = client.post("/api/v1/auth/refresh", headers={"X-Requested-With": "reelforge", "Cookie": f"rf_refresh={new_cookie}"})
    assert after.status_code == 401


def test_weak_password_and_duplicate_email_rejected(client) -> None:  # type: ignore[no-untyped-def]
    assert client.post("/api/v1/auth/register", json={"email": _email(), "password": "short", "display_name": "x"}).status_code == 422
    assert client.post("/api/v1/auth/register", json={"email": _email(), "password": "alllowercaseletters", "display_name": "x"}).status_code == 422
    email = _email()
    register(client, email)
    dup = client.post("/api/v1/auth/register", json={"email": email.upper(), "password": "Sup3r-secret-pass", "display_name": "x"})
    assert dup.status_code == 409


def test_requires_auth_and_rejects_tampered_tokens(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/projects").status_code == 401
    assert client.get("/api/v1/projects", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_security_headers_present(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "x-request-id" in resp.headers


def test_request_size_limit(client) -> None:  # type: ignore[no-untyped-def]
    headers = register(client, _email())
    big = b"x" * (31 * 1024 * 1024)
    resp = client.post("/api/v1/media/upload", headers=headers, files={"file": ("a.png", big, "image/png")})
    assert resp.status_code == 413


# ---- isolation -----------------------------------------------------------------------------------------
def test_users_cannot_access_each_others_data(client) -> None:  # type: ignore[no-untyped-def]
    alice, bob = register(client, _email()), register(client, _email())
    project = client.post("/api/v1/projects", json={"topic": "The Library of Alexandria"}, headers=alice).json()
    pid = project["id"]
    assert client.get(f"/api/v1/projects/{pid}", headers=bob).status_code == 404
    assert client.patch(f"/api/v1/projects/{pid}", json={"title": "hijack"}, headers=bob).status_code == 404
    assert client.delete(f"/api/v1/projects/{pid}", headers=bob).status_code == 404
    assert client.post(f"/api/v1/projects/{pid}/produce", json={}, headers=bob).status_code == 404
    jobs = client.get("/api/v1/jobs", headers=alice).json()
    assert client.get(f"/api/v1/jobs/{jobs[0]['id']}", headers=bob).status_code == 404
    assert client.post(f"/api/v1/jobs/{jobs[0]['id']}/cancel", headers=bob).status_code == 404
    assert client.get("/api/v1/projects", headers=bob).json()["total"] == 0


# ---- full editor flow ------------------------------------------------------------------------------------
@pytest.mark.slow
def test_create_edit_regenerate_render_download(client, worker) -> None:  # type: ignore[no-untyped-def]
    h = register(client, _email())
    project = client.post("/api/v1/projects", json={"topic": "The Dancing Plague of 1518", "duration_seconds": 30}, headers=h).json()
    drain(worker)
    board = client.get(f"/api/v1/projects/{project['id']}/storyboard", headers=h).json()
    scenes = board["scenes"]
    assert len(scenes) >= 3 and board["analysis"]["total_words"] > 0
    script = client.get(f"/api/v1/projects/{project['id']}/script", headers=h).json()
    assert len(script["hooks"]) == 6 and script["claims"]

    # edit + add + reorder + delete
    edit = client.patch(f"/api/v1/scenes/{scenes[1]['id']}", json={"narration": "A brand new line.", "camera_movement": "crash_zoom",
                                                                  "caption_override": {"animation": "bounce"}}, headers=h)
    assert edit.status_code == 200 and edit.json()["camera_movement"] == "crash_zoom"
    bad = client.patch(f"/api/v1/scenes/{scenes[1]['id']}", json={"camera_movement": "teleport"}, headers=h)
    assert bad.status_code == 422
    added = client.post(f"/api/v1/projects/{project['id']}/scenes", json={"narration": "An extra ending.", "position": 99}, headers=h)
    assert added.status_code == 201
    order = [s["id"] for s in client.get(f"/api/v1/projects/{project['id']}/storyboard", headers=h).json()["scenes"]]
    reordered = client.post(f"/api/v1/projects/{project['id']}/scenes/reorder", json={"scene_ids": list(reversed(order))}, headers=h)
    assert reordered.status_code == 200
    assert client.delete(f"/api/v1/scenes/{added.json()['id']}", headers=h).status_code == 204

    # regenerate one scene's visuals only
    regen = client.post(f"/api/v1/scenes/{scenes[0]['id']}/regenerate", json={"parts": ["visual_plan", "image"]}, headers=h)
    assert regen.status_code == 202
    drain(worker)
    assert client.get(f"/api/v1/jobs/{regen.json()['id']}", headers=h).json()["status"] == "completed"

    # render a draft and download it
    job = client.post(f"/api/v1/projects/{project['id']}/produce", json={"quality": "draft"}, headers=h)
    assert job.status_code == 202
    assert client.post(f"/api/v1/projects/{project['id']}/produce", json={}, headers=h).status_code == 409  # one job at a time
    drain(worker)
    status = client.get(f"/api/v1/jobs/{job.json()['id']}", headers=h).json()
    assert status["status"] == "completed", status
    exports = client.get(f"/api/v1/projects/{project['id']}/exports", headers=h).json()
    video = client.get(exports[0]["download_url"].replace("http://127.0.0.1:8000", ""))
    assert video.status_code == 200 and video.content[4:8] == b"ftyp"
    assert "attachment" in video.headers["content-disposition"]
    tampered = exports[0]["video_url"].replace("http://127.0.0.1:8000", "").replace("sig=", "sig=x")
    assert client.get(tampered).status_code == 403
    logs = client.get(f"/api/v1/jobs/{job.json()['id']}/logs", headers=h).json()
    assert any("Assembling" in log["message"] for log in logs)


# ---- uploads ---------------------------------------------------------------------------------------------
def _png(w: int = 200, h: int = 300) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 30, 200)).save(buf, format="PNG")
    return buf.getvalue()


def test_upload_validation(client) -> None:  # type: ignore[no-untyped-def]
    h = register(client, _email())
    ok = client.post("/api/v1/media/upload", headers=h, files={"file": ("pic.png", _png(), "image/png")})
    assert ok.status_code == 201 and ok.json()["mime_type"] == "image/png"
    spoofed = client.post("/api/v1/media/upload", headers=h, files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")})
    assert spoofed.status_code == 422
    wrong_ext = client.post("/api/v1/media/upload", headers=h, files={"file": ("pic.svg", _png(), "image/svg+xml")})
    assert wrong_ext.status_code == 422
    traversal = client.post("/api/v1/media/upload", headers=h, files={"file": ("../../etc/passwd.png", _png(), "image/png")})
    assert traversal.status_code == 201 and ".." not in traversal.json()["url"]
    library = client.get("/api/v1/media?kind=image", headers=h).json()
    assert library["total"] == 2


def test_story_dna_and_series_flow(client, worker) -> None:  # type: ignore[no-untyped-def]
    h = register(client, _email())
    dna = client.post("/api/v1/story-dna", json={"name": "Dark History", "visual_style": "dark_mystery", "color_palette": ["#101020", "#A78BFA"],
                                                 "caption_style": {"font": "Anton", "animation": "word_pop"}, "brand": {"handle": "@darkhist"}}, headers=h)
    assert dna.status_code == 201
    bad_font = client.post("/api/v1/story-dna", json={"name": "x", "caption_style": {"font": "Comic Sans"}}, headers=h)
    assert bad_font.status_code == 422
    project = client.post("/api/v1/projects", json={"topic": "Mary Celeste", "story_dna_id": dna.json()["id"]}, headers=h).json()
    assert project["settings"]["visual_style"] == "dark_mystery"
    assert project["settings"]["caption_style"]["font"] == "Anton"

    series = client.post("/api/v1/series", json={"theme": "Ghost ships", "episode_count": 3, "story_dna_id": dna.json()["id"]}, headers=h)
    assert series.status_code == 201
    drain(worker, limit=3)
    detail = client.get(f"/api/v1/series/{series.json()['id']}", headers=h).json()
    assert detail["status"] == "planned" and len(detail["episodes"]) == 3
    assert detail["bible"]["recurring_characters"]

    idea = client.post("/api/v1/ideas", json={"title": "The Flannan Isles", "scheduled_for": "2026-12-01"}, headers=h)
    assert idea.status_code == 201
    in_month = client.get("/api/v1/ideas?start=2026-12-01&end=2026-12-31", headers=h).json()
    assert [i["title"] for i in in_month] == ["The Flannan Isles"]


def test_options_and_provider_health(client) -> None:  # type: ignore[no-untyped-def]
    h = register(client, _email())
    opts = client.get("/api/v1/system/options").json()
    assert "historical_map" in opts["visual_types"] and "Anton" in opts["fonts"]
    health = client.get("/api/v1/system/providers", headers=h).json()
    assert all(p["is_test_double"] for p in health if p["kind"] in ("llm", "tts"))
