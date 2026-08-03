---
id: dark-theme-rules
title: "Тёмная тема: 7 правил отдельного дизайна"
url: https://github.com/pavelevgrafov/ux-wiki/blob/main/guidelines/dark-theme.md
evidence_level: curated
verified_at: 2026-08-04
tags: [dark-theme, color, elevation, tokens, encyclopedia]
thesis: "Тёмная тема отдельно: #121212, elevation светлотой, текст 87%."
---

## Что это
Семь правил (MUST/SHOULD): (1) фон тёмно-серый #121212, не чистый чёрный
(MUST); (2) десатурация акцентов ~20 процентных пунктов; (3) elevation —
светлотой, не тенью: белый оверлей по уровням hover 8% / focus 12% /
pressed 12% / drag 16% (MUST); (4) контраст белого текста к тёмной
поверхности ≥ 15.8:1 (MUST); (5) семантика перенастраивается: error
#B00020 → #CF6679 (MUST); (6) текст не чисто белый: primary 87%,
secondary 60%, disabled 38%; (7) изображения приглушаются
(brightness 0.9). Инженерное следствие: тёмная тема «бесплатна» только
при семантических токенах; `bg-white` в коде = тёмной темы нет.

## Использование в пайплайне
- K2A/K2B tokens: --elevation-0dp…24dp (overlay %), --color-bg-dark:
  #121212, --color-text-primary-dark: rgba(255,255,255,0.87),
  semantic-dark слой.
- A.21: компоненты ссылаются только на семантику — смена темы = подмена
  слоя значений.
- K3: D.25 (контраст) прогоняется для обеих тем; D.37 проверяет, что
  компоненты не ссылаются на примитивы.

## Границы
- Исключение: осознанный dark-first/OLED-стиль с истинным чёрным — MAY,
  фиксируется в contract как divergence direction.
