import random
import time
import aiosqlite
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (
    get_user, get_user_by_country, update_user, get_cooldown, set_cooldown,
    get_city, occupy_city, update_occupation_progress, deduct_gold,
    update_occupation, get_all_provinces
)
from config import COUNTRIES, PROVINCES, DB_PATH

# الحدود (يمكنك تعديلها حسب خريطتك)
BORDERS = {
    "ألمانيا":          {"فرنسا", "بولندا", "النمسا", "الدنمارك"},
    "فرنسا":            {"ألمانيا", "إسبانيا", "إيطاليا", "بريطانيا"},
    "إسبانيا":          {"فرنسا", "البرتغال"},
    "إيطاليا":          {"فرنسا", "النمسا"},
    "النمسا":           {"ألمانيا", "إيطاليا", "رومانيا"},
    "السويد":           {"النرويج", "فنلندا", "الدنمارك"},
    "فنلندا":           {"السويد", "النرويج", "روسيا"},
    "النرويج":          {"السويد", "فنلندا"},
    "بريطانيا":         {"فرنسا"},
    "بولندا":           {"ألمانيا", "روسيا", "رومانيا"},
    "الدنمارك":         {"ألمانيا", "السويد"},
    "رومانيا":          {"النمسا", "بولندا", "روسيا", "الدولة العثمانية"},
    "الدولة العثمانية": {"رومانيا", "روسيا"},
    "روسيا":            {"بولندا", "فنلندا", "رومانيا", "الدولة العثمانية"},
    "البرتغال":         {"إسبانيا"},
    "أيسلندا":          set(),
}

async def is_adjacent(attacker_country: str, defender_country: str) -> bool:
    if attacker_country == defender_country:
        return False
    return defender_country in BORDERS.get(attacker_country, set())

# ======================== عرض المدن المتاحة للغزو ========================
async def invasion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "💡 *استخدم:* `غزو [دولة]`\nمثال: `غزو فرنسا`\n• ستظهر لك قائمة بالمدن التي يمكنك غزوها.\n• يمكنك بعدها مهاجمة مدينة محددة بالضغط على الزر.",
            parse_mode="Markdown"
        )
        return

    target_country = " ".join(args)
    if target_country not in PROVINCES:
        await update.message.reply_text(f"❌ *دولة `{target_country}` غير موجودة في الخريطة.*", parse_mode="Markdown")
        return

    if not await is_adjacent(user["country"], target_country):
        neighbors = BORDERS.get(user["country"], set())
        await update.message.reply_text(
            f"⚠️ *لا يمكنك غزو {target_country}!*\n📍 *هذه الدولة لا تحد أراضيك.*\n"
            f"🌍 *دول مجاورة لك:* {', '.join(neighbors) if neighbors else 'لا توجد دول مجاورة'}",
            parse_mode="Markdown"
        )
        return

    cities = PROVINCES.get(target_country, {})
    if not cities:
        await update.message.reply_text(f"❌ *لا توجد مدن مسجلة لـ {target_country}.*", parse_mode="Markdown")
        return

    buttons = []
    for city_name in cities.keys():
        db_city = await get_city(city_name, target_country)
        if db_city and db_city.get("owner_id") == user["user_id"] and db_city.get("merged"):
            continue
        buttons.append([InlineKeyboardButton(f"⚔️ {city_name}", callback_data=f"invade_city_{target_country}_{city_name}")])

    if not buttons:
        await update.message.reply_text(f"⚠️ *لا توجد مدن متاحة للغزو في {target_country}.*", parse_mode="Markdown")
        return

    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="military_back")])
    await update.message.reply_text(
        f"**🗺️ مدن {target_country} المتاحة للغزو**\n━━━━━━━━━━━━━━━━━━━━━\n• اختر مدينة لشن الهجوم عليها:\n━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ======================== تنفيذ الهجوم على مدينة ========================
async def attack_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) < 4:
        await query.edit_message_text("❌ *خطأ في البيانات.*", parse_mode="Markdown")
        return
    target_country = parts[2]
    city_name = parts[3]

    user = await get_user(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    if target_country not in PROVINCES:
        await query.edit_message_text("❌ *الدولة غير موجودة في الخريطة.*", parse_mode="Markdown")
        return

    if not await is_adjacent(user["country"], target_country):
        await query.edit_message_text(f"⚠️ *لا يمكنك مهاجمة {city_name}!*\n📍 *هذه المدينة لا تحد أراضيك.*", parse_mode="Markdown")
        return

    cd = await get_cooldown(user["user_id"], "city_attack")
    if cd > 0:
        await query.edit_message_text(f"⏳ *يجب الانتظار {cd // 60} دقيقة قبل الهجوم التالي.*", parse_mode="Markdown")
        return

    db_city = await get_city(city_name, target_country)
    # إذا كانت المدينة مملوكة لشخص آخر (دولة مسجلة)
    if db_city and db_city.get("owner_id") and db_city["owner_id"] != user["user_id"]:
        defender = await get_user(db_city["owner_id"])
        if not defender:
            await query.edit_message_text("❌ *خطأ: لا يمكن تحديد المدافع.*", parse_mode="Markdown")
            return

        result = await calculate_battle_for_city(user, defender, db_city)
        await set_cooldown(user["user_id"], "city_attack", 300)

        new_atk_soldiers = max(0, user["soldiers"] - result["attacker_losses"])
        new_def_soldiers = max(0, defender["soldiers"] - result["defender_losses"])
        await update_user(user["user_id"], soldiers=new_atk_soldiers)
        await update_user(defender["user_id"], soldiers=new_def_soldiers)

        new_progress = min(100, db_city.get("occupation_progress", 0) + result["progress_gain"])
        await update_occupation_progress(city_name, target_country, new_progress)

        # تحديث لون المدينة بلون المحتل (أثناء الاحتلال)
        atk_color = COUNTRIES.get(user["country"], {}).get("color", (180, 50, 50))
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE cities SET color_r=?, color_g=?, color_b=? WHERE city_name=? AND country=?", (atk_color[0], atk_color[1], atk_color[2], city_name, target_country))
            await db.commit()

        if new_progress >= 100:
            # احتلال كامل (نسبة 100%) لكن لم يدمج بعد
            await occupy_city(city_name, target_country, user["user_id"], 100)
            msg = f"**🏴 احتللت مدينة {city_name} بالكامل!**\n━━━━━━━━━━━━━━━━━━━━━\n📍 *أصبحت تحت سيطرتك (احتلال).*\n💡 *استخدم `دمج {city_name}` لدمجها نهائياً في دولتك.*"
        else:
            msg = (
                f"**⚔️ نتيجة الهجوم على {city_name}**\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *تقدم الاحتلال:* `{result['progress_gain']:.1f}%` (الإجمالي: `{new_progress:.1f}%`)\n"
                f"💥 *خسائرك:* `{result['attacker_losses']:,}` جندي\n"
                f"💀 *خسائر المدافع:* `{result['defender_losses']:,}` جندي\n"
                f"━━━━━━━━━━━━━━━━━━━━━"
            )
        await query.edit_message_text(msg, parse_mode="Markdown")
    else:
        # مدينة حرة (غير مسجلة لأحد) – غزو سريع
        cost = 30000
        army_needed = 500
        if user["gold"] < cost or user["soldiers"] < army_needed:
            await query.edit_message_text(f"❌ *لا يمكنك غزو {city_name}!*\n💰 تحتاج `{cost:,} ¥` و `{army_needed:,}` جندي.", parse_mode="Markdown")
            return
        await deduct_gold(user["user_id"], cost)
        new_soldiers = user["soldiers"] - army_needed
        await update_user(user["user_id"], soldiers=new_soldiers, gold=user["gold"] - cost)
        await occupy_city(city_name, target_country, user["user_id"], 100)
        # تحديث اللون بلون المحتل
        atk_color = COUNTRIES.get(user["country"], {}).get("color", (180, 50, 50))
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE cities SET color_r=?, color_g=?, color_b=? WHERE city_name=? AND country=?", (atk_color[0], atk_color[1], atk_color[2], city_name, target_country))
            await db.commit()
        await query.edit_message_text(
            f"**🏴 احتللت مدينة {city_name} بنجاح!**\n━━━━━━━━━━━━━━━━━━━━━\n💡 *استخدم `دمج {city_name}` لدمجها في دولتك.*",
            parse_mode="Markdown"
        )

async def calculate_battle_for_city(attacker: dict, defender: dict, city: dict) -> dict:
    atk_power = (attacker["soldiers"] * 1 + attacker["tanks"] * 25 + attacker["artillery"] * 50) * attacker["damage_bonus"] * (attacker["morale"] / 100)
    def_power = (defender["soldiers"] * 1.2 + defender["tanks"] * 30 + defender["artillery"] * 55) * defender["defense_bonus"] * (defender["morale"] / 100)
    city_defense = city.get("occupation_progress", 0) * 0.5
    def_power *= (1 + city_defense / 100)
    atk_power *= random.uniform(0.85, 1.15)
    def_power *= random.uniform(0.85, 1.15)
    attacker_wins = atk_power > def_power
    ratio = atk_power / max(def_power, 1)
    if attacker_wins:
        atk_loss_pct = random.uniform(0.05, 0.15)
        def_loss_pct = random.uniform(0.10, 0.25)
        progress_gain = min(25.0, ratio * 10)
    else:
        atk_loss_pct = random.uniform(0.15, 0.30)
        def_loss_pct = random.uniform(0.05, 0.12)
        progress_gain = max(0.0, ratio * 2 - 5)
    return {
        "attacker_wins": attacker_wins,
        "attacker_losses": int(attacker["soldiers"] * atk_loss_pct),
        "defender_losses": int(defender["soldiers"] * def_loss_pct),
        "progress_gain": progress_gain
    }

# ======================== دمج المدينة المحتلة ========================
async def merge_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `دمج [مدينة]`\nمثال: `دمج باريس`", parse_mode="Markdown")
        return

    city_name = " ".join(args)
    target_country = None
    for country, cities in PROVINCES.items():
        if city_name in cities:
            target_country = country
            break
    if not target_country:
        await update.message.reply_text(f"❌ *مدينة `{city_name}` غير موجودة في الخريطة.*", parse_mode="Markdown")
        return

    db_city = await get_city(city_name, target_country)
    if not db_city or db_city.get("owner_id") != user["user_id"]:
        await update.message.reply_text(f"⚠️ *أنت لا تحتل مدينة `{city_name}`.*", parse_mode="Markdown")
        return

    if db_city.get("merged"):
        await update.message.reply_text(f"⚠️ *مدينة `{city_name}` مدمجة بالفعل.*", parse_mode="Markdown")
        return

    if db_city.get("occupation_progress", 0) < 100:
        await update.message.reply_text(f"⚠️ *مدينة `{city_name}` غير محتلة بالكامل بعد.*\n📊 نسبة الاحتلال: `{db_city.get('occupation_progress', 0):.1f}%`", parse_mode="Markdown")
        return

    # تحديث قاعدة البيانات: وضع علامة مدمجة (merged=1)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE cities SET merged=1 WHERE city_name=? AND country=?", (city_name, target_country))
        await db.commit()

    await update.message.reply_text(
        f"**✅ تم دمج مدينة {city_name} بنجاح!**\n━━━━━━━━━━━━━━━━━━━━━\n🌍 *أصبحت الآن جزءاً من دولتك `{user['country']}`.*\n🌟 *+100 XP*",
        parse_mode="Markdown"
    )
    await update_user(user["user_id"], xp=user["xp"] + 100)
