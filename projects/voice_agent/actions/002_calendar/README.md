# 002_calendar

Ověřená akce pro čtení a vytváření událostí v Google Calendar.

## Soubory

- `calendar.py` — implementace nástrojů `get_calendar_events`,
  `add_calendar_event` a `delete_calendar_event`.
- `__init__.py` — označení adresáře jako Python balíčku pro import přes loader.

## Konfigurace

Akce používá Google OAuth pro desktopovou aplikaci.

Lokální soubory:

- `config/google_calendar_credentials.json` — OAuth client stažený z Google Cloud
  Console. Tento soubor se neukládá do Gitu.
- `runtime/google_calendar_token.json` — token vytvořený po prvním přihlášení.
  Tento soubor se neukládá do Gitu.

Volitelné proměnné prostředí:

```env
GOOGLE_CALENDAR_CREDENTIALS_PATH="config/google_calendar_credentials.json"
GOOGLE_CALENDAR_TOKEN_PATH="runtime/google_calendar_token.json"
JARVIS_TIMEZONE="Europe/Prague"
```

## Nástroje

Agent používá tuto akci přes nástroje popsané v `actions/tool_catalog.py`.

- `get_calendar_events` čte události pro dotazy typu dnes, zítra, týden,
  příští týden, vyhledání názvu události nebo konkrétní kalendář. Pokud není
  uveden konkrétní kalendář, prohledá primární, vlastněné/zapisovatelné a vybrané
  kalendáře.
- Dotazy na vlastní kalendář, Anežku, Márinku a rodinu se mapují pevně:
  `moje/já/můj` -> `travnicek.michal5@gmail.com`,
  `Anežka` -> `travnickova.anezka@gmail.com`,
  `Márinka` -> `marinka.travnickova`,
  `rodina` -> `Rodina`.
- `add_calendar_event` přidává událost. Agent ho má volat až ve chvíli, kdy zná
  název, datum a čas začátku, trvání nebo konec a cílový kalendář.
- `delete_calendar_event` odstraňuje událost po názvu a volitelném upřesnění času.

Pokud chybí povinné údaje, nástroj vrátí českou hlášku s tím, co je potřeba
doplnit. Primární doptávání má ale dělat agent ještě před voláním nástroje.
