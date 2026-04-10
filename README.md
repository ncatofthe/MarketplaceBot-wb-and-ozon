# MarketplaceBot

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Локальный desktop MVP на Python + Tkinter для автоответов на отзывы Ozon и Wildberries.

## Статус

- Основной рабочий сценарий по-прежнему поддерживается и для source/dev запуска, и для Windows packaging.
- Windows packaging теперь собирается через PyInstaller из зафиксированного spec-файла.
- Инсталлятора, auto-update и code signing в проекте пока нет.
- Реальный Windows smoke нужно выполнять отдельно на Win10/11. В этом репозитории он описан как manual checklist, но не заявлен как уже пройденный.

## Что делает приложение

1. Поднимает локальный GUI.
2. Хранит конфиг, шаблоны, review state и single-instance lock в пользовательских runtime-папках.
3. Запускает отдельных ботов для Ozon и Wildberries, включая multi-account сценарий.
4. Пишет runtime-логи локально на машине пользователя.

## Требования

### Runtime

- Python `>=3.8`
- `tkinter` в установленном Python
- доступ в интернет к API Ozon и Wildberries

Установка runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

### Build

Build dependencies вынесены отдельно и не засоряют runtime manifest:

```bash
python -m pip install -r requirements-build.txt
```

`requirements-build.txt` включает runtime requirements и PyInstaller.

## Запуск из исходников

### Windows

```cmd
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy settings\config.example.json settings\config.local.json
copy settings\answers.example.json settings\answers.local.json
python main.py
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp settings/config.example.json settings/config.local.json
cp settings/answers.example.json settings/answers.local.json
python main.py
```

## Как собрать Windows `.exe`

Сборку нужно запускать на Windows.

### Вариант через `build.bat`

```cmd
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-build.txt
build.bat
```

Что делает `build.bat`:

- проверяет наличие Python;
- проверяет, что установлен `PyInstaller`;
- запускает реальную сборку через `MarketplaceBot.spec`;
- завершает процесс ошибкой, если spec или build dependency отсутствуют.

### Вариант вручную

```cmd
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-build.txt
python -m PyInstaller --clean --noconfirm MarketplaceBot.spec
```

### Результат сборки

PyInstaller собирает onedir-package:

- `dist\MarketplaceBot\MarketplaceBot.exe`

`MarketplaceBot.exe` нужно запускать вместе с содержимым папки `dist\MarketplaceBot`, не выдёргивая exe отдельно.

## First Run у compiled app

При первом запуске собранного Windows-приложения:

1. Приложение определяет runtime-папки пользователя.
2. Если в пользовательской папке настроек ещё нет example-файлов, bundled `config.example.json` и `answers.example.json` копируются туда автоматически.
3. Создаётся папка логов пользователя.
4. После первого сохранения настроек GUI создаёт `config.local.json`.
5. После первого сохранения шаблонов GUI создаёт `answers.local.json`.
6. При запуске single-instance lock не даёт открыть второй экземпляр параллельно.

Форматы `config.local.json` и `answers.local.json` source/dev режим не меняют.

## Где хранятся данные пользователя

### Source/dev режим

- настройки и шаблоны: локальная папка репозитория `settings/`
- логи: локальная папка репозитория `logs/`

### Frozen Windows runtime

- настройки, шаблоны, review state и lock: `%APPDATA%\MarketplaceBot\settings`
- логи: `%LOCALAPPDATA%\MarketplaceBot\logs`

Обычно в `%APPDATA%\MarketplaceBot\settings` будут лежать:

- `config.example.json`
- `answers.example.json`
- `config.local.json`
- `answers.local.json`
- `review_state.json`
- `marketplacebot.lock`

## Секреты и защита ключей

- `config.example.json` и `answers.example.json` в репозитории не содержат секретов.
- Рабочие ключи сохраняются только в `config.local.json`.
- На Windows API keys при сохранении защищаются через DPAPI для текущего пользователя Windows на текущей машине.
- Если реальные ключи раньше попадали в Git-историю, их нужно перевыпустить у Ozon и Wildberries.

Поддерживаются env overrides:

- `MARKETPLACEBOT_OZON_API_KEY`
- `MARKETPLACEBOT_OZON_COMPANY_ID`
- `MARKETPLACEBOT_WB_API_KEY`
- `MARKETPLACEBOT_WILDBERRIES_API_KEY`

## Тесты и локальные проверки

Unit/smoke тесты:

```bash
python -m unittest discover -s tests -v
```

Проверка компиляции Python-модулей:

```bash
python3 -m compileall main.py config.py api bots gui utils tests runtime_paths.py runtime_assets.py
```

При изменении packaging/bootstrap также полезно проверить:

```bash
python3 -m py_compile runtime_assets.py
python3 -m py_compile config.py
```

## Manual Smoke Checklist для Win10/11

Этот список нужно пройти на реальной Windows-машине после сборки:

1. Запустить `dist\MarketplaceBot\MarketplaceBot.exe`.
2. Убедиться, что первый запуск создал пользовательские runtime-папки и example-файлы.
3. Ввести ключи Ozon/WB в GUI и сохранить настройки.
4. Проверить, что после сохранения появился `config.local.json`.
5. Перезапустить приложение и убедиться, что настройки и аккаунты сохранились.
6. Проверить multi-account: добавить несколько аккаунтов одного маркетплейса и сохранить.
7. Проверить запуск только включённых аккаунтов.
8. Проверить остановку всех ботов из GUI.
9. Проверить single-instance: второй запуск должен показать предупреждение и не открыть второй экземпляр.
10. Проверить, что логи пишутся в `%LOCALAPPDATA%\MarketplaceBot\logs`.
11. После сохранения настроек снова запустить приложение и убедиться, что ключи корректно подхватываются.

## Ключевые файлы

```text
MarketplaceBot/
├── MarketplaceBot.spec
├── build.bat
├── requirements.txt
├── requirements-build.txt
├── runtime_paths.py
├── runtime_assets.py
├── secure_storage.py
├── single_instance.py
├── config.py
├── main.py
├── api/
├── bots/
├── gui/
├── settings/
├── tests/
└── utils/
```

## Ограничения до финального релиза

- Windows packaging flow подготовлен, но не заменяет реальный smoke на Win10/11.
- Инсталлятора и code signing пока нет.
- Нет автосборки через CI.
- Нет подписанного релизного артефакта.

## Лицензия

Проект распространяется под лицензией MIT. См. [LICENSE](LICENSE).
