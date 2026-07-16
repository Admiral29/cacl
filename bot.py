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

# Импортируем игровые данные
from game_data import (
    hero_cum, skill_cum, star_cum, star_levels,
    gear_cum_stones, gear_cum_grass, gear_cum_steel,
    adv_cum_stones, adv_cum_blueprints, adv_cum_steel, adv_steps
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- Конфигурация ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

ALLOWED_THREAD_ID = os.getenv("ALLOWED_THREAD_ID")
if ALLOWED_THREAD_ID:
    try:
        ALLOWED_THREAD_ID = int(ALLOWED_THREAD_ID)
    except ValueError:
        ALLOWED_THREAD_ID = None

# ---------- Состояния для ConversationHandler ----------
TYPE, MODE, INPUT_FROM, INPUT_REV, INPUT_COUNT, INPUT_COUNT_REV = range(6)

# ---------- Вспомогательные функции ----------
def fmt(n: int) -> str:
    """Форматирует число с разделением тысяч пробелами."""
    return f"{n:,}".replace(",", " ")

def is_allowed(update: Update) -> bool:
    """Проверяет, разрешён ли чат/топик."""
    if ALLOWED_THREAD_ID is None:
        return True
    if update.effective_chat.type == 'private':
        return True
    thread_id = update.effective_message.message_thread_id
    return thread_id == ALLOWED_THREAD_ID

# ---------- Функции расчётов ----------
def calc_hero_direct(from_lvl: int, to_lvl: int, count: int) -> str:
    if not (1 <= from_lvl < to_lvl <= 150):
        raise ValueError("Уровни должны быть от 1 до 150, причём текущий меньше целевого.")
    need = hero_cum[to_lvl] - hero_cum[from_lvl]
    total = need * count
    return f"💊 Противоядие: {fmt(total)} (на {count} героев)"

def calc_hero_reverse(from_lvl: int, res: int, count: int) -> str:
    if from_lvl < 1 or from_lvl >= 150:
        raise ValueError("Текущий уровень должен быть от 1 до 149.")
    res_per = res // count
    max_lvl = from_lvl
    for lvl in range(from_lvl + 1, 151):
        if (hero_cum[lvl] - hero_cum[from_lvl]) <= res_per:
            max_lvl = lvl
        else:
            break
    used_per = hero_cum[max_lvl] - hero_cum[from_lvl]
    used_total = used_per * count
    rem = res - used_total
    return (f"📊 Имея {fmt(res)} противоядия (на {count} героев), можно поднять каждого до {max_lvl} уровня.\n"
            f"Потребуется всего: {fmt(used_total)}, останется: {fmt(rem)}.")

def calc_skill_direct(from_lvl: int, to_lvl: int, count: int) -> str:
    if not (1 <= from_lvl < to_lvl <= 30):
        raise ValueError("Уровни навыка должны быть от 1 до 30, причём текущий меньше целевого.")
    need = skill_cum[to_lvl] - skill_cum[from_lvl]
    total = need * count
    return f"📘 Значки навыка: {fmt(total)} (на {count} навыков)"

def calc_skill_reverse(from_lvl: int, res: int, count: int) -> str:
    if from_lvl < 1 or from_lvl >= 30:
        raise ValueError("Текущий уровень должен быть от 1 до 29.")
    res_per = res // count
    max_lvl = from_lvl
    for lvl in range(from_lvl + 1, 31):
        if (skill_cum[lvl] - skill_cum[from_lvl]) <= res_per:
            max_lvl = lvl
        else:
            break
    used_per = skill_cum[max_lvl] - skill_cum[from_lvl]
    used_total = used_per * count
    rem = res - used_total
    return (f"📊 Имея {fmt(res)} значков (на {count} навыков), можно поднять каждый до {max_lvl} уровня.\n"
            f"Потребуется всего: {fmt(used_total)}, останется: {fmt(rem)}.")

def calc_stars_direct(from_star: float, to_star: float, count: int) -> str:
    if from_star not in star_cum or to_star not in star_cum:
        raise ValueError("Звезда должна быть от 0 до 10 с шагом 0.2.")
    if from_star >= to_star:
        raise ValueError("Текущая звезда должна быть меньше целевой.")
    need = star_cum[to_star] - star_cum[from_star]
    total = need * count
    return f"🧩 Фрагменты: {fmt(total)} (на {count} героев)"

def calc_stars_reverse(from_star: float, res: int, count: int) -> str:
    if from_star not in star_cum:
        raise ValueError("Некорректная текущая звезда.")
    if from_star == 10.0:
        raise ValueError("Звезда уже максимальная.")
    res_per = res // count
    max_star = from_star
    for s in star_levels:
        if s <= from_star:
            continue
        if (star_cum[s] - star_cum[from_star]) <= res_per:
            max_star = s
        else:
            break
    used_per = star_cum[max_star] - star_cum[from_star]
    used_total = used_per * count
    rem = res - used_total
    return (f"📊 Имея {fmt(res)} фрагментов (на {count} героев), можно поднять звезду каждого до {max_star}.\n"
            f"Потребуется всего: {fmt(used_total)}, останется: {fmt(rem)}.")

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

def calc_gear_reverse(from_lvl: int, stones: int, grass: int, steel: int, count: int) -> str:
    if from_lvl < 1 or from_lvl >= 60:
        raise ValueError("Текущий уровень должен быть от 1 до 59.")
    stones_per = stones // count
    grass_per = grass // count
    steel_per = steel // count
    max_lvl = from_lvl
    for lvl in range(from_lvl + 1, 61):
        need_st = gear_cum_stones[lvl] - gear_cum_stones[from_lvl]
        need_gr = gear_cum_grass[lvl] - gear_cum_grass[from_lvl]
        need_stl = gear_cum_steel[lvl] - gear_cum_steel[from_lvl]
        if need_st <= stones_per and need_gr <= grass_per and need_stl <= steel_per:
            max_lvl = lvl
        else:
            break
    used_st = (gear_cum_stones[max_lvl] - gear_cum_stones[from_lvl]) * count
    used_gr = (gear_cum_grass[max_lvl] - gear_cum_grass[from_lvl]) * count
    used_stl = (gear_cum_steel[max_lvl] - gear_cum_steel[from_lvl]) * count
    rem_st = stones - used_st
    rem_gr = grass - used_gr
    rem_stl = steel - used_stl
    return (f"📊 Имеющихся ресурсов хватит для поднятия каждого снаряжения (всего {count} шт.) "
            f"с {from_lvl} до {max_lvl} уровня.\n"
            f"Потребуется всего: камней {fmt(used_st)}, травы {fmt(used_gr)}, стали {fmt(used_stl)}.\n"
            f"Останется: камней {fmt(rem_st)}, травы {fmt(rem_gr)}, стали {fmt(rem_stl)}.")

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

def calc_advgear_reverse(from_star: float, stones: int, blueprints: int, steel: int, count: int) -> str:
    if from_star not in adv_cum_stones:
        raise ValueError("Некорректная текущая звезда.")
    if from_star == 5.0:
        raise ValueError("Звезда уже максимальная.")
    stones_per = stones // count
    bp_per = blueprints // count
    steel_per = steel // count
    max_star = from_star
    for s in adv_steps:
        if s <= from_star:
            continue
        need_st = adv_cum_stones[s] - adv_cum_stones[from_star]
        need_bp = adv_cum_blueprints[s] - adv_cum_blueprints[from_star]
        need_stl = adv_cum_steel[s] - adv_cum_steel[from_star]
        if need_st <= stones_per and need_bp <= bp_per and need_stl <= steel_per:
            max_star = s
        else:
            break
    used_st = (adv_cum_stones[max_star] - adv_cum_stones[from_star]) * count
    used_bp = (adv_cum_blueprints[max_star] - adv_cum_blueprints[from_star]) * count
    used_stl = (adv_cum_steel[max_star] - adv_cum_steel[from_star]) * count
    rem_st = stones - used_st
    rem_bp = blueprints - used_bp
    rem_stl = steel - used_stl
    msg = (f"📊 Имеющихся ресурсов хватит для поднятия каждого продвинутого снаряжения (всего {count} шт.) "
           f"с {from_star} до {max_star} звезды.\n"
           f"Потребуется всего: камней {fmt(used_st)}, чертежей {fmt(used_bp)}, стали {fmt(used_stl)}.\n"
           f"Останется: камней {fmt(rem_st)}, чертежей {fmt(rem_bp)}, стали {fmt(rem_stl)}.")
    if max_star >= 4.2:
        msg += "\n* С 4 звезды требуются чертежи MR качества."
    return msg

# ---------- Обработчики команд ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    keyboard = [
        [InlineKeyboardButton("Герой (противоядие)", callback_data="hero")],
        [InlineKeyboardButton("Навык (значки)", callback_data="skill")],
        [InlineKeyboardButton("Звёзды героя (фрагменты)", callback_data="stars")],
        [InlineKeyboardButton("Обычное снаряжение", callback_data="gear")],
        [InlineKeyboardButton("Продвинутое снаряжение", callback_data="advgear")],
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
    await update.message.reply_text(
        "📖 Помощь по калькулятору:\n\n"
        "1. Нажмите /start, чтобы выбрать тип развития.\n"
        "2. Выберите прямой или обратный расчёт.\n"
        "3. Введите запрашиваемые числа через пробел.\n"
        "4. Затем введите количество (сколько единиц прокачиваете).\n"
        "5. /cancel – отменить текущий расчёт.\n\n"
        "Доступные типы:\n"
        "• Герой (противоядие) – уровни 1..150\n"
        "• Навык (значки) – уровни 1..30\n"
        "• Звёзды героя (фрагменты) – 0..10, шаг 0.2\n"
        "• Обычное снаряжение – уровни 1..60\n"
        "• Продвинутое снаряжение – 0..5, шаг 0.2\n\n"
        "⚠️ Числа вводите без разделителей, например 5000, а не 5 000."
    )

async def type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    keyboard = [
        [InlineKeyboardButton("Прямой расчёт (по уровням)", callback_data="direct")],
        [InlineKeyboardButton("Обратный расчёт (по ресурсам)", callback_data="reverse")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите режим расчёта:", reply_markup=reply_markup)
    return MODE

async def mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    query = update.callback_query
    await query.answer()
    context.user_data['mode'] = query.data
    t = context.user_data['type']
    if query.data == "direct":
        messages = {
            "hero": "Введите текущий уровень и целевой уровень через пробел (например: 2 10)\nИли /cancel для отмены.",
            "skill": "Введите текущий уровень навыка и целевой через пробел (например: 1 5)\nИли /cancel для отмены.",
            "stars": "Введите текущую звезду и целевую звезду через пробел (например: 0 8)\nИли /cancel для отмены.",
            "gear": "Введите текущий уровень снаряжения и целевой через пробел (например: 1 10)\nИли /cancel для отмены.",
            "advgear": "Введите текущую звезду и целевую звезду через пробел (например: 0 5)\nИли /cancel для отмены.",
        }
        await query.edit_message_text(messages[t])
        return INPUT_FROM
    else:
        messages = {
            "hero": "Введите текущий уровень и количество противоядия через пробел (например: 1 5000)\nИли /cancel для отмены.",
            "skill": "Введите текущий уровень навыка и количество значков через пробел (например: 1 1000)\nИли /cancel для отмены.",
            "stars": "Введите текущую звезду и количество фрагментов через пробел (например: 0 100)\nИли /cancel для отмены.",
            "gear": "Введите текущий уровень, затем камни, траву, сталь через пробел (например: 1 1500 180000 0)\nИли /cancel для отмены.",
            "advgear": "Введите текущую звезду, затем камни, чертежи, сталь через пробел (например: 0 2500 1 30)\nИли /cancel для отмены.",
        }
        await query.edit_message_text(messages[t])
        return INPUT_REV

# ---------- Прямой расчёт (два числа) ----------
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
        await update.message.reply_text("Теперь введите количество (сколько героев/навыков/снаряжения прокачиваете):")
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

# ---------- Обратный расчёт ----------
async def reverse_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        parts = update.message.text.split()
        t = context.user_data['type']
        if t in ("hero", "skill", "stars"):
            if len(parts) != 2:
                raise ValueError("Требуется два числа: текущий уровень и количество ресурса.")
            context.user_data['rev_from'] = parts[0]
            context.user_data['rev_res'] = parts[1]
        elif t in ("gear", "advgear"):
            if len(parts) != 4:
                raise ValueError("Требуется четыре числа: текущий уровень/звезда и три ресурса.")
            context.user_data['rev_from'] = parts[0]
            context.user_data['rev_stones'] = parts[1]
            context.user_data['rev_grass'] = parts[2] if t == "gear" else None
            context.user_data['rev_blueprints'] = parts[2] if t == "advgear" else None
            context.user_data['rev_steel'] = parts[3]
        else:
            raise ValueError("Неизвестный тип.")
        await update.message.reply_text("Теперь введите количество (сколько героев/навыков/снаряжения):")
        return INPUT_COUNT_REV
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return INPUT_REV

async def reverse_count_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        count = int(update.message.text)
        if count < 1:
            await update.message.reply_text("Количество должно быть больше 0. Попробуйте снова.")
            return INPUT_COUNT_REV
        t = context.user_data['type']
        if t == "hero":
            from_lvl = int(context.user_data['rev_from'])
            res = int(context.user_data['rev_res'])
            result = calc_hero_reverse(from_lvl, res, count)
        elif t == "skill":
            from_lvl = int(context.user_data['rev_from'])
            res = int(context.user_data['rev_res'])
            result = calc_skill_reverse(from_lvl, res, count)
        elif t == "stars":
            from_star = float(context.user_data['rev_from'])
            res = int(context.user_data['rev_res'])
            result = calc_stars_reverse(from_star, res, count)
        elif t == "gear":
            from_lvl = int(context.user_data['rev_from'])
            stones = int(context.user_data['rev_stones'])
            grass = int(context.user_data['rev_grass'])
            steel = int(context.user_data['rev_steel'])
            result = calc_gear_reverse(from_lvl, stones, grass, steel, count)
        elif t == "advgear":
            from_star = float(context.user_data['rev_from'])
            stones = int(context.user_data['rev_stones'])
            blueprints = int(context.user_data['rev_blueprints'])
            steel = int(context.user_data['rev_steel'])
            result = calc_advgear_reverse(from_star, stones, blueprints, steel, count)
        else:
            result = "Неизвестный тип."
        await update.message.reply_text(result)
        await update.message.reply_text("Расчёт выполнен. Напишите /start для нового расчёта или /cancel для выхода.")
        return ConversationHandler.END
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return INPUT_COUNT_REV
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Ошибка ввода. Попробуйте ещё раз или /cancel.")
        return INPUT_COUNT_REV

# ---------- Главная функция ----------
async def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TYPE: [CallbackQueryHandler(type_selected)],
            MODE: [CallbackQueryHandler(mode_selected)],
            INPUT_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_input)],
            INPUT_REV: [MessageHandler(filters.TEXT & ~filters.COMMAND, reverse_input)],
            INPUT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_count_input)],
            INPUT_COUNT_REV: [MessageHandler(filters.TEXT & ~filters.COMMAND, reverse_count_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    # Установка команд бота
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
