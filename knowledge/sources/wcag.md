---
id: wcag
title: "W3C — Web Content Accessibility Guidelines (WCAG) 2.2"
url: https://www.w3.org/TR/WCAG22/
evidence_level: industry-standard
verified_at: 2026-07-21
tags: [accessibility, contrast, a11y, standard]
thesis: "Контраст 4.5:1, видимый фокус, мишень ≥24px — основа D3/D10."
---

## Что это
Действующий стандарт доступности W3C. Для пайплайна релевантны
машино-проверяемые критерии уровня AA: контраст (1.4.3/1.4.11),
фокус-видимость (2.4.7/2.4.13), размер мишени (2.5.8).

## Использование в пайплайне
- K3 D3: check-contrast.py считает relative luminance по формуле
  стандарта; пары объявлены в токенах (contrast-pairs).
- K3 D10: focus-visible на всех интерактивных элементах.

## Границы
- Проверяем только машино-проверяемое; полный аудит доступности —
  отдельная задача, не флор.
