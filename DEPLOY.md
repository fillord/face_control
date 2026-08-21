# Развёртывание — от пустого сервера Ubuntu до работающего PM2-процесса

## 1. Что НЕ хранится в Git

Следующее не отслеживается git и не попадёт при клонировании репозитория:

- `data/app.db` — база SQLite
- `data/encodings.json` — 128-мерные эмбеддинги лиц
- `data/faces/` — фотографии сотрудников
- `ecosystem.config.js` — боевой конфиг PM2 с реальным `SECRET_KEY`
- `backups/` — архивы, создаваемые `scripts/backup_data.sh`
- `.planning/` — внутренние заметки процесса разработки
- `venv/` — виртуальное окружение Python

Данные (`data/`) переносятся отдельным архивом через
`scripts/backup_data.sh` (см. раздел 7). Конфиг PM2 создаётся из
`ecosystem.config.js.example` (см. раздел 8).

## 2. ШАГ 0 — обязательно перед первым push

Пока история git не вычищена от утёкшего секрета, репозиторий
**публиковать нельзя**. Сначала выполните ручные шаги из
[SECURITY-NOTES.md](./SECURITY-NOTES.md) — там же объясняется, зачем
это нужно и почему это разрушительная операция, которую executor не
делает автоматически.

## 3. Создание репозитория и первый push (вручную)

Эти команды executor не выполнял — их запускает владелец проекта, после
выполнения ШАГа 0.

1. На github.com создать **пустой** репозиторий: без README, без
   `.gitignore`, без лицензии (иначе конфликт при первом push).
2. Подключить remote и запушить:
   ```bash
   git remote add origin git@github.com:USER/REPO.git
   # или https-вариант:
   # git remote add origin https://github.com/USER/REPO.git
   git push -u origin master
   ```
   Текущая ветка называется `master`. Если на GitHub нужна ветка `main`:
   ```bash
   git branch -M main
   git push -u origin main
   ```

## 4. Требования сервера

- Ubuntu 22.04 или 24.04.
- Минимум 2 GB RAM — сборка `dlib` из исходников прожорлива по памяти.
  При 1 GB RAM обязательно добавить swap:
  ```bash
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```
- Python 3.14 отсутствует в стандартных репозиториях Ubuntu:
  ```bash
  sudo add-apt-repository ppa:deadsnakes/ppa
  sudo apt update
  sudo apt install -y python3.14 python3.14-venv python3.14-dev
  ```
  Python 3.12 или 3.13 тоже подходят, если 3.14 недоступен.

## 5. Системные пакеты

```bash
sudo apt update && sudo apt install -y \
  git build-essential cmake pkg-config \
  libopenblas-dev liblapack-dev \
  libx11-dev libgtk-3-dev libjpeg-dev libpng-dev \
  libgl1 libglib2.0-0
```

`cmake` и `build-essential` нужны для сборки `dlib` из исходников.
`libgl1` и `libglib2.0-0` нужны для колёс `opencv-contrib-python` на
headless-сервере без графической подсистемы.

## 6. Клонирование и venv

```bash
sudo mkdir -p /var/www/face-almgp33
sudo chown "$USER":"$USER" /var/www/face-almgp33
git clone git@github.com:USER/REPO.git /var/www/face-almgp33
cd /var/www/face-almgp33

python3.14 -m venv venv
./venv/bin/pip install --upgrade pip wheel setuptools
./venv/bin/pip install -r requirements.txt
```

Сборка `dlib` из исходников занимает несколько минут — это нормально.

Если нужно прогнать тесты:
```bash
./venv/bin/pip install pytest==9.0.3
./venv/bin/pytest
```

## 7. Перенос данных

На старом сервере:
```bash
bash scripts/backup_data.sh
```
Скопировать выведенный архив на новый сервер:
```bash
scp backups/face-data-*.tar.gz backups/face-data-*.tar.gz.sha256 user@new-server:/tmp/
```

На новом сервере:
```bash
cd /tmp
sha256sum -c face-data-*.tar.gz.sha256
tar -xzf face-data-*.tar.gz -C /var/www/face-almgp33
```

Проверить, что появились `data/app.db`, `data/encodings.json`,
`data/faces/`. Каталог `data_backup_pre_sqlite/`, если он попал в
архив — это старый дамп до миграции на SQLite, для работы приложения
он не нужен, на новом сервере его можно удалить.

## 8. Секрет и конфиг PM2

```bash
cp ecosystem.config.js.example ecosystem.config.js
./venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
```

Вставить полученное значение в `SECRET_KEY` внутри `ecosystem.config.js`,
сверить пути (`script`, `cwd`) с реальным расположением проекта на
сервере. Файл в `.gitignore` — в репозиторий он не попадёт.

## 9. Запуск через PM2

```bash
sudo apt install -y nodejs npm
sudo npm install -g pm2

pm2 start /var/www/face-almgp33/ecosystem.config.js
pm2 save
pm2 startup   # выполнить команду, которую выведет pm2 startup

pm2 status
pm2 logs face-recognition
```

Обновление после `git pull`:
```bash
pm2 restart face-recognition
```

**Важно:** флаг `-w 1` (один воркер gunicorn) в `ecosystem.config.js`
менять нельзя. Запись в SQLite защищена advisory-блокировками
`fcntl.flock`, которые не работают между несколькими процессами-воркерами
gunicorn — при `-w > 1` возможна порча данных при одновременной записи.

## 10. Nginx + HTTPS

Пример конфига реверс-прокси на `127.0.0.1:5051`:

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:5051;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 20M;
    }
}
```

`X-Forwarded-Proto` обязателен — приложение использует
`werkzeug.middleware.proxy_fix.ProxyFix`.
`client_max_body_size 20M` — для загрузки фотографий при регистрации.

**Предупреждение про камеру:** киоск и страница регистрации используют
камеру через браузерный `getUserMedia`, а браузеры дают доступ к камере
только в защищённом контексте (HTTPS или `localhost`). **Без HTTPS
камера не заработает** на реальном домене.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

## 11. Проверка и типовые проблемы

Проверка, что сервис отвечает:
```bash
curl -I http://127.0.0.1:5051/
```

| Симптом | Причина |
|---|---|
| «Камера не открывается» | Нет HTTPS (см. раздел 10) |
| `ImportError: libGL.so.1` | Не установлен `libgl1` (см. раздел 5) |
| `dlib` падает при сборке | Нет `cmake` / `build-essential` или не хватает памяти (см. разделы 4–5) |
| Сотрудники не распознаются | Не восстановлен `data/encodings.json` (см. раздел 7) |
| Ошибка `SECRET_KEY environment variable must be set` при старте | Не создан `ecosystem.config.js` или не задан `SECRET_KEY` (см. раздел 8) |
