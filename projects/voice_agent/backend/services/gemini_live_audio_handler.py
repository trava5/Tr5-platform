"""Gemini Live API audio handler: bridges a WebSocket to a Gemini Live session.

Backend plumbing only (Phase 4b-1) — the backend holds the Live session
(Variant A); a client only streams raw mic-shaped audio in and plays audio
out, never talking to Gemini directly. No memory, no desktop client, one
hardcoded profile (see IMPLEMENTATION_CONTRACT_0008).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from backend.services.gemini_common import build_system_instruction, build_tools, execute_tool_live
from profiles.profile_loader import Profile

AUDIO_INPUT_MIME_TYPE = "audio/pcm;rate=16000"


def build_live_config(profile: Profile) -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        system_instruction=build_system_instruction(profile),
        tools=build_tools(profile),
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )


async def _forward_client_audio(websocket: WebSocket, session) -> None:
    try:
        while True:
            data = await websocket.receive_bytes()
            await session.send_realtime_input(
                audio=types.Blob(data=data, mime_type=AUDIO_INPUT_MIME_TYPE)
            )
    except WebSocketDisconnect:
        return


async def _forward_live_events(websocket: WebSocket, session, profile: Profile) -> None:
    async for message in session.receive():
        if message.tool_call and message.tool_call.function_calls:
            responses = [
                execute_tool_live(call, profile) for call in message.tool_call.function_calls
            ]
            await session.send_tool_response(function_responses=responses)
            continue

        content = message.server_content
        if content is None:
            continue

        if content.model_turn and content.model_turn.parts:
            for part in content.model_turn.parts:
                if part.inline_data and part.inline_data.data:
                    await websocket.send_bytes(part.inline_data.data)

        if content.input_transcription and content.input_transcription.text:
            await websocket.send_json({
                "type": "transcript",
                "role": "user",
                "text": content.input_transcription.text,
            })
        if content.output_transcription and content.output_transcription.text:
            await websocket.send_json({
                "type": "transcript",
                "role": "assistant",
                "text": content.output_transcription.text,
            })
        if content.turn_complete:
            await websocket.send_json({"type": "turn_complete"})


class GeminiLiveAudioHandler:
    """Opens one Gemini Live session per WebSocket connection."""

    def __init__(self, client: genai.Client, model: str, profile: Profile) -> None:
        self._client = client
        self._model = model
        self._profile = profile

    async def handle_connection(self, websocket: WebSocket) -> None:
        config = build_live_config(self._profile)
        async with self._client.aio.live.connect(model=self._model, config=config) as session:
            client_task = asyncio.create_task(_forward_client_audio(websocket, session))
            live_task = asyncio.create_task(_forward_live_events(websocket, session, self._profile))
            try:
                done, pending = await asyncio.wait(
                    {client_task, live_task}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    task.result()
            except WebSocketDisconnect:
                pass
            finally:
                for task in (client_task, live_task):
                    if not task.done():
                        task.cancel()


def build_handler(api_key: str, model: str, profiles_root: Path) -> GeminiLiveAudioHandler:
    from actions.tool_catalog import TOOL_CATALOG
    from profiles.profile_loader import load_profile

    profile = load_profile("000_base", profiles_root, TOOL_CATALOG)
    client = genai.Client(api_key=api_key)
    return GeminiLiveAudioHandler(client, model, profile)
