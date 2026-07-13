# TR5 Current State

Generator: Tr5 Discovery Engine v1.1

---

## Repository Structure

- artifacts/
  - foundation/
    - DOCUMENT_STANDARD.md
    - FOUNDATIONAL_WORLDVIEW.md
  - implementation_contracts/
    - IMPLEMENTATION_CONTRACT_0001.md
    - IMPLEMENTATION_CONTRACT_0002.md
  - principles/
    - PRINCIPLES.md
- projects/
  - voice_agent/
    - backend/
      - db/
        - __init__.py
        - base.py
        - models.py
        - session.py
      - services/
        - __init__.py
        - agent_runtime.py
        - conversations.py
        - memory.py
        - memory_migration.py
        - postgres_conversations.py
        - postgres_memory.py
        - realtime.py
      - README.md
      - __init__.py
      - __main__.py
      - api.py
      - app.py
      - client.py
      - config.py
      - database.py
      - realtime_client.py
      - schemas.py
      - storage.py
    - .env.example
    - README.md
    - requirements.txt
- tools/
  - discovery_engine/
    - README.md
    - generate_current_state.py
- .gitignore
- CLAUDE.md
- README.md
- TR5_CURRENT_STATE.md

---

## Artifacts

| Name | Relative Path | Type |
|---|---|---|
| .gitignore | .gitignore | Unknown |
| CLAUDE.md | CLAUDE.md | Markdown Document |
| README.md | README.md | Markdown Document |
| TR5_CURRENT_STATE.md | TR5_CURRENT_STATE.md | Markdown Document |
| artifacts | artifacts | Directory |
| foundation | artifacts/foundation | Directory |
| DOCUMENT_STANDARD.md | artifacts/foundation/DOCUMENT_STANDARD.md | Markdown Document |
| FOUNDATIONAL_WORLDVIEW.md | artifacts/foundation/FOUNDATIONAL_WORLDVIEW.md | Markdown Document |
| implementation_contracts | artifacts/implementation_contracts | Directory |
| IMPLEMENTATION_CONTRACT_0001.md | artifacts/implementation_contracts/IMPLEMENTATION_CONTRACT_0001.md | Markdown Document |
| IMPLEMENTATION_CONTRACT_0002.md | artifacts/implementation_contracts/IMPLEMENTATION_CONTRACT_0002.md | Markdown Document |
| principles | artifacts/principles | Directory |
| PRINCIPLES.md | artifacts/principles/PRINCIPLES.md | Markdown Document |
| projects | projects | Directory |
| voice_agent | projects/voice_agent | Directory |
| .env.example | projects/voice_agent/.env.example | Unknown |
| README.md | projects/voice_agent/README.md | Markdown Document |
| backend | projects/voice_agent/backend | Directory |
| README.md | projects/voice_agent/backend/README.md | Markdown Document |
| __init__.py | projects/voice_agent/backend/__init__.py | Python Source |
| __main__.py | projects/voice_agent/backend/__main__.py | Python Source |
| api.py | projects/voice_agent/backend/api.py | Python Source |
| app.py | projects/voice_agent/backend/app.py | Python Source |
| client.py | projects/voice_agent/backend/client.py | Python Source |
| config.py | projects/voice_agent/backend/config.py | Python Source |
| database.py | projects/voice_agent/backend/database.py | Python Source |
| db | projects/voice_agent/backend/db | Directory |
| __init__.py | projects/voice_agent/backend/db/__init__.py | Python Source |
| base.py | projects/voice_agent/backend/db/base.py | Python Source |
| models.py | projects/voice_agent/backend/db/models.py | Python Source |
| session.py | projects/voice_agent/backend/db/session.py | Python Source |
| realtime_client.py | projects/voice_agent/backend/realtime_client.py | Python Source |
| schemas.py | projects/voice_agent/backend/schemas.py | Python Source |
| services | projects/voice_agent/backend/services | Directory |
| __init__.py | projects/voice_agent/backend/services/__init__.py | Python Source |
| agent_runtime.py | projects/voice_agent/backend/services/agent_runtime.py | Python Source |
| conversations.py | projects/voice_agent/backend/services/conversations.py | Python Source |
| memory.py | projects/voice_agent/backend/services/memory.py | Python Source |
| memory_migration.py | projects/voice_agent/backend/services/memory_migration.py | Python Source |
| postgres_conversations.py | projects/voice_agent/backend/services/postgres_conversations.py | Python Source |
| postgres_memory.py | projects/voice_agent/backend/services/postgres_memory.py | Python Source |
| realtime.py | projects/voice_agent/backend/services/realtime.py | Python Source |
| storage.py | projects/voice_agent/backend/storage.py | Python Source |
| requirements.txt | projects/voice_agent/requirements.txt | Unknown |
| tools | tools | Directory |
| discovery_engine | tools/discovery_engine | Directory |
| README.md | tools/discovery_engine/README.md | Markdown Document |
| generate_current_state.py | tools/discovery_engine/generate_current_state.py | Python Source |
