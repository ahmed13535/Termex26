"""
handlers/intelligence.py – نظام المخابرات
يستخدم حقول intel_level و intel_exp من جدول users مباشرة.
"""
import random
import time
import aiosqlite
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, deduct_gold, add_gold, get_user_by_country,
    get_cooldown, set_cooldown, log_intel_operation, DB_PATH
)
from config import ADMIN_IDS

INTEL_LEVELS = {
    0: {"name": "مبتدئ 🔍",          "exp_needed": 0,  "spy": 25,  "sabotage": 0,  "assassinate": 0,  "infiltrate": False},
    1: {"name": "جاسوس 🕵️",          "exp_needed": 3,  "spy": 40,  "sabotage": 0,  "assassinate": 0,  "infiltrate": False},
    2: {"name": "عميل ميداني 🥷",     "exp_needed": 7,  "spy": 55,  "sabotage": 30, "assassinate": 0,  "infiltrate": False},
    3: {"name": "قائد مخابرات 🧠",    "exp_needed": 12, "spy": 68,  "sabotage": 45, "assassinate": 20, "infiltrate": True},
    4: {"name": "مدير جهاز 🏛️",       "exp_needed": 18, "spy": 78,  "sabotage": 58, "assassinate": 35, "infiltrate": True},
    5: {"name": "أسطورة تجسس 👑",     "exp_needed": 25, "spy": 88,  "sabotage": 72, "assassinate": 52, "infiltrate": True},
}

async def get_intel_data(user_id: int):
    """جلب مستوى وخبرة المخابرات من قاعدة البيانات"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT intel_level, intel_exp FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return row[0] or 0, row[1] or 0
    return 0, 0

async def add_intel_exp(user_id: int, exp_gain: int) -> bool:
    """إضافة خبرة مخابرات وتحديث المستوى. تُعيد True إذا تمت الترقية."""
    level, exp = await get_intel_data(user_id)
    new_exp = max(0, exp + exp_gain)
    new_level = level
    upgraded = False
    for lvl in sorted(INTEL_LEVELS.keys()):
        if new_exp >= INTEL_LEVELS[lvl]["exp_needed"] and lvl > new_level:
            new_level = lvl
            upgraded = True
    await update_user(user_id, intel_level=new_level, intel_exp=new_exp)
    return upgraded

# ======================== عرض لوحة المخابرات ========================
async def intelligence_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة. ابدأ بـ /start")
        return

    level, exp = await get_intel_data(user["user_id"])
    info = INTEL_LEVELS.get(level, INTEL_LEVELS[0])
    next_level = level + 1
    next_exp = INTEL_LEVELS.get(next_level, {}).get("exp_needed", "MAX")

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕵️ *جهاز المخابرات — {user['country']}*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📊 المستوى: *{info['name']}* (Lv.{level})\n"
        f"⭐ خبرة: `{exp}/{next_exp}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 فرصة التجسس: `{info['spy']}%`\n"
        f"💣 فرصة التخريب: `{info['sabotage']}%`\n"
        f"🗡️ فرصة الاغتيال: `{info['assassinate']}%`\n"
        f"🔍 زرع عميل: {'✅ متاح' if info['infiltrate'] else '❌ يتطلب Lv.3+'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *الأوامر:*\n"
        f"  `تجسس على [دولة]`\n"
        f"  `تخريب [دولة]`\n"
        f"  `اغتيال [دولة]`\n"
        f"  `مضادة تجسس`\n"
        f"  `معلومات مزيفة`\n"
        f"  `جواسيس مكشوفون`\n"
        f"  `تحصين`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ======================== عمليات التجسس ========================
async def spy_operation(update: Update, context: ContextTypes.DEFAULT_TYPE, operation: str):
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(f"💡 استخدم: `{operation} [اسم الدولة]`", parse_mode="Markdown")
        return

    target_country = " ".join(args).strip()
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text(f"❌ لا توجد دولة بهذا الاسم: *{target_country}*", parse_mode="Markdown")
        return

    if target["user_id"] == user["user_id"]:
        await update.message.reply_text("❌ لا يمكنك التجسس على نفسك!")
        return

    level, exp = await get_intel_data(user["user_id"])
    info = INTEL_LEVELS.get(level, INTEL_LEVELS[0])

    # فترة الانتظار
    cooldown = await get_cooldown(user["user_id"], f"spy_{operation}")
    if cooldown > 0:
        from utils import fmt_time_remaining
        await update.message.reply_text(
            f"⏳ انتظر *{fmt_time_remaining(cooldown)}* قبل إجراء عملية جديدة.",
            parse_mode="Markdown"
        )
        return

    # -- تجسس --
    if operation == "تجسس على":
        if level < 1:
            await update.message.reply_text("🔒 تحتاج *مستوى مخابرات 1+* للتجسس.", parse_mode="Markdown")
            return
        cost = 500_000
        if not await deduct_gold(user["user_id"], cost):
            await update.message.reply_text(f"❌ تحتاج *{cost:,} ¥* لبدء عملية التجسس.", parse_mode="Markdown")
            return

        detected = random.randint(1, 100) <= (30 - level * 4)
        if detected:
            fine = 200_000
            await add_intel_exp(user["user_id"], -1)
            await update.message.reply_text(
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚨 *جاسوسك انكشف في {target_country}!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💸 خسارة إضافية: `-{fine:,} ¥`\n"
                f"📉 -1 خبرة مخابرات\n"
                f"━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )
            await log_intel_operation(user["user_id"], target["user_id"], "تجسس على", False, True)
            return

        success = random.randint(1, 100) <= info["spy"]
        if success:
            stolen = int(target["gold"] * random.uniform(0.02, 0.06))
            await add_gold(user["user_id"], stolen)
            await deduct_gold(target["user_id"], stolen)
            upgraded = await add_intel_exp(user["user_id"], 1)
            msg = (
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔍 *تجسس ناجح على {target_country}!*\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"📊 الجيش: `{target['soldiers']:,}`\n"
                f"💰 الذهب: `{int(target['gold']):,} ¥`\n"
                f"💥 مضاعف الهجوم: `x{target['damage_bonus']:.2f}`\n"
                f"🛡️ مضاعف الدفاع: `x{target['defense_bonus']:.2f}`\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"💰 سرقة: `+{stolen:,} ¥`\n"
                f"⭐ +1 خبرة مخابرات"
            )
            if upgraded:
                new_level, _ = await get_intel_data(user["user_id"])
                msg += f"\n🎉 *ترقية! المستوى {new_level}*"
            msg += "\n━━━━━━━━━━━━━━━━━━━━━"
            await update.message.reply_text(msg, parse_mode="Markdown")
            await log_intel_operation(user["user_id"], target["user_id"], "تجسس على", True, False)
        else:
            await update.message.reply_text(f"❌ *فشل التجسس على {target_country}.*", parse_mode="Markdown")
            await log_intel_operation(user["user_id"], target["user_id"], "تجسس على", False, False)
        await set_cooldown(user["user_id"], "spy_تجسس على", 1800)

    # -- تخريب --
    elif operation == "تخريب":
        if level < 2:
            await update.message.reply_text("🔒 تحتاج *مستوى مخابرات 2+* للتخريب.", parse_mode="Markdown")
            return
        cost = 1_000_000
        if not await deduct_gold(user["user_id"], cost):
            await update.message.reply_text(f"❌ تحتاج `{cost:,} ¥`.", parse_mode="Markdown")
            return

        detected = random.randint(1, 100) <= (35 - level * 4)
        if detected:
            await update.message.reply_text(
                f"🚨 *تم كشف عميلك في {target_country}!*\n💸 خسرت `{cost:,} ¥`.",
                parse_mode="Markdown"
            )
            await log_intel_operation(user["user_id"], target["user_id"], "تخريب", False, True)
            return

        success = random.randint(1, 100) <= info["sabotage"]
        if success:
            stype = random.choice(["gold", "soldiers", "building"])
            if stype == "gold":
                stolen = int(target["gold"] * 0.10)
                await deduct_gold(target["user_id"], stolen)
                await add_gold(user["user_id"], stolen)
                result = f"💰 سرقت `{stolen:,} ¥` من خزينة {target_country}"
            elif stype == "soldiers":
                loss = int(target["soldiers"] * 0.15)
                await update_user(target["user_id"], soldiers=max(0, target["soldiers"] - loss))
                result = f"⚔️ دمّرت `{loss:,}` جندياً من {target_country}"
            else:
                result = f"🏭 دمّرت منشأة عشوائية في {target_country}"
            await add_intel_exp(user["user_id"], 2)
            await update.message.reply_text(
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💣 *تخريب ناجح!*\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"{result}\n"
                f"⭐ +2 خبرة مخابرات\n"
                f"━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )
            try:
                await context.bot.send_message(target["user_id"],
                    f"💣 *تعرضت لعملية تخريب!*\n{result}", parse_mode="Markdown")
            except Exception:
                pass
            await log_intel_operation(user["user_id"], target["user_id"], "تخريب", True, False)
        else:
            await update.message.reply_text(f"❌ *فشل التخريب في {target_country}.*", parse_mode="Markdown")
        await set_cooldown(user["user_id"], "spy_تخريب", 3600)

    # -- اغتيال --
    elif operation == "اغتيال":
        if level < 3:
            await update.message.reply_text("🔒 تحتاج *مستوى مخابرات 3+* للاغتيال.", parse_mode="Markdown")
            return
        cost = 2_000_000
        if not await deduct_gold(user["user_id"], cost):
            await update.message.reply_text(f"❌ تحتاج `{cost:,} ¥`.", parse_mode="Markdown")
            return

        success = random.randint(1, 100) <= info["assassinate"]
        if success:
            kill = int(target["soldiers"] * 0.30)
            await update_user(target["user_id"], soldiers=max(0, target["soldiers"] - kill))
            await add_intel_exp(user["user_id"], 3)
            await update.message.reply_text(
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🗡️ *اغتيال ناجح!*\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"💀 قتلت `{kill:,}` جندياً من {target_country}\n"
                f"⭐ +3 خبرة مخابرات\n"
                f"━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )
            try:
                await context.bot.send_message(target["user_id"],
                    f"🗡️ *تعرضت لعملية اغتيال! فقدت {kill:,} جندي.*", parse_mode="Markdown")
            except Exception:
                pass
            await log_intel_operation(user["user_id"], target["user_id"], "اغتيال", True, False)
        else:
            await update.message.reply_text(f"❌ *فشلت عملية الاغتيال في {target_country}.*", parse_mode="Markdown")
            await log_intel_operation(user["user_id"], target["user_id"], "اغتيال", False, False)
        await set_cooldown(user["user_id"], "spy_اغتيال", 7200)

    else:
        await update.message.reply_text("❌ عملية غير معروفة.")

# ======================== عمليات أخرى ========================
async def counter_intelligence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    cost = 300_000
    if not await deduct_gold(user["user_id"], cost):
        await update.message.reply_text(f"❌ تحتاج `{cost:,} ¥` لتفعيل مضادة التجسس.", parse_mode="Markdown")
        return
    await set_cooldown(user["user_id"], "counter_intel_active", 3600)
    await update.message.reply_text(
        f"🛡️ *تم تفعيل مضادة التجسس!*\n"
        f"لمدة ساعة، احتمال كشف الجواسيس مرتفع جداً.\n"
        f"💸 التكلفة: `{cost:,} ¥`",
        parse_mode="Markdown"
    )

async def fake_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    cost = 200_000
    if not await deduct_gold(user["user_id"], cost):
        await update.message.reply_text(f"❌ تحتاج `{cost:,} ¥` لنشر معلومات مزيفة.", parse_mode="Markdown")
        return
    await set_cooldown(user["user_id"], "fake_info_active", 3600)
    await update.message.reply_text(
        f"🎭 *معلومات مزيفة نشطة!*\n"
        f"لمدة ساعة، من يتجسس عليك سيحصل على بيانات خاطئة.\n"
        f"💸 التكلفة: `{cost:,} ¥`",
        parse_mode="Markdown"
    )

async def exposed_spies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM intel_operations WHERE target_id=? AND detected=1 ORDER BY executed_at DESC LIMIT 10",
            (user["user_id"],)
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await update.message.reply_text("📋 *لا توجد محاولات تجسس مكشوفة.*", parse_mode="Markdown")
        return

    text = "━━━━━━━━━━━━━━━━━━━━━\n🕵️ *جواسيس مكشوفون*\n➖➖➖➖➖➖➖➖➖➖\n"
    import time as t
    for row in rows:
        ts = t.strftime("%Y-%m-%d %H:%M", t.localtime(row["executed_at"]))
        op = await get_user(row["operator_id"])
        op_name = op["country"] if op else f"ID:{row['operator_id']}"
        text += f"• *{op_name}* — {row['operation_type']} — `{ts}`\n"
    text += "━━━━━━━━━━━━━━━━━━━━━"
    await update.message.reply_text(text, parse_mode="Markdown")

async def fortify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    fortify_level = user.get("fortify_level", 0)
    if fortify_level >= 3:
        await update.message.reply_text("❌ وصلت للحد الأقصى من التحصين (3/3).")
        return
    cost = 5_000_000 * (fortify_level + 1)
    if not await deduct_gold(user["user_id"], cost):
        await update.message.reply_text(
            f"❌ تحتاج `{cost:,} ¥` للتحصين.\n💵 رصيدك: `{user['gold']:,.0f} ¥`",
            parse_mode="Markdown"
        )
        return
    new_defense = round(user["defense_bonus"] + 0.15, 4)
    new_fortify = fortify_level + 1
    await update_user(user["user_id"], defense_bonus=new_defense, fortify_level=new_fortify)
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧱 *تحصين ناجح!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🛡️ +15% دفاع (المستوى {new_fortify}/3)\n"
        f"💪 الدفاع الكلي: `x{new_defense:.2f}`\n"
        f"💸 التكلفة: `-{cost:,} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
