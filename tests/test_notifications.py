
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app
from auth import create_access_token
from notifications import (
    create_notification,
    safe_notify,
)

client = TestClient(app)


def make_token(user_id, role="viewer"):
    return create_access_token({
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "role": role,
    })


def test_list_notifications():
    response = client.get("/notifications")
    assert response.status_code == 200

    data = response.json()
    assert "notifications" in data
    assert "unread_count" in data
    assert "total" in data
    assert isinstance(data["notifications"], list)


def test_mark_notification_as_read():
    user_id = f"read-user-{uuid4().hex}"
    notif = create_notification(
        title="Test Notification",
        message="Please review discovered lead",
    )

    response = client.patch(
        f"/notifications/{notif['id']}/read",
        headers={"Authorization": f"Bearer {make_token(user_id)}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["id"] == notif["id"]


def test_mark_notification_not_found():
    random_id = str(uuid4())
    user_id = f"missing-user-{uuid4().hex}"

    response = client.patch(
        f"/notifications/{random_id}/read",
        headers={"Authorization": f"Bearer {make_token(user_id)}"},
    )

    assert response.status_code == 404
    assert "Notification not found" in response.json()["detail"]


def test_mark_all_notifications_read():
    import notifications

    user_id = f"bulk-user-{uuid4().hex}"

    own1 = create_notification(
        title="Unread 1",
        message="Message 1",
        user_id=user_id,
    )
    own2 = create_notification(
        title="Unread 2",
        message="Message 2",
        user_id=user_id,
    )

    result = notifications.mark_all_as_read(
        user_id=user_id,
        client=None,
    )

    assert result >= 2
    assert (own1["id"], user_id) in notifications._fallback_notification_reads
    assert (own2["id"], user_id) in notifications._fallback_notification_reads


def test_create_system_notification_admin():
    admin_token = make_token("admin-id", "admin")

    response = client.post(
        "/notifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Platform Maintenance",
            "message": "Scraping pipeline updated.",
            "type": "info",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Platform Maintenance"
    assert data["is_read"] is False


def test_create_system_notification_viewer_forbidden():
    viewer_token = make_token("viewer-id")

    response = client.post(
        "/notifications",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "title": "Unauthorized Notification",
            "message": "This should be blocked.",
            "type": "warning",
        },
    )

    assert response.status_code == 403
    assert "Administrator access required" in response.json()["detail"]


def test_safe_notify_never_raises():
    safe_notify(
        title="Safe notification",
        message="This should run cleanly",
        client=None,
    )


def test_user_cannot_mark_another_users_notification_as_read():
    notif = create_notification(
        title="Private notification",
        message="This belongs to another user.",
        user_id="notification-owner",
    )

    response = client.patch(
        f"/notifications/{notif['id']}/read",
        headers={
            "Authorization": f"Bearer {make_token('different-user')}"
        },
    )

    assert response.status_code == 404


def test_user_can_mark_own_notification_as_read():
    notif = create_notification(
        title="My notification",
        message="This belongs to me.",
        user_id="notification-owner",
    )

    response = client.patch(
        f"/notifications/{notif['id']}/read",
        headers={
            "Authorization": f"Bearer {make_token('notification-owner')}"
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_broadcast_read_status_is_independent_per_user():
    import notifications

    broadcast = create_notification(
        title="System broadcast",
        message="This is visible to all users.",
    )

    user_a = f"user-a-{uuid4().hex}"
    user_b = f"user-b-{uuid4().hex}"

    assert notifications.mark_as_read(
        broadcast["id"],
        user_id=user_a,
        client=None,
    )

    assert (broadcast["id"], user_a) in notifications._fallback_notification_reads
    assert (broadcast["id"], user_b) not in notifications._fallback_notification_reads

    list_a = notifications.list_notifications(
        user_id=user_a,
        client=None,
    )
    list_b = notifications.list_notifications(
        user_id=user_b,
        client=None,
    )

    item_a = next(
        item for item in list_a["notifications"]
        if item["id"] == broadcast["id"]
    )
    item_b = next(
        item for item in list_b["notifications"]
        if item["id"] == broadcast["id"]
    )

    assert item_a["is_read"] is True
    assert item_b["is_read"] is False


def test_user_cannot_mark_another_users_notification_read():
    import notifications

    private = create_notification(
        title="Private",
        message="Only its owner can read it.",
        user_id="private-owner",
    )

    result = notifications.mark_as_read(
        private["id"],
        user_id="not-the-owner",
        client=None,
    )

    assert result is False


def test_admin_cannot_list_another_users_private_notifications():
    import notifications

    private = create_notification(
        title="Private admin test",
        message="This belongs to a different user.",
        user_id="private-owner",
    )

    result = notifications.list_notifications(
        user_id="admin-user",
        role="admin",
        client=None,
    )

    returned_ids = {
        item["id"] for item in result["notifications"]
    }

    assert private["id"] not in returned_ids


def test_mark_all_as_read_only_affects_own_and_broadcast_notifications():
    import notifications

    user_id = f"bulk-isolation-{uuid4().hex}"

    own = create_notification(
        title="Own notification",
        message="Own message",
        user_id=user_id,
    )

    other = create_notification(
        title="Other user's notification",
        message="Other message",
        user_id="someone-else",
    )

    broadcast = create_notification(
        title="System broadcast",
        message="Broadcast message",
    )

    notifications.mark_all_as_read(
        user_id=user_id,
        client=None,
    )

    reads = notifications._fallback_notification_reads

    assert (own["id"], user_id) in reads
    assert (broadcast["id"], user_id) in reads
    assert (other["id"], user_id) not in reads


def test_mark_all_as_read_without_user_id_changes_nothing():
    import notifications

    notif = create_notification(
        title="Protected notification",
        message="Must remain unread.",
        user_id="protected-user",
    )

    result = notifications.mark_all_as_read(
        user_id=None,
        client=None,
    )

    assert result == 0
    assert not any(
        notification_id == notif["id"]
        for notification_id, _ in notifications._fallback_notification_reads
    )
