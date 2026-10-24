"""Run a bounded TwitchIO close diagnostic in a disposable production-image container.

Copy this script and app/infrastructure/twitch_websocket.py to the SSH host.
Run: python3 /tmp/diagnose_twitch_websocket.py --docker
Only --docker is intended for manual use. --inside is called by that launcher.
No application settings, tokens, production volumes or external services are used.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import signal
import subprocess
import sys
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import cast

EXPECTED_VERSIONS = {"twitchio": "3.3.2", "aiohttp": "3.14.5"}
CYCLES_PER_MODE = 5


class FictionalClient:
    def dispatch(self, event: str, payload: object) -> None:
        # Do not retain payloads or start real conduit reassociation.
        pass


def run_docker() -> int:
    source_path = Path(__file__).resolve()
    compatibility_path = (
        source_path.parent.parent / "app" / "infrastructure" / "twitch_websocket.py"
        if source_path.parent.name == "scripts"
        else source_path.with_name("twitch_websocket.py")
    )
    if not compatibility_path.is_file():
        raise RuntimeError("Copier aussi twitch_websocket.py a cote du script.")
    compatibility_source = compatibility_path.read_text(encoding="utf-8")
    source = source_path.read_text(encoding="utf-8")
    # Compile each source separately so its future imports stay valid. The shim
    # comes from the application file, not a second diagnostic implementation.
    payload = (
        f"_TWITCH_WEBSOCKET_COMPAT_SOURCE = {compatibility_source!r}\n"
        f"exec(compile({source!r}, '<diagnostic>', 'exec'))\n"
    ).encode("utf-8")
    image = subprocess.run(
        ["sudo", "docker", "inspect", "--format", "{{.Image}}", "overlays-app"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
        timeout=10,
    ).stdout.strip()
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None:
        raise RuntimeError("Identifiant d'image inattendu ; aucun conteneur lance.")

    name = f"overlays-ram-diag-{uuid.uuid4().hex}"
    command = [
        "sudo", "docker", "run", "--rm", "-i", "--name", name,
        "--pull", "never", "--network", "none", "--read-only",
        "--memory", "256m", "--memory-swap", "256m", "--cpus", "0.5",
        "--pids-limit", "64", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges=true",
        "--entrypoint", "python", image, "-B", "-", "--inside",
    ]
    print(f"Conteneur temporaire : {name}\nImage : {image}", flush=True)
    try:
        return subprocess.run(command, input=payload, timeout=60).returncode
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        print("Diagnostic interrompu ; suppression du conteneur temporaire.", flush=True)
        subprocess.run(
            ["sudo", "docker", "rm", "--force", name], check=False, timeout=10
        )
        return 124 if isinstance(error, subprocess.TimeoutExpired) else 130


async def experiment() -> None:
    # Deferred imports keep the SSH launcher dependent on the standard library only.
    from aiohttp import web
    from twitchio.authentication.tokens import ManagedHTTPClient
    from twitchio.client import Client
    from twitchio.eventsub.websockets import Websocket

    versions = {package: version(package) for package in EXPECTED_VERSIONS}
    print("Python :", sys.version.split()[0], flush=True)
    print("Versions :", json.dumps(versions), flush=True)
    if versions != EXPECTED_VERSIONS:
        raise RuntimeError("Versions inattendues ; experience annulee.")
    compatibility_source = globals().get("_TWITCH_WEBSOCKET_COMPAT_SOURCE")
    if not isinstance(compatibility_source, str):
        raise RuntimeError("Source du correctif absente ; utiliser --docker.")
    compatibility_namespace: dict[str, object] = {
        "__name__": "overlays_twitch_websocket_compat"
    }
    exec(
        compile(compatibility_source, "<twitch_websocket_compat>", "exec"),
        compatibility_namespace,
    )
    install_fix = cast(
        Callable[[], None], compatibility_namespace["install_twitchio_keepalive_close_fix"]
    )
    original_close = Websocket.close

    active: set[web.WebSocketResponse] = set()
    welcome = {
        "metadata": {"message_type": "session_welcome"},
        "payload": {"session": {
            "id": "session-fictive", "status": "connected",
            "connected_at": "2026-01-01T00:00:00Z",
            "keepalive_timeout_seconds": 10, "reconnect_url": None,
        }},
    }

    async def handler(request: web.Request) -> web.WebSocketResponse:
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        active.add(socket)
        try:
            await socket.send_json(welcome)
            async for _ in socket:
                pass
        finally:
            active.discard(socket)
            await socket.close()
        return socket

    app = web.Application()
    app.router.add_get("/ws", handler)
    runner = web.AppRunner(app, shutdown_timeout=1)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        server = site._server
        assert server is not None and server.sockets
        port = server.sockets[0].getsockname()[1]
        for mode in ("actuel", "corrige"):
            if mode == "corrige":
                install_fix()
            counts = dict(
                cycles=0, nettoyage_incomplet=0, websocket_ouvert=0,
                tcp_ouvert=0, serveur_ouvert=0, listener_en_cours=0,
            )
            for _ in range(CYCLES_PER_MODE):
                # Private internals are intentional and pinned to the versions above.
                wrapper = Websocket(
                    client=cast(Client, FictionalClient()),
                    http=cast(ManagedHTTPClient, object()),
                    shard_id="0",
                )
                await wrapper.connect(url=f"ws://127.0.0.1:{port}/ws", fail_once=True)
                socket = wrapper._socket
                listener = wrapper._listen_task
                keepalive = wrapper._keep_alive_task
                assert socket is not None and listener is not None and keepalive is not None
                connection = socket._response.connection
                assert connection is not None, "Transport TCP inaccessible."
                connector = connection._connector
                transport = connection.transport
                tasks = (listener, keepalive)
                try:
                    wrapper._keep_alive_timeout = 1
                    wrapper._last_keepalive = datetime.now() - timedelta(seconds=60)
                    result = (await asyncio.wait_for(
                        asyncio.gather(keepalive, return_exceptions=True), 3
                    ))[0]
                    if isinstance(result, BaseException) and not isinstance(
                        result, asyncio.CancelledError
                    ):
                        raise RuntimeError("Echec inattendu du keepalive.") from result
                    await asyncio.sleep(0.05)
                    counts["cycles"] += 1
                    counts["nettoyage_incomplet"] += int(
                        wrapper._closing or any(item is not None for item in (
                            wrapper._socket, wrapper._keep_alive_task, wrapper._listen_task
                        ))
                    )
                    counts["websocket_ouvert"] += int(not socket.closed)
                    counts["tcp_ouvert"] += int(
                        transport is not None and not transport.is_closing()
                    )
                    counts["serveur_ouvert"] += len(active)
                    counts["listener_en_cours"] += int(not listener.done())
                finally:
                    # Measure first, then tear down both baseline and fixed cases.
                    # This manual teardown is not the application workaround.
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    async with asyncio.timeout(2):
                        await socket.close()
                        await connector.close()
                    await asyncio.sleep(0.05)
            print(mode + " : " + json.dumps(counts), flush=True)
            expected_open = CYCLES_PER_MODE if mode == "actuel" else 0
            for key in (
                "nettoyage_incomplet", "websocket_ouvert", "tcp_ouvert", "serveur_ouvert"
            ):
                if counts[key] != expected_open:
                    raise RuntimeError(f"Resultat inattendu pour {mode}: {key}.")
            if counts["listener_en_cours"] != 0:
                raise RuntimeError(f"Listener encore actif pour {mode}.")
        print("Connexions serveur restantes apres nettoyage :", len(active), flush=True)
        if active:
            raise RuntimeError("Connexions serveur restantes apres nettoyage.")
    finally:
        Websocket.close = original_close
        for server_socket in list(active):
            await server_socket.close()
        await runner.cleanup()
    pending = [
        task for task in asyncio.all_tasks()
        if task is not asyncio.current_task() and not task.done()
    ]
    print("Taches restantes apres demontage :", len(pending), flush=True)
    if pending:
        raise RuntimeError("Taches restantes apres demontage.")
    print("Comparaison avant/apres reussie.", flush=True)
    print("Ce controle ne mesure ni TLS, ni la RAM retenue, ni les reconnexions AutoBot.", flush=True)


async def bounded_experiment() -> None:
    async with asyncio.timeout(45):
        await experiment()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--docker", action="store_true", help="Lancer le conteneur jetable depuis SSH."
    )
    modes.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.docker:
        return run_docker()
    signal.alarm(50)
    logging.disable(logging.CRITICAL)
    asyncio.run(bounded_experiment())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
