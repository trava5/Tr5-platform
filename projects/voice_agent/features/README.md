# Běhové vlastnosti asistenta

Adresář `features` slouží pro části asistenta, které nejsou nástroje volané
agentem přes tool/function calling.

Features tvoří sdílenou runtime vrstvu projektu. Nemají určovat zaměření
konkrétního agenta; jen poskytují schopnosti, které si budoucí specializované
profily mohou zapnout nebo vypnout.

Komunikační features se navrhují jako klienti nad sdíleným agentním backendem.
Nemají duplikovat prompt, paměť, actions ani rozhodovací logiku agenta. Desktop
UI, Telegram bridge a budoucí webové nebo mobilní rozhraní mají používat stejný
agentní runtime.

Každá nová nebo revidovaná feature má vlastní číslovaný podadresář ve tvaru
`features/NNN_name`, například `features/001_telegram` nebo
`features/002_elevenlabs_voice`. Implementace, dokumentace, konfigurace a
pomocné adaptéry dané feature se ukládají dovnitř tohoto adresáře.

Patří sem například:

- vstupní a výstupní kanály, například Telegram bridge nebo mobilní web,
- hlasové moduly a poskytovatelé, například budoucí integrace ElevenLabs,
- runtime adaptéry, které obsluhují komunikaci mezi uživatelem a agentem,
- podpůrné služby, které rozšiřují způsob používání asistenta, ale nejsou samy
  o sobě nástrojem dostupným v `actions/tool_catalog.py`.

Nepatří sem:

- funkce, které má agent přímo volat jako nástroj,
- deklarace nástrojů pro model,
- doménové akce typu počasí, kalendář, připomínky, shell nebo ovládání aplikací.

Tyto nástroje patří do `actions` a musí mít záznam v `actions/tool_catalog.py`.

## Dostupné features

| Feature | Stav | Popis |
|---|---|---|
| `001_elevenlabs_voice` | zapnuto | Hlasový provider ElevenLabs pro desktopový výstup, pokud je nakonfigurovaný v `.env`. |
| `002_telegram_bridge` | textový a hlasový vstup | Telegram Bot API bridge pro komunikaci s JARVIS; textové i přepsané hlasové vstupy se posílají do backend API. V embedded desktop režimu backend vrací skutečnou odpověď agenta, při nedostupnosti zůstává bezpečný desktopový fallback. Odpověď se vždy vrací jako textová zpráva. |

## Vztah k profilům

Budoucí specializované kopie agenta budou definované profilem v `profiles`.
Profil určí vlastní prompt, povolené actions a zapnuté features. Stejná feature
tak může být použitá ve více agentech bez kopírování její implementace.

Příklad:

- osobní agent může zapnout Telegram bridge a hlasový výstup,
- pracovní agent může zapnout mobilní web a jiné notifikace,
- mediální agent může sdílet stejný hlasový provider, ale mít jiný prompt a jiné
  actions.
