# Scopa Bot

Автоматизований бот для гри в Scopa на Betsson.it з AI decision engine.

## ✅ Реалізовано

1. **Login Workflow** - автентифікація з обробкою cookie banner
2. **Proxy Support** - робота через проксі
3. **Game Frame Detection** - автоматичне знаходження iframe з грою
4. **Lobby Navigation** - відкриття "мої столів"
5. **Room Selection** - вибір кімнати 0.5-1 євро
6. **Game State Reader** - парсинг карт з DOM (масти, значення)
7. **Move Executor** - виконання ходів через Playwright
8. **Engine Adapter** - підключення decision engine
9. **Game Controller** - повний game loop
10. **Enhanced Selectors** - розширена система селекторів для кнопки "Vai al tavolo"

## 🚀 Швидкий старт

### 1. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 2. Налаштування .env

Створіть файл `.env` в корені проекту:

```env
# Обов'язкові налаштування
BOT_USERNAME=GUIDO123
BOT_PASSWORD=your_password

# Опціональні налаштування
DEBUG=true                    # Увімкнути debug mode (screenshots, detailed logs)
USE_PROXY=false              # Використовувати проксі
PROXY_SERVER=http://proxy:port
PROXY_USERNAME=user
PROXY_PASSWORD=pass

# ShardX (анти-детект браузер)
SHARDX_ENABLED=false
SHARDX_API_URL=http://127.0.0.1:40325
SHARDX_API_TOKEN=your_token
SHARDX_PROFILE_ID=profile_id
```

### 3. Запуск бота

```bash
cd src
python main.py
```

## 📋 Структура проекту

```
project/
├── src/
│   ├── browser/          # Browser automation
│   │   ├── browser.py    # Browser wrapper
│   │   ├── selectors.py  # DOM selectors
│   │   └── SELECTORS_GUIDE.md  # Selector documentation
│   ├── config/           # Configuration
│   │   ├── config.py     # Config loader
│   │   └── exceptions.py # Custom exceptions
│   ├── game/             # Game logic
│   │   ├── controller.py # Game loop controller
│   │   ├── reader.py     # Game state reader
│   │   ├── executor.py   # Move executor
│   │   └── adapter.py    # Engine adapter
│   ├── workflows/        # Workflows
│   │   ├── login.py      # Login workflow
│   │   └── lobby.py      # Lobby navigation
│   └── main.py           # Entry point
├── engine/               # AI Decision Engine
│   ├── cards/            # Card models
│   ├── decision_engine/  # Decision making
│   ├── game_state/       # Game state
│   ├── game_tree/        # Game tree search
│   ├── moves/            # Move models
│   ├── opponent_model/   # Opponent modeling
│   ├── probabilities/   # Probability calculations
│   ├── rules/            # Game rules
│   ├── scoring/          # Scoring system
│   └── simulation/       # Game simulation
└── .env                  # Environment variables
```

## 🔧 Налаштування селекторів

Якщо бот не знаходить кнопку "Vai al tavolo" або "Iscriviti":

1. Увімкніть `DEBUG=true` в `.env`
2. Запустіть бота - створяться screenshots
3. Відкрийте `debug-scopa-page.png` або `debug-join-game.png`
4. Інспектуйте DOM через browser dev tools
5. Додайте нові селектори в `src/browser/selectors.py`

**Примітка**: Кнопка для входу в стіл може мати різні назви:
- "Vai al tavolo" (Go to table)
- "Iscriviti" (Subscribe/Sign Up) - часто з'являється в списку столів у розділі "STATO"
- "Entra" (Enter)
- "Gioca" (Play)

Дивіться `src/browser/SELECTORS_GUIDE.md` для детальної документації.

## 🎮 Workflow

1. **Login** - Вхід в акаунт
2. **Dismiss Cookie Banner** - Закриття cookie banner
3. **Navigate to Scopa** - Перехід на сторінку Scopa
4. **Select Game Variant** - Вибір Scopa Classica
5. **Open My Tables** - Відкриття списку столів
6. **Select Room** - Вибір кімнати 0.5-1 євро
7. **Join Game** - Натискання "Vai al tavolo" або "Iscriviti"
8. **Game Loop** - Автоматична гра

## 🐛 Debugging

Увімкніть debug mode для отримання screenshot:

```env
DEBUG=true
```

Screenshots будуть збережені в корені проекту:
- `debug-scopa-page.png` - сторінка після входу в Scopa
- `debug-rooms-page.png` - сторінка зі списком кімнат
- `debug-join-game.png` - сторінка перед входом в гру

## 📝 Додатково

- **Proxy Support** - Працює через HTTP/SOCKS5 проксі
- **ShardX Integration** - Анти-детект браузер (опціонально)
- **Error Handling** - Детальна обробка помилок
- **Logging** - Детальні логи для кожного кроку

## ⚠️ Important

- Використовуйте бота відповідально
- Дотримуйтесь правил сайту
- Бот створений для навчальних цілей
