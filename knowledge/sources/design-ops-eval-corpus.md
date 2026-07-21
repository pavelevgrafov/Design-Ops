---
id: design-ops-eval-corpus
title: "Design-Ops eval corpus — внутренние наблюдения слопа"
url: internal:eval/
evidence_level: curated
verified_at: 2026-07-21
tags: [internal, eval, slop, mode-collapse]
thesis: "Наш eval-корпус фиксирует слоп-дефолты моделей (Inter, indigo→purple, bento)."
---

## Что это
Собственные наблюдения пайплайна: eval-промпты (eval/example-prompts.md),
прогон P08 (slop provocation), тесты дивергенции (mode collapse —
«три реколора одного лейаута»). Внутренний источник: url = internal:eval/.

## Использование в пайплайне
- K2 бан-лист §1, §2, §4: обоснование запрета дефолтов — они
  воспроизводятся независимо от брифа, значит не несут решения.

## Границы
- curated (наблюдение, не контролируемый эксперимент); пополняется
  каждым прогоном eval.
