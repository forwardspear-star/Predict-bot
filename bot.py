# cat > bot.py << 'EOF'
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import sys
import re

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN or ":" not in TOKEN:
    print("Ошибка: переменная окружения BOT_TOKEN не задана или некорректна.")
    print("Пример: export BOT_TOKEN=123456:ABC-DEF...")
    sys.exit(1)

# Главное меню (кнопки)
main_menu = [
    ["📅 Сегодняшние матчи"],
    ["📊 Прогноз по матчу"],
    ["⚡ Экспрессы"],
    ["❓ Помощь"]
]

# --- Упрощённый «движок» прогноза (заглушка до подключения API) ---

# Наши заранее известные примеры (можно расширять)
KNOWN_MATCHES = {
    # CS2
    ("vitality", "faze"): ("Vitality vs FaZe", 78, 22, "Состав и форма у Vitality сильнее; рынок на их стороне."),
    ("mouz", "furia"): ("MOUZ vs FURIA", 62, 38, "MOUZ сильнее по форме, H2H и по рынку."),
    ("team spirit", "g2"): ("Team Spirit vs G2", 75, 25, "Spirit на серии, сильный костяк; G2 нестабильнее."),
    # Футбол (пример)
    ("real madrid", "barcelona"): ("Real Madrid vs Barcelona", 40, 60, "Форма Барсы выше (пример)."),
}

def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())

def parse_match_name(text: str):
    # ожидаем форматы вида: "КомандаA vs КомандаB" или "КомандаA - КомандаB"
    m = re.split(r"\bvs\b|–|-|—", text, flags=re.IGNORECASE)
    if len(m) >= 2:
        a = normalize_name(m[0])
        b = normalize_name(m[1])
        return a, b
    return None, None

def predict_stub(query: str):
    a, b = parse_match_name(query)
    if not a or not b:
        return None

    key = (a, b)
    key_rev = (b, a)
    if key in KNOWN_MATCHES:
        title, pA, pB, note = KNOWN_MATCHES[key]
        sideA, sideB = title.split(" vs ")
        return title, sideA, pA, sideB, pB, note
    if key_rev in KNOWN_MATCHES:
        title, pB, pA, note = KNOWN_MATCHES[key_rev]
        sideB, sideA = title.split(" vs ")
        # Поменяем местами, чтобы отражать порядок запроса пользователя
        return f"{a.title()} vs {b.title()}", a.title(), pA, b.title(), pB, note

    # Если матча нет в списке — отдаём аккуратную заглушку по нашему шаблону
    A = a.title()
    B = b.title()
    # нейтральная оценка (до подключения реальных данных)
    pA, pB = 50, 50
    note = "Пока без данных: нужен сбор статистики и коэффициентов. Это заглушка до подключения API."
    return f"{A} vs {B}", A, pA, B, pB, note

# --- Обработчики команд и сообщений ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот спортивных прогнозов ⚽🎮\nВыбери действие:",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "❓ Как пользоваться:\n"
        "• Нажми «📅 Сегодняшние матчи» — увижишь примеры.\n"
        "• Нажми «📊 Прогноз по матчу» — пришли название матча в формате:\n"
        "  Пример: Vitality vs FaZe\n"
        "• «⚡ Экспрессы» — пример комбинированного прогноза.\n\n"
        "Скоро добавим реальные данные и авто-рассылку."
    )
    await update.message.reply_text(msg)

async def todays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📅 Примеры матчей на сегодня (демо):\n"
        "• Vitality vs FaZe\n"
        "• MOUZ vs FURIA\n"
        "• Team Spirit vs G2\n"
        "Отправь один из этих вариантов через «📊 Прогноз по матчу»."
    )
    await update.message.reply_text(msg)

async def ask_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пришли матч в формате: «КомандаA vs КомандаB».\n"
        "Например: Vitality vs FaZe"
    )

def render_prediction_card(title: str, A: str, pA: int, B: str, pB: int, note: str) -> str:
    # Наш «шаблон карточки»
    fav = A if pA > pB else B
    return (
        f"🏆 Матч: {title}\n\n"
        f"📊 Факторы (сводка):\n"
        f"• Форма, состав, H2H, коэффициенты, психология — по нашей модели\n\n"
        f"🧮 Итоговый прогноз:\n"
        f"• {A} → {pA}%\n"
        f"• {B} → {pB}%\n\n"
        f"✅ Фаворит: {fav}\n"
        f"ℹ️ Примечание: {note}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().lower()

    if text in ["📅 сегодняшние матчи", "сегодняшние матчи", "сегодняшние"]:
        await todays(update, context)
        return
    if text in ["📊 прогноз по матчу", "прогноз по матчу", "прогноз"]:
        await ask_prediction(update, context)
        return
    if text in ["⚡ экспрессы", "экспрессы", "экспресс"]:
        await update.message.reply_text(
            "⚡ Экспресс (пример):\n"
            "• Vitality (78%) × MOUZ (62%) → ~48% общий шанс"
        )
        return
    if text in ["❓ помощь", "помощь", "/help"]:
        await help_cmd(update, context)
        return

    # Если пользователь прислал строку с «vs» — попробуем предсказать
    if " vs " in text or re.search(r"\s[-–—]\s", text):
        res = predict_stub(text)
        if res:
            title, A, pA, B, pB, note = res
            await update.message.reply_text(render_prediction_card(title, A, pA, B, pB, note))
            return

    # Фоллбек
    await update.message.reply_text(
        "Не понял 🤔\n"
        "Нажми кнопку ниже или пришли матч в формате: «КомандаA vs КомандаB».",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

def main():
    app = Application.builder() \
        .token(TOKEN) \
        .http_version("1.1") \
        .get_updates_http_version("1.1") \
        .concurrent_updates(True) \
        .build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("help", help_cmd))

    # Любой текст (кнопки/ввод)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Быстрый опрос апдейтов + сбрасываем старую очередь после рестарта
    app.run_polling(
        poll_interval=0.5,
        drop_pending_updates=True,
        close_loop=False,
    )

if __name__ == "__main__":
    main()
