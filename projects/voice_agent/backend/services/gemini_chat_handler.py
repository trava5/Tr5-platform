"""Gemini generate_content handler: connects real Gemini responses to AgentRuntime."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from actions.action_loader import load_action_function
from backend.schemas import MessageRequest, ShortTermMemoryItem
from backend.services.memory import MemoryRepository
from profiles.profile_loader import Profile

MAX_TOOL_ROUND_TRIPS = 5
MEMORY_RECENT_TURNS_LIMIT = 20


def _current_time_context() -> str:
    """Aktuální datum a čas, vkládá se čerstvě do každé zprávy.

    Bez tohoto bloku model nemá žádný způsob, jak převést relativní čas
    ("zítra v 15:00") na skutečné ISO datum — stejný vzor jako
    main.py's `_build_config` (`[AKTUÁLNÍ ČAS]`), ale počítaný per-message,
    ne jednou při připojení, protože zde neexistuje trvalá relace.
    """
    tz = ZoneInfo(os.getenv("JARVIS_TIMEZONE", "Europe/Prague"))
    now = datetime.now(tz)
    return f"[AKTUÁLNÍ ČAS]\n{now.strftime('%d.%m.%Y — %H:%M')}"


def build_generation_config(profile: Profile) -> types.GenerateContentConfig:
    function_declarations = [
        types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
        )
        for tool in profile.tools.values()
    ]
    system_instruction = f"{_current_time_context()}\n\n{profile.prompt}"
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[types.Tool(function_declarations=function_declarations)],
    )


def execute_tool(function_call: types.FunctionCall, profile: Profile) -> types.Part:
    name = function_call.name
    tool = profile.tools.get(name)
    if tool is None:
        return types.Part.from_function_response(
            name=name,
            response={"error": f"Neznamy nastroj '{name}'."},
        )
    try:
        function = load_action_function(tool["module"], tool["function"])
        result = function(**dict(function_call.args or {}))
    except Exception as exc:
        return types.Part.from_function_response(
            name=name,
            response={"error": f"Nastroj '{name}' selhal: {exc}"},
        )
    return types.Part.from_function_response(name=name, response={"result": result})


def _extract_function_calls(response: types.GenerateContentResponse) -> list[types.FunctionCall]:
    candidates = response.candidates or []
    if not candidates or not candidates[0].content or not candidates[0].content.parts:
        return []
    return [part.function_call for part in candidates[0].content.parts if part.function_call]


def _extract_text(response: types.GenerateContentResponse) -> str:
    candidates = response.candidates or []
    if not candidates or not candidates[0].content or not candidates[0].content.parts:
        return ""
    return "".join(part.text for part in candidates[0].content.parts if part.text)


def _content_from_memory_item(item: ShortTermMemoryItem) -> types.Content:
    role = "model" if item.role == "assistant" else "user"
    return types.Content(role=role, parts=[types.Part(text=item.content)])


async def handle_message(
    client: genai.Client,
    model: str,
    request: MessageRequest,
    conversation_id: str,
    profile: Profile,
    memory: MemoryRepository,
) -> str:
    config = build_generation_config(profile)
    history = await memory.recent_short_term_turns(
        limit=MEMORY_RECENT_TURNS_LIMIT,
        session_id=conversation_id,
    )
    contents: list[types.Content] = [_content_from_memory_item(item) for item in history]
    contents.append(types.Content(role="user", parts=[types.Part(text=request.text)]))

    final_text = ""
    for _ in range(MAX_TOOL_ROUND_TRIPS):
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        function_calls = _extract_function_calls(response)
        if not function_calls:
            final_text = _extract_text(response).strip()
            break

        contents.append(response.candidates[0].content)
        contents.append(
            types.Content(
                role="user",
                parts=[execute_tool(call, profile) for call in function_calls],
            )
        )
    else:
        final_text = "Agent prekrocil maximalni pocet volani nastroju pro jednu zpravu."

    await memory.save_short_term_turn(role="user", content=request.text, session_id=conversation_id)
    await memory.save_short_term_turn(role="assistant", content=final_text, session_id=conversation_id)
    return final_text


class GeminiChatHandler:
    """Thin adapter matching AgentRuntime's LiveMessageHandler signature."""

    def __init__(
        self,
        client: genai.Client,
        model: str,
        profile: Profile,
        memory: MemoryRepository,
    ) -> None:
        self._client = client
        self._model = model
        self._profile = profile
        self._memory = memory

    async def __call__(self, request: MessageRequest, conversation_id: str) -> str:
        return await handle_message(
            self._client,
            self._model,
            request,
            conversation_id,
            self._profile,
            self._memory,
        )


def build_handler(
    api_key: str,
    model: str,
    profiles_root: Path,
    memory: MemoryRepository,
) -> GeminiChatHandler:
    from actions.tool_catalog import TOOL_CATALOG
    from profiles.profile_loader import load_profile

    profile = load_profile("000_base", profiles_root, TOOL_CATALOG)
    client = genai.Client(api_key=api_key)
    return GeminiChatHandler(client, model, profile, memory)
