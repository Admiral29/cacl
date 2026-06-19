import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)

# ---------- Читаем переменные окружения ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

# Опционально: можно задать ID темы (если не нужна, оставьте None)
ALLOWED_THREAD_ID = os.getenv("ALLOWED_THREAD_ID")
if ALLOWED_THREAD_ID:
    try:
        ALLOWED_THREAD_ID = int(ALLOWED_THREAD_ID)
    except ValueError:
        ALLOWED_THREAD_ID = None

# ---------- ДАННЫЕ (из вашего HTML) ----------

# 1. ГЕРОЙ (противоядие)
hero_cost = {
    2:100,3:200,4:300,5:500,6:700,7:900,8:1100,9:1300,10:1500,
    11:2100,12:2700,13:3300,14:3900,15:4700,16:5500,17:6300,18:7100,19:7900,20:8700,
    21:9700,22:10700,23:11700,24:12700,25:13900,26:15100,27:16300,28:17500,29:18700,30:19900,
    31:21900,32:23900,33:25900,34:27900,35:29900,36:31900,37:33900,38:35900,39:37900,40:39900,
    41:41900,42:43900,43:45900,44:47900,45:137900,46:227900,47:317900,48:407900,49:497900,50:587900,
    51:677900,52:767900,53:857900,54:947900,55:1050000,56:1150000,57:1250000,58:1350000,59:1450000,60:1550000,
    61:1650000,62:1750000,63:1850000,64:1950000,65:2500000,66:3000000,67:3600000,68:4200000,69:4800000,70:5500000,
    71:6000000,72:6700000,73:7200000,74:7800000,75:8400000,76:9100000,77:9700000,78:10200000,79:10900000,80:11800000,
    81:12700000,82:13600000,83:14500000,84:15400000,85:16300000,86:17200000,87:18100000,88:19000000,89:19900000,90:20800000,
    91:21700000,92:22600000,93:23500000,94:24400000,95:26100000,96:27800000,97:29500000,98:31200000,99:32900000,100:34600000,
    101:36300000,102:38000000,103:39700000,104:41400000,105:43100000,106:44800000,107:46500000,108:48200000,109:49900000,110:51600000,
    111:53300000,112:55000000,113:56700000,114:58400000,115:60700000,116:63000000,117:65300000,118:67600000,119:69900000,120:72200000,
    121:74500000,122:76800000,123:79100000,124:81400000,125:83700000,126:86000000,127:88300000,128:90600000,129:92900000,130:96500000,
    131:100100000,132:104000000,133:108000000,134:112000000,135:116000000,136:120000000,137:124000000,138:128000000,139:132000000,140:136000000,
    141:140000000,142:144000000,143:148000000,144:152000000,145:156000000,146:160000000,147:164000000,148:168000000,149:172000000,150:176000000
}
hero_cum = {0:0}
for i in range(2,151):
    hero_cum[i] = hero_cum.get(i-1,0) + hero_cost.get(i,0)

# 2. НАВЫК (значки)
skill_cost = {
    1:0,2:50,3:100,4:150,5:300,6:450,7:600,8:750,9:900,10:1200,
    11:1500,12:1800,13:2100,14:2400,15:3100,16:3800,17:4500,18:5200,19:5900,20:6900,
    21:7900,22:8900,23:9900,24:10900,25:12100,26:13300,27:14500,28:15700,29:16900,30:18400
}
skill_cum = {0:0,1:0}
for i in range(2,31):
    skill_cum[i] = skill_cum.get(i-1,0) + skill_cost.get(i,0)

# 3. ЗВЁЗДЫ ГЕРОЯ (фрагменты)
star_step = {
    0.2:2,0.4:2,0.6:2,0.8:2,1.0:2,
    1.2:3,1.4:3,1.6:3,1.8:3,2.0:3,
    2.2:4,2.4:4,2.6:4,2.8:4,3.0:4,
    3.2:6,3.4:6,3.6:6,3.8:6,4.0:6,
    4.2:8,4.4:8,4.6:8,4.8:8,5.0:8,
    5.2:12,5.4:12,5.6:12,5.8:12,6.0:12,
    6.2:25,6.4:25,6.6:25,6.8:25,7.0:25,
    7.2:35,7.4:35,7.6:35,7.8:35,8.0:35,
    8.2:40,8.4:40,8.6:40,8.8:40,9.0:40,
    9.2:60,9.4:60,9.6:60,9.8:60,10.0:60
}
star_step[0] = 0
star_levels = [0,0.2,0.4,0.6,0.8,1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.4,2.6,2.8,3.0,3.2,3.4,3.6,3.8,4.0,4.2,4.4,4.6,4.8,5.0,5.2,5.4,5.6,5.8,6.0,6.2,6.4,6.6,6.8,7.0,7.2,7.4,7.6,7.8,8.0,8.2,8.4,8.6,8.8,9.0,9.2,9.4,9.6,9.8,10.0]
star_cum = {0:0}
cum = 0
for s in star_levels:
    if s == 0: continue
    cum += star_step[s]
    star_cum[s] = cum

# 4. ОБЫЧНОЕ СНАРЯЖЕНИЕ (уровни 1..60)
gear_stone = {
    1:1500,2:1500,3:1500,4:1500,5:2250,6:2250,7:2250,8:2250,
    9:3000,10:3000,11:3000,12:3000,13:3750,14:3750,15:3750,16:3750,
    17:4500,18:4500,19:4500,20:4500,21:5250,22:5250,23:5250,24:5250,
    25:6000,26:6000,27:6000,28:6000,29:6750,30:6750,31:6750,32:6750,
    33:7500,34:7500,35:7500,36:7500,37:8250,38:8250,39:8250,40:8250,
    41:12500,42:12500,43:12500,44:12500,45:16250,46:16250,47:16250,48:16250,
    49:20000,50:20000,51:20000,52:20000,53:23750,54:23750,55:23750,56:23750,
    57:27500,58:27500,59:27500,60:27500
}
gear_grass = {
    1:180000,2:180000,3:180000,4:180000,5:287000,6:287000,7:287000,8:287000,
    9:405000,10:405000,11:405000,12:405000,13:534000,14:534000,15:534000,16:534000,
    17:675000,18:675000,19:675000,20:675000,21:803000,22:803000,23:803000,24:803000,
    25:936000,26:936000,27:936000,28:936000,29:1100000,30:1100000,31:1100000,32:1100000,
    33:1200000,34:1200000,35:1200000,36:1200000,37:1400000,38:1400000,39:1400000,40:1400000,
    41:23400000,42:23400000,43:23400000,44:23400000,45:30500000,46:30500000,47:30500000,48:30500000,
    49:37500000,50:37500000,51:37500000,52:37500000,53:44500000,54:44500000,55:44500000,56:44500000,
    57:51500000,58:51500000,59:51500000,60:51500000
}
gear_steel = {i:0 for i in range(1,41)}
gear_steel.update({
    41:150,42:150,43:150,44:150,45:195,46:195,47:195,48:195,
    49:240,50:240,51:240,52:240,53:285,54:285,55:285,56:285,
    57:330,58:330,59:330,60:330
})

gear_cum_stones = {0:0}
gear_cum_grass = {0:0}
gear_cum_steel = {0:0}
for i in range(1,61):
    gear_cum_stones[i] = gear_cum_stones.get(i-1,0) + gear_stone.get(i,0)
    gear_cum_grass[i] = gear_cum_grass.get(i-1,0) + gear_grass.get(i,0)
    gear_cum_steel[i] = gear_cum_steel.get(i-1,0) + gear_steel.get(i,0)

# 5. ПРОДВИНУТОЕ СНАРЯЖЕНИЕ (звёзды 0..5, шаг 0.2)
adv_gear = {
    0.2: {'stones':2500, 'blueprints':1, 'steel':30},
    0.4: {'stones':2500, 'blueprints':1, 'steel':30},
    0.6: {'stones':2500, 'blueprints':1, 'steel':30},
    0.8: {'stones':2500, 'blueprints':1, 'steel':30},
    1.0: {'stones':2500, 'blueprints':1, 'steel':30},
    1.2: {'stones':3240, 'blueprints':2, 'steel':39},
    1.4: {'stones':3240, 'blueprints':2, 'steel':39},
    1.6: {'stones':3240, 'blueprints':2, 'steel':39},
    1.8: {'stones':3240, 'blueprints':2, 'steel':39},
    2.0: {'stones':3240, 'blueprints':2, 'steel':39},
    2.2: {'stones':4000, 'blueprints':3, 'steel':48},
    2.4: {'stones':4000, 'blueprints':3, 'steel':48},
    2.6: {'stones':4000, 'blueprints':3, 'steel':48},
    2.8: {'stones':4000, 'blueprints':3, 'steel':48},
    3.0: {'stones':4000, 'blueprints':3, 'steel':48},
    3.2: {'stones':4750, 'blueprints':4, 'steel':57},
    3.4: {'stones':4750, 'blueprints':4, 'steel':57},
    3.6: {'stones':4750, 'blueprints':4, 'steel':57},
    3.8: {'stones':4750, 'blueprints':4, 'steel':57},
    4.0: {'stones':4750, 'blueprints':4, 'steel':57},
    4.2: {'stones':5500, 'blueprints':2, 'steel':66},
    4.4: {'stones':5500, 'blueprints':2, 'steel':66},
    4.6: {'stones':5500, 'blueprints':2, 'steel':66},
    4.8: {'stones':5500, 'blueprints':2, 'steel':66},
    5.0: {'stones':5500, 'blueprints':2, 'steel':66}
}
adv_gear[0] = {'stones':0, 'blueprints':0, 'steel':0}
adv_steps = [0,0.2,0.4,0.6,0.8,1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.4,2.6,2.8,3.0,3.2,3.4,3.6,3.8,4.0,4.2,4.4,4.6,4.8,5.0]
adv_cum_stones = {0:0}
adv_cum_blueprints = {0:0}
adv_cum_steel = {0:0}
cs = cb = cst = 0
for s in adv_steps:
    if s == 0: continue
    cs += adv_gear[s]['stones']
    cb += adv_gear[s]['blueprints']
    cst += adv_gear[s]['steel']
    adv_cum_stones[s] = cs
    adv_cum_blueprints[s] = cb
    adv_cum_steel[s] = cst

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def fmt(n):
    return f"{n:,.0f}".replace(",", " ")

# ---------- ПРОВЕРКА ТЕМЫ (если нужно) ----------
def is_allowed(update: Update) -> bool:
    if ALLOWED_THREAD_ID is None:
        return True
    chat = update.effective_chat
    if chat.type == 'private':
        return True
    thread_id = update.effective_message.message_thread_id
    return thread_id == ALLOWED_THREAD_ID

# ---------- СОСТОЯНИЯ ----------
TYPE, MODE, INPUT_FROM, INPUT_TO, INPUT_REV = range(5)

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
        if t == "hero":
            from_lvl = int(a); to_lvl = int(b)
            if from_lvl < 1 or to_lvl > 150 or from_lvl >= to_lvl:
                raise ValueError
            need = hero_cum[to_lvl] - hero_cum.get(from_lvl, 0)
            await update.message.reply_text(f"💊 Противоядие: {fmt(need)}")
        elif t == "skill":
            from_lvl = int(a); to_lvl = int(b)
            if from_lvl < 1 or to_lvl > 30 or from_lvl >= to_lvl:
                raise ValueError
            need = skill_cum[to_lvl] - skill_cum.get(from_lvl, 0)
            await update.message.reply_text(f"📘 Значки навыка: {fmt(need)}")
        elif t == "stars":
            from_star = float(a); to_star = float(b)
            if from_star not in star_cum or to_star not in star_cum or from_star >= to_star:
                raise ValueError
            need = star_cum[to_star] - star_cum.get(from_star, 0)
            await update.message.reply_text(f"🧩 Фрагменты: {fmt(need)}")
        elif t == "gear":
            from_lvl = int(a); to_lvl = int(b)
            if from_lvl < 1 or to_lvl > 60 or from_lvl >= to_lvl:
                raise ValueError
            stones = gear_cum_stones[to_lvl] - gear_cum_stones[from_lvl]
            grass = gear_cum_grass[to_lvl] - gear_cum_grass[from_lvl]
            steel = gear_cum_steel[to_lvl] - gear_cum_steel[from_lvl]
            await update.message.reply_text(
                f"💎 Камни снаряжения: {fmt(stones)}\n"
                f"🌿 Трава: {fmt(grass)}\n"
                f"⚙️ Закалённая сталь: {fmt(steel)}"
            )
        elif t == "advgear":
            from_star = float(a); to_star = float(b)
            if from_star not in adv_cum_stones or to_star not in adv_cum_stones or from_star >= to_star:
                raise ValueError
            stones = adv_cum_stones[to_star] - adv_cum_stones[from_star]
            bp = adv_cum_blueprints[to_star] - adv_cum_blueprints[from_star]
            steel = adv_cum_steel[to_star] - adv_cum_steel[from_star]
            await update.message.reply_text(
                f"💎 Камни снаряжения: {fmt(stones)}\n"
                f"📜 Чертежи: {fmt(bp)}\n"
                f"⚙️ Закалённая сталь: {fmt(steel)}"
            )
        await update.message.reply_text("Расчёт выполнен. Напишите /start для нового расчёта или /cancel для выхода.")
        return ConversationHandler.END
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("Неверный формат или значения. Попробуйте ещё раз или /cancel для отмены.")
        return INPUT_FROM

async def reverse_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        parts = update.message.text.split()
        t = context.user_data['type']
        if t == "hero":
            if len(parts) != 2:
                raise ValueError
            from_lvl = int(parts[0]); res = float(parts[1])
            max_lvl = from_lvl
            for lvl in range(from_lvl+1, 151):
                need = hero_cum[lvl] - hero_cum.get(from_lvl, 0)
                if need <= res:
                    max_lvl = lvl
                else:
                    break
            used = hero_cum[max_lvl] - hero_cum.get(from_lvl, 0)
            rem = res - used
            await update.message.reply_text(
                f"📊 Имея {fmt(res)} противоядия, с уровня {from_lvl} можно подняться до {max_lvl}.\n"
                f"Потребуется {fmt(used)}, останется {fmt(rem)}."
            )
        elif t == "skill":
            if len(parts) != 2:
                raise ValueError
            from_lvl = int(parts[0]); res = float(parts[1])
            max_lvl = from_lvl
            for lvl in range(from_lvl+1, 31):
                need = skill_cum[lvl] - skill_cum.get(from_lvl, 0)
                if need <= res:
                    max_lvl = lvl
                else:
                    break
            used = skill_cum[max_lvl] - skill_cum.get(from_lvl, 0)
            rem = res - used
            await update.message.reply_text(
                f"📊 Имея {fmt(res)} значков, с уровня {from_lvl} можно подняться до {max_lvl}.\n"
                f"Потребуется {fmt(used)}, останется {fmt(rem)}."
            )
        elif t == "stars":
            if len(parts) != 2:
                raise ValueError
            from_star = float(parts[0]); res = float(parts[1])
            max_star = from_star
            for s in star_levels:
                if s <= from_star:
                    continue
                need = star_cum[s] - star_cum.get(from_star, 0)
                if need <= res:
                    max_star = s
                else:
                    break
            used = star_cum[max_star] - star_cum.get(from_star, 0)
            rem = res - used
            await update.message.reply_text(
                f"📊 Имея {fmt(res)} фрагментов, с звезды {from_star} можно подняться до {max_star}.\n"
                f"Потребуется {fmt(used)}, останется {fmt(rem)}."
            )
        elif t == "gear":
            if len(parts) != 4:
                raise ValueError
            from_lvl = int(parts[0])
            stones = float(parts[1]); grass = float(parts[2]); steel = float(parts[3])
            max_lvl = from_lvl
            for lvl in range(from_lvl+1, 61):
                need_st = gear_cum_stones[lvl] - gear_cum_stones[from_lvl]
                need_gr = gear_cum_grass[lvl] - gear_cum_grass[from_lvl]
                need_stl = gear_cum_steel[lvl] - gear_cum_steel[from_lvl]
                if need_st <= stones and need_gr <= grass and need_stl <= steel:
                    max_lvl = lvl
                else:
                    break
            used_st = gear_cum_stones[max_lvl] - gear_cum_stones[from_lvl]
            used_gr = gear_cum_grass[max_lvl] - gear_cum_grass[from_lvl]
            used_stl = gear_cum_steel[max_lvl] - gear_cum_steel[from_lvl]
            await update.message.reply_text(
                f"📊 Имеющихся ресурсов хватит, чтобы поднять снаряжение с {from_lvl} до {max_lvl}.\n"
                f"Потребуется: камней {fmt(used_st)}, травы {fmt(used_gr)}, стали {fmt(used_stl)}.\n"
                f"Останется: камней {fmt(stones-used_st)}, травы {fmt(grass-used_gr)}, стали {fmt(steel-used_stl)}."
            )
        elif t == "advgear":
            if len(parts) != 4:
                raise ValueError
            from_star = float(parts[0])
            stones = float(parts[1]); bp = float(parts[2]); steel = float(parts[3])
            max_star = from_star
            for s in adv_steps:
                if s <= from_star:
                    continue
                need_st = adv_cum_stones[s] - adv_cum_stones.get(from_star, 0)
                need_bp = adv_cum_blueprints[s] - adv_cum_blueprints.get(from_star, 0)
                need_stl = adv_cum_steel[s] - adv_cum_steel.get(from_star, 0)
                if need_st <= stones and need_bp <= bp and need_stl <= steel:
                    max_star = s
                else:
                    break
            used_st = adv_cum_stones[max_star] - adv_cum_stones.get(from_star, 0)
            used_bp = adv_cum_blueprints[max_star] - adv_cum_blueprints.get(from_star, 0)
            used_stl = adv_cum_steel[max_star] - adv_cum_steel.get(from_star, 0)
            await update.message.reply_text(
                f"📊 Имеющихся ресурсов хватит, чтобы поднять продвинутое снаряжение с {from_star} до {max_star}.\n"
                f"Потребуется: камней {fmt(used_st)}, чертежей {fmt(used_bp)}, стали {fmt(used_stl)}.\n"
                f"Останется: камней {fmt(stones-used_st)}, чертежей {fmt(bp-used_bp)}, стали {fmt(steel-used_stl)}."
            )
        await update.message.reply_text("Расчёт выполнен. Напишите /start для нового расчёта или /cancel для выхода.")
        return ConversationHandler.END
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("Неверный формат или значения. Попробуйте ещё раз или /cancel для отмены.")
        return INPUT_REV

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
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()