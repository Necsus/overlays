const OVERLAY_IDLE_CLOSE_CODE = 4000;

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const token = window.location.hash.slice(1);

  if (!token) {
    return;
  }

  const websocket = new WebSocket(
    `${protocol}//${window.location.host}/plugins/giveaway/ws`,
  );

  websocket.addEventListener("open", () => {
    websocket.send(JSON.stringify({
      type: "overlay.authenticate",
      token,
    }));
  });

  websocket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "giveaway.state") {
      renderGiveaway(message.data);
    }
  });

  websocket.addEventListener("close", (event) => {
    // Idle expiry requires refreshing the OBS source, not an automatic retry.
    if (event.code === 1008 || event.code === OVERLAY_IDLE_CLOSE_CODE) {
      clearGiveaway();
      return;
    }
    window.setTimeout(connectWebSocket, 1000);
  });

  websocket.addEventListener("error", () => {
    websocket.close();
  });
}

window.setInterval(renderCountdown, 250);
connectWebSocket();
