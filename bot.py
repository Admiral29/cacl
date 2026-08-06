import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from game_data import (
    hero_cum, skill_cum, star_cum, star_levels,
    gear_cum_stones, gear_cum_grass, gear_cum_steel,
    adv_cum_stones, adv_cum_blueprints, adv_cum_steel, adv_steps,
    awakening_cum
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

ALLOWED_THREAD_ID = os.getenv("ALLOWED_THREAD_ID")
if ALLOWED_THREAD_ID:
    try:
        ALLOWED_THREAD_ID = int(ALLOWED_THREAD_ID)
    except ValueError:
        ALLOWED_THREAD_ID = None

# Контакт автора — читаем из переменной окружения или задаём здесь по умолчанию
AUTHOR_CONTACT = os.getenv("AUTHOR_CONTACT", "@your_username")  # Замените при необходимости

TYPE, INPUT_FROM, INPUT_COUNT = range(3)

def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")

def is_allowed(update: Update) -> bool:
    if ALLOWED_THREAD_ID is None:
        return True
    if update.effective_chat.type == 'private':
        return True
    thread_id = update.effective_message.message_thread_id
    return thread_id == ALLOWED_THREAD_ID

# ---------- Функции расчёта ----------
def calc_hero_direct(from_lvl: int, to_lvl: int, count: int) -> str:
    if not (1 <= from_lvl < to_lvl <= 150):
        raise ValueError("Уровни героя должны быть от 1 до 150, причём текущий меньше целевого.")
    need = hero_cum[to_lvl] - hero_cum[from_lvl]
    total = need * count
    return f"💊 Противоядие: {fmt(total)} (на {count} героев)"

def calc_skill_direct(from_lvl: int, to_lvl: int, count: int) -> str:
    if not (1 <= from_lvl < to_lvl <= 35):
        raise ValueError("Уровни навыка должны быть от 1 до 35, причём текущий меньше целевого.")
    need = skill_cum[to_lvl] - skill_cum[from_lvl]
    total = need * count
    return f"📘 Значки навыка: {fmt(total)} (на {count} навыков)"

def calc_stars_direct(from_star: float, to_star: float, count: int) -> str:
    if from_star not in star_cum or to_star not in star_cum:
        raise ValueError("Звезда должна быть от 0 до 10 с шагом 0.2.")
    if from_star >= to_star:
        raise ValueError("Текущая звезда должна быть меньше целевой.")
    need = star_cum[to_star] - star_cum[from_star]
    total = need * count
    # Уточняем, что это для оружия или героя
    return f"🧩 Фрагменты (звёзды экс.оружия/героя): {fmt(total)} (на {count} шт.)"

def calc_gear_direct(from_lvl: int, to_lvl: int, count: int) -> str:
    if not (1 <= from_lvl < to_lvl <= 60):
        raise ValueError("Уровни снаряжения должны быть от 1 до 60, причём текущий меньше целевого.")
    stones = (gear_cum_stones[to_lvl] - gear_cum_stones[from_lvl]) * count
    grass = (gear_cum_grass[to_lvl] - gear_cum_grass[from_lvl]) * count
    steel = (gear_cum_steel[to_lvl] - gear_cum_steel[from_lvl]) * count
    return (f"💎 Камни снаряжения: {fmt(stones)}\n"
            f"🌿 Трава: {fmt(grass)}\n"
            f"⚙️ Закалённая сталь: {fmt(steel)}\n"
            f"(на {count} снаряжений)")

def calc_advgear_direct(from_star: float, to_star: float, count: int) -> str:
    if from_star not in adv_cum_stones or to_star not in adv_cum_stones:
        raise ValueError("Звезда должна быть от 0 до 5 с шагом 0.2.")
    if from_star >= to_star:
        raise ValueError("Текущая звезда должна быть меньше целевой.")
    stones = (adv_cum_stones[to_star] - adv_cum_stones[from_star]) * count
    bp = (adv_cum_blueprints[to_star] - adv_cum_blueprints[from_star]) * count
    steel = (adv_cum_steel[to_star] - adv_cum_steel[from_star]) * count
    msg = (f"💎 Камни снаряжения: {fmt(stones)}\n"
           f"📜 Чертежи: {fmt(bp)}\n"
           f"⚙️ Закалённая сталь: {fmt(steel)}\n"
           f"(на {count} снаряжений)")
    if to_star >= 4.2:
        msg += "\n* С 4 звёзды требуются чертежи MR качества."
    return msg

def calc_awakening_direct(from_lvl: int, to_lvl: int, count: int) -> str:
    if not (0 <= from_lvl < to_lvl <= 40):
        raise ValueError("Уровни пробуждения должны быть от 0 до 40, причём текущий меньше целевого.")
    need = awakening_cum[to_lvl] - awakening_cum[from_lvl]
    total = need * count
    return f"🌀 Фрагменты пробуждения: {fmt(total)} (на {count} героев)"

# ---------- Обработчики ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    keyboard = [
        [InlineKeyboardButton("Уровни героя", callback_data="hero")],
        [InlineKeyboardButton("Навыки героя", callback_data="skill")],
        [InlineKeyboardButton("Звёзды экс.оружия/героя", callback_data="stars")],
        [InlineKeyboardButton("Уровни снаряжения", callback_data="gear")],
        [InlineKeyboardButton("Звёзды снаряжения", callback_data="advgear")],
        [InlineKeyboardButton("Пробуждение", callback_data="awakening")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите тип развития:", reply_markup=reply_markup)
    return TYPE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("Расчёт отменён. Напишите /start, чтобы начать заново.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    help_text = (
        "📖 Помощь по калькулятору:\n\n"
        "1. Нажмите /start, чтобы выбрать тип развития.\n"
        "2. Введите текущий и целевой уровни/звёзды через пробел.\n"
        "3. Введите количество (сколько единиц прокачиваете).\n"
        "4. /cancel – отменить текущий расчёт.\n\n"
        "Доступные типы:\n"
        "• Уровни героя (противоядие) – 1..150\n"
        "• Навыки героя (значки) – 1..35\n"
        "• Звёзды экс.оружия/героя (фрагменты) – 0..10, шаг 0.2\n"
        "• Уровни снаряжения – 1..60\n"
        "• Звёзды снаряжения – 0..5, шаг 0.2\n"
        "• Пробуждение (фрагменты) – 0..40\n\n"
        "⚠️ Числа вводите без разделителей, например 5000, а не 5 000.\n\n"
        f"По вопросам и проблемам обращайтесь: {AUTHOR_CONTACT}"
    )
    await update.message.reply_text(help_text)

async def type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    t = query.data
    messages = {
        "hero": "Введите текущий уровень героя и целевой уровень через пробел (например: 2 10)\nИли /cancel для отмены.",
        "skill": "Введите текущий уровень навыка и целевой через пробел (например: 1 5)\nИли /cancel для отмены.",
        "stars": "Введите текущую звезду (для экс.оружия или героя) и целевую звезду через пробел (например: 0 8)\nИли /cancel для отмены.",
        "gear": "Введите текущий уровень снаряжения и целевой через пробел (например: 1 10)\nИли /cancel для отмены.",
        "advgear": "Введите текущую звезду снаряжения и целевую звезду через пробел (например: 0 5)\nИли /cancel для отмены.",
        "awakening": "Введите текущий уровень пробуждения и целевой через пробел (например: 0 10)\nИли /cancel для отмены.",
    }
    await query.edit_message_text(messages[t])
    return INPUT_FROM

async def direct_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text("Нужно два числа через пробел. Попробуйте ещё раз или /cancel для отмены.")
            return INPUT_FROM
        context.user_data['from_val'] = parts[0]
        context.user_data['to_val'] = parts[1]
        await update.message.reply_text("Теперь введите количество (сколько героев/навыков/снаряжения/оружия прокачиваете):")
        return INPUT_COUNT
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Неверный формат. Попробуйте ещё раз или /cancel.")
        return INPUT_FROM

async def direct_count_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        count = int(update.message.text)
        if count < 1:
            await update.message.reply_text("Количество должно быть больше 0. Попробуйте снова.")
            return INPUT_COUNT
        t = context.user_data['type']
        a = context.user_data['from_val']
        b = context.user_data['to_val']
        if t == "hero":
            result = calc_hero_direct(int(a), int(b), count)
        elif t == "skill":
            result = calc_skill_direct(int(a), int(b), count)
        elif t == "stars":
            result = calc_stars_direct(float(a), float(b), count)
        elif t == "gear":
            result = calc_gear_direct(int(a), int(b), count)
        elif t == "advgear":
            result = calc_advgear_direct(float(a), float(b), count)
        elif t == "awakening":
            result = calc_awakening_direct(int(a), int(b), count)
        else:
            result = "Неизвестный тип."
        await update.message.reply_text(result)
        await update.message.reply_text("Расчёт выполнен. Напишите /start для нового расчёта или /cancel для выхода.")
        return ConversationHandler.END
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return INPUT_COUNT
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Ошибка ввода. Попробуйте ещё раз или /cancel.")
        return INPUT_COUNT

# ---------- Запуск ----------
async def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TYPE: [CallbackQueryHandler(type_selected)],
            INPUT_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_input)],
            INPUT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_count_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    await app.initialize()
    await app.bot.set_my_commands([
        ("start", "Запустить калькулятор"),
        ("help", "Помощь"),
        ("cancel", "Отменить расчёт"),
    ])
    await app.start()
    logger.info("Бот запущен...")
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
