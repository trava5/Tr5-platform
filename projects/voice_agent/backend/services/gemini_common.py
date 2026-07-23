"""Shared Gemini helpers: tool execution, time context, tool-declaration building.

Used by both gemini_chat_handler.py (generate_content) and
gemini_live_audio_handler.py (Live API), so tool-execution logic has one
implementation, not two separately maintained copies.
"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from google.genai import types

from actions.action_loader import load_action_function
from profiles.profile_loader import Profile


def current_time_context() -> str:
    """Aktuální datum a čas, vkládá se čerstvě do každé zprávy.

    Bez tohoto bloku model nemá žádný způsob, jak převést relativní čas
    ("zítra v 15:00") na skutečné ISO datum — stejný vzor jako
    main.py's `_build_config` (`[AKTUÁLNÍ ČAS]`), ale počítaný per-message
    nebo per-relaci, ne jednou globálně, protoze zde neexistuje trvala
    sdilena relace mezi zpravami.
    """
    tz = ZoneInfo(os.getenv("JARVIS_TIMEZONE", "Europe/Prague"))
    now = datetime.now(tz)
    return f"[AKTUÁLNÍ ČAS]\n{now.strftime('%d.%m.%Y — %H:%M')}"


def build_system_instruction(profile: Profile) -> str:
    return f"{current_time_context()}\n\n{profile.prompt}"


def build_tools(profile: Profile) -> list[types.Tool]:
    function_declarations = [
        types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
        )
        for tool in profile.tools.values()
    ]
    return [types.Tool(function_declarations=function_declarations)]


def _invoke_tool(function_call: types.FunctionCall, profile: Profile) -> dict:
    name = function_call.name
    tool = profile.tools.get(name)
    if tool is None:
        return {"error": f"Neznamy nastroj '{name}'."}
    try:
        function = load_action_function(tool["module"], tool["function"])
        result = function(**dict(function_call.args or {}))
    except Exception as exc:
        return {"error": f"Nastroj '{name}' selhal: {exc}"}
    return {"result": result}


def execute_tool(function_call: types.FunctionCall, profile: Profile) -> types.Part:
    return types.Part.from_function_response(
        name=function_call.name,
        response=_invoke_tool(function_call, profile),
    )


def execute_tool_live(function_call: types.FunctionCall, profile: Profile) -> types.FunctionResponse:
    return types.FunctionResponse(
        id=function_call.id,
        name=function_call.name,
        response=_invoke_tool(function_call, profile),
    )
