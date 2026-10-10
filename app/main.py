import asyncio
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.application.commands import GiveawayCommandHandler
from app.application.oauth_state import OAuthStateStore
from app.application.service import GiveawayService
from app.application.session import SessionSigner
from app.core.configuration import configuration_from_settings
from app.core.environment import Settings
from app.domain.giveaway import GiveawayEngine
from app.domain.streamer import Streamer
from app.infrastructure.configuration_store import ConfigurationStore
from app.infrastructure.database import Database
from app.infrastructure.history import load_command_prefix, restore_active_giveaway
from app.infrastructure.streamers import load_active_streamers
from app.infrastructure.twitch import GiveawayTwitchBot
from app.infrastructure.twitch_oauth import TwitchOAuthClient
from app.web.access_logging import install_oauth_access_log_filter
from app.web.routes.admin import router as admin_router
from app.web.routes.auth import router as auth_router
from app.web.routes.health import router as health_router
from app.web.routes.home import router as home_router
from app.web.routes.overlay import create_overlay_router
from app.web.websocket import OverlayConnectionManager

STATIC_DIRECTORY = Path(__file__).parent / "web" / "static"
ADMIN_STATIC_DIRECTORY = STATIC_DIRECTORY / "admin"
GIVEAWAY_STATIC_DIRECTORY = STATIC_DIRECTORY / "plugins" / "giveaway"
install_oauth_access_log_filter()
overlay_connections = OverlayConnectionManager()
giveaway_engines: dict[str, GiveawayEngine] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    database = Database(settings)
    await database.check_schema()
    session_signer = SessionSigner(
        secret_key=settings.session_secret.get_secret_value(),
        max_age_seconds=settings.session_max_age_seconds,
    )
    configuration_store = ConfigurationStore(settings.giveaway_config_file)
    configuration = configuration_store.load()
    if configuration is None:
        configuration = configuration_from_settings(settings)
        configuration_store.save(configuration)

    connections = overlay_connections
    engines = giveaway_engines
    engines.clear()
    services: dict[str, GiveawayService] = {}
    handlers: dict[str, GiveawayCommandHandler] = {}

    async def ensure_streamer_context(streamer: Streamer) -> GiveawayCommandHandler:
        streamer_id = streamer.twitch_user_id
        existing = handlers.get(streamer_id)
        if existing is not None:
            return existing
        engine = GiveawayEngine()
        await restore_active_giveaway(database, streamer_id, engine)
        prefix = await load_command_prefix(database, streamer_id)
        service = GiveawayService(streamer_id, engine, database, connections)
        handler = GiveawayCommandHandler(service=service, prefix=prefix)
        handler.set_active_broadcaster(streamer_id)
        engines[streamer_id] = engine
        services[streamer_id] = service
        handlers[streamer_id] = handler
        service.resume_timer()
        return handler

    for streamer in await load_active_streamers(database):
        await ensure_streamer_context(streamer)

    app.state.settings = settings
    app.state.database = database
    app.state.configuration = configuration
    app.state.session_signer = session_signer
    app.state.oauth_state_store = OAuthStateStore()
    app.state.overlay_connections = connections
    app.state.giveaway_engines = engines
    app.state.giveaway_services = services
    app.state.giveaway_command_handlers = handlers
    app.state.ensure_streamer_context = ensure_streamer_context

    twitch_bot: GiveawayTwitchBot | None = None
    twitch_task: asyncio.Task[None] | None = None
    async with AsyncExitStack() as resources:
        twitch_oauth_client = TwitchOAuthClient(
            client_id=settings.twitch_client_id,
            client_secret=settings.twitch_client_secret.get_secret_value(),
            redirect_uri=settings.twitch_admin_redirect_uri,
        )
        resources.push_async_callback(twitch_oauth_client.close)
        app.state.twitch_oauth_client = twitch_oauth_client

        async def close_services() -> None:
            for service in list(services.values()):
                await service.close()

        resources.push_async_callback(close_services)
        if configuration.twitch.enabled:
            twitch_bot = GiveawayTwitchBot(settings, configuration, handlers)
            resources.push_async_callback(twitch_bot.close)
            twitch_task = asyncio.create_task(
                twitch_bot.start(with_adapter=False), name="twitch-bot"
            )
        app.state.twitch_bot = twitch_bot
        try:
            yield
        finally:
            if twitch_task is not None:
                twitch_task.cancel()
                with suppress(asyncio.CancelledError):
                    await twitch_task


app = FastAPI(title="NecsusDevOverlays", lifespan=lifespan)
app.include_router(home_router)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(
    create_overlay_router(
        giveaway_engines,
        overlay_connections,
        GIVEAWAY_STATIC_DIRECTORY,
    )
)
app.mount(
    "/plugins/giveaway/static",
    StaticFiles(directory=GIVEAWAY_STATIC_DIRECTORY),
    name="giveaway-static",
)
app.mount("/static", StaticFiles(directory=ADMIN_STATIC_DIRECTORY), name="static")
