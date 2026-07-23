"""Console client: microphone capture and playback against /api/v1/live/audio.

Plain streaming client, no GUI, no activation gating (Phase 4b-2). Streams
continuously while running; stop with Ctrl+C. See
IMPLEMENTATION_CONTRACT_0009 for scope and the concurrent send/receive
thread-safety rationale.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import pyaudio
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
DEFAULT_API_PREFIX = "/api/v1"


@dataclass(frozen=True)
class LiveAudioClientConfig:
    live_audio_url: str


def _default_base_url() -> str:
    explicit = (
        os.getenv("JARVIS_BACKEND_BASE_URL") or os.getenv("JARVIS_BACKEND_URL") or ""
    ).strip()
    if explicit:
        return explicit.rstrip("/")
    host = os.getenv("JARVIS_BACKEND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = os.getenv("JARVIS_BACKEND_PORT", "8000").strip() or "8000"
    return f"http://{host}:{port}"


def _normalize_api_prefix(value: str | None) -> str:
    raw = str(value or DEFAULT_API_PREFIX).strip() or DEFAULT_API_PREFIX
    return raw if raw.startswith("/") else f"/{raw}"


def _default_live_audio_url(base_url: str, api_prefix: str) -> str:
    explicit = (os.getenv("JARVIS_BACKEND_LIVE_AUDIO_URL") or "").strip()
    if explicit:
        return explicit
    parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
    scheme = "wss" if parsed.scheme == "https" else "ws"
    path = f"{api_prefix.rstrip('/')}/live/audio"
    return urlunparse((scheme, parsed.netloc, path, "", "", ""))


def load_config() -> LiveAudioClientConfig:
    base_url = _default_base_url()
    api_prefix = _normalize_api_prefix(os.getenv("JARVIS_BACKEND_API_PREFIX"))
    return LiveAudioClientConfig(
        live_audio_url=_default_live_audio_url(base_url, api_prefix),
    )


def _send_microphone_audio(websocket, stop: threading.Event) -> None:
    """Runs on its own thread; only ever calls send() on this connection."""
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )
    try:
        while not stop.is_set():
            chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            websocket.send(chunk)
    except ConnectionClosed:
        pass
    finally:
        stop.set()
        stream.stop_stream()
        stream.close()
        audio.terminate()


def _receive_and_play(websocket, stop: threading.Event) -> bool:
    """Runs on the main thread; only ever calls recv() (via iteration) on
    this connection. Returns True if the server reported runtime_unavailable.
    """
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RECV_SAMPLE_RATE, output=True)
    runtime_unavailable = False
    try:
        for message in websocket:
            if stop.is_set():
                break
            if isinstance(message, bytes):
                stream.write(message)
                continue
            try:
                event = json.loads(message)
            except (TypeError, ValueError):
                continue
            event_type = event.get("type")
            if event_type == "transcript":
                print(f"[{event.get('role', '')}] {event.get('text', '')}")
            elif event_type == "error":
                print(f"Zivy audio runtime neni dostupny: {event.get('detail', '')}")
                runtime_unavailable = True
                break
    except ConnectionClosed:
        pass
    finally:
        stop.set()
        stream.stop_stream()
        stream.close()
        audio.terminate()
    return runtime_unavailable


def run() -> None:
    config = load_config()
    print(f"Pripojuji se na {config.live_audio_url} ...")
    stop = threading.Event()
    try:
        with connect(config.live_audio_url) as websocket:
            send_thread = threading.Thread(
                target=_send_microphone_audio,
                args=(websocket, stop),
                name="LiveAudioMicSender",
                daemon=True,
            )
            send_thread.start()
            runtime_unavailable = _receive_and_play(websocket, stop)
            stop.set()
            send_thread.join(timeout=2)
            if runtime_unavailable:
                sys.exit(1)
    except KeyboardInterrupt:
        stop.set()
        print("Ukonceno uzivatelem (Ctrl+C).")
    except ConnectionClosed as exc:
        stop.set()
        print(f"Spojeni se serverem bylo ukonceno: {exc}")


if __name__ == "__main__":
    run()
