---
id: async-seven-states
title: "7 системных состояний асинхронного экрана"
url: https://github.com/pavelevgrafov/ux-wiki/blob/main/patterns/system-states.md
evidence_level: curated
verified_at: 2026-08-04
tags: [states, async, loading, skeleton, empty, error, encyclopedia]
thesis: "7 состояний асинхронного блока: idle…success. Одного мало."
---

## Что это
Семь состояний: idle (что здесь будет + CTA), loading (< 4 c — спиннер,
> 4 c — прогресс с процентами/шагами), skeleton (предсказуемая структура
→ скелетон вместо спиннера), populated (идеальное — ему уделяют 95%
времени), empty (не пустота, а онбординг: причина + следующий шаг + CTA),
error (конкретика без кодов + действие восстановления + сохранение
ввода), success (подтверждение, правило «пик–конец»). Качество: не
несколько спиннеров одновременно; ошибки инлайн в периметре блока; тосты
не для критичных ошибок; фоновое обновление не прячет данные. Доступность:
aria-busy, aria-live="polite", role="alert" для критичных, скелетоны
aria-hidden, лоадеры уважают prefers-reduced-motion.

## Использование в пайплайне
- A.12: каждый асинхронный экран — автомат из 7 состояний (invariant).
- K1: state matrix (app-профиль) покрывает все 7 для каждого блока.
- K3: D.38 — 7 states check на каждый асинхронный блок (blocking).
- Pack state-generator: генерирует спецификации состояний из state matrix.

## Границы
- Агент применяет state spec (YAML/JSON с CSS на состояние), а не
  «проектирует» состояния: spec — из design system, агент — executor.
