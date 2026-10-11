from datetime import UTC, datetime

from app.infrastructure.database import Database


async def rotate_overlay_access_key(
    database: Database, streamer_id: str, plugin_slug: str, token_hash: str
) -> str:
    now = datetime.now(UTC)
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """INSERT INTO overlay_access_keys (
                       streamer_id, plugin_slug, token_hash, created_at, rotated_at
                   ) VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (streamer_id, plugin_slug) DO UPDATE SET
                       token_hash = excluded.token_hash,
                       rotated_at = excluded.rotated_at""",
            (streamer_id, plugin_slug, token_hash, now, now),
        )
    return now.isoformat()


async def resolve_overlay_access_key(
    database: Database, plugin_slug: str, token_hash: str
) -> str | None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """SELECT access.streamer_id FROM overlay_access_keys AS access
                   JOIN streamers ON streamers.twitch_user_id = access.streamer_id
                   WHERE access.plugin_slug = %s AND access.token_hash = %s
                       AND streamers.enabled LIMIT 1""",
            (plugin_slug, token_hash),
        )
        row = await cursor.fetchone()
    return row["streamer_id"] if row is not None else None


async def load_overlay_access_key_rotated_at(
    database: Database, streamer_id: str, plugin_slug: str
) -> str | None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """SELECT rotated_at FROM overlay_access_keys
                   WHERE streamer_id = %s AND plugin_slug = %s LIMIT 1""",
            (streamer_id, plugin_slug),
        )
        row = await cursor.fetchone()
    return row["rotated_at"].isoformat() if row is not None else None
