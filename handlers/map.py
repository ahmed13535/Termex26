from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import get_user, get_all_provinces, get_buildings, get_wars_for_user, get_alliance
from map_renderer import render_province_map
from config import COUNTRIES

async def map_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خريطة المدن"""
    try:
        user = await get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
            return

        img = await render_province_map(update, context)
        provinces = await get_all_provinces()
        total = len(provinces)
        owned = len([p for p in provinces if p.get("owner_id") and p["owner_id"] != 0])
        free = total - owned

        caption = (
            f"**🌍 خريطة المدن – الوضع الراهن**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏙️ *إجمالي المدن:* `{total}`\n"
            f"🔴 *مدن مملوكة:* `{owned}`\n"
            f"⚪ *مدن حرة:* `{free}`\n"
            f"🌟 *دولتك:* `{user['country']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 نقاط ملونة = مدن مملوكة (لون الدولة + علم)\n"
            f"⚪ نقاط رمادية = مدن حرة (غير محجوزة)\n"
            f"🚩 نقطة حمراء مع راية = مدينة محتلة (لم تدمج بعد)\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحديث", callback_data="refresh_map"),
             InlineKeyboardButton("🌍 خريطة كاملة", callback_data="full_map")],
            [InlineKeyboardButton("📊 حالتي", callback_data="my_status")]
        ])
        await update.message.reply_photo(photo=img, caption=caption, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        await update.message.reply_text(f"⚠️ *حدث خطأ أثناء تحميل الخريطة:* `{e}`", parse_mode="Markdown")

async def map_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الخريطة"""
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    if query.data in ("refresh_map", "full_map"):
        img = await render_province_map(update, context)
        await query.message.reply_photo(photo=img, caption="🗺 *خريطة محدثة*", parse_mode="Markdown")
    elif query.data == "my_status":
        await status_handler(update, context)

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حالة الدولة (المستخدم)"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    buildings = await get_buildings(user_id)
    wars = await get_wars_for_user(user_id)
    alliance = await get_alliance(user_id)

    morale_bar = "█" * (user["morale"] // 10) + "░" * (10 - user["morale"] // 10)
    blist = ", ".join(f"{b}({d['level']})" for b, d in buildings.items()) or "لا يوجد"

    text = (
        f"📊 *لوحة حالة {user['country']}* {user['flag'] if len(user['flag']) < 5 else ''}\n"
        f"———————————————\n"
        f"👑 الحاكم: @{user['username']}\n"
        f"🌟 المستوى: {user['level']} | XP: {user['xp']:,}\n"
        f"🏆 الهيبة: {user['prestige']:,} نقطة\n"
        f"———————————————\n"
        f"💰 الذهب: *{user['gold']:,.0f} ¥*\n"
        f"🌾 الطعام: {user['food']:,}\n"
        f"⚡ الطاقة: {user['energy']:,}\n"
        f"———————————————\n"
        f"⚔️ الجنود: *{user['soldiers']:,}*\n"
        f"🚛 الدبابات: {user['tanks']:,}\n"
        f"💥 المدفعية: {user['artillery']:,}\n"
        f"✈️ الطائرات: {user['aircraft']:,}\n"
        f"🚀 الصواريخ: {user['missiles']:,}\n"
        f"🛡 الدفاع الجوي: {user['air_defense']:,}\n"
        f"🚢 الحاملات: {user['carriers']:,}\n"
        f"🌊 الغواصات: {user['submarines']:,}\n"
        f"☣️ بيولوجي: {user['bio_weapons']:,}\n"
        f"☢️ نووي: {user['nukes']:,}\n"
        f"———————————————\n"
        f"💪 المعنويات: [{morale_bar}] {user['morale']}%\n"
        f"🔰 مضاعف الهجوم: x{user['damage_bonus']:.2f}\n"
        f"🛡 مضاعف الدفاع: x{user['defense_bonus']:.2f}\n"
        f"———————————————\n"
        f"🏗 المباني: {blist}\n"
        f"⚔️ حروب نشطة: {len(wars)}\n"
        f"🤝 الحلف: {alliance['name'] if alliance else 'بدون حلف'}\n"
        f"———————————————"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
