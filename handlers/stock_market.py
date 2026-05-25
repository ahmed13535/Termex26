import time
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, deduct_gold, add_gold,
    get_all_stocks, update_stock_price,
    get_user_stocks, add_stock, remove_stock
)

# ================================ تحديث أسعار البورصة (يُستدعى من game_loop) ================================
async def update_stock_prices():
    """تحديث أسعار جميع الأسهم بشكل عشوائي (±5% إلى ±15%)"""
    stocks = await get_all_stocks()
    for stock in stocks:
        change = random.uniform(-0.15, 0.15)
        new_price = max(10.0, stock["current_price"] * (1 + change))
        await update_stock_price(stock["resource_name"], new_price)

# ================================ عرض البورصة ================================
async def stock_market_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بورصة – عرض أسعار الموارد والرسم البياني"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    stocks = await get_all_stocks()
    text = "━━━━━━━━━━━━━━━━━━━━━\n📈 *سوق الأوراق المالية – عصر الأمم*\n➖➖➖➖➖➖➖➖➖➖\n"
    for stock in stocks:
        text += f"• **{stock['resource_name']}** : `{stock['current_price']:,.2f} ¥`\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n💡 *الأوامر:*\n• `شراء أسهم [مورد] [عدد]`\n• `بيع أسهم [مورد] [عدد]`\n• `محفظتي`"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 تحديث الأسعار", callback_data="refresh_stocks"),
         InlineKeyboardButton("📁 محفظتي", callback_data="my_portfolio")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ================================ شراء أسهم ================================
async def buy_stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شراء أسهم [مورد] [عدد]"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("💡 *استخدم:* `شراء أسهم [المورد] [العدد]`\nمثال: `شراء أسهم ذهب 10`", parse_mode="Markdown")
        return

    resource = args[0]
    try:
        quantity = int(args[1])
    except:
        await update.message.reply_text("❌ *العدد يجب أن يكون رقماً صحيحاً.*", parse_mode="Markdown")
        return

    if quantity <= 0:
        await update.message.reply_text("❌ *العدد يجب أن يكون أكبر من صفر.*", parse_mode="Markdown")
        return

    stocks = await get_all_stocks()
    stock = next((s for s in stocks if s["resource_name"] == resource), None)
    if not stock:
        await update.message.reply_text(f"❌ *المورد `{resource}` غير موجود.*\n📌 الموارد المتاحة: قمح، ذهب، نفط، حديد، خشب، قهوة، شاي", parse_mode="Markdown")
        return

    price = stock["current_price"]
    total_cost = price * quantity

    if user["gold"] < total_cost:
        await update.message.reply_text(f"❌ *ذهب غير كافٍ!*\n💰 *تحتاج:* `{total_cost:,.2f} ¥`\n💵 *رصيدك:* `{user['gold']:,.0f} ¥`", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], total_cost)
    await add_stock(user["user_id"], resource, quantity)

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *شراء أسهم ناجح!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📦 *المورد:* `{resource}`\n"
        f"🔢 *الكمية:* `{quantity}`\n"
        f"💰 *السعر الإجمالي:* `-{total_cost:,.2f} ¥`\n"
        f"💵 *رصيدك الجديد:* `{user['gold'] - total_cost:,.0f} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

# ================================ بيع أسهم ================================
async def sell_stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بيع أسهم [مورد] [عدد]"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("💡 *استخدم:* `بيع أسهم [المورد] [العدد]`", parse_mode="Markdown")
        return

    resource = args[0]
    try:
        quantity = int(args[1])
    except:
        await update.message.reply_text("❌ *العدد يجب أن يكون رقماً صحيحاً.*", parse_mode="Markdown")
        return

    if quantity <= 0:
        await update.message.reply_text("❌ *العدد يجب أن يكون أكبر من صفر.*", parse_mode="Markdown")
        return

    user_stocks = await get_user_stocks(user["user_id"])
    if resource not in user_stocks or user_stocks[resource]["quantity"] < quantity:
        await update.message.reply_text(f"❌ *ليس لديك {quantity} سهم من {resource} في محفظتك.*", parse_mode="Markdown")
        return

    stocks = await get_all_stocks()
    stock = next((s for s in stocks if s["resource_name"] == resource), None)
    if not stock:
        await update.message.reply_text(f"❌ *المورد `{resource}` غير موجود.*", parse_mode="Markdown")
        return

    price = stock["current_price"]
    total_revenue = price * quantity

    await remove_stock(user["user_id"], resource, quantity)
    await add_gold(user["user_id"], total_revenue)

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *بيع أسهم ناجح!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📦 *المورد:* `{resource}`\n"
        f"🔢 *الكمية:* `{quantity}`\n"
        f"💰 *الإيرادات:* `+{total_revenue:,.2f} ¥`\n"
        f"💵 *رصيدك الجديد:* `{user['gold'] + total_revenue:,.0f} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

# ================================ عرض المحفظة ================================
async def my_portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """محفظتي – عرض أسهمك والربح/الخسارة"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    user_stocks = await get_user_stocks(user["user_id"])
    if not user_stocks:
        await update.message.reply_text("📭 *محفظتك فارغة.* ابدأ بشراء الأسهم باستخدام `شراء أسهم [مورد] [عدد]`.", parse_mode="Markdown")
        return

    stocks = await get_all_stocks()
    stock_dict = {s["resource_name"]: s["current_price"] for s in stocks}

    text = "━━━━━━━━━━━━━━━━━━━━━\n📁 *محفظتك الاستثمارية*\n➖➖➖➖➖➖➖➖➖➖\n"
    total_value = 0
    for resource, data in user_stocks.items():
        qty = data["quantity"]
        current_price = stock_dict.get(resource, 0)
        value = qty * current_price
        total_value += value
        text += f"• **{resource}** : `{qty}` سهم × `{current_price:,.2f}` = `{value:,.2f} ¥`\n"
    text += f"➖➖➖➖➖➖➖➖➖➖\n💰 *القيمة الإجمالية:* `{total_value:,.2f} ¥`\n━━━━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(text, parse_mode="Markdown")

# ================================ معالج الأزرار (تحديث الأسعار، محفظتي) ================================
async def stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "refresh_stocks":
        await update_stock_prices()
        await query.edit_message_text("✅ *تم تحديث أسعار البورصة.* استخدم `بورصة` مرة أخرى لعرض الأسعار الجديدة.", parse_mode="Markdown")
    elif query.data == "my_portfolio":
        await my_portfolio_handler(update, context)
