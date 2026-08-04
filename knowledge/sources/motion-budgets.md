---
id: motion-budgets
title: "Моушн: длительности, easing, spring, 60fps"
url: https://github.com/pavelevgrafov/ux-wiki/blob/main/patterns/motion.md
evidence_level: curated
verified_at: 2026-08-04
tags: [motion, animation, easing, spring, performance, encyclopedia]
thesis: "100–700 мс, ease-out вход, transform+opacity, reduced-motion."
---

## Что это
Длительности: микро 100–200 мс (hover, тоггл), стандарт 200–500 мс
(модалка, аккордеон), крупные 500–700 мс; дольше 700 мс = «тормозит».
Порог Доэрти: реакция начинается < 400 мс (MUST). Easing: linear запрещён
(MUST); ease-out — 80% UI-анимаций (вход), ease-in — уход, ease-in-out —
перемещения. Spring: bounce 0–0.3 (максимум 0.4), начинать с 0;
perceptual duration вместо физических параметров. Жёсткие ограничения:
только transform + opacity (MUST), width/height/top/left запрещены;
prefers-reduced-motion — обязательная «тихая» версия (MUST); nonblocking —
анимация прерывается вводом (MUST). Плавность: бюджет кадра 16.6 мс (60 Гц)
/ 8.3 мс (120 Гц); jank < 1% — отлично, > 10% — плохо; p95 frame time
важнее среднего FPS. Консистентность: 2–3 кривые и 2–3 длительности на
продукт (токены).

## Использование в пайплайне
- K2B tokens: --duration-fast/normal/slow, --ease-out/in/in-out,
  --spring-bounce/duration.
- A.17: transform+opacity, nonblocking, reduced-motion (invariant).
- K3: D.29 (reduced-motion, blocking), D.35 (jank, warning).
- У каждой анимации — функция (направить/объяснить/подтвердить);
  «для красоты» не считается — правило K2B merge.

## Границы
- «Работает» ≠ «ощущается правильно»: feels-right критерии (вращение
  вместо морфа, без лишнего bounce) прошиваются правилами, но финальный
  просмотр — за Gate 2.
