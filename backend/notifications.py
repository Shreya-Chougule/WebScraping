
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set, Tuple

logger = logging.getLogger("scrapescout.notifications")

# In-memory fallback store for local development and tests.
_fallback_notifications: List[Dict[str, Any]] = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "title": "Welcome to ScrapeScout",
        "message": "ScrapeScout workspace is active. Discovered projects will appear here.",
        "type": "info",
        "is_read": False,
        "user_id": None,
        "link": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
]

# Individual read receipts: (notification_id, user_id).
_fallback_notification_reads: Set[Tuple[str, str]] = set()


def _can_access_notification(notif, user_id):
    """Users can access their own notifications and system broadcasts."""
    notification_user_id = notif.get("user_id")

    if notification_user_id is None:
        return True

    return bool(user_id and notification_user_id == user_id)


def _with_user_read_status(notifications, user_id, read_ids=None):
    """Return notification copies with read status for the current user."""
    read_ids = read_ids or set()
    result = []

    for notification in notifications:
        item = dict(notification)
        item["is_read"] = bool(
            user_id and item.get("id") in read_ids
        )
        result.append(item)

    return result


def create_notification(
    title,
    message,
    notif_type="info",
    user_id=None,
    link=None,
    client=None,
):
    """Create a notification in Supabase, falling back to memory if needed."""
    record = {
        "id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "type": notif_type,
        "is_read": False,
        "user_id": user_id,
        "link": link,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if client:
        try:
            response = client.table("notifications").insert(record).execute()

            if response.data:
                created = dict(response.data[0])
                created["is_read"] = False
                return created

        except Exception as exc:
            logger.debug("Database notification insert failed: %s", exc)

    _fallback_notifications.insert(0, record)

    if len(_fallback_notifications) > 500:
        removed = _fallback_notifications.pop()
        removed_id = removed.get("id")

        if removed_id:
            _fallback_notification_reads.difference_update(
                entry
                for entry in _fallback_notification_reads
                if entry[0] == removed_id
            )

    return record


def list_notifications(
    user_id=None,
    role="viewer",
    unread_only=False,
    limit=50,
    client=None,
):
    """Retrieve notifications visible to the current user."""
    if client:
        try:
            query = client.table("notifications").select("*")

            if user_id:
                query = query.or_(
                    f"user_id.is.null,user_id.eq.{user_id}"
                )
            else:
                query = query.is_("user_id", "null")

            response = query.order("created_at", desc=True).execute()
            items = response.data or []

            notification_ids = [
                item["id"] for item in items if item.get("id")
            ]

            read_ids = set()

            if user_id and notification_ids:
                reads_response = (
                    client.table("notification_reads")
                    .select("notification_id")
                    .eq("user_id", user_id)
                    .in_("notification_id", notification_ids)
                    .execute()
                )

                read_ids = {
                    row["notification_id"]
                    for row in (reads_response.data or [])
                    if row.get("notification_id")
                }

            visible_items = _with_user_read_status(
                items, user_id, read_ids
            )

            unread_count = sum(
                1 for item in visible_items if not item["is_read"]
            )

            if unread_only:
                visible_items = [
                    item for item in visible_items
                    if not item["is_read"]
                ]

            return {
                "notifications": visible_items[:limit],
                "unread_count": unread_count,
                "total": (
                    len(visible_items) if unread_only else len(items)
                ),
            }

        except Exception as exc:
            logger.debug("Database notification list failed: %s", exc)

    filtered = [
        notif for notif in _fallback_notifications
        if _can_access_notification(notif, user_id)
    ]

    read_ids = {
        notification_id
        for notification_id, read_user_id in _fallback_notification_reads
        if user_id and read_user_id == user_id
    }

    visible_items = _with_user_read_status(
        filtered, user_id, read_ids
    )

    unread_count = sum(
        1 for item in visible_items if not item["is_read"]
    )

    if unread_only:
        visible_items = [
            item for item in visible_items if not item["is_read"]
        ]

    return {
        "notifications": visible_items[:limit],
        "unread_count": unread_count,
        "total": len(visible_items),
    }


def mark_as_read(notification_id, user_id=None, client=None):
    """Create a read receipt for this user without changing shared content."""
    if not user_id:
        return False

    # Check local fallback notifications first.
    for notif in _fallback_notifications:
        if notif.get("id") == notification_id:
            if not _can_access_notification(notif, user_id):
                return False

            _fallback_notification_reads.add(
                (notification_id, user_id)
            )
            return True

    # Check Supabase only if the notification is not in local storage.
    if client:
        try:
            response = (
                client.table("notifications")
                .select("id,user_id")
                .eq("id", notification_id)
                .execute()
            )

            rows = response.data or []

            if not rows:
                return False

            notification = rows[0]

            if not _can_access_notification(notification, user_id):
                return False

            client.table("notification_reads").upsert(
                {
                    "notification_id": notification_id,
                    "user_id": user_id,
                    "read_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="notification_id,user_id",
            ).execute()

            return True

        except Exception as exc:
            logger.debug("Database notification mark-read failed: %s", exc)

    return False


def mark_all_as_read(user_id=None, client=None):
    """Create individual read receipts for all visible unread notifications."""
    if not user_id:
        return 0

    if client:
        try:
            response = (
                client.table("notifications")
                .select("id,user_id")
                .or_(f"user_id.is.null,user_id.eq.{user_id}")
                .execute()
            )

            notifications = response.data or []

            notification_ids = [
                item["id"] for item in notifications if item.get("id")
            ]

            if not notification_ids:
                return 0

            existing_response = (
                client.table("notification_reads")
                .select("notification_id")
                .eq("user_id", user_id)
                .in_("notification_id", notification_ids)
                .execute()
            )

            existing_ids = {
                row["notification_id"]
                for row in (existing_response.data or [])
                if row.get("notification_id")
            }

            new_records = [
                {
                    "notification_id": notification_id,
                    "user_id": user_id,
                    "read_at": datetime.now(timezone.utc).isoformat(),
                }
                for notification_id in notification_ids
                if notification_id not in existing_ids
            ]

            if not new_records:
                return 0

            client.table("notification_reads").upsert(
                new_records,
                on_conflict="notification_id,user_id",
            ).execute()

            return len(new_records)

        except Exception as exc:
            logger.debug("Database mark-all-read failed: %s", exc)

    count = 0

    for notif in _fallback_notifications:
        notification_id = notif.get("id")

        if (
            notification_id
            and _can_access_notification(notif, user_id)
            and (notification_id, user_id)
            not in _fallback_notification_reads
        ):
            _fallback_notification_reads.add(
                (notification_id, user_id)
            )
            count += 1

    return count


def safe_notify(
    title,
    message,
    notif_type="info",
    user_id=None,
    link=None,
    client=None,
):
    """Prevent notification failures from interrupting core application work."""
    try:
        create_notification(
            title=title,
            message=message,
            notif_type=notif_type,
            user_id=user_id,
            link=link,
            client=client,
        )
    except Exception as exc:
        logger.warning("Safe notification bypassed exception: %s", exc)
