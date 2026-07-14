"""Katalog popisů nástrojů dostupných agentovi."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


TOOL_CATALOG: dict[str, dict[str, Any]] = {
    "open_app": {
        "name": "open_app",
        "module": "actions.003_open_app.open_app",
        "function": "open_app",
        "status": "verified",
        "description": (
            "Otevře aplikaci ve Windows podle názvu, českého aliasu, spustitelného "
            "souboru v PATH nebo podporovaného Windows URI schématu. Použij, když "
            "uživatel chce otevřít aplikaci, nastavení, Průzkumník souborů nebo "
            "běžný systémový nástroj. Spuštění se předává Windows neblokujícím "
            "způsobem v samostatném okně."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": (
                        "Název aplikace nebo alias, například Spotify, Chrome, Terminal, "
                        "Průzkumník souborů, Nastavení nebo Kalendář."
                    ),
                },
            },
            "required": ["app_name"],
        },
        "agent_notes": {
            "use_when": [
                "Uživatel výslovně chce otevřít aplikaci nebo systémové nastavení.",
                "Uživatel chce spustit běžný Windows nástroj, například kalkulačku nebo Průzkumník.",
            ],
            "do_not_use_when": [
                "Uživatel chce najít informace na webu; použij browser_control.",
                "Uživatel chce přehrát konkrétní hudbu nebo video; použij mediální nástroj.",
                "Uživatel chce ověřit, že se aplikace skutečně plně načetla; nástroj umí potvrdit jen předání spuštění systému.",
            ],
            "examples": [
                'Otevři Chrome -> open_app(app_name="Chrome")',
                'Spusť Průzkumník souborů -> open_app(app_name="Průzkumník souborů")',
                'Otevři nastavení -> open_app(app_name="Nastavení")',
            ],
            "verified_on": "2026-06-19",
            "verification": (
                "Ověřena syntaxe, import přes loader, katalogová deklarace, bezpečný "
                "smoke test validace prázdného názvu bez otevírání aplikací a "
                "neblokující sestavení Windows start příkazu."
            ),
        },
    },
    "get_weather": {
        "name": "get_weather",
        "module": "actions.001_weather.weather",
        "function": "get_weather_summary",
        "status": "verified",
        "description": (
            "Shrne aktuální počasí nebo krátkou předpověď pro zadané místo. "
            "Výchozí lokalitou je Praha. Použij, když se uživatel ptá na "
            "aktuální počasí, teplotu, déšť, sníh, vítr, vlhkost nebo "
            "předpověď počasí. Parametry location, mode a days je možné "
            "kombinovat."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": (
                        "Město nebo lokalita. Pokud zůstane prázdná, použije se Praha."
                    ),
                },
                "mode": {
                    "type": "STRING",
                    "description": (
                        "Typ dotazu: current pro aktuální počasí, forecast pro předpověď."
                    ),
                },
                "days": {
                    "type": "NUMBER",
                    "description": (
                        "Počet dnů předpovědi. Používá se jen pro mode=forecast; maximum jsou 3 dny."
                    ),
                },
            },
        },
        "agent_notes": {
            "use_when": [
                "Uživatel chce aktuální počasí v konkrétní lokalitě.",
                "Uživatel se ptá na teplotu, déšť, sníh, vítr nebo vlhkost.",
                "Uživatel chce krátkou předpověď počasí pro konkrétní místo.",
                "Uživatel nezadá místo a dotaz dává smysl pro výchozí Prahu.",
            ],
            "do_not_use_when": [
                "Uživatel chce historická meteorologická data.",
                "Uživatel chce dlouhodobou předpověď delší než 3 dny.",
            ],
            "examples": [
                'Jaké je počasí v Praze? -> get_weather(location="Praha")',
                'Kolik je stupňů v Brně? -> get_weather(location="Brno", mode="current")',
                'Jaká je předpověď pro Ostravu? -> get_weather(location="Ostrava", mode="forecast", days=3)',
                'Bude zítra pršet v Berlíně? -> get_weather(location="Berlín", mode="forecast", days=2)',
            ],
            "verified_on": "2026-06-17",
            "verification": (
                "Reálný dotaz na wttr.in pro Prahu vrátil souhrn počasí; "
                "předpověď byla ověřena smoke testem nad stejným zdrojem."
            ),
        },
    },
    "get_calendar_events": {
        "name": "get_calendar_events",
        "module": "actions.002_calendar.calendar",
        "function": "get_calendar_events",
        "status": "verified",
        "description": (
            "Načte události z Google Calendar. Použij, když se uživatel ptá na "
            "kalendář, schůzky, události, denní program, zítřek, příští týden "
            "nebo na termín konkrétní události. Umí pracovat s primárním "
            "kalendářem i s konkrétním kalendářem podle názvu. Dotazy na vlastní "
            "kalendář, Anežku, Márinku a rodinu se mapují na pevně určené kalendáře."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Časový rozsah nebo hledaný text. Podporované hodnoty: "
                        "today, tomorrow, week, next_week, next, agenda, případně "
                        "přirozený text názvu události. Pro běžné časové dotazy "
                        "preferuj normalizované hodnoty, například tomorrow nebo next_week."
                    ),
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maximální počet vrácených událostí. Doporučené maximum je 20.",
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": (
                        "Volitelný název kalendáře, například Anežka. Pokud chybí, "
                        "modul si z query sám odvodí pevné mapování: moje/já/můj -> "
                        "travnicek.michal5@gmail.com, Anežka -> travnickova.anezka@gmail.com, "
                        "Márinka -> marinka.travnickova, rodina -> Rodina. Pokud query "
                        "neobsahuje žádný z těchto aliasů, prohledají se primární, "
                        "vlastněné/zapisovatelné a vybrané kalendáře."
                    ),
                },
            },
            "required": ["query"],
        },
        "agent_notes": {
            "use_when": [
                "Uživatel se ptá, jaké události má dnes, zítra, tento týden nebo příští týden.",
                "Uživatel se ptá na termín konkrétní události podle názvu.",
                "Uživatel uvede konkrétní kalendář, například kalendář Anežka.",
            ],
            "do_not_use_when": [
                "Uživatel chce vytvořit novou událost; použij add_calendar_event.",
                "Uživatel chce odstranit událost; použij delete_calendar_event.",
            ],
            "examples": [
                'Jaké události mám na zítřek? -> get_calendar_events(query="tomorrow")',
                'Jaké události mám na příští týden? -> get_calendar_events(query="next_week")',
                'Na kdy mám naplánovanou událost zubař? -> get_calendar_events(query="zubař")',
                'Jaké události má na příští týden kalendář Anežka? -> get_calendar_events(query="next_week", calendar_name="Anežka")',
            ],
            "verified_on": "2026-06-18",
            "verification": (
                "Ověřena syntaxe, import přes loader a lokální smoke test parsování "
                "časových rozsahů bez reálného Google API volání."
            ),
        },
    },
    "add_calendar_event": {
        "name": "add_calendar_event",
        "module": "actions.002_calendar.calendar",
        "function": "add_calendar_event",
        "status": "verified",
        "description": (
            "Přidá novou událost do Google Calendar. Použij až tehdy, když uživatel "
            "sdělil název události, datum a čas začátku, trvání nebo konec události "
            "a název cílového kalendáře. Pokud některý z těchto údajů chybí, "
            "nejprve se uživatele doptej a nástroj ještě nevolej."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Název události, například 'Návštěva zubaře'.",
                },
                "start_iso": {
                    "type": "STRING",
                    "description": (
                        "Datum a čas začátku v ISO formátu, například 2026-06-19T14:00:00."
                    ),
                },
                "end_iso": {
                    "type": "STRING",
                    "description": "Volitelné datum a čas konce v ISO formátu.",
                },
                "duration_minutes": {
                    "type": "NUMBER",
                    "description": (
                        "Trvání události v minutách. Použij, pokud není vyplněn end_iso."
                    ),
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Název cílového kalendáře, do kterého se má událost přidat.",
                },
                "location": {
                    "type": "STRING",
                    "description": "Volitelné místo události.",
                },
                "notes": {
                    "type": "STRING",
                    "description": "Volitelné poznámky k události.",
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "Hodnota true vytvoří celodenní událost.",
                },
            },
            "required": ["title", "start_iso", "duration_minutes", "calendar_name"],
        },
        "agent_notes": {
            "use_when": [
                "Uživatel výslovně chce přidat schůzku, termín nebo událost.",
                "Jsou známé název, datum, čas, trvání nebo konec a cílový kalendář.",
            ],
            "do_not_use_when": [
                "Chybí název události.",
                "Chybí datum nebo čas začátku.",
                "Chybí trvání nebo čas konce.",
                "Chybí název kalendáře; nejprve se doptej.",
            ],
            "examples": [
                'Přidej zítra v 15:00 poradu na hodinu do kalendáře Práce -> add_calendar_event(title="porada", start_iso="...", duration_minutes=60, calendar_name="Práce")',
                "Když uživatel řekne jen 'přidej zubaře', agent se nejdřív doptá na datum, čas, trvání a kalendář.",
            ],
            "verified_on": "2026-06-18",
            "verification": (
                "Ověřena syntaxe, import přes loader a lokální validace chybějících "
                "povinných údajů bez reálného Google API volání."
            ),
        },
    },
    "delete_calendar_event": {
        "name": "delete_calendar_event",
        "module": "actions.002_calendar.calendar",
        "function": "delete_calendar_event",
        "status": "verified",
        "description": (
            "Odstraní událost z Google Calendar podle názvu a volitelného času. "
            "Použij pouze tehdy, když uživatel jasně požádá o odstranění události."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Název odstraňované události.",
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Volitelný čas začátku pro rozlišení více shod.",
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Volitelný název kalendáře.",
                },
                "delete_all_matches": {
                    "type": "BOOLEAN",
                    "description": "Hodnota true odstraní všechny odpovídající shody.",
                },
            },
            "required": ["title"],
        },
        "agent_notes": {
            "use_when": [
                "Uživatel chce odstranit existující kalendářovou událost.",
            ],
            "do_not_use_when": [
                "Uživatel se jen ptá na události; použij get_calendar_events.",
                "Uživatel chce vytvořit událost; použij add_calendar_event.",
            ],
            "examples": [
                'Smaž z kalendáře zubaře zítra ve 14:00 -> delete_calendar_event(title="zubař", start_iso="...")',
            ],
            "verified_on": "2026-06-18",
            "verification": "Ověřena syntaxe a deklarace nástroje.",
        },
    },
}


def get_tool_metadata(name: str) -> dict[str, Any]:
    """Vrátí úplná metadata nástroje pro dokumentaci a budoucí orchestraci."""
    return deepcopy(TOOL_CATALOG[name])


def get_tool_declaration(name: str) -> dict[str, Any]:
    """Vrátí deklaraci nástroje ve formátu používaném Gemini Live API."""
    metadata = TOOL_CATALOG[name]
    return {
        "name": metadata["name"],
        "description": metadata["description"],
        "parameters": deepcopy(metadata["parameters"]),
    }
