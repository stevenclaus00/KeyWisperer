"""
VoiceKey AI Phase 1 Backend API Tests
Tests: Health, Profiles CRUD, History CRUD
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def api():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def created_profile_id(api):
    """Create a test profile and yield its ID, then clean up"""
    resp = api.post(f"{BASE_URL}/api/profiles", json={
        "name": "TEST_Profile_Pytest",
        "custom_vocabulary": ["pytest", "voicekey"],
    })
    assert resp.status_code == 200
    profile_id = resp.json()["id"]
    yield profile_id
    # Cleanup
    api.delete(f"{BASE_URL}/api/profiles/{profile_id}")

@pytest.fixture(scope="module")
def created_history_id(api):
    """Create a test history item and yield its ID, then clean up"""
    resp = api.post(f"{BASE_URL}/api/history", json={
        "text": "TEST_This is a test transcription with five words here",
        "profile_id": "",
        "profile_name": "Default",
    })
    assert resp.status_code == 200
    history_id = resp.json()["id"]
    yield history_id
    # Cleanup
    api.delete(f"{BASE_URL}/api/history/{history_id}")

# ── Health ──

class TestHealth:
    def test_health_returns_200(self, api):
        resp = api.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200

    def test_health_status_healthy(self, api):
        resp = api.get(f"{BASE_URL}/api/health")
        data = resp.json()
        assert data["status"] == "healthy"

    def test_health_has_stt_available(self, api):
        resp = api.get(f"{BASE_URL}/api/health")
        data = resp.json()
        assert "stt_available" in data

# ── Profiles ──

class TestProfiles:
    def test_get_profiles_returns_list(self, api):
        resp = api.get(f"{BASE_URL}/api/profiles")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_profiles_has_default(self, api):
        resp = api.get(f"{BASE_URL}/api/profiles")
        names = [p["name"] for p in resp.json()]
        assert "Default" in names

    def test_create_profile(self, api, created_profile_id):
        # created_profile_id fixture creates profile, just verify it's there
        resp = api.get(f"{BASE_URL}/api/profiles")
        ids = [p["id"] for p in resp.json()]
        assert created_profile_id in ids

    def test_created_profile_has_custom_vocabulary(self, api, created_profile_id):
        resp = api.get(f"{BASE_URL}/api/profiles")
        profiles = {p["id"]: p for p in resp.json()}
        profile = profiles[created_profile_id]
        assert "pytest" in profile["custom_vocabulary"]

    def test_get_active_profile(self, api):
        resp = api.get(f"{BASE_URL}/api/profiles/active")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["is_active"] == True

    def test_activate_profile(self, api, created_profile_id):
        resp = api.put(f"{BASE_URL}/api/profiles/{created_profile_id}/activate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] == True
        assert data["id"] == created_profile_id

    def test_activate_nonexistent_profile_returns_404(self, api):
        resp = api.put(f"{BASE_URL}/api/profiles/nonexistent-id-12345/activate")
        assert resp.status_code == 404

    def test_delete_nonexistent_profile_returns_404(self, api):
        resp = api.delete(f"{BASE_URL}/api/profiles/nonexistent-id-12345")
        assert resp.status_code == 404

    def test_update_profile(self, api, created_profile_id):
        resp = api.put(f"{BASE_URL}/api/profiles/{created_profile_id}", json={
            "name": "TEST_Profile_Updated"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "TEST_Profile_Updated"

# ── History ──

class TestHistory:
    def test_get_history_returns_list(self, api):
        resp = api.get(f"{BASE_URL}/api/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_history_item(self, api, created_history_id):
        resp = api.get(f"{BASE_URL}/api/history")
        ids = [h["id"] for h in resp.json()]
        assert created_history_id in ids

    def test_history_item_has_word_count(self, api, created_history_id):
        resp = api.get(f"{BASE_URL}/api/history")
        items = {h["id"]: h for h in resp.json()}
        item = items[created_history_id]
        assert item["word_count"] > 0

    def test_update_history_item(self, api, created_history_id):
        resp = api.put(f"{BASE_URL}/api/history/{created_history_id}", json={
            "text": "TEST_Updated transcription text with word count"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Updated" in data["text"]
        assert data["word_count"] > 0

    def test_delete_history_item(self, api):
        # Create a fresh item to delete
        create_resp = api.post(f"{BASE_URL}/api/history", json={
            "text": "TEST_To be deleted",
            "profile_name": "Default",
        })
        assert create_resp.status_code == 200
        item_id = create_resp.json()["id"]
        
        del_resp = api.delete(f"{BASE_URL}/api/history/{item_id}")
        assert del_resp.status_code == 200
        
        # Verify deleted
        get_resp = api.get(f"{BASE_URL}/api/history")
        ids = [h["id"] for h in get_resp.json()]
        assert item_id not in ids

    def test_delete_nonexistent_history_returns_404(self, api):
        resp = api.delete(f"{BASE_URL}/api/history/nonexistent-id-12345")
        assert resp.status_code == 404
