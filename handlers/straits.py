import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import get_user, get_strait, set_strait, get_cooldown, set_cooldown, get_cities_by_country
from config import STRAITS, STRAIT_BLOCK_COOLDOWN, PROVINCES

# ربط كل مضيق بالدول التي لها الحق في التحكم به (الدول المطلة عليه)
STRAIT_OWNERS = {
    "البسفور": ["الدولة العثمانية", "تركيا"],
    "جبل طارق": ["إسبانيا", "المغرب"],
    "القنال الإنجليزي": ["المملكة المتحدة", "فرنسا"],
    "ميسينا": ["إيطاليا"],
    "الدنمارك": ["الدنمارك", "السويد"],
}

async def can_control_strait(user_country: str, strait_name: str) -> bool:
    """التحقق مما إذا كانت الدولة تملك الحق في التحكم بالمضيق (بناءً على المنطقة أو المدن التابعة لها)"""
    allowed_countries = STRAIT_OWNERS.get(strait_name, [])
    if user_country in allowed_countries:
        return True
    # التحقق أيضاً من المدن: إذا كان المستخدم يملك أي مدينة تابعة للدول المطلة للمضيق
    for country in allowed_countries:
        cities = await get_cities_by_country(country)
        for city in cities:
            if city.get("owner_id") == user_country:
                return True
    return False

async def straits_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    text = "🌊 *المضائق والممرات البحرية*\n———————————————\n"
    buttons = []

    for strait_name, info in STRAITS.items():
        db_strait = await get_strait(strait_name)
        if db_strait:
            blocked = db_strait["blocked"]
            ctrl_id = db_strait["controller_id"]
            blocked_until = db_strait.get("blocked_until", 0)
            remaining = max(0, blocked_until - int(time.time()))
        else:
            blocked = False
            ctrl_id = 0
            remaining = 0

        status = "🔴 *مغلق*" if blocked else "🟢 *مفتوح*"
        ctrl_user = await get_user(ctrl_id) if ctrl_id else None
        ctrl_text = f"*المتحكم:* `{ctrl_user['country']}`" if ctrl_user else "*المتحكم:* `لا أحد`"
        remaining_text = f" ({remaining // 3600}س {(remaining % 3600) // 60}د)" if remaining > 0 else ""

        text += f"{'—' * 20}\n"
        text += f"🌊 *{strait_name}*\n  {status}{remaining_text}\n  {ctrl_text}\n"

        # عرض أزرار التحكم فقط إذا كان المستخدم يملك الحق
        if await can_control_strait(user["country"], strait_name):
            if not blocked:
                buttons.append([InlineKeyboardButton(f"🔒 إغلاق {strait_name}", callback_data=f"block_strait_{strait_name}")])
            else:
                buttons.append([InlineKeyboardButton(f"🔓 فتح {strait_name}", callback_data=f"open_strait_{strait_name}")])
        else:
            # إظهار زر غير مفعل أو رسالة توضيحية
            text += f"  ⚠️ *لا يمكنك التحكم بهذا المضيق* (لا تملك سواحله)\n"

    text += "———————————————\n"
    text += "💡 إغلاق المضيق يمنع عبور السفن ويؤثر على التجارة!"

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def straits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        return

    data = query.data

    if data.startswith("block_strait_"):
        strait_name = data.replace("block_strait_", "")
        if strait_name not in STRAITS:
            await query.answer("❌ مضيق غير موجود", show_alert=True)
            return

        # التحقق من الحق في التحكم
        if not await can_control_strait(user["country"], strait_name):
            await query.answer("❌ ليس لديك الحق في التحكم بهذا المضيق!", show_alert=True)
            return

        cd = await get_cooldown(user["user_id"], f"strait_{strait_name}")
        if cd > 0:
            await query.answer(f"⏳ انتظر {cd // 60} دقيقة", show_alert=True)
            return

        await set_strait(strait_name, user["user_id"], True, STRAIT_BLOCK_COOLDOWN)
        await set_cooldown(user["user_id"], f"strait_{strait_name}", STRAIT_BLOCK_COOLDOWN)

        await query.edit_message_text(
            f"🔒 *تم إغلاق مضيق {strait_name}!*\n———————————————\n"
            f"🌊 المضيق: {strait_name}\n"
            f"👤 المتحكم: {user['country']}\n"
            f"⏳ مدة الإغلاق: {STRAIT_BLOCK_COOLDOWN // 3600} ساعة\n"
            f"———————————————\n"
            f"⚠️ يمنع عبور السفن الحربية والتجارية!\n"
            f"📉 يؤثر على اقتصاد الدول المجاورة!",
            parse_mode="Markdown"
        )

        # إشعار الدول المتأثرة
        affected = STRAITS[strait_name].get("routes", [])
        for country in affected:
            from database import get_user_by_country
            affected_user = await get_user_by_country(country)
            if affected_user and affected_user["user_id"] != user["user_id"]:
                try:
                    await query.bot.send_message(
                        affected_user["user_id"],
                        f"🚨 *تحذير: مضيق {strait_name} أُغلق!*\n"
                        f"👤 المتحكم: {user['country']}\n"
                        f"📉 سيؤثر على تجارتك البحرية!",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
        return

    if data.startswith("open_strait_"):
        strait_name = data.replace("open_strait_", "")
        db_strait = await get_strait(strait_name)

        if not await can_control_strait(user["country"], strait_name):
            await query.answer("❌ ليس لديك الحق في التحكم بهذا المضيق!", show_alert=True)
            return

        if db_strait and db_strait["controller_id"] != user["user_id"]:
            await query.answer("❌ أنت لست المتحكم في هذا المضيق!", show_alert=True)
            return

        await set_strait(strait_name, 0, False, 0)
        await query.edit_message_text(
            f"🔓 *تم فتح مضيق {strait_name}!*\n———————————————\n"
            f"🟢 المضيق مفتوح الآن للملاحة\n"
            f"🚢 العبور متاح لجميع السفن\n"
            f"———————————————",
            parse_mode="Markdown"
        )

async def close_strait_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    args = context.args
    if not args:
        straits_list = "\n".join(f"  🌊 {s}" for s in STRAITS)
        await update.message.reply_text(
            f"💡 *استخدم:* `اغلق مضيق [اسم]`\n\nالمضائق المتاحة:\n{straits_list}",
            parse_mode="Markdown"
        )
        return
    strait_name = " ".join(args)
    if strait_name not in STRAITS:
        await update.message.reply_text("❌ مضيق غير موجود.")
        return

    if not await can_control_strait(user["country"], strait_name):
        await update.message.reply_text("❌ *ليس لديك الحق في التحكم بهذا المضيق!* (لا تملك سواحله)", parse_mode="Markdown")
        return

    cd = await get_cooldown(user["user_id"], f"strait_{strait_name}")
    if cd > 0:
        await update.message.reply_text(f"⏳ *انتظر {cd // 60} دقيقة للتحكم في هذا المضيق.*", parse_mode="Markdown")
        return

    await set_strait(strait_name, user["user_id"], True, STRAIT_BLOCK_COOLDOWN)
    await set_cooldown(user["user_id"], f"strait_{strait_name}", STRAIT_BLOCK_COOLDOWN)

    await update.message.reply_text(
        f"🔒 *أغلقت مضيق {strait_name}!*\n———————————————\n"
        f"⏳ يظل مغلقاً لمدة {STRAIT_BLOCK_COOLDOWN // 3600} ساعة\n"
        f"🌊 ممنوع العبور البحري\n"
        f"———————————————",
        parse_mode="Markdown"
    )

async def open_strait_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `افتح مضيق [اسم]`", parse_mode="Markdown")
        return
    strait_name = " ".join(args)
    db_strait = await get_strait(strait_name)

    if not await can_control_strait(user["country"], strait_name):
        await update.message.reply_text("❌ *ليس لديك الحق في التحكم بهذا المضيق!*", parse_mode="Markdown")
        return

    if db_strait and db_strait["controller_id"] != user["user_id"]:
        await update.message.reply_text("❌ *أنت لست المتحكم في هذا المضيق!*", parse_mode="Markdown")
        return

    await set_strait(strait_name, 0, False, 0)
    await update.message.reply_text(
        f"🔓 *فتحت مضيق {strait_name}!*\n🟢 العبور متاح الآن.",
        parse_mode="Markdown"
    )
