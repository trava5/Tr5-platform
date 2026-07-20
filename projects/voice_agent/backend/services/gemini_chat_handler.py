"""Gemini generate_content handler: connects real Gemini responses to AgentRuntime."""

from __future__ import annotations

from pathlib import Path

from google import genai
from google.genai import types

from actions.action_loader import load_action_function
from backend.schemas import MessageRequest
from profiles.profile_loader import Profile

MAX_TOOL_ROUND_TRIPS = 5


def build_generation_config(profile: Profile) -> types.GenerateContentConfig:
    function_declarations = [
        types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
        )
        for tool in profile.tools.values()
    ]
    return types.GenerateContentConfig(
        system_instruction=profile.prompt,
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


async def handle_message(
    client: genai.Client,
    model: str,
    request: MessageRequest,
    profile: Profile,
) -> str:
    config = build_generation_config(profile)
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=request.text)]),
    ]

    for _ in range(MAX_TOOL_ROUND_TRIPS):
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        function_calls = _extract_function_calls(response)
        if not function_calls:
            return _extract_text(response).strip()

        contents.append(response.candidates[0].content)
        contents.append(
            types.Content(
                role="user",
                parts=[execute_tool(call, profile) for call in function_calls],
            )
        )

    return "Agent prekrocil maximalni pocet volani nastroju pro jednu zpravu."


class GeminiChatHandler:
    """Thin adapter matching AgentRuntime's LiveMessageHandler signature."""

    def __init__(self, client: genai.Client, model: str, profile: Profile) -> None:
        self._client = client
        self._model = model
        self._profile = profile

    async def __call__(self, request: MessageRequest) -> str:
        return await handle_message(self._client, self._model, request, self._profile)


def build_handler(api_key: str, model: str, profiles_root: Path) -> GeminiChatHandler:
    from actions.tool_catalog import TOOL_CATALOG
    from profiles.profile_loader import load_profile

    profile = load_profile("000_base", profiles_root, TOOL_CATALOG)
    client = genai.Client(api_key=api_key)
    return GeminiChatHandler(client, model, profile)
