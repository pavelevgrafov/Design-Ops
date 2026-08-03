---
id: ai-look-catalog
title: "AI-look: каталог маркеров и лечение"
url: https://github.com/pavelevgrafov/ux-wiki/blob/main/guidelines/ai-look-antipatterns.md
evidence_level: curated
verified_at: 2026-08-04
tags: [ai-look, anti-patterns, slop, ban-list, encyclopedia]
thesis: "Маркеры AI-look по слоям; лечение: замена палитры, слом шаблона."
---

## Что это
Каталог узнаваемых маркеров генеративного дизайна. Цвет: фиолетово-синий
градиент в герое, indigo-600 / slate-900 из дефолтов Tailwind. Лейаут:
«герой → 3 карточки → соцдоказательство → прайсинг → FAQ → футер», всё по
центру. Типографика: Inter на всё, дефолтные интерлиньяж и трекинг.
Компоненты: rounded-2xl shadow-lg p-6 на каждой карточке; карточки в
карточках. Эффекты: glassmorphism без причины, градиентный текст на
метриках, bounce/elastic на всём. Текст: «Empower/Unlock/Seamless», ноль
конкретики. Лечение: (1) палитра — заменить целиком, не extend; (2)
грамматику лейаута — сломать (асимметрия, смещение); (3) словарь
компонентов — один радиус-словарь, одна философия поверхности, запреты
прошить линтером; (4) процесс — по фазам (песочница → критика → аудит →
полировка → нормализация). Тест: «здесь видно, что человек это выбрал?» —
любые 2 признака из 4 (пара шрифтов, палитра, асимметрия, копи с числом).

## Использование в пайплайне
- A.24: AI-look detection — ban-list дефолтных маркеров (invariant).
- K2B: ai-look-detector прогоняется на каждом divergence direction до
  contact sheet; карточки в карточках — запрет (A.16).
- K3: D.30 (маркеры, blocking), D.36 (копи, warning).
- Ban-list tiered: Tier 1 blocking (indigo-600-герой, карточки в карточках),
  Tier 2 warning (glassmorphism без контента под стеклом), Tier 3 reference.

## Границы
- Уровень evidence — single-team practice (каталог из практики, не
  стандарт): ban-list обновляется через eval-корпус (design-ops-eval-corpus),
  каждая позиция цитирует свою ноту.
