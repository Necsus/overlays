from datetime import UTC, datetime

from app.domain.giveaway import GiveawayEngine, GiveawayState, Participant
from app.infrastructure.database import Database


async def create_giveaway(
    database: Database, streamer_id: str, giveaway_id: str, lot: str
) -> None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """INSERT INTO giveaways (id, streamer_id, lot, status, created_at)
                   VALUES (%s, %s, %s, 'WAITING', %s)""",
            (giveaway_id, streamer_id, lot, datetime.now(UTC)),
        )


async def open_giveaway(
    database: Database, streamer_id: str, giveaway_id: str,
    closes_at: datetime | None = None,
) -> None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """UPDATE giveaways SET status = 'OPEN', opened_at = %s, closes_at = %s
                   WHERE id = %s AND streamer_id = %s AND status = 'WAITING'""",
            (datetime.now(UTC), closes_at, giveaway_id, streamer_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("The giveaway is not waiting")


async def add_participant(
    database: Database, streamer_id: str, giveaway_id: str, participant: Participant
) -> bool:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """INSERT INTO participants (
                       giveaway_id, twitch_user_id, login, display_name, joined_at
                   ) SELECT g.id, %s, %s, %s, %s FROM giveaways g
                     WHERE g.id = %s AND g.streamer_id = %s
                   ON CONFLICT (giveaway_id, twitch_user_id) DO NOTHING""",
            (participant.twitch_user_id, participant.login, participant.display_name,
             datetime.now(UTC), giveaway_id, streamer_id),
        )
        return cursor.rowcount == 1


async def draw_giveaway(
    database: Database, streamer_id: str, giveaway_id: str, winner: Participant
) -> None:
    drawn_at = datetime.now(UTC)
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """UPDATE giveaways
                   SET status = 'WINNER', closes_at = NULL,
                       drawn_at = COALESCE(drawn_at, %s)
                   WHERE id = %s AND streamer_id = %s
                     AND status IN ('OPEN', 'WINNER')""",
            (drawn_at, giveaway_id, streamer_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("The giveaway cannot be drawn")
        await cursor.execute(
            """INSERT INTO winners (
                       giveaway_id, twitch_user_id, display_name, drawn_at, draw_order
                   ) SELECT %s, %s, %s, %s, COALESCE(MAX(draw_order), 0) + 1
                     FROM winners WHERE giveaway_id = %s""",
            (giveaway_id, winner.twitch_user_id, winner.display_name, drawn_at, giveaway_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("The winner was not persisted")


async def stop_giveaway(
    database: Database, streamer_id: str, giveaway_id: str
) -> None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """UPDATE giveaways
                   SET status = CASE WHEN status = 'WINNER' THEN 'COMPLETED'
                                     ELSE 'CANCELLED' END,
                       closes_at = NULL, stopped_at = %s
                   WHERE id = %s AND streamer_id = %s
                     AND status IN ('WAITING', 'OPEN', 'WINNER')""",
            (datetime.now(UTC), giveaway_id, streamer_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("There is no active giveaway")


async def restore_active_giveaway(
    database: Database, streamer_id: str, engine: GiveawayEngine
) -> bool:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        await cursor.execute(
            """SELECT id, lot, status, closes_at FROM giveaways
               WHERE streamer_id = %s AND status IN ('WAITING', 'OPEN', 'WINNER')
               ORDER BY created_at DESC LIMIT 1""",
            (streamer_id,),
        )
        giveaway = await cursor.fetchone()
        if giveaway is None:
            return False
        await cursor.execute(
            """SELECT twitch_user_id, login, display_name FROM participants
               WHERE giveaway_id = %s ORDER BY joined_at, id""",
            (giveaway["id"],),
        )
        participants = [Participant(**row) for row in await cursor.fetchall()]
        await cursor.execute(
            "SELECT twitch_user_id FROM winners WHERE giveaway_id = %s ORDER BY draw_order",
            (giveaway["id"],),
        )
        winner_ids = [row["twitch_user_id"] for row in await cursor.fetchall()]
    engine.restore(
        giveaway_id=giveaway["id"], lot=giveaway["lot"],
        state=GiveawayState(giveaway["status"]), participants=participants,
        winner_user_ids=winner_ids,
    )
    if engine.state is GiveawayState.OPEN:
        engine.closes_at = giveaway["closes_at"]
    return True


async def list_giveaways(
    database: Database, streamer_id: str, limit: int, before: datetime | None = None,
    before_id: str | None = None,
) -> list[dict[str, object]]:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """SELECT id, lot, status, created_at, opened_at, drawn_at, stopped_at,
                      closes_at,
                      (SELECT count(*) FROM participants p WHERE p.giveaway_id=g.id) AS participant_count
               FROM giveaways g
               WHERE streamer_id = %s
                 AND (%s::timestamptz IS NULL OR (created_at, id) < (%s, %s))
               ORDER BY created_at DESC, id DESC LIMIT %s""",
            (streamer_id, before, before, before_id, limit),
        )
        return list(await cursor.fetchall())


async def load_giveaway_detail(
    database: Database, streamer_id: str, giveaway_id: str
) -> dict[str, object] | None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """SELECT id, lot, status, created_at, opened_at, drawn_at, stopped_at, closes_at
               FROM giveaways WHERE id = %s AND streamer_id = %s""",
            (giveaway_id, streamer_id),
        )
        giveaway = await cursor.fetchone()
        if giveaway is None:
            return None
        await cursor.execute(
            """SELECT twitch_user_id, login, display_name, joined_at FROM participants
               WHERE giveaway_id = %s ORDER BY joined_at, id""", (giveaway_id,)
        )
        participants = list(await cursor.fetchall())
        await cursor.execute(
            """SELECT twitch_user_id, display_name, drawn_at, draw_order FROM winners
               WHERE giveaway_id = %s ORDER BY draw_order""", (giveaway_id,)
        )
        winners = list(await cursor.fetchall())
    return {**giveaway, "participants": participants, "winners": winners}


async def load_command_prefix(database: Database, streamer_id: str) -> str:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            "SELECT command_prefix FROM streamer_preferences WHERE streamer_id = %s",
            (streamer_id,),
        )
        row = await cursor.fetchone()
    return row["command_prefix"] if row is not None else "!"


async def save_command_prefix(
    database: Database, streamer_id: str, prefix: str
) -> None:
    async with database.transaction() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """INSERT INTO streamer_preferences (streamer_id, command_prefix, updated_at)
               VALUES (%s, %s, %s)
               ON CONFLICT (streamer_id) DO UPDATE SET
                 command_prefix = excluded.command_prefix, updated_at = excluded.updated_at""",
            (streamer_id, prefix, datetime.now(UTC)),
        )
