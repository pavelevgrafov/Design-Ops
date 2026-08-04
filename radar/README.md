# Design-Ops Radar (MVP)

Еженедельный мониторинг GitHub-экосистемы для улучшения pipeline.
Стоимость $0 (GitHub Actions), время владельца ≤ 30 минут в неделю.

## Как работает

1. `.github/workflows/radar.yml` — cron, понедельник 06:17 UTC (+ ручной запуск).
2. `radar.py` — 5 topic-запросов к GitHub search API, жёсткие пороги
   (≥100 stars, возраст >90 дней, активность <30 дней), digest топ-5
   одним issue с меткой `radar`.
3. Владелец раз в неделю ревьюит digest: accept → issue на интеграцию
   (метка версии v7.x), defer → backlog, reject → закрыть.

## Правила (антидоты булщитолога)

- Не «мониторим всё» — 5 категорий, жёсткие пороги, digest = 1 страница.
- Digest не читается 4 недели → workflow отключаем (radar экономит время,
  а не тратит).
- Расширение (AI reviewer, HN/npm, decision log) — только после 4 недель
  доказанной пользы, отдельной фазой.

## Локальный прогон

```bash
GITHUB_TOKEN=ghp_... GITHUB_REPOSITORY=pavelevgrafov/Design-Ops python radar/radar.py
```
