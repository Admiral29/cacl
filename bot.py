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
    awakening_cum,
    star_weapon_cum
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

AUTHOR_CONTACT = os.getenv("AUTHOR_CONTACT", "@your_username")

CATEGORY, TYPE, INPUT_FROM, INPUT_COUNT = range(4)

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
    if not (1 <= from_lvl < to_lvl <= 40):
        raise ValueError("Уровни навыка должны быть от 1 до 40, причём текущий меньше целевого.")
    need = skill_cum[to_lvl] - skill_cum[from_lvl]
    total = need * count
    return f"📘 Значки навыка: {fmt(total)} (на {count} навыков)"

def calc_stars_hero_direct(from_star: float, to_star: float, count: int) -> str:
    if from_star not in star_cum or to_star not in star_cum:
        raise ValueError("Звезда должна быть от 0 до 10 с шагом 0.2.")
    if from_star >= to_star:
        raise ValueError("Текущая звезда должна быть меньше целевой.")
    need = star_cum[to_star] - star_cum[from_star]
    total = need * count
    return f"🧩 Фрагменты (звёзды героя): {fmt(total)} (на {count} героев)"

def calc_stars_weapon_direct(from_star: float, to_star: float, count: int) -> str:
    if from_star not in star_weapon_cum or to_star not in star_weapon_cum:
        raise ValueError("Звезда должна быть от 0 до 10 с шагом 0.2.")
    if from_star >= to_star:
        raise ValueError("Текущая звезда должна быть меньше целевой.")
    need = star_weapon_cum[to_star] - star_weapon_cum[from_star]
    total = need * count
    return f"🧩 Фрагменты (звёзды экс.оружия): {fmt(total)} (на {count} оружий)"

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
        [InlineKeyboardButton("👤 Герой", callback_data="cat_hero")],
        [InlineKeyboardButton("🛡 Снаряжение", callback_data="cat_gear")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)
    return CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    query = update.callback_query
    await query.answer()
    category = query.data
    context.user_data['category'] = category
    if category == "cat_hero":
        keyboard = [
            [InlineKeyboardButton("Уровни героя", callback_data="hero")],
            [InlineKeyboardButton("Навыки героя", callback_data="skill")],
            [InlineKeyboardButton("Звёзды героя", callback_data="stars_hero")],
            [InlineKeyboardButton("Пробуждение", callback_data="awakening")],
        ]
    else:  # cat_gear
        keyboard = [
            [InlineKeyboardButton("Уровни снаряжения", callback_data="gear")],
            [InlineKeyboardButton("Звёзды снаряжения", callback_data="advgear")],
            [InlineKeyboardButton("Звёзды экс.оружия", callback_data="stars_weapon")],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите тип развития:", reply_markup=reply_markup)
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
        "1. Нажмите /start, выберите категорию (Герой или Снаряжение).\n"
        "2. Выберите тип развития.\n"
        "3. Введите текущий и целевой уровни/звёзды через пробел.\n"
        "4. Введите количество (сколько единиц прокачиваете).\n"
        "5. /cancel – отменить текущий расчёт.\n\n"
        "Категория «Герой»:\n"
        "• Уровни героя (противоядие) – 1..150\n"
        "• Навыки героя (значки) – 1..40\n"
        "• Звёзды героя (фрагменты) – 0..10, шаг 0.2\n"
        "• Пробуждение (фрагменты) – 0..40\n\n"
        "Категория «Снаряжение»:\n"
        "• Уровни снаряжения – 1..60\n"
        "• Звёзды снаряжения – 0..5, шаг 0.2\n"
        "• Звёзды экс.оружия (фрагменты) – 0..10, шаг 0.2 (первый шаг 30)\n\n"
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
        "hero": "Введите текущий уровень героя и целевой уровень через пробел (например: 2 10).\nДопустимые уровни: от 1 до 150, текущий < целевой.\nИли /cancel для отмены.",
        "skill": "Введите текущий уровень навыка и целевой через пробел (например: 1 35).\nДопустимые уровни: от 1 до 40, текущий < целевой.\nИли /cancel для отмены.",
        "stars_hero": "Введите текущую звезду героя и целевую через пробел (например: 0 8).\nДопустимые значения: от 0 до 10 с шагом 0.2.\nИли /cancel для отмены.",
        "stars_weapon": "Введите текущую звезду экс.оружия и целевую через пробел (например: 0 8).\nДопустимые значения: от 0 до 10 с шагом 0.2.\nИли /cancel для отмены.",
        "gear": "Введите текущий уровень снаряжения и целевой через пробел (например: 1 10).\nДопустимые уровни: от 1 до 60, текущий < целевой.\nИли /cancel для отмены.",
        "advgear": "Введите текущую звезду снаряжения и целевую звезду через пробел (например: 0 5).\nДопустимые значения: от 0 до 5 с шагом 0.2.\nИли /cancel для отмены.",
        "awakening": "Введите текущий уровень пробуждения и целевой через пробел (например: 0 10).\nДопустимые уровни: от 0 до 40, текущий < целевой.\nИли /cancel для отмены.",
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

        # Преобразование с проверкой допустимых значений
        if t == "hero":
            from_lvl = int(a)
            to_lvl = int(b)
            if not (1 <= from_lvl < to_lvl <= 150):
                raise ValueError("Уровни героя должны быть от 1 до 150, причём текущий меньше целевого.")
            result = calc_hero_direct(from_lvl, to_lvl, count)
        elif t == "skill":
            from_lvl = int(a)
            to_lvl = int(b)
            if not (1 <= from_lvl < to_lvl <= 40):
                raise ValueError("Уровни навыка должны быть от 1 до 40, причём текущий меньше целевого.")
            result = calc_skill_direct(from_lvl, to_lvl, count)
        elif t == "stars_hero":
            from_star = float(a)
            to_star = float(b)
            if from_star not in star_cum or to_star not in star_cum:
                raise ValueError("Звезда должна быть от 0 до 10 с шагом 0.2.")
            if from_star >= to_star:
                raise ValueError("Текущая звезда должна быть меньше целевой.")
            result = calc_stars_hero_direct(from_star, to_star, count)
        elif t == "stars_weapon":
            from_star = float(a)
            to_star = float(b)
            if from_star not in star_weapon_cum or to_star not in star_weapon_cum:
                raise ValueError("Звезда должна быть от 0 до 10 с шагом 0.2.")
            if from_star >= to_star:
                raise ValueError("Текущая звезда должна быть меньше целевой.")
            result = calc_stars_weapon_direct(from_star, to_star, count)
        elif t == "gear":
            from_lvl = int(a)
            to_lvl = int(b)
            if not (1 <= from_lvl < to_lvl <= 60):
                raise ValueError("Уровни снаряжения должны быть от 1 до 60, причём текущий меньше целевого.")
            result = calc_gear_direct(from_lvl, to_lvl, count)
        elif t == "advgear":
            from_star = float(a)
            to_star = float(b)
            if from_star not in adv_cum_stones or to_star not in adv_cum_stones:
                raise ValueError("Звезда должна быть от 0 до 5 с шагом 0.2.")
            if from_star >= to_star:
                raise ValueError("Текущая звезда должна быть меньше целевой.")
            result = calc_advgear_direct(from_star, to_star, count)
        elif t == "awakening":
            from_lvl = int(a)
            to_lvl = int(b)
            if not (0 <= from_lvl < to_lvl <= 40):
                raise ValueError("Уровни пробуждения должны быть от 0 до 40, причём текущий меньше целевого.")
            result = calc_awakening_direct(from_lvl, to_lvl, count)
        else:
            result = "Неизвестный тип."
        await update.message.reply_text(result)
        await update.message.reply_text("Расчёт выполнен. Напишите /start для нового расчёта или /cancel для выхода.")
        return ConversationHandler.END
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return INPUT_COUNT
    except KeyError as e:
        await update.message.reply_text(f"❌ Ошибка: значение {e} недопустимо. Проверьте диапазон и попробуйте снова.")
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
            CATEGORY: [CallbackQueryHandler(category_selected)],
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
