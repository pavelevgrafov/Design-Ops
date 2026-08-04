# Design-Ops Pipeline — Docs Portal

Production pipeline: текстовый запрос → рабочий, машинно-проверенный
фундамент интерфейса (сайты и веб-приложения).

## Быстрый старт

- Установка и миграция v6 → v7: [`INSTALL.md`](https://github.com/pavelevgrafov/Design-Ops/blob/main/INSTALL.md)
- Архитектура, инварианты, гейты: [`AGENTS.md`](https://github.com/pavelevgrafov/Design-Ops/blob/main/AGENTS.md)
- Обзор и changelog: [`README.md`](https://github.com/pavelevgrafov/Design-Ops/blob/main/README.md)

## Конвейер

```
K0 discovery → K1 structure → GATE 1 (human) → K2A base skin (automatic)
→ K3 verification → [K2B full visual craft — optional] → [K4 deploy — optional, GATE 3]
```

| Skill | Конвейер | Владеет |
| :-- | :-- | :-- |
| `pipeline-orchestrator` | — | маршрутизация, контракт, гейты, packs, decision log |
| `structure-builder` | K1 | UX: experience model, domain/RBAC, нейтральный скелет |
| `visual-director` | K2A/K2B | UI: base skin, дивергенция, токены, ассеты |
| `quality-guardian` | K3 | доказательство: пол D1–D38, диагностика, вердикт |

## v7.0

- Детерминированный пол D1–D38 (tiered: blocking / warning).
- Инварианты A.1–A.24; knowledge vault из 33 evidence notes.
- Трёхслойные токены (primitive → semantic → component), тёмная тема,
  motion- и elevation-токены.
- 6 новых packs: ai-look-detector, contrast-checker, token-validator,
  state-generator, copy-linter, awwwards-reference.
- Экосистема: Radar (weekly digest), Showcase, этот портал.

Документы релиза — в разделе **v7.0 release** навигации.

## Экосистема

- `radar/` — еженедельный мониторинг GitHub (MVP).
- `showcase/` — галерея проектов из Verified Starters (`build-showcase.py`).
- GitHub Discussions — канал сообщества (включается владельцем в настройках репо).
