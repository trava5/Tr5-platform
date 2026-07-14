# 003_open_app

Ověřená akce pro otevírání aplikací ve Windows.

## Soubory

- `open_app.py` - implementace funkce `open_app`.
- `__init__.py` - označení adresáře jako Python balíčku pro import přes loader.

## Nástroj

Agent používá tuto akci přes nástroj `open_app`, který je popsaný v
`actions/tool_catalog.py`.

Akce podporuje běžné názvy aplikací, české aliasy a vybraná Windows URI schémata,
například `ms-settings:` nebo `outlookcal:`.

Spouštění probíhá neblokujícím způsobem. Aplikace a konzolové nástroje se předají
Windows jako samostatné okno, aby akce nedržela běžící relaci asistenta čekáním
na otevřený proces.
