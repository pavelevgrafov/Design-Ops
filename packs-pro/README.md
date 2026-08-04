# packs-pro/ — Pro tier packs (placeholder, v7.0)

Модель: **Core free, Ecosystem paid**. Весь pipeline (K0–K4, все навыки,
гейты, base skins, base packs, self-test, knowledge vault) остаётся в
open source (MIT) — навсегда. Эта директория зарезервирована под
расширенные packs, которые будут распространяться по подписке Pro
($29/мес, запуск — отдельным решением после v7.0).

Кандидаты (из исследования v7.0): mcp-bridge, figma-bridge,
deploy-aws-s3, deploy-gcp-bucket, supabase-connect, firebase-connect.

## Access control (как будет работать)

1. `.agents/config.yaml` содержит `subscription.tier` (default: `free`).
2. `install.sh` читает tier; при `free` pro-packs пропускаются с
   сообщением «Upgrade to Pro for this pack».
3. Pro packs — это assets с кураторством и верификацией (acceptance
   tests, frozen registry), не код ядра: именно это сложно форкнуть
   (defensibility: time to replicate + trust).

Пока директория пуста — это осознанное состояние v7.0 (подготовка без
запуска платежей; Stripe не подключён).
