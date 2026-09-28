import asyncio
import logging

from twitchio import ChatMessage, authentication, eventsub
from twitchio.ext import commands
from typing_extensions import override

from app.application.commands import ChatUser, GiveawayCommandHandler
from app.core.configuration import ApplicationConfiguration
from app.core.environment import Settings
from app.infrastructure.twitch_oauth import BOT_SCOPE_NAMES, TwitchAuthorization

LOGGER = logging.getLogger("uvicorn.error")
BOT_SCOPES = authentication.Scopes(BOT_SCOPE_NAMES)


class GiveawayTwitchBot(commands.AutoBot):
    def __init__(
        self,
        settings: Settings,
        configuration: ApplicationConfiguration,
        command_handlers: dict[str, GiveawayCommandHandler],
    ) -> None:
        self._handlers = dict(command_handlers)
        self._subscription_lock = asyncio.Lock()
        self._chat_subscription_ids: dict[str, str] = {}
        super().__init__(
            client_id=settings.twitch_client_id,
            client_secret=settings.twitch_client_secret.get_secret_value(),
            bot_id=configuration.twitch.bot_id,
            owner_id=configuration.twitch.owner_id,
            prefix=configuration.commands.prefix,
            scopes=BOT_SCOPES,
            subscriptions=[],
        )

    def chat_subscription_ready_for(self, streamer_id: str) -> bool:
        return (
            streamer_id in self._handlers
            and streamer_id in self._chat_subscription_ids
        )

    async def authorize_bot(self, authorization: TwitchAuthorization) -> None:
        if authorization.twitch_user_id != self.bot_id:
            raise ValueError("The Twitch authorization does not belong to the bot")
        if not BOT_SCOPE_NAMES.issubset(authorization.scopes):
            raise ValueError("The Twitch bot authorization is missing a required scope")
        validated_token = await self.add_token(
            authorization.access_token, authorization.refresh_token
        )
        if validated_token.user_id != self.bot_id:
            if validated_token.user_id is not None:
                _ = await self.remove_token(validated_token.user_id)
            raise ValueError("The added Twitch token does not belong to the bot")
        await self.save_tokens()
        LOGGER.info("Twitch bot authorization saved: bot_id=%s", self.bot_id)

    async def subscribe_to_streamer(
        self,
        authorization: TwitchAuthorization,
        handler: GiveawayCommandHandler,
    ) -> None:
        validated_token = await self.add_token(
            authorization.access_token, authorization.refresh_token
        )
        if validated_token.user_id != authorization.twitch_user_id:
            if validated_token.user_id is not None:
                _ = await self.remove_token(validated_token.user_id)
            raise ValueError("The added Twitch token does not match the streamer identity")

        streamer_id = authorization.twitch_user_id
        async with self._subscription_lock:
            self._handlers[streamer_id] = handler
            existing_id = await self._reconcile_chat_subscription(streamer_id)
            if existing_id is not None:
                self._chat_subscription_ids[streamer_id] = existing_id
                return
            result = await self.multi_subscribe(
                [eventsub.ChatMessageSubscription(
                    broadcaster_user_id=streamer_id, user_id=self.bot_id
                )],
                wait=True,
                stop_on_error=True,
            )
            if len(result.success) != 1:
                raise RuntimeError("Twitch did not create the chat subscription")
            response_data = result.success[0].response["data"]
            if len(response_data) != 1 or not response_data[0]["id"]:
                raise RuntimeError("Twitch returned an invalid subscription response")
            self._chat_subscription_ids[streamer_id] = response_data[0]["id"]

    @override
    async def event_subscription_revoked(self, payload: object) -> None:
        if getattr(payload, "type", None) != "channel.chat.message":
            return
        subscription_id = getattr(payload, "id", None)
        for streamer_id, active_subscription_id in list(self._chat_subscription_ids.items()):
            if active_subscription_id == subscription_id:
                self._chat_subscription_ids.pop(streamer_id, None)
                self._handlers.pop(streamer_id, None)
                LOGGER.warning(
                    "Twitch chat authorization revoked: streamer_id=%s",
                    streamer_id,
                )
                return

    @override
    async def event_message(self, payload: ChatMessage) -> None:
        handler = self._handlers.get(payload.broadcaster.id)
        if handler is None:
            LOGGER.debug(
                "Ignoring Twitch message without a streamer context: broadcaster_id=%s",
                payload.broadcaster.id,
            )
            return
        login = payload.chatter.name or payload.chatter.id
        author = ChatUser(
            twitch_user_id=payload.chatter.id,
            login=login,
            display_name=payload.chatter.display_name or login,
        )
        _ = await handler.handle(payload.text, author)

    async def _reconcile_chat_subscription(self, broadcaster_id: str) -> str | None:
        conduit = self.conduit_info.conduit
        if conduit is None:
            raise RuntimeError("No Twitch conduit is available")
        result = await self.fetch_eventsub_subscriptions(conduit_id=conduit.id)
        matching_id: str | None = None
        stale_ids: list[str] = []
        async for subscription in result.subscriptions:
            if (
                subscription.status != "enabled"
                or subscription.type != "channel.chat.message"
                or subscription.condition.get("user_id") != self.bot_id
                or subscription.condition.get("broadcaster_user_id") != broadcaster_id
            ):
                continue
            if matching_id is None:
                matching_id = subscription.id
            else:
                stale_ids.append(subscription.id)
        for subscription_id in stale_ids:
            await self.delete_eventsub_subscription(subscription_id)
        if stale_ids:
            LOGGER.info(
                "Removed duplicate Twitch chat subscriptions: broadcaster_id=%s count=%d",
                broadcaster_id, len(stale_ids),
            )
        return matching_id

    @override
    async def setup_hook(self) -> None:
        await super().setup_hook()
        if not self._handlers:
            return
        if self.conduit_info.conduit is None:
            LOGGER.warning("Unable to restore Twitch chat: no conduit available")
            return
        for broadcaster_id in list(self._handlers):
            try:
                existing_id = await self._reconcile_chat_subscription(broadcaster_id)
                if existing_id is not None:
                    self._chat_subscription_ids[broadcaster_id] = existing_id
                    continue
                result = await self.multi_subscribe(
                    [eventsub.ChatMessageSubscription(
                        broadcaster_user_id=broadcaster_id, user_id=self.bot_id
                    )],
                    wait=True,
                    stop_on_error=False,
                )
                if len(result.success) == 1:
                    response_data = result.success[0].response["data"]
                    if len(response_data) == 1 and response_data[0]["id"]:
                        self._chat_subscription_ids[broadcaster_id] = response_data[0]["id"]
                        continue
                LOGGER.warning(
                    "Unable to restore Twitch chat: broadcaster_id=%s errors=%d",
                    broadcaster_id, len(result.errors),
                )
            except Exception as error:
                LOGGER.warning(
                    "Unable to restore Twitch chat: broadcaster_id=%s error=%s",
                    broadcaster_id, type(error).__name__,
                )
