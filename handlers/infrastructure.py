import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, deduct_gold,
    get_infrastructure, upgrade_infrastructure
)

# ================================ عرض البنية التحتية الحالية ================================
async def infrastructure_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بنية تحتية – عرض حالة البنية التحتية لدولتك"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    infra = await get_infrastructure(user["user_id"])
    next_cost = infra["upgrade_cost"]

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏗️ *البنية التحتية – {user['country']}*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📊 *المستوى الحالي:* `{infra['level']}`\n"
        f"🌾 *سعة الطعام:* `{infra['food_capacity']:,}` وحدة\n"
        f"⚡ *سعة الطاقة:* `{infra['energy_capacity']:,}` وحدة\n"
        f"⚔️ *سعة الجيش:* `{infra['army_capacity']:,}` جندي\n"
        f"💰 *تكلفة الترقية القادمة:* `{next_cost:,.0f} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *الترقية تزيد كل السعات بنسبة 50% تقريباً.*\n"
        f"🔧 *لتطوير بنيتك التحتية، استخدم الزر أدناه.*"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 ترقية البنية التحتية", callback_data="upgrade_infra")],
        [InlineKeyboardButton("📊 إحصائيات متقدمة", callback_data="infra_stats")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ================================ ترقية البنية التحتية (كول باك) ================================
async def upgrade_infra_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ ترقية البنية التحتية"""
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    infra = await get_infrastructure(user["user_id"])
    cost = infra["upgrade_cost"]

    if user["gold"] < cost:
        await query.edit_message_text(
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ *فشل الترقية – ذهب غير كافٍ!*\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"💰 *تحتاج:* `{cost:,.0f} ¥`\n"
            f"💵 *رصيدك:* `{user['gold']:,.0f} ¥`\n"
            f"━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        return

    # خصم التكلفة وترقية البنية
    await deduct_gold(user["user_id"], cost)
    new_level = await upgrade_infrastructure(user["user_id"])

    # جلب البيانات الجديدة
    new_infra = await get_infrastructure(user["user_id"])

    await query.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *ترقية البنية التحتية ناجحة!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📊 *المستوى الجديد:* `{new_level}`\n"
        f"🌾 *سعة الطعام:* `{new_infra['food_capacity']:,}` (+{new_infra['food_capacity'] - infra['food_capacity']})\n"
        f"⚡ *سعة الطاقة:* `{new_infra['energy_capacity']:,}` (+{new_infra['energy_capacity'] - infra['energy_capacity']})\n"
        f"⚔️ *سعة الجيش:* `{new_infra['army_capacity']:,}` (+{new_infra['army_capacity'] - infra['army_capacity']})\n"
        f"💰 *التكلفة:* `-{cost:,.0f} ¥`\n"
        f"💎 *التكلفة التالية:* `{new_infra['upgrade_cost']:,.0f} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

# ================================ إحصائيات متقدمة للبنية التحتية ================================
async def infra_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات متقدمة للبنية التحتية (تأثيراتها على الإنتاج)"""
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    infra = await get_infrastructure(user["user_id"])
    # حساب بعض الإحصائيات التقديرية
    food_multiplier = 1 + (infra["level"] * 0.1)
    energy_multiplier = 1 + (infra["level"] * 0.08)
    army_multiplier = 1 + (infra["level"] * 0.05)

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 *تأثير البنية التحتية – {user['country']}*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🌾 *مضاعف الإنتاج الزراعي:* `x{food_multiplier:.2f}`\n"
        f"⚡ *مضاعف إنتاج الطاقة:* `x{energy_multiplier:.2f}`\n"
        f"⚔️ *مضاعف سعة الجيش:* `x{army_multiplier:.2f}`\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💡 *كل مستوى يمنح بونص تراكمي:*\n"
        f"• +10% طعام\n• +8% طاقة\n• +5% سعة جيش\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔨 *ارفع مستواك لزيادة حدود الإنتاج والقوة العسكرية.*"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع للبنية", callback_data="back_to_infra")]
    ]))

# ================================ العودة للوحة البنية التحتية ================================
async def back_to_infra_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await infrastructure_handler(update, context)

# ================================ معالج الأوامر النصية ================================
async def build_infrastructure_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بناء بنية تحتية – أمر نصي لترقية البنية (اختصار)"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    infra = await get_infrastructure(user["user_id"])
    cost = infra["upgrade_cost"]

    if user["gold"] < cost:
        await update.message.reply_text(
            f"❌ *لا يمكن ترقية البنية التحتية – رصيد غير كافٍ!*\n💰 تحتاج `{cost:,.0f} ¥`\n💵 رصيدك: `{user['gold']:,.0f} ¥`",
            parse_mode="Markdown"
        )
        return

    await deduct_gold(user["user_id"], cost)
    new_level = await upgrade_infrastructure(user["user_id"])
    new_infra = await get_infrastructure(user["user_id"])

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *تمت ترقية البنية التحتية!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📊 *المستوى:* `{infra['level']}` → `{new_level}`\n"
        f"🌾 *سعة الطعام:* `{new_infra['food_capacity']:,}`\n"
        f"⚡ *سعة الطاقة:* `{new_infra['energy_capacity']:,}`\n"
        f"⚔️ *سعة الجيش:* `{new_infra['army_capacity']:,}`\n"
        f"💰 *التكلفة:* `-{cost:,.0f} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
