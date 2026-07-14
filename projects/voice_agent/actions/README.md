# Akce asistenta

Adresář `actions` obsahuje pouze nástroje, které agent přímo volá přes
tool/function calling.

Každá nová nebo revidovaná akce má vlastní číslovaný podadresář ve tvaru
`actions/NNN_name`, například `actions/001_weather`.

Uvnitř podadresáře mohou být:

- implementační moduly,
- pomocné adaptéry,
- dokumentace,
- testovací nebo konfigurační soubory potřebné pro danou akci.

Každý nástroj dostupný agentovi musí mít záznam v `actions/tool_catalog.py`.

Starší ploché moduly v kořeni `actions` jsou legacy stav. Budou se přesouvat do
číslovaných podadresářů postupně při revizi konkrétní akce.
