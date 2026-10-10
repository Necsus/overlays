"""PostgreSQL connections and explicit, versioned schema initialization.

Apply migrations before starting the application:
    python -m app.infrastructure.database
"""

import argparse
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.environment import Settings

SCHEMA_VERSION = 2
Connection = psycopg.AsyncConnection[dict[str, Any]]

# The initial migration targets an empty PostgreSQL database, not a SQLite dump.
INITIAL_SCHEMA = (
    """CREATE TABLE streamers (
        twitch_user_id TEXT PRIMARY KEY,
        login TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        profile_image_url TEXT NOT NULL DEFAULT '',
        enabled BOOLEAN NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE overlay_access_keys (
        streamer_id TEXT NOT NULL REFERENCES streamers(twitch_user_id) ON DELETE CASCADE,
        plugin_slug TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL,
        rotated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (streamer_id, plugin_slug)
    )""",
    """CREATE TABLE giveaways (
        id TEXT PRIMARY KEY,
        lot TEXT NOT NULL,
        status TEXT NOT NULL CHECK (
            status IN ('WAITING', 'OPEN', 'WINNER', 'COMPLETED', 'CANCELLED')
        ),
        created_at TIMESTAMPTZ NOT NULL,
        opened_at TIMESTAMPTZ,
        drawn_at TIMESTAMPTZ,
        stopped_at TIMESTAMPTZ,
        closes_at TIMESTAMPTZ
    )""",
    """CREATE TABLE participants (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        giveaway_id TEXT NOT NULL REFERENCES giveaways(id) ON DELETE CASCADE,
        twitch_user_id TEXT NOT NULL,
        login TEXT NOT NULL,
        display_name TEXT NOT NULL,
        joined_at TIMESTAMPTZ NOT NULL,
        UNIQUE (giveaway_id, twitch_user_id)
    )""",
    """CREATE TABLE winners (
        giveaway_id TEXT NOT NULL,
        twitch_user_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        drawn_at TIMESTAMPTZ NOT NULL,
        draw_order INTEGER NOT NULL CHECK (draw_order > 0),
        PRIMARY KEY (giveaway_id, twitch_user_id),
        UNIQUE (giveaway_id, draw_order),
        FOREIGN KEY (giveaway_id, twitch_user_id)
            REFERENCES participants(giveaway_id, twitch_user_id) ON DELETE CASCADE
    )""",
    "CREATE UNIQUE INDEX one_active_streamer ON streamers ((1)) WHERE enabled",
    """CREATE UNIQUE INDEX one_active_giveaway ON giveaways ((1))
        WHERE status IN ('WAITING', 'OPEN', 'WINNER')""",
)

MULTI_STREAMER_SCHEMA = (
    "DROP INDEX one_active_streamer",
    "DROP INDEX one_active_giveaway",
    "ALTER TABLE giveaways ADD COLUMN streamer_id TEXT REFERENCES streamers(twitch_user_id) ON DELETE CASCADE",
    # Existing records are disposable test data; do not guess their ownership.
    "DELETE FROM giveaways",
    "ALTER TABLE giveaways ALTER COLUMN streamer_id SET NOT NULL",
    "CREATE UNIQUE INDEX one_active_giveaway_per_streamer ON giveaways (streamer_id) WHERE status IN ('WAITING', 'OPEN', 'WINNER')",
    "CREATE INDEX giveaways_streamer_history ON giveaways (streamer_id, created_at DESC, id DESC)",
    """CREATE TABLE streamer_preferences (
        streamer_id TEXT PRIMARY KEY REFERENCES streamers(twitch_user_id) ON DELETE CASCADE,
        command_prefix TEXT NOT NULL DEFAULT '!' CHECK (length(command_prefix) BETWEEN 1 AND 5),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
)


class DatabaseError(RuntimeError):
    """Public error that never includes credentials, SQL values or driver details."""


class Database:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Serialize identity/key changes with WebSocket authentication in this worker.
        self.access_lock = asyncio.Lock()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Connection]:
        settings = self._settings
        transaction_started = False
        try:
            async with (
                await Connection.connect(
                    host=settings.psql_host,
                    port=settings.psql_port,
                    dbname=settings.psql_db,
                    user=settings.psql_user,
                    password=settings.psql_password.get_secret_value(),
                    sslmode=settings.psql_sslmode,
                    sslrootcert=(
                        str(settings.psql_sslrootcert)
                        if settings.psql_sslrootcert is not None
                        else None
                    ),
                    connect_timeout=5,
                    application_name="necsusdev-overlays",
                    options=(
                        "-c timezone=UTC -c search_path=public "
                        "-c statement_timeout=10000 -c lock_timeout=5000"
                    ),
                    autocommit=True,
                    row_factory=dict_row,
                ) as connection,
                connection.transaction(),
            ):
                transaction_started = True
                yield connection
        except psycopg.Error as error:
            # Only fixed descriptions are public: never print driver messages,
            # which can contain connection details or SQL parameter values.
            descriptions = {
                "28P01": "Authentication rejected; check PSQL_USER and PSQL_PASSWORD",
                "28000": "Authorization rejected; check the role and server access rules",
                "3D000": "Database not found; check PSQL_DB",
                "42501": "Insufficient privileges; check database/schema/table permissions",
                "42P07": "A migration table already exists; inspect the target schema without deleting it",
                "42P01": "A required table is missing; apply the database migrations",
                "42601": "SQL syntax error in a database operation",
                "55P03": "Lock unavailable or lock timeout; another operation may be running",
                "57014": "Database operation cancelled or statement timeout exceeded",
                "53300": "PostgreSQL connection limit reached",
            }
            fallback = (
                "PostgreSQL transaction failed; no driver details are displayed"
                if transaction_started
                else "Connection or transaction startup failed; check PSQL_HOST "
                "(without port), PSQL_PORT, PSQL_DB, credentials, TLS and server availability"
            )
            raise DatabaseError(
                descriptions.get(error.sqlstate or "", fallback)
            ) from None

    async def check_schema(self) -> None:
        async with (
            self.transaction() as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            versions = [row["version"] for row in await cursor.fetchall()]
        if versions != list(range(1, SCHEMA_VERSION + 1)):
            raise DatabaseError(
                "Incompatible PostgreSQL schema; run database migrations"
            )

    async def preflight_migration(self) -> None:
        """Check the production schema without changing it before deployment."""
        async with (
            self.transaction() as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute("SET TRANSACTION READ ONLY")
            await cursor.execute(
                "SELECT to_regclass('public.schema_migrations') AS migration_table"
            )
            if (await cursor.fetchone())["migration_table"] is None:
                raise DatabaseError(
                    "Refusing deployment: target database has no migration history; "
                    "restore or initialize it explicitly first"
                )

            await cursor.execute(
                "SELECT version FROM public.schema_migrations ORDER BY version"
            )
            versions = [row["version"] for row in await cursor.fetchall()]
            if versions not in ([1], list(range(1, SCHEMA_VERSION + 1))):
                raise DatabaseError(
                    "Refusing deployment: target database has an unsupported "
                    "schema version"
                )

            if versions[-1] == 1:
                await cursor.execute(
                    "SELECT to_regclass('public.giveaways') AS giveaways_table"
                )
                if (await cursor.fetchone())["giveaways_table"] is not None:
                    await cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM public.giveaways) AS has_giveaways"
                    )
                    if (await cursor.fetchone())["has_giveaways"]:
                        raise DatabaseError(
                            "Refusing migration: schema version 1 contains giveaways "
                            "that migration version 2 deletes"
                        )

    async def migrate(self) -> None:
        async with (
            self.transaction() as connection,
            connection.cursor() as cursor,
        ):
            # Serialize concurrent migration invocations, including first creation.
            await cursor.execute("SELECT pg_advisory_xact_lock(728194601)")
            await cursor.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            await cursor.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            versions = [row["version"] for row in await cursor.fetchall()]
            if versions == list(range(1, SCHEMA_VERSION + 1)):
                return
            if versions not in ([], [1]):
                raise DatabaseError("Unsupported PostgreSQL schema version")
            if not versions:
                for statement in INITIAL_SCHEMA:
                    await cursor.execute(statement)
                await cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (1)"
                )
            for statement in MULTI_STREAMER_SCHEMA:
                await cursor.execute(statement)
            await cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (2)"
            )


async def _main() -> None:
    from pydantic import ValidationError

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="check the production migration guard without changing the database",
    )
    args = parser.parse_args()

    try:
        settings = Settings()  # pyright: ignore[reportCallIssue]
    except ValidationError as error:
        fields = sorted(
            {
                str(item["loc"][0]).upper()
                for item in error.errors(
                    include_input=False, include_context=False, include_url=False
                )
                if item["loc"] and item["loc"][0] in Settings.model_fields
            }
        )
        names = ", ".join(fields) if fields else "configuration"
        raise SystemExit(
            f"Invalid or missing settings: {names}. "
            "Compare with .env.example; no values are displayed."
        ) from None

    database = Database(settings)
    try:
        if args.preflight:
            await database.preflight_migration()
        else:
            await database.migrate()
    except DatabaseError as error:
        action = "Migration preflight failed" if args.preflight else "Migration failed"
        raise SystemExit(f"{action}: {error}") from None
    if args.preflight:
        print("PostgreSQL migration preflight passed.")
    else:
        print(f"PostgreSQL schema version {SCHEMA_VERSION} ready.")


if __name__ == "__main__":
    asyncio.run(_main())
