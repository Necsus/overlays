from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class AdminFramingProtection:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        root_path = scope.get("root_path", "").rstrip("/")
        if root_path and (path == root_path or path.startswith(root_path + "/")):
            path = path[len(root_path):] or "/"
        is_admin_document = scope["type"] == "http" and (
            path in {"/admin", "/static"}
            or path.startswith(("/admin/", "/static/"))
        )
        if not is_admin_document:
            await self._app(scope, receive, send)
            return

        async def protected_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message.setdefault("headers", []))
                # An additional CSP composes with existing policies instead of replacing them.
                headers.append("Content-Security-Policy", "frame-ancestors 'none'")
                headers["X-Frame-Options"] = "DENY"
            await send(message)

        await self._app(scope, receive, protected_send)
