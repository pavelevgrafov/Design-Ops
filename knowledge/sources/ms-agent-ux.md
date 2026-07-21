---
id: ms-agent-ux
title: "Microsoft — Agent UX Design Principles"
url: https://microsoft.design/articles/ux-design-for-agents/
evidence_level: industry-standard
verified_at: 2026-07-21
tags: [ai-features, agents, transparency, control, trust]
thesis: "Принципы агентного UX Microsoft: прозрачность статуса, контроль, консистентность."
---

## Что это
Набор принципов проектирования агентов (Agent Space / Time / Core) от
Microsoft Design: агент действует в фоне, но его действия видимы и
контролируемы; неопределённость показывается, а не прячется; статус
агента виден всегда.

## Использование в пайплайне
- K1 для AI-фич: обязательные состояния агента (что делает сейчас,
  история действий, как отключить) входят в state_matrix.
- Прямо подтверждает паттерн гейтов пайплайна: provisional-решения
  машины видимы и обратимы (право вето при возврате).

## Границы
- Принципы, не метрики: машино-проверяемых порогов нет, флор — только
  как рекомендации в отчёт.
