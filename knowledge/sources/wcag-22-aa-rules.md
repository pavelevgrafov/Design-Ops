---
id: wcag-22-aa-rules
title: "WCAG 2.2 AA: контраст, тач-таргеты, фокус, семантика"
url: https://github.com/pavelevgrafov/ux-wiki/blob/main/guidelines/accessibility.md
evidence_level: industry-standard
verified_at: 2026-08-04
tags: [a11y, wcag, contrast, focus, target-size, encyclopedia]
thesis: "WCAG 2.2 AA: 4.5:1, 24px, фокус, семантика прежде ARIA."
---

## Что это
Действующий стандарт — WCAG 2.2, уровень AA. Контраст: текст 4.5:1,
крупный (≥ 18pt / ≥ 14pt bold) 3:1, non-text (иконки, бордеры инпутов,
фокус-индикаторы) 3:1 (SC 1.4.11); округление запрещено (4.499 = провал);
текст на градиенте — по самой светлой точке. Мишени: 24×24 CSS px минимум
(SC 2.5.8, MUST), комфорт 44–48px (SHOULD). Фокус: не удаляется, а
стилизуется (:focus-visible), контраст индикатора ≥ 3:1, толщина от 2px;
клавиатурный порядок = визуальному; модалки захватывают и возвращают
фокус. Смысл: семантический HTML прежде ARIA (MUST); не цветом единым —
цвет + иконка + текст (SC 1.4.1); масштабирование до 200% (SC 1.4.4);
статусные сообщения role="status"/aria-live (SC 4.1.3);
prefers-reduced-motion всегда. Skip-link на страницах с навигацией.

## Использование в пайплайне
- K3 blocking: D.25 (контраст), D.26 (тач-таргет), D.27 (фокус),
  D.28 (семантика, H-иерархия), D.29 (reduced-motion) — failure = blocking.
- A.18 (семантика прежде ARIA), A.19 (не цветом единым) — invariants.
- K1: skip-link — component spec. K2A: rem и отказ от фиксированных
  высот текстовых блоков (зум 200%).

## Границы
- Автоматика ловит часть проблем: SHOULD — ручной проход (клавиатура,
  скринридер, зум) на human gate; D.34 keyboard test — warning-уровень.
