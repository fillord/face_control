#!/usr/bin/env bash
# Резервная копия рантайм-данных для переноса на новый сервер.
#
# В архив попадают (только если существуют на диске):
#   data/app.db              — основная база SQLite
#   data/encodings.json      — 128-мерные эмбеддинги лиц
#   data/faces/               — исходные фото сотрудников
#   data_backup_pre_sqlite/  — старый дамп до миграции на SQLite (если ещё не удалён)
#
# Восстановление на новом сервере:
#   sha256sum -c face-data-<ТС>.tar.gz.sha256
#   tar -xzf face-data-<ТС>.tar.gz -C /var/www/face-almgp33
#
# Каталог назначения можно переопределить переменной окружения BACKUP_DIR.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$BACKUP_DIR"

TS="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$BACKUP_DIR/face-data-$TS.tar.gz"

cd "$ROOT"

PATHS=()
for p in data/app.db data/encodings.json data/faces data_backup_pre_sqlite; do
  if [ -e "$p" ]; then
    PATHS+=("$p")
  fi
done

if [ "${#PATHS[@]}" -eq 0 ]; then
  echo "Ошибка: не найдено ни одного из ожидаемых путей с данными (data/app.db, data/encodings.json, data/faces, data_backup_pre_sqlite) — архивировать нечего." >&2
  exit 1
fi

tar -czf "$ARCHIVE" "${PATHS[@]}"
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"

echo "$ARCHIVE"
