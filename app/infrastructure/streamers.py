from datetime import UTC, datetime

from app.domain.streamer import Streamer
from app.infrastructure.database import Database


async def save_streamer(
    database: Database,
    twitch_user_id: str,
    login: str,
    display_name: str,
    profile_image_url: str,
) -> None:
    now = datetime.now(UTC)
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """INSERT INTO streamers (
                       twitch_user_id, login, display_name, profile_image_url,
                       enabled, created_at, updated_at
                   ) VALUES (%s, %s, %s, %s, TRUE, %s, %s)
                   ON CONFLICT (twitch_user_id) DO UPDATE SET
                       login = excluded.login,
                       display_name = excluded.display_name,
                       profile_image_url = excluded.profile_image_url,
                       enabled = excluded.enabled,
                       updated_at = excluded.updated_at""",
            (twitch_user_id, login, display_name, profile_image_url, now, now),
        )


async def load_active_streamers(database: Database) -> list[Streamer]:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """SELECT twitch_user_id, login, display_name, profile_image_url
                   FROM streamers WHERE enabled ORDER BY twitch_user_id"""
        )
        return [Streamer(**row) for row in await cursor.fetchall()]


async def load_streamer(database: Database, twitch_user_id: str) -> Streamer | None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """SELECT twitch_user_id, login, display_name, profile_image_url
                   FROM streamers WHERE twitch_user_id = %s AND enabled LIMIT 1""",
            (twitch_user_id,),
        )
        row = await cursor.fetchone()
    return Streamer(**row) if row is not None else None
