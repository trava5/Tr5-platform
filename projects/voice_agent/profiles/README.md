# Profily agenta

Adresář `profiles` popisuje specializované varianty voice agenta.

Základní projekt drží společné runtime jádro:

- backend service (`backend/`),
- katalog nástrojů (`actions/tool_catalog.py`),
- sdílené features (`features/`),
- obecné načítání promptu a katalogu nástrojů přes `profile_loader.py`.

Konkrétní profil se liší:

- vlastním systémovým promptem,
- výběrem povolených nástrojů z `actions/tool_catalog.py`,
- výběrem zapnutých features z `features/`,
- dokumentací zaměření profilu.

## Struktura profilu

```text
profiles/NNN_name/
  README.md
  prompt.txt
  actions.json
  features.json
```

`prompt.txt` obsahuje specializovaný systémový prompt.

`actions.json` obsahuje `{"enabled_tools": [...]}` — seznam názvů nástrojů,
které musí existovat jako klíče v `actions/tool_catalog.py`. `profile_loader.py`
každý název ověří a při neznámém názvu selže s konkrétní chybou.

`features.json` obsahuje `{"enabled_features": [...]}` — seznam názvů features
z `features/`. `profile_loader.py` tento seznam zatím nevaliduje proti žádnému
registru features, protože žádný takový registr ještě neexistuje; vrací ho tak,
jak je zapsaný.

## Načítání profilu

`profile_loader.py` čte statické soubory profilu, ověřuje je a vrací
strukturovaný výsledek. Nemá závislost na `backend/` ani na živém běhu —
načítání profilu je nezávislé na tom, jestli existuje běžící agent.

Nic zatím `profile_loader.py` nevolá — napojení na živý agent runtime je
budoucí krok (Phase 4).
