"""Google Calendar action for reading and creating calendar events."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TIMEZONE = os.getenv("JARVIS_TIMEZONE", "Europe/Prague")
DEFAULT_CALENDAR_CREDENTIALS = BASE_DIR / "config" / "google_calendar_credentials.json"
DEFAULT_CALENDAR_TOKEN = BASE_DIR / "runtime" / "google_calendar_token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
MONTH_ALIASES = {
    1: {"leden", "lednu", "ledna", "january"},
    2: {"unor", "unoru", "unora", "february"},
    3: {"brezen", "breznu", "brezna", "march"},
    4: {"duben", "dubnu", "dubna", "april"},
    5: {"kveten", "kvetnu", "kvetna", "may"},
    6: {"cerven", "cervnu", "cervna", "june"},
    7: {"cervenec", "cervenci", "cervence", "july"},
    8: {"srpen", "srpnu", "srpna", "august"},
    9: {"zari", "september"},
    10: {"rijen", "rijnu", "rijna", "october"},
    11: {"listopad", "listopadu", "november"},
    12: {"prosinec", "prosinci", "prosince", "december"},
}
MONTH_LABELS = {
    1: "leden",
    2: "únor",
    3: "březen",
    4: "duben",
    5: "květen",
    6: "červen",
    7: "červenec",
    8: "srpen",
    9: "září",
    10: "říjen",
    11: "listopad",
    12: "prosinec",
}
CALENDAR_QUERY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "travnicek.michal5@gmail.com",
        (
            "muj",
            "moje",
            "mem",
            "me",
            "meho",
            "mne",
            "ja",
            "mam",
        ),
    ),
    (
        "travnickova.anezka@gmail.com",
        (
            "anezka",
            "anezky",
            "anezce",
            "anezku",
        ),
    ),
    (
        "marinka.travnickova",
        (
            "marinka",
            "marinky",
            "marince",
            "marinku",
            "marinka.travnickova",
        ),
    ),
    (
        "Rodina",
        (
            "rodina",
            "rodiny",
            "rodine",
            "rodinnem",
            "rodinny",
        ),
    ),
)


class CalendarActionError(RuntimeError):
    """Expected calendar action error shown to the user."""


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    start: str
    end: str = ""
    calendar: str = ""
    location: str = ""
    description: str = ""
    sort_start: str = ""


@dataclass(frozen=True)
class CalendarQueryWindow:
    label: str
    time_min: datetime
    time_max: datetime
    search_text: str = ""


def _tz() -> tzinfo:
    try:
        return ZoneInfo(DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        local_tz = datetime.now().astimezone().tzinfo
        if local_tz is None:
            return timezone.utc
        return local_tz


def _now() -> datetime:
    return datetime.now(_tz())


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    zone = _tz()
    start = datetime.combine(day, time.min, tzinfo=zone)
    return start, start + timedelta(days=1)


def _next_week_bounds(today: date) -> tuple[datetime, datetime]:
    days_until_next_monday = 7 - today.weekday()
    next_monday = today + timedelta(days=days_until_next_monday)
    return _day_bounds(next_monday)[0], _day_bounds(next_monday + timedelta(days=7))[0]


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    zone = _tz()
    start = datetime(year, month, 1, tzinfo=zone)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=zone)
    else:
        end = datetime(year, month + 1, 1, tzinfo=zone)
    return start, end


def _normalize_query(query: str) -> str:
    return " ".join(str(query or "").strip().lower().split())


def _normalize_text_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_marks.split())


def _normalize_calendar_match(value: str) -> str:
    return _normalize_text_match(value)


def _contains_any(text: str, needles: set[str]) -> bool:
    return any(needle in text for needle in needles)


def _contains_word(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


def _infer_calendar_name_from_query(query: str) -> str:
    text = _normalize_text_match(query)
    for calendar_name, aliases in CALENDAR_QUERY_ALIASES:
        if any(_contains_word(text, alias) for alias in aliases):
            return calendar_name
    return ""


def _calendar_token_match(requested: str, summary: str) -> bool:
    requested_tokens = [
        token for token in re.split(r"[^a-z0-9]+", requested.split("@", 1)[0])
        if len(token) > 2
    ]
    summary_tokens = [
        token for token in re.split(r"[^a-z0-9]+", summary.split("@", 1)[0])
        if len(token) > 2
    ]
    if not requested_tokens or not summary_tokens:
        return False
    return all(
        any(summary_token.startswith(token) or token.startswith(summary_token) for summary_token in summary_tokens)
        for token in requested_tokens
    )


def _extract_subject_search_text(query: str) -> str:
    original_words = str(query or "").strip().split()
    plain_words = _normalize_text_match(query).split()
    for marker in {"ma", "má"}:
        if marker not in plain_words:
            continue
        marker_index = plain_words.index(marker)
        if marker_index + 1 >= len(plain_words):
            continue
        candidate_words: list[str] = []
        for plain_word, original_word in zip(
            plain_words[marker_index + 1:],
            original_words[marker_index + 1:],
        ):
            if plain_word in {
                "na",
                "v",
                "ve",
                "pro",
                "kalendari",
                "kalendar",
                "udalosti",
                "udalost",
            }:
                break
            candidate_words.append(original_word.strip(".,?!\"'"))
        candidate = " ".join(word for word in candidate_words if word).strip()
        if candidate and _normalize_text_match(candidate) not in {"ja", "me", "muj", "moje"}:
            return candidate
    return ""


def _resolve_month_window(query: str, current: datetime) -> CalendarQueryWindow | None:
    text = _normalize_text_match(query)
    for month, aliases in MONTH_ALIASES.items():
        if not any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            continue

        year_match = re.search(r"\b(20\d{2})\b", text)
        if year_match:
            year = int(year_match.group(1))
        else:
            year = current.year
            if month < current.month:
                year += 1

        start, end = _month_bounds(year, month)
        return CalendarQueryWindow(
            f"{MONTH_LABELS[month]} {year}",
            start,
            end,
            search_text=_extract_subject_search_text(query),
        )
    return None


def _extract_event_search_text(query: str) -> str:
    search = str(query or "").strip()
    plain = _normalize_text_match(search)
    prefixes = [
        "na kdy mam naplanovanou udalost",
        "na kdy mam naplanovanou",
        "kdy mam naplanovanou udalost",
        "kdy mam naplanovanou",
        "kdy je udalost",
        "najdi udalost",
        "vyhledej udalost",
        "udalost",
    ]
    for prefix in prefixes:
        if plain.startswith(prefix):
            words_to_drop = len(prefix.split())
            return " ".join(search.split()[words_to_drop:]).strip() or search
    return search


def resolve_query_window(query: str = "today") -> CalendarQueryWindow:
    """Resolve Czech/English calendar query text into a Google Calendar time window."""
    normalized = _normalize_query(query)
    plain = _normalize_text_match(query)
    current = _now()
    today = current.date()

    month_window = _resolve_month_window(str(query or ""), current)
    if month_window:
        return month_window

    if normalized in {"", "today", "dnes"} or _contains_any(
        plain,
        {
            "dnes",
            "dnesni",
            "dnesek",
        },
    ):
        start, end = _day_bounds(today)
        return CalendarQueryWindow("dnes", start, end)

    if normalized in {"tomorrow", "zítra", "zitra"} or _contains_any(
        plain,
        {
            "zitra",
            "zitrejsi",
            "zitrek",
            "zitrka",
        },
    ):
        start, end = _day_bounds(today + timedelta(days=1))
        return CalendarQueryWindow("zítra", start, end)

    if normalized in {"next_week", "next week", "příští týden", "pristi tyden"} or _contains_any(
        plain,
        {
            "pristi tyden",
            "pristiho tydne",
            "nasledujici tyden",
            "dalsi tyden",
        },
    ):
        start, end = _next_week_bounds(today)
        return CalendarQueryWindow("příští týden", start, end)

    if normalized in {"week", "this week", "agenda", "týden", "tyden", "program"} or _contains_any(
        plain,
        {
            "tento tyden",
            "tenhle tyden",
            "aktualni tyden",
            "nasledujicich 7 dni",
            "program",
            "agenda",
        },
    ):
        return CalendarQueryWindow("následujících 7 dní", current, current + timedelta(days=7))

    if normalized in {"next", "upcoming", "nadcházející", "nadchazejici"} or _contains_any(
        plain,
        {
            "nadchazejici",
            "nejblizsi",
            "pristi udalosti",
        },
    ):
        return CalendarQueryWindow("nadcházející události", current, current + timedelta(days=30))

    search_text = _extract_event_search_text(str(query or "").strip())
    return CalendarQueryWindow(
        f'vyhledání "{search_text}"',
        current - timedelta(days=30),
        current + timedelta(days=365),
        search_text=search_text,
    )


def _parse_datetime(value: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise CalendarActionError("Chybí datum a čas začátku události.")
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CalendarActionError(
            "Datum a čas musí být v ISO formátu, například 2026-06-19T14:00:00."
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_tz())
    return parsed.astimezone(_tz())


def _format_dt(value: str, all_day: bool = False) -> str:
    if not value:
        return ""
    if all_day:
        try:
            parsed_date = date.fromisoformat(value[:10])
            return parsed_date.strftime("%d.%m.%Y")
        except ValueError:
            return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.astimezone(_tz()).strftime("%d.%m.%Y %H:%M")


def _load_google_calendar_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CalendarActionError(
            "Chybí knihovny pro Google Calendar API. Nainstalujte závislosti z requirements.txt."
        ) from exc

    credentials_path = Path(
        os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", str(DEFAULT_CALENDAR_CREDENTIALS))
    )
    token_path = Path(os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", str(DEFAULT_CALENDAR_TOKEN)))

    if not credentials_path.exists():
        raise CalendarActionError(
            "Kalendář Google není nakonfigurovaný. Chybí OAuth soubor "
            f"`{credentials_path}`."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("calendar", "v3", credentials=creds)


def _list_calendars(service) -> list[dict[str, Any]]:
    response = service.calendarList().list().execute()
    return list(response.get("items", []))


def _find_calendar_id(service, calendar_name: str = "") -> tuple[str, str]:
    requested = str(calendar_name or "").strip()
    calendars = _list_calendars(service)

    if not requested:
        for calendar in calendars:
            if calendar.get("primary"):
                return calendar["id"], calendar.get("summary", "primární kalendář")
        return "primary", "primární kalendář"

    requested_match = _normalize_calendar_match(requested)
    requested_prefix = requested_match.split("@", 1)[0]
    for calendar in calendars:
        summary = str(calendar.get("summary", ""))
        summary_match = _normalize_calendar_match(summary)
        summary_prefix = summary_match.split("@", 1)[0]
        if summary_match == requested_match or summary_prefix == requested_prefix:
            return calendar["id"], summary
    for calendar in calendars:
        summary = str(calendar.get("summary", ""))
        summary_match = _normalize_calendar_match(summary)
        summary_prefix = summary_match.split("@", 1)[0]
        if (
            requested_match in summary_match
            or requested_prefix in summary_match
            or requested_match in summary_prefix
            or _calendar_token_match(requested_match, summary_match)
        ):
            return calendar["id"], summary

    available = ", ".join(str(c.get("summary", "")) for c in calendars if c.get("summary"))
    if available:
        raise CalendarActionError(
            f"Kalendář '{requested}' nebyl nalezen. Dostupné kalendáře: {available}."
        )
    raise CalendarActionError(f"Kalendář '{requested}' nebyl nalezen.")


def _default_calendar_targets(service) -> list[tuple[str, str]]:
    calendars = _list_calendars(service)
    targets: list[tuple[str, str]] = []
    for calendar in calendars:
        calendar_id = str(calendar.get("id", "")).strip()
        summary = str(calendar.get("summary", "")).strip()
        access_role = str(calendar.get("accessRole", "")).strip().lower()
        if not calendar_id:
            continue
        if calendar.get("primary") or calendar.get("selected") is True or access_role in {"owner", "writer"}:
            targets.append((calendar_id, summary or calendar_id))

    if targets:
        return targets
    return [("primary", "primární kalendář")]


def _event_from_google(item: dict[str, Any], calendar_label: str) -> CalendarEvent:
    start_info = item.get("start", {})
    end_info = item.get("end", {})
    all_day = "date" in start_info
    raw_start = start_info.get("dateTime") or start_info.get("date", "")
    start = _format_dt(start_info.get("dateTime") or start_info.get("date", ""), all_day)
    end = _format_dt(end_info.get("dateTime") or end_info.get("date", ""), all_day)
    return CalendarEvent(
        title=item.get("summary", "(bez názvu)"),
        start=start,
        end=end,
        calendar=calendar_label,
        location=item.get("location", ""),
        description=item.get("description", ""),
        sort_start=str(raw_start),
    )


def format_events(events: list[CalendarEvent], label: str, calendar_label: str) -> str:
    if calendar_label == "vybraných":
        empty_prefix = "Ve vybraných kalendářích"
        list_prefix = "Události ve vybraných kalendářích"
    else:
        empty_prefix = f"V kalendáři {calendar_label}"
        list_prefix = f"Události v kalendáři {calendar_label}"
    if not events:
        return f"{empty_prefix} nejsou pro období {label} žádné události."

    lines = [f"{list_prefix} pro období {label}:"]
    for event in events:
        when = event.start
        if event.end and event.end != event.start:
            when = f"{event.start} - {event.end}"
        location = f" ({event.location})" if event.location else ""
        calendar = f" [{event.calendar}]" if calendar_label == "vybraných" else ""
        lines.append(f"- {when}: {event.title}{location}{calendar}")
    return "\n".join(lines)


def get_calendar_events(query: str = "today", limit: int = 6, calendar_name: str = "") -> str:
    """Read events from Google Calendar."""
    try:
        window = resolve_query_window(query)
        service = _load_google_calendar_service()
        inferred_calendar = _infer_calendar_name_from_query(query)
        clean_calendar = str(calendar_name or "").strip() or inferred_calendar
        if inferred_calendar and window.search_text:
            subject = _extract_subject_search_text(query)
            if subject and _normalize_text_match(subject) == _normalize_text_match(window.search_text):
                window = replace(window, search_text="")
        max_results = max(1, min(int(limit or 6), 20))
        if clean_calendar:
            calendar_id, calendar_label = _find_calendar_id(service, clean_calendar)
            targets = [(calendar_id, calendar_label)]
            result_calendar_label = calendar_label
        else:
            targets = _default_calendar_targets(service)
            result_calendar_label = (
                targets[0][1] if len(targets) == 1 else "vybraných"
            )

        events: list[CalendarEvent] = []
        for calendar_id, calendar_label in targets:
            request = service.events().list(
                calendarId=calendar_id,
                timeMin=window.time_min.isoformat(),
                timeMax=window.time_max.isoformat(),
                q=window.search_text or None,
                singleEvents=True,
                orderBy="startTime",
                maxResults=max_results,
            )
            items = request.execute().get("items", [])
            events.extend(_event_from_google(item, calendar_label) for item in items)

        events.sort(key=lambda event: event.sort_start or event.start)
        events = events[:max_results]
        return format_events(events, window.label, result_calendar_label)
    except CalendarActionError as exc:
        return f"Kalendář Google: {exc}"
    except Exception as exc:
        return f"Kalendář Google se nepodařilo načíst: {exc}"


def add_calendar_event(
    title: str,
    start_iso: str,
    end_iso: str = "",
    notes: str = "",
    location: str = "",
    calendar_name: str = "",
    all_day: bool = False,
    duration_minutes: int = 60,
) -> str:
    """Create a new event in Google Calendar."""
    try:
        clean_title = str(title or "").strip()
        clean_calendar = str(calendar_name or "").strip()
        if not clean_title:
            raise CalendarActionError("Chybí název události.")
        if not clean_calendar:
            raise CalendarActionError("Chybí název cílového kalendáře.")

        service = _load_google_calendar_service()
        calendar_id, calendar_label = _find_calendar_id(service, clean_calendar)

        if all_day:
            start_dt = _parse_datetime(start_iso)
            end_dt = _parse_datetime(end_iso) if end_iso else start_dt + timedelta(days=1)
            event_body: dict[str, Any] = {
                "summary": clean_title,
                "start": {"date": start_dt.date().isoformat()},
                "end": {"date": end_dt.date().isoformat()},
            }
        else:
            start_dt = _parse_datetime(start_iso)
            if end_iso:
                end_dt = _parse_datetime(end_iso)
            else:
                minutes = max(1, int(duration_minutes or 60))
                end_dt = start_dt + timedelta(minutes=minutes)
            event_body = {
                "summary": clean_title,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": DEFAULT_TIMEZONE},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": DEFAULT_TIMEZONE},
            }

        if notes:
            event_body["description"] = str(notes)
        if location:
            event_body["location"] = str(location)

        created = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        html_link = created.get("htmlLink", "")
        suffix = f" Odkaz: {html_link}" if html_link else ""
        return f"Událost '{clean_title}' byla přidána do kalendáře {calendar_label}.{suffix}"
    except CalendarActionError as exc:
        return f"Kalendář Google: {exc}"
    except Exception as exc:
        return f"Událost se nepodařilo přidat do Kalendáře Google: {exc}"


def delete_calendar_event(
    title: str,
    start_iso: str = "",
    calendar_name: str = "",
    delete_all_matches: bool = False,
) -> str:
    """Delete matching events from Google Calendar."""
    try:
        clean_title = str(title or "").strip()
        if not clean_title:
            raise CalendarActionError("Chybí název události pro odstranění.")

        service = _load_google_calendar_service()
        calendar_id, calendar_label = _find_calendar_id(service, calendar_name)

        if start_iso:
            start_dt = _parse_datetime(start_iso)
            time_min = (start_dt - timedelta(hours=12)).isoformat()
            time_max = (start_dt + timedelta(hours=12)).isoformat()
        else:
            now = _now()
            time_min = (now - timedelta(days=30)).isoformat()
            time_max = (now + timedelta(days=365)).isoformat()

        items = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            q=clean_title,
            singleEvents=True,
            orderBy="startTime",
            maxResults=20,
        ).execute().get("items", [])

        matches = [
            item for item in items
            if clean_title.lower() in str(item.get("summary", "")).lower()
        ]
        if not matches:
            return f"V kalendáři {calendar_label} jsem nenašel událost '{clean_title}'."
        if len(matches) > 1 and not delete_all_matches and not start_iso:
            return (
                f"Našel jsem více událostí '{clean_title}' v kalendáři {calendar_label}. "
                "Upřesněte datum a čas, nebo potvrďte odstranění všech shod."
            )

        selected = matches if delete_all_matches else matches[:1]
        for item in selected:
            service.events().delete(calendarId=calendar_id, eventId=item["id"]).execute()
        return f"Z kalendáře {calendar_label} bylo odstraněno událostí: {len(selected)}."
    except CalendarActionError as exc:
        return f"Kalendář Google: {exc}"
    except Exception as exc:
        return f"Událost se nepodařilo odstranit z Kalendáře Google: {exc}"


if __name__ == "__main__":
    print(json.dumps(resolve_query_window("zítra").__dict__, default=str, ensure_ascii=False, indent=2))
