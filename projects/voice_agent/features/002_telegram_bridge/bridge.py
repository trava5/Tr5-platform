"""Telegram Bot API bridge for JARVIS runtime communication."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import requests


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DOWNLOAD_DIR = BASE_DIR / "runtime" / "telegram"

TextHandler = Callable[[str, int], str]
VoiceHandler = Callable[[Path, int, dict], str]
LogHandler = Callable[[str], None]


class TelegramBridgeError(RuntimeError):
    """Expected Telegram bridge setup/runtime error."""


@dataclass(frozen=True)
class TelegramBridgeConfig:
    bot_token: str
    allowed_chat_ids: frozenset[int]
    enabled: bool = False
    poll_timeout: int = 25
    request_timeout: int = 35
    download_dir: Path = DEFAULT_DOWNLOAD_DIR


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled", "ano"}


def parse_allowed_chat_ids(raw_value: str | Iterable[int] | None) -> frozenset[int]:
    if raw_value is None:
        return frozenset()
    if not isinstance(raw_value, str):
        return frozenset(int(value) for value in raw_value)

    values: set[int] = set()
    for item in raw_value.replace(";", ",").split(","):
        stripped = item.strip()
        if not stripped:
            continue
        try:
            values.add(int(stripped))
        except ValueError as exc:
            raise TelegramBridgeError(
                f"TELEGRAM_ALLOWED_CHAT_IDS obsahuje neplatnou hodnotu: {stripped}"
            ) from exc
    return frozenset(values)


def load_config() -> TelegramBridgeConfig:
    token = str(os.getenv("TELEGRAM_BOT_TOKEN", "") or "").strip()
    allowed_ids = parse_allowed_chat_ids(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", ""))
    enabled = _parse_bool(os.getenv("TELEGRAM_BRIDGE_ENABLED"), default=bool(token))
    download_dir = Path(os.getenv("TELEGRAM_DOWNLOAD_DIR", str(DEFAULT_DOWNLOAD_DIR)))
    return TelegramBridgeConfig(
        bot_token=token,
        allowed_chat_ids=allowed_ids,
        enabled=enabled,
        download_dir=download_dir,
    )


def is_configured(config: TelegramBridgeConfig | None = None) -> bool:
    selected = config or load_config()
    return bool(selected.enabled and selected.bot_token and selected.allowed_chat_ids)


class TelegramBotBridge:
    def __init__(
        self,
        config: TelegramBridgeConfig,
        on_text: TextHandler,
        on_voice: VoiceHandler | None = None,
        logger: LogHandler | None = None,
    ) -> None:
        self.config = config
        self.on_text = on_text
        self.on_voice = on_voice
        self.logger = logger or (lambda message: None)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset = 0
        self._api_base = f"https://api.telegram.org/bot{self.config.bot_token}"

    def start(self) -> None:
        if not self.config.bot_token:
            raise TelegramBridgeError("Chybí TELEGRAM_BOT_TOKEN.")
        if not self.config.allowed_chat_ids:
            raise TelegramBridgeError("Chybí TELEGRAM_ALLOWED_CHAT_IDS.")
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="TelegramBridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        self.logger("Telegram bridge spuštěn.")
        while not self._stop_event.is_set():
            try:
                updates = self._get_updates()
                for update in updates:
                    self._offset = max(self._offset, int(update.get("update_id", 0)) + 1)
                    self._handle_update(update)
            except Exception as exc:
                self.logger(f"Telegram bridge: {exc}")
                time.sleep(3)

    def _request(self, method: str, **params):
        response = requests.post(
            f"{self._api_base}/{method}",
            data=params,
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise TelegramBridgeError(str(payload.get("description", "Telegram API chyba.")))
        return payload.get("result")

    def _get_updates(self) -> list[dict]:
        result = self._request(
            "getUpdates",
            offset=self._offset,
            timeout=self.config.poll_timeout,
            allowed_updates='["message"]',
        )
        return list(result or [])

    def _send_message(self, chat_id: int, text: str) -> None:
        chunks = _split_telegram_text(text)
        for chunk in chunks:
            self._request("sendMessage", chat_id=chat_id, text=chunk)

    def _send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        try:
            self._request("sendChatAction", chat_id=chat_id, action=action)
        except Exception:
            pass

    def _get_file_path(self, file_id: str) -> str:
        result = self._request("getFile", file_id=file_id)
        file_path = str((result or {}).get("file_path", "")).strip()
        if not file_path:
            raise TelegramBridgeError("Telegram nevrátil cestu k hlasovému souboru.")
        return file_path

    def _download_file(self, file_path: str, target: Path) -> None:
        url = f"https://api.telegram.org/file/bot{self.config.bot_token}/{file_path}"
        response = requests.get(url, timeout=self.config.request_timeout)
        response.raise_for_status()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)

    def _handle_update(self, update: dict) -> None:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = int(chat.get("id", 0) or 0)
        if chat_id not in self.config.allowed_chat_ids:
            if chat_id:
                text = str(message.get("text", "") or "").strip()
                command = text.split(maxsplit=1)[0].lower() if text else ""
                if command in {"/start", "/help", "/id", "/chatid", "/chat_id"}:
                    self._send_message(
                        chat_id,
                        f"ID tohoto chatu je {chat_id}. Tento chat zatím nemá povolený přístup k JARVIS.",
                    )
                else:
                    self._send_message(chat_id, "Tento chat nemá povolený přístup k JARVIS.")
            return

        if message.get("text"):
            text = str(message["text"]).strip()
            command_reply = self._handle_command(text, chat_id)
            if command_reply:
                self._send_message(chat_id, command_reply)
                return
            self._send_chat_action(chat_id)
            reply = self.on_text(text, chat_id)
            self._send_message(chat_id, reply or "Bez odpovědi.")
            return

        if message.get("voice"):
            self._handle_voice(chat_id, message)
            return

        self._send_message(chat_id, "Umím zpracovat textové a hlasové zprávy.")

    @staticmethod
    def _handle_command(text: str, chat_id: int) -> str | None:
        command = str(text or "").strip().split(maxsplit=1)[0].lower()
        if command in {"/start", "/help"}:
            return (
                "JARVIS Telegram bridge je aktivní.\n"
                "Pošli textovou zprávu nebo hlasovou zprávu.\n"
                f"ID tohoto chatu je {chat_id}."
            )
        if command in {"/id", "/chatid", "/chat_id"}:
            return f"ID tohoto chatu je {chat_id}."
        return None

    def _handle_voice(self, chat_id: int, message: dict) -> None:
        if not self.on_voice:
            self._send_message(
                chat_id,
                "Hlasová zpráva dorazila, ale přepis hlasu zatím není zapojený.",
            )
            return

        voice = message.get("voice") or {}
        file_id = str(voice.get("file_id", "")).strip()
        if not file_id:
            self._send_message(chat_id, "Telegram neposlal identifikátor hlasové zprávy.")
            return

        self._send_chat_action(chat_id, "typing")
        file_path = self._get_file_path(file_id)
        suffix = Path(file_path).suffix or ".oga"
        target = self.config.download_dir / f"{file_id}{suffix}"
        self._download_file(file_path, target)
        self._send_chat_action(chat_id, "typing")
        reply = self.on_voice(target, chat_id, voice)
        self._send_message(chat_id, reply or "Hlasová zpráva byla přijata.")


def _split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    clean = str(text or "").strip()
    if not clean:
        return [""]
    return [clean[index:index + limit] for index in range(0, len(clean), limit)]
