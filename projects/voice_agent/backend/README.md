# Backend

Serverova vrstva pro budouci viceklientskou architekturu JARVIS.

Backend je zavedena serverova vrstva pro vice klientu. Soucasna desktop aplikace
zustava funkcni a muze spustit embedded backend ve stejnem procesu. V embedded
rezimu backend pouzije live handler napojeny na aktualni Gemini Live relaci v
`main.py`, takze `POST /api/v1/messages` muze vratit skutecnou odpoved agenta.
Dalsi migracni kroky budou postupne presouvat sdilenou agentni logiku za API, aby
ji mohly pouzivat Desktop UI, Telegram bridge a budouci mobilni frontend,
napriklad Flutter.

## Spusteni

Skutecne hodnoty patri do lokalniho `.env`.

```powershell
.\.venv\Scripts\python.exe -m backend
```

nebo primo pres uvicorn s factory patternem (`create_app()` neni volana pri
importu modulu, jen kdyz server skutecne startuje):

```powershell
.\.venv\Scripts\uvicorn.exe backend.app:create_app --factory --reload --port 8000
```

Vychozi adresa je `http://127.0.0.1:8000`.

## Endpointy

- `GET /api/v1/health` vraci zakladni stav backendu.
- `GET /api/v1/status` vraci stav backendu a PostgreSQL konfigurace.
- `WS /api/v1/realtime` poskytuje realtime stream udalosti pro stav runtime,
  textove zpravy a budouci audio eventy.
- `POST /api/v1/messages` prijima stabilni agentni message kontrakt. V embedded
  desktop rezimu vraci skutecnou odpoved agenta. V samostatnem backend procesu bez
  live handleru vraci `runtime_unavailable`.
- `GET /api/v1/conversations` vraci seznam konverzacnich relaci z aktivniho
  repository.
- `GET /api/v1/conversations/{conversation_id}` vraci detail relace vcetne zprav.
- `POST /api/v1/memory/short-term` ulozi kratkodoby pametovy turn.
- `GET /api/v1/memory/short-term` vraci posledni kratkodobe turny.
- `GET /api/v1/memory/short-term/search` vyhleda text v kratkodobe pameti.
- `DELETE /api/v1/memory/short-term` smaze kratkodobe turny starsi nez zadany
  pocet dni.
- `POST /api/v1/memory/decisions` ulozi potvrzene dlouhodobe rozhodnuti.
- `GET /api/v1/memory/decisions` vraci potvrzena dlouhodoba rozhodnuti.
- `POST /api/v1/memory/import/sqlite` importuje soucasne lokalni SQLite zaznamy
  kratkodobe pameti a dlouhodobych rozhodnuti do aktivni backend storage vrstvy.

Priklad zpravy:

```json
{
  "text": "Ahoj, jaky je dnes plan?",
  "channel": "mobile",
  "client_id": "flutter-dev",
  "conversation_id": null,
  "want_audio": false
}
```

Realtime WebSocket po pripojeni posle `hello` event:

```json
{
  "event_id": "...",
  "event_type": "hello",
  "timestamp": "2026-06-21T12:00:00+00:00",
  "channel": "backend",
  "client_id": null,
  "conversation_id": null,
  "role": null,
  "text": null,
  "audio_mime_type": null,
  "audio_base64": null,
  "payload": {
    "schema_version": "realtime.v1",
    "supported_event_types": ["hello", "pong", "runtime_state", "message", "audio"]
  }
}
```

Pri zpracovani `POST /api/v1/messages` backend vysila `message` event pro
uzivatelsky turn a navazujici odpoved asistenta. Pri pripojeni nebo odpojeni live
handleru vysila `runtime_state`. Typ `audio` je v kontraktu pripraveny, ale
skutecne audio bloky se budou doplnovat v navazujicim migracnim kroku.

API uz nepouziva konkretni in-memory uloziste primo. Konverzace jdou pres
`ConversationRepository` a factory `create_conversation_repository`. Bez
`DATABASE_URL` factory vraci in-memory fallback. Pri nastavene databazi pouzije
PostgreSQL repository nad SQLAlchemy modely; pokud pripojeni k databazi selze,
backend zustane funkcni nad in-memory fallbackem.

Databazove schéma pro PostgreSQL uz ma SQLAlchemy 2.0 modely v `backend/db`.
Modely `Client`, `Conversation` a `Message` pripravuji tabulky `clients`,
`conversations` a `messages`, vcetne zakladnich vazeb, indexu a timestampu.
Repository pri prvnim pouziti provede vyvojovou inicializaci schematu pres
`Base.metadata.create_all`.

Backend storage vrstva pro pamet pridava tabulky `short_term_memory_turns` a
`long_term_decisions`. Import ze SQLite je idempotentni: opakovane spusteni
importu nepridava duplicitni zaznamy se stejnou identitou.

## Konfigurace

```env
JARVIS_BACKEND_HOST="127.0.0.1"
JARVIS_BACKEND_PORT="8000"
JARVIS_BACKEND_RELOAD="false"
JARVIS_EMBEDDED_BACKEND_ENABLED="true"
DATABASE_URL=""
DATABASE_NAME="postgres"
DATABASE_USER=""
DATABASE_PASS=""
DATABASE_SCHEMA=""
```

`DATABASE_URL` bude smerovat na PostgreSQL, napriklad pres async driver
`postgresql+asyncpg://...`. Pokud URL neobsahuje prihlaseni, backend doplni
`DATABASE_USER` a `DATABASE_PASS`. Pokud URL neobsahuje nazev databaze, pouzije
se `DATABASE_NAME`. `DATABASE_SCHEMA` je volitelne databazove schema, napriklad
pro oddeleni vyvojovych tabulek. Skutecny connection string se neverzuje.

Desktopovy textovy vstup muze backend volat jako prvni cestu pres obecneho
klienta `backend.client`:

```env
JARVIS_BACKEND_CLIENT_ENABLED="true"
JARVIS_BACKEND_BASE_URL=""
JARVIS_BACKEND_CONNECT_TIMEOUT_SECONDS="2.5"
JARVIS_BACKEND_TIMEOUT_SECONDS="95.0"
```

Pokud `JARVIS_BACKEND_BASE_URL` neni vyplnene, klient pouzije
`JARVIS_BACKEND_HOST` a `JARVIS_BACKEND_PORT`. Pri nedostupnem backendu nebo
prechodovych stavech `runtime_unavailable`, `not_implemented` a `runtime_error`
desktopova aplikace pouzije primy fallback do soucasne Gemini Live relace.
Desktopovy backend pozadavek neblokuje lokalni audio vystup; potlaceni lokalniho
audia zustava vyhrazene pro externi kanaly, jako je Telegram.

Desktopova aplikace se muze zaroven pripojit jako realtime WebSocket klient pres:

```env
JARVIS_BACKEND_REALTIME_ENABLED="true"
JARVIS_BACKEND_REALTIME_URL=""
JARVIS_BACKEND_REALTIME_OPEN_TIMEOUT_SECONDS="2.5"
JARVIS_BACKEND_REALTIME_RECONNECT_SECONDS="3.0"
```

Pokud `JARVIS_BACKEND_REALTIME_URL` neni vyplnene, klient odvodí adresu z
`JARVIS_BACKEND_BASE_URL` nebo z `JARVIS_BACKEND_HOST` a `JARVIS_BACKEND_PORT`.
Desktopovy klient prijima `hello`, `runtime_state` a `message` eventy. Zpravy
deduplikuje proti soucasnym lokalnim logum, protoze audio a Gemini Live smycky
zatim porad bezi v `main.py`.

Telegram bridge muze backend volat jako prvni cestu pres:

```env
TELEGRAM_BACKEND_ENABLED="true"
TELEGRAM_BACKEND_BASE_URL=""
TELEGRAM_BACKEND_CONNECT_TIMEOUT_SECONDS="2.5"
TELEGRAM_BACKEND_TIMEOUT_SECONDS="95.0"
```

Pokud `TELEGRAM_BACKEND_BASE_URL` neni vyplnene, Telegram klient pouzije
`JARVIS_BACKEND_HOST` a `JARVIS_BACKEND_PORT`. Connect timeout je kratky, aby
nedostupny backend rychle spadl do fallbacku. Read timeout je delsi, protoze
embedded backend muze cekat na skutecnou odpoved z live modelu.

## Embedded backend

Desktopova aplikace spousti embedded backend, pokud je
`JARVIS_EMBEDDED_BACKEND_ENABLED="true"`. Embedded backend bezi na stejne adrese a
portu jako samostatny backend. Pokud je port obsazeny, desktop aplikace pokracuje
bez embedded backendu a klienti pouziji dostupne fallbacky.

Pri navazani Gemini Live relace se desktopovy runtime zaregistruje do backend
`AgentRuntime`. Pri reconnectu nebo chybe relace se zase odpoji. Samostatny backend
spusteny pres `python -m backend` nema live handler a zustava v rizene prechodove
odpovedi `runtime_unavailable`.
