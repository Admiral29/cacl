import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

# ---------- Читаем переменные окружения ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

# Опционально: ID темы (если не задан, работает везде)
ALLOWED_THREAD_ID = os.getenv("ALLOWED_THREAD_ID")
if ALLOWED_THREAD_ID:
    try:
        ALLOWED_THREAD_ID = int(ALLOWED_THREAD_ID)
    except ValueError:
        ALLOWED_THREAD_ID = None

# ---------- ДАННЫЕ (из HTML) ----------
# ... (все словари hero_cost, skill_cost, star_step, gear_*, adv_* и кумулятивные массивы)
# Они такие же, как в вашем файле, поэтому я их не дублирую для краткости,
# но в финальном коде они должны быть полностью. Я включу их в итоговый код.

# Для экономии места я покажу только изменения, но в финальном ответе дам полный код.

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def fmt(n):
    return f"{n:,.0f}".replace(",", " ")

def is_allowed(update: Update) -> bool:
    if ALLOWED_THREAD_ID is None:
        return True
    chat = update.effective_chat
    if chat.type == 'private':
        return True
    thread_id = update.effective_message.message_thread_id
    return thread_id == ALLOWED_THREAD_ID

# ---------- СОСТОЯНИЯ (расширенные) ----------
TYPE, MODE, INPUT_FROM, INPUT_TO, INPUT_REV, INPUT_COUNT, INPUT_COUNT_REV = range(7)

# ---------- ОБРАБОТЧИКИ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    keyboard = [
        [InlineKeyboardButton("Герой (противоядие)", callback_data="hero")],
        [InlineKeyboardButton("Навык (значки)", callback_data="skill")],
        [InlineKeyboardButton("Звёзды героя (фрагменты)", callback_data="stars")],
        [InlineKeyboardButton("Обычное снаряжение", callback_data="gear")],
        [InlineKeyboardButton("Продвинутое снаряжение", callback_data="advgear")]
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
        "3. Введите числа через пробел.\n"
        "4. Затем введите количество (сколько единиц прокачиваете).\n"
        "5. /cancel – отменить текущий расчёт.\n\n"
        "Доступные типы:\n"
        "• Герой (противоядие) – уровни 1..150\n"
        "• Навык (значки) – уровни 1..30\n"
        "• Звёзды героя (фрагменты) – 0..10, шаг 0.2\n"
        "• Обычное снаряжение – уровни 1..60\n"
        "• Продвинутое снаряжение – 0..5, шаг 0.2\n"
    )

async def type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    keyboard = [
        [InlineKeyboardButton("Прямой расчёт (по уровням)", callback_data="direct")],
        [InlineKeyboardButton("Обратный расчёт (по ресурсам)", callback_data="reverse")]
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
        if t == "hero":
            await query.edit_message_text("Введите текущий уровень и целевой уровень через пробел (например: 2 10)\nИли /cancel для отмены.")
        elif t == "skill":
            await query.edit_message_text("Введите текущий уровень навыка и целевой через пробел (например: 1 5)\nИли /cancel для отмены.")
        elif t == "stars":
            await query.edit_message_text("Введите текущую звезду и целевую звезду через пробел (например: 0 8)\nИли /cancel для отмены.")
        elif t == "gear":
            await query.edit_message_text("Введите текущий уровень снаряжения и целевой через пробел (например: 1 10)\nИли /cancel для отмены.")
        elif t == "advgear":
            await query.edit_message_text("Введите текущую звезду и целевую звезду через пробел (например: 0 5)\nИли /cancel для отмены.")
        return INPUT_FROM
    else:  # reverse
        if t == "hero":
            await query.edit_message_text("Введите текущий уровень и количество противоядия через пробел (например: 1 5000)\nИли /cancel для отмены.")
        elif t == "skill":
            await query.edit_message_text("Введите текущий уровень навыка и количество значков через пробел (например: 1 1000)\nИли /cancel для отмены.")
        elif t == "stars":
            await query.edit_message_text("Введите текущую звезду и количество фрагментов через пробел (например: 0 100)\nИли /cancel для отмены.")
        elif t == "gear":
            await query.edit_message_text("Введите текущий уровень, затем камни, траву, сталь через пробел (например: 1 1500 180000 0)\nИли /cancel для отмены.")
        elif t == "advgear":
            await query.edit_message_text("Введите текущую звезду, затем камни, чертежи, сталь через пробел (например: 0 2500 1 30)\nИли /cancel для отмены.")
        return INPUT_REV

# ---------- ПРЯМОЙ РАСЧЁТ (ввод двух чисел, затем количество) ----------
async def direct_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text("Нужно два числа через пробел. Попробуйте ещё раз или /cancel для отмены.")
            return INPUT_FROM
        a, b = parts[0], parts[1]
        t = context.user_data['type']
        # Сохраняем введённые значения
        context.user_data['from_val'] = a
        context.user_data['to_val'] = b
        await update.message.reply_text("Теперь введите количество (сколько героев/навыков/снаряжения прокачиваете):")
        return INPUT_COUNT
    except Exception as e:
        logging.error(e)
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
        a = context.user_data['from_val']
        b = context.user_data['to_val']
        t = context.user_data['type']
        # Выполняем расчёт
        if t == "hero":
            from_lvl = int(a); to_lvl = int(b)
            if from_lvl < 1 or to_lvl > 150 or from_lvl >= to_lvl:
                raise ValueError
            need = hero_cum[to_lvl] - hero_cum.get(from_lvl, 0)
            total = need * count
            await update.message.reply_text(f"💊 Противоядие: {fmt(total)} (на {count} героев)")
        elif t == "skill":
            from_lvl = int(a); to_lvl = int(b)
            if from_lvl < 1 or to_lvl > 30 or from_lvl >= to_lvl:
                raise ValueError
            need = skill_cum[to_lvl] - skill_cum.get(from_lvl, 0)
            total = need * count
            await update.message.reply_text(f"📘 Значки навыка: {fmt(total)} (на {count} навыков)")
        elif t == "stars":
            from_star = float(a); to_star = float(b)
            if from_star not in star_cum or to_star not in star_cum or from_star >= to_star:
                raise ValueError
            need = star_cum[to_star] - star_cum.get(from_star, 0)
            total = need * count
            await update.message.reply_text(f"🧩 Фрагменты: {fmt(total)} (на {count} героев)")
        elif t == "gear":
            from_lvl = int(a); to_lvl = int(b)
            if from_lvl < 1 or to_lvl > 60 or from_lvl >= to_lvl:
                raise ValueError
            stones = (gear_cum_stones[to_lvl] - gear_cum_stones[from_lvl]) * count
            grass = (gear_cum_grass[to_lvl] - gear_cum_grass[from_lvl]) * count
            steel = (gear_cum_steel[to_lvl] - gear_cum_steel[from_lvl]) * count
            await update.message.reply_text(
                f"💎 Камни снаряжения: {fmt(stones)}\n"
                f"🌿 Трава: {fmt(grass)}\n"
                f"⚙️ Закалённая сталь: {fmt(steel)}\n"
                f"(на {count} снаряжений)"
            )
        elif t == "advgear":
            from_star = float(a); to_star = float(b)
            if from_star not in adv_cum_stones or to_star not in adv_cum_stones or from_star >= to_star:
                raise ValueError
            stones = (adv_cum_stones[to_star] - adv_cum_stones[from_star]) * count
            bp = (adv_cum_blueprints[to_star] - adv_cum_blueprints[from_star]) * count
            steel = (adv_cum_steel[to_star] - adv_cum_steel[from_star]) * count
            msg = f"💎 Камни снаряжения: {fmt(stones)}\n📜 Чертежи: {fmt(bp)}\n⚙️ Закалённая сталь: {fmt(steel)}\n(на {count} снаряжений)"
            if to_star >= 4.2:
                msg += "\n* С 4 звёзды требуются чертежи MR качества."
            await update.message.reply_text(msg)
        await update.message.reply_text("Расчёт выполнен. Напишите /start для нового расчёта или /cancel для выхода.")
        return ConversationHandler.END
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("Ошибка ввода. Попробуйте ещё раз или /cancel.")
        return INPUT_COUNT

# ---------- ОБРАТНЫЙ РАСЧЁТ (ввод чисел, затем количество) ----------
async def reverse_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        parts = update.message.text.split()
        t = context.user_data['type']
        # Сохраняем введённые значения в зависимости от типа
        if t == "hero":
            if len(parts) != 2:
                raise ValueError
            context.user_data['rev_from'] = parts[0]
            context.user_data['rev_res'] = parts[1]
        elif t == "skill":
            if len(parts) != 2:
                raise ValueError
            context.user_data['rev_from'] = parts[0]
            context.user_data['rev_res'] = parts[1]
        elif t == "stars":
            if len(parts) != 2:
                raise ValueError
            context.user_data['rev_from'] = parts[0]
            context.user_data['rev_res'] = parts[1]
        elif t == "gear":
            if len(parts) != 4:
                raise ValueError
            context.user_data['rev_from'] = parts[0]
            context.user_data['rev_stones'] = parts[1]
            context.user_data['rev_grass'] = parts[2]
            context.user_data['rev_steel'] = parts[3]
        elif t == "advgear":
            if len(parts) != 4:
                raise ValueError
            context.user_data['rev_from'] = parts[0]
            context.user_data['rev_stones'] = parts[1]
            context.user_data['rev_blueprints'] = parts[2]
            context.user_data['rev_steel'] = parts[3]
        await update.message.reply_text("Теперь введите количество (сколько героев/навыков/снаряжения):")
        return INPUT_COUNT_REV
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("Неверный формат. Попробуйте ещё раз или /cancel.")
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
            res = float(context.user_data['rev_res'])
            res_per = res / count
            max_lvl = from_lvl
            for lvl in range(from_lvl+1, 151):
                need = hero_cum[lvl] - hero_cum.get(from_lvl, 0)
                if need <= res_per:
                    max_lvl = lvl
                else:
                    break
            used_per = hero_cum[max_lvl] - hero_cum.get(from_lvl, 0)
            used_total = used_per * count
            rem = res - used_total
            await update.message.reply_text(
                f"📊 Имея {fmt(res)} противоядия (на {count} героев), можно поднять каждого до {max_lvl} уровня.\n"
                f"Потребуется всего: {fmt(used_total)}, останется: {fmt(rem)}."
            )
        elif t == "skill":
            from_lvl = int(context.user_data['rev_from'])
            res = float(context.user_data['rev_res'])
            res_per = res / count
            max_lvl = from_lvl
            for lvl in range(from_lvl+1, 31):
                need = skill_cum[lvl] - skill_cum.get(from_lvl, 0)
                if need <= res_per:
                    max_lvl = lvl
                else:
                    break
            used_per = skill_cum[max_lvl] - skill_cum.get(from_lvl, 0)
            used_total = used_per * count
            rem = res - used_total
            await update.message.reply_text(
                f"📊 Имея {fmt(res)} значков (на {count} навыков), можно поднять каждый до {max_lvl} уровня.\n"
                f"Потребуется всего: {fmt(used_total)}, останется: {fmt(rem)}."
            )
        elif t == "stars":
            from_star = float(context.user_data['rev_from'])
            res = float(context.user_data['rev_res'])
            res_per = res / count
            max_star = from_star
            for s in star_levels:
                if s <= from_star:
                    continue
                need = star_cum[s] - star_cum.get(from_star, 0)
                if need <= res_per:
                    max_star = s
                else:
                    break
            used_per = star_cum[max_star] - star_cum.get(from_star, 0)
            used_total = used_per * count
            rem = res - used_total
            await update.message.reply_text(
                f"📊 Имея {fmt(res)} фрагментов (на {count} героев), можно поднять звезду каждого до {max_star}.\n"
                f"Потребуется всего: {fmt(used_total)}, останется: {fmt(rem)}."
            )
        elif t == "gear":
            from_lvl = int(context.user_data['rev_from'])
            stones = float(context.user_data['rev_stones'])
            grass = float(context.user_data['rev_grass'])
            steel = float(context.user_data['rev_steel'])
            stones_per = stones / count
            grass_per = grass / count
            steel_per = steel / count
            max_lvl = from_lvl
            for lvl in range(from_lvl+1, 61):
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
            await update.message.reply_text(
                f"📊 Имеющихся ресурсов хватит для поднятия каждого снаряжения (всего {count} шт.) с {from_lvl} до {max_lvl} уровня.\n"
                f"Потребуется всего: камней {fmt(used_st)}, травы {fmt(used_gr)}, стали {fmt(used_stl)}.\n"
                f"Останется: камней {fmt(rem_st)}, травы {fmt(rem_gr)}, стали {fmt(rem_stl)}."
            )
        elif t == "advgear":
            from_star = float(context.user_data['rev_from'])
            stones = float(context.user_data['rev_stones'])
            bp = float(context.user_data['rev_blueprints'])
            steel = float(context.user_data['rev_steel'])
            stones_per = stones / count
            bp_per = bp / count
            steel_per = steel / count
            max_star = from_star
            for s in adv_steps:
                if s <= from_star:
                    continue
                need_st = adv_cum_stones[s] - adv_cum_stones.get(from_star, 0)
                need_bp = adv_cum_blueprints[s] - adv_cum_blueprints.get(from_star, 0)
                need_stl = adv_cum_steel[s] - adv_cum_steel.get(from_star, 0)
                if need_st <= stones_per and need_bp <= bp_per and need_stl <= steel_per:
                    max_star = s
                else:
                    break
            used_st = (adv_cum_stones[max_star] - adv_cum_stones.get(from_star, 0)) * count
            used_bp = (adv_cum_blueprints[max_star] - adv_cum_blueprints.get(from_star, 0)) * count
            used_stl = (adv_cum_steel[max_star] - adv_cum_steel.get(from_star, 0)) * count
            rem_st = stones - used_st
            rem_bp = bp - used_bp
            rem_stl = steel - used_stl
            msg = f"📊 Имеющихся ресурсов хватит для поднятия каждого продвинутого снаряжения (всего {count} шт.) с {from_star} до {max_star} звезды.\n" \
                  f"Потребуется всего: камней {fmt(used_st)}, чертежей {fmt(used_bp)}, стали {fmt(used_stl)}.\n" \
                  f"Останется: камней {fmt(rem_st)}, чертежей {fmt(rem_bp)}, стали {fmt(rem_stl)}."
            if max_star >= 4.2:
                msg += "\n* С 4 звезды требуются чертежи MR качества."
            await update.message.reply_text(msg)
        await update.message.reply_text("Расчёт выполнен. Напишите /start для нового расчёта или /cancel для выхода.")
        return ConversationHandler.END
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("Ошибка ввода. Попробуйте ещё раз или /cancel.")
        return INPUT_COUNT_REV

# ---------- УСТАНОВКА КОМАНД (всплывающие подсказки) ----------
async def set_commands(app):
    await app.bot.set_my_commands([
        ("start", "Запустить калькулятор"),
        ("help", "Помощь"),
        ("cancel", "Отменить расчёт"),
    ])

# ---------- ГЛАВНАЯ ----------
def main():
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
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_commands(app))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
