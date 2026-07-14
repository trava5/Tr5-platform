# 000_base

Výchozí profil pro obecného osobního asistenta.

Tento profil má povolené všechny nástroje aktuálně registrované v
`actions/tool_catalog.py` (počasí, čtení/přidání/odstranění událostí v
Google Calendar, otevírání aplikací) — je to obecný asistent bez zaměření
na konkrétní doménu, takže žádný z pěti aktuálně dostupných nástrojů není
důvod vynechávat.

Žádná feature není zapnutá ve výchozím stavu. Zapnutí `002_telegram_bridge`
nebo jiné feature je samostatné, výslovné rozhodnutí, ne vedlejší efekt
tohoto profilu.
