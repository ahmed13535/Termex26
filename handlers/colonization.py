import time
import random
import json
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, get_user_by_country, update_occupation,
    add_occupied_territory, get_occupied_territory, get_user_occupied_territories,
    merge_territory, add_colony, get_colonies, get_colony_by_name,
    delete_colony, update_colony_harvest, record_harvest,
    add_gold, deduct_gold, get_map_cells
)
from config import COUNTRIES

# قائمة المناطق القابلة للغزو مع الدول الحدودية المسموح لها بالغزو
AVAILABLE_TERRITORIES = {
    "استونيا": {
        "resources": {"خشب": 500, "حبوب": 200}, "cost": 30000, "army_needed": 1000,
        "borders": {"روسيا", "فنلندا"},
    },
    "لاتفيا": {
        "resources": {"خشب": 400, "حبوب": 300}, "cost": 28000, "army_needed": 900,
        "borders": {"روسيا", "بولندا"},
    },
    "بيلاروس": {
        "resources": {"حديد": 600, "فحم": 400}, "cost": 50000, "army_needed": 1500,
        "borders": {"روسيا", "بولندا", "رومانيا"},
    },
    "مولدوفا": {
        "resources": {"عنب": 700, "قمح": 500}, "cost": 25000, "army_needed": 800,
        "borders": {"رومانيا", "روسيا"},
    },
    "الأردن": {
        "resources": {"فوسفات": 800, "زيتون": 300}, "cost": 45000, "army_needed": 1200,
        "borders": {"الدولة العثمانية"},
    },
    "قطر": {
        "resources": {"غاز": 1000, "نفط": 800}, "cost": 100000, "army_needed": 2000,
        "borders": {"الدولة العثمانية"},
    },
    "سويسرا": {
        "resources": {"ذهب": 900, "شوكولاتة": 400}, "cost": 70000, "army_needed": 1800,
        "borders": {"فرنسا", "إيطاليا", "النمسا", "ألمانيا"},
    },
}

async def invade_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """غزو [منطقة] – احتلال منطقة فارغة"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `غزو [منطقة]`\nمثال: `غزو بيلاروس`", parse_mode="Markdown")
        return

    territory = " ".join(args)
    if territory not in AVAILABLE_TERRITORIES:
        await update.message.reply_text(
            f"❌ *منطقة `{territory}` غير موجودة للغزو.*\n📌 المناطق المتاحة:\n" +
            "\n".join(f"• {t}" for t in AVAILABLE_TERRITORIES),
            parse_mode="Markdown"
        )
        return

    info = AVAILABLE_TERRITORIES[territory]

    # فحص الحدود: يُسمح بالغزو فقط للدول المجاورة
    allowed_borders = info.get("borders", set())
    if allowed_borders and user["country"] not in allowed_borders:
        await update.message.reply_text(
            f"⚠️ *لا يمكنك غزو {territory}!*\n"
            f"📍 *هذه المنطقة لا تحد أراضيك.*\n"
            f"🌍 *الدول التي تحدها:* {', '.join(allowed_borders)}",
            parse_mode="Markdown"
        )
        return

    cost = info["cost"]
    army_needed = info["army_needed"]

    if user["gold"] < cost:
        await update.message.reply_text(f"❌ *ذهب غير كافٍ!*\n💰 تحتاج `{cost:,.0f} ¥`\n💵 رصيدك: `{user['gold']:,.0f} ¥`", parse_mode="Markdown")
        return
    if user["soldiers"] < army_needed:
        await update.message.reply_text(f"❌ *جيش غير كافٍ!*\n⚔️ تحتاج `{army_needed:,}` جندي\n👥 جيشك: `{user['soldiers']:,}`", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], cost)
    new_soldiers = user["soldiers"] - army_needed
    await update_user(user["user_id"], soldiers=new_soldiers, gold=user["gold"] - cost)

    await add_occupied_territory(territory, user["user_id"], user["country"], info["resources"], cooldown_seconds=3600)

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏴 *احتلال ناجح!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🌍 المنطقة: `{territory}`\n"
        f"💰 التكلفة: `-{cost:,.0f} ¥`\n"
        f"⚔️ خسائر الجيش: `-{army_needed:,}` جندي\n"
        f"📦 الموارد: " + ", ".join(f"{k}: +{v}" for k,v in info["resources"].items()) + "\n"
        f"⏳ يمكنك دمج المنطقة بعد ساعة واحدة\n"
        f"💡 استخدم: `دمج {territory}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def merge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دمج [منطقة] – دمج الأراضي المحتلة إلى دولتك"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `دمج [منطقة]`", parse_mode="Markdown")
        return

    territory = " ".join(args)
    occupied = await get_occupied_territory(territory)
    if not occupied or occupied["occupied_by"] != user["user_id"]:
        await update.message.reply_text(f"❌ *أنت لا تحتل `{territory}` أو المنطقة غير موجودة.*", parse_mode="Markdown")
        return

    if occupied.get("is_merged"):
        await update.message.reply_text(f"⚠️ *`{territory}` مدمجة بالفعل.*", parse_mode="Markdown")
        return

    now = int(time.time())
    if now < occupied["merge_ready_at"]:
        remaining = occupied["merge_ready_at"] - now
        await update.message.reply_text(f"⏳ *لا يمكن دمج `{territory}` الآن.*\n⏱️ متبقي: `{remaining // 60}` دقيقة.", parse_mode="Markdown")
        return

    await merge_territory(territory)
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *تم دمج `{territory}` بنجاح!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🌍 أصبحت المنطقة جزءاً من `{user['country']}`.\n"
        f"🌟 +100 XP\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    await update_user(user["user_id"], xp=user["xp"] + 100)

async def colonize_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استعمر [دولة] – تحويل دولة محتلة إلى مستعمرة"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `استعمر [دولة]`", parse_mode="Markdown")
        return

    target_country = " ".join(args)
    target_user = await get_user_by_country(target_country)
    if not target_user:
        await update.message.reply_text(f"❌ *دولة `{target_country}` غير موجودة أو ليس لها حاكم.*", parse_mode="Markdown")
        return

    cells = await get_map_cells()
    cell = next((c for c in cells if c["country"] == target_country), None)
    if not cell or not cell.get("is_occupied") or cell["owner"] != user["country"]:
        await update.message.reply_text(f"⚠️ *`{target_country}` ليست محتلة بواسطتك أو غير موجودة.*", parse_mode="Markdown")
        return

    daily_income = max(500000, target_user["gold"] * 0.02)
    await add_colony(target_country, user["user_id"], target_user["user_id"], daily_income)

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏴 *تم استعمار `{target_country}`!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"👑 أصبحت مستعمرة تابعة لـ `{user['country']}`.\n"
        f"💰 الدخل اليومي: `+{daily_income:,.0f} ¥`\n"
        f"🌾 يمكنك حصاد إنتاجها بأمر `احصد دولي`.\n"
        f"🕊️ لتحريرها: استخدم `استقلال` (إذا كنت المستعمرة).\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def harvest_empire_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """احصد دولي – حصاد كل المستعمرات والمحتلات دفعة واحدة"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    colonies = await get_colonies(user["user_id"])
    if not colonies:
        await update.message.reply_text("⚠️ *ليس لديك أي مستعمرات لحصادها.*", parse_mode="Markdown")
        return

    total_income = 0
    now = int(time.time())
    for col in colonies:
        last_harvest = col["last_harvest_at"]
        hours_passed = (now - last_harvest) // 3600
        if hours_passed > 0:
            income = col["daily_income"] * hours_passed
            total_income += income
            await update_colony_harvest(col["colony_name"], now)

    if total_income > 0:
        await add_gold(user["user_id"], total_income)
        await record_harvest(user["user_id"], total_income)
        await update.message.reply_text(
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌾 *حصاد الإمبراطورية*\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"💰 إجمالي الذهب المجموع: `+{total_income:,.0f} ¥`\n"
            f"💵 رصيدك الجديد: `{user['gold'] + total_income:,.0f} ¥`\n"
            f"🗓️ تم حصاد {len(colonies)} مستعمرة.\n"
            f"━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ *لا توجد مستعمرات جاهزة للحصاد حالياً.* انتظر ساعة على الأقل.", parse_mode="Markdown")

async def revolt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثورة – تحرر من الاحتلال"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    cells = await get_map_cells()
    cell = next((c for c in cells if c["country"] == user["country"]), None)
    if not cell or not cell.get("is_occupied"):
        await update.message.reply_text("❌ *دولتك غير محتلة حالياً.*", parse_mode="Markdown")
        return

    occupier_country = cell["owner"]
    occupier = await get_user_by_country(occupier_country)
    if not occupier:
        await update.message.reply_text("❌ *خطأ: لا يمكن تحديد المحتل.*", parse_mode="Markdown")
        return

    required_army = occupier["soldiers"] * 0.3
    required_gold = 15000
    if user["soldiers"] < required_army:
        await update.message.reply_text(
            f"⚠️ *الثورة تحتاج قوة!*\n"
            f"⚔️ جيشك: `{user['soldiers']:,}`\n"
            f"⚔️ المطلوب: `{required_army:,.0f}` جندي (30% من جيش المحتل)\n"
            f"💰 الذهب المطلوب: `+{required_gold:,} ¥`\n"
            f"💡 قوِ جيشك ثم حاول مجدداً.",
            parse_mode="Markdown"
        )
        return

    if user["gold"] < required_gold:
        await update.message.reply_text(f"❌ *تحتاج `{required_gold:,} ¥` لتمويل الثورة.*", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], required_gold)
    new_soldiers = user["soldiers"] - required_army
    await update_user(user["user_id"], soldiers=new_soldiers, gold=user["gold"] - required_gold)
    await update_occupation(user["country"], user["country"], 0, (180,180,180))

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✊ *نجحت الثورة!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🏴 تحررت `{user['country']}` من احتلال `{occupier_country}`.\n"
        f"💰 تكلفة الثورة: `-{required_gold:,} ¥`\n"
        f"⚔️ خسائر الجيش: `-{required_army:,.0f}` جندي\n"
        f"🌟 +500 XP | 🏆 +100 هيبة\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    await update_user(user["user_id"], xp=user["xp"] + 500, prestige=user["prestige"] + 100)

async def independence_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقلال – تحرر من الاستعمار"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    colony = await get_colony_by_name(user["country"])
    if not colony:
        await update.message.reply_text("❌ *دولتك ليست مستعمرة لأحد.*", parse_mode="Markdown")
        return

    colonizer_id = colony["colonizer_id"]
    colonizer = await get_user(colonizer_id)
    if not colonizer:
        await update.message.reply_text("❌ *خطأ: لا يمكن تحديد المستعمر.*", parse_mode="Markdown")
        return

    required_army = colonizer["soldiers"] * 0.6
    required_gold = 25000
    if user["soldiers"] < required_army:
        await update.message.reply_text(
            f"⚠️ *الاستقلال يحتاج قوة!*\n"
            f"⚔️ جيشك: `{user['soldiers']:,}`\n"
            f"⚔️ المطلوب: `{required_army:,.0f}` جندي (60% من جيش المستعمر)\n"
            f"💰 الذهب المطلوب: `+{required_gold:,} ¥`\n"
            f"💡 قوِ جيشك ثم حاول مجدداً.",
            parse_mode="Markdown"
        )
        return

    if user["gold"] < required_gold:
        await update.message.reply_text(f"❌ *تحتاج `{required_gold:,} ¥` لتمويل الاستقلال.*", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], required_gold)
    new_soldiers = user["soldiers"] - required_army
    await update_user(user["user_id"], soldiers=new_soldiers, gold=user["gold"] - required_gold)
    await delete_colony(user["country"])

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✊ *تحقق الاستقلال!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🏴 أصبحت `{user['country']}` دولة حرة ومستقلة.\n"
        f"💰 تكلفة الاستقلال: `-{required_gold:,} ¥`\n"
        f"⚔️ خسائر الجيش: `-{required_army:,.0f}` جندي\n"
        f"🌟 +1000 XP | 🏆 +500 هيبة\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    await update_user(user["user_id"], xp=user["xp"] + 1000, prestige=user["prestige"] + 500)

async def gift_colony_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اهدي مستعمرة [اسم] الى [كود] – نقل مستعمرة إلى لاعب آخر"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text("💡 *استخدم:* `اهدي مستعمرة [اسم] الى [كود]`\nمثال: `اهدي مستعمرة فرنسا الى 123456789`", parse_mode="Markdown")
        return

    colony_name = args[0]
    # تجاهل كلمة "الى" إذا وجدت
    if args[1] == "الى":
        target_code = args[2]
    else:
        target_code = args[1]

    try:
        target_id = int(target_code)
    except:
        await update.message.reply_text("❌ *الكود (ID) غير صحيح.*", parse_mode="Markdown")
        return

    colony = await get_colony_by_name(colony_name)
    if not colony or colony["colonizer_id"] != user["user_id"]:
        await update.message.reply_text(f"❌ *أنت لا تملك مستعمرة باسم `{colony_name}`.*", parse_mode="Markdown")
        return

    target_user = await get_user(target_id)
    if not target_user:
        await update.message.reply_text(f"❌ *لا يوجد لاعب بهذا الكود: `{target_code}`.*", parse_mode="Markdown")
        return

    await delete_colony(colony_name)
    await add_colony(colony_name, target_id, colony["original_owner_id"], colony["daily_income"])

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 *تم نقل المستعمرة!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🏴 المستعمرة: `{colony_name}`\n"
        f"👑 المالك الجديد: `{target_user['country']}` (ID: `{target_id}`)\n"
        f"💡 استخدم `احصد دولي` لجني أرباحها.\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
