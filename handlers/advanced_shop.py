import time
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, deduct_gold, add_gold,
    get_all_crops, get_user_crops, add_crop_to_user, update_crop_harvest,
    get_infrastructure, get_buildings, add_building
)

# ================================ الأسعار الأساسية (ستتغير عبر game_loop) ================================
MARKET_PRICES = {
    "بنادق هجومية": 250,
    "دروع واقية": 400,
    "مدفعية ثقيلة": 700,
    "دبابة": 80000,
    "مركبة مدرعة": 120000,
    "طائرة مسيرة": 250000,
    "طائرة حربية": 1000000,
    "طائرة شبح": 3000000,
    "زورق صاروخي": 300000,
    "مدمرة": 800000,
    "حاملة طائرات": 5000000,
    "صواريخ فرط صوتية": 3000000,
}

# قوائم الأسلحة والفئات
WEAPONS_GROUND = {
    "بنادق هجومية": {"soldiers": 0, "damage": 0.05, "defense": 0, "emoji": "🔫"},
    "دروع واقية":   {"soldiers": 0, "damage": 0,    "defense": 0.08, "emoji": "🛡️"},
    "مدفعية ثقيلة": {"soldiers": 0, "damage": 0.15, "defense": 0, "emoji": "💣"},
    "دبابة":        {"soldiers": 25, "damage": 0.003, "defense": 0, "emoji": "🚛"},
    "مركبة مدرعة":  {"soldiers": 15, "damage": 0.002, "defense": 0.003, "emoji": "🛡️"},
}

WEAPONS_AIR = {
    "طائرة مسيرة":   {"soldiers": 8,  "damage": 0.004, "defense": 0.002, "emoji": "🛸"},
    "طائرة حربية":   {"soldiers": 40, "damage": 0.01,  "defense": 0,     "emoji": "✈️"},
    "طائرة شبح":     {"soldiers": 100, "damage": 0.018, "defense": 0.005, "emoji": "🛩️"},
}

WEAPONS_NAVAL = {
    "زورق صاروخي": {"soldiers": 20, "damage": 0.01, "defense": 0.005, "emoji": "🚤"},
    "مدمرة":       {"soldiers": 50, "damage": 0.02, "defense": 0.01,  "emoji": "🚢"},
    "حاملة طائرات":{"soldiers": 200, "damage": 0.05, "defense": 0.02, "emoji": "🛳️"},
}

WEAPONS_MISSILES = {
    "صواريخ فرط صوتية": {"soldiers": 0, "damage": 0.45, "defense": 0, "emoji": "⚡"},
}

FARMS_LIST = {
    "مزرعة قمح":   {"cost": 50000,  "production": 500,  "emoji": "🌾"},
    "مزرعة بن":    {"cost": 80000,  "production": 800,  "emoji": "☕"},
    "بستان زيتون": {"cost": 60000,  "production": 600,  "emoji": "🫒"},
    "مزرعة ذرة":   {"cost": 45000,  "production": 450,  "emoji": "🌽"},
    "مزرعة بطاطس": {"cost": 40000,  "production": 400,  "emoji": "🥔"},
}

BUILDINGS_LIST = {
    "مصنع أسلحة":   {"cost": 2000000, "production": 200, "emoji": "🔩"},
    "ميناء تجاري": {"cost": 1500000, "production": 150, "emoji": "⚓"},
    "مستشفى":      {"cost": 800000,  "production": 80,  "emoji": "🏥"},
    "مفاعل نووي":  {"cost": 20000000, "production": 1000, "emoji": "☢️"},
    "جامعة":       {"cost": 4000000, "production": 200, "emoji": "🎓"},
    "بنك مركزي":   {"cost": 6000000, "production": 400, "emoji": "🏦"},
}

FORTRESS_LIST = {
    "برج دفاع":      {"cost": 3000000, "defense_bonus": 0.10, "emoji": "🗼"},
    "جدار حماية":    {"cost": 5000000, "defense_bonus": 0.15, "emoji": "🧱"},
    "قاعدة عسكرية":  {"cost": 10000000, "defense_bonus": 0.25, "emoji": "🏰"},
}

RESOURCES_LIST = {
    "نفط خام":     {"cost": 200000, "production": 50,  "emoji": "🛢️"},
    "غاز طبيعي":   {"cost": 180000, "production": 45,  "emoji": "⛽"},
    "حديد خام":    {"cost": 150000, "production": 40,  "emoji": "⛏️"},
    "ذهب":         {"cost": 500000, "production": 10,  "emoji": "🥇"},
}

# ================================ دوال مساعدة ================================
def get_current_price(item_name: str) -> int:
    return MARKET_PRICES.get(item_name, 0)

# ================================ القائمة الرئيسية للسوق ================================
async def market_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    text = (
        "**『 🏪 السوق العسكري العالمي 』**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *رصيدك:* `{user['gold']:,.0f} ¥`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "• اختر الفئة التي تريد التسوق منها:\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 السوق البري", callback_data="market_weapons_ground")],
        [InlineKeyboardButton("✈️ السوق الجوي", callback_data="market_weapons_air")],
        [InlineKeyboardButton("🚢 السوق البحري", callback_data="market_weapons_naval")],
        [InlineKeyboardButton("🌾 السوق – مزارع", callback_data="market_farms")],
        [InlineKeyboardButton("🏭 السوق – مباني", callback_data="market_buildings")],
        [InlineKeyboardButton("🏰 السوق – حصون", callback_data="market_fortresses")],
        [InlineKeyboardButton("💎 السوق – موارد", callback_data="market_resources")],
        [InlineKeyboardButton("📊 مخزني", callback_data="my_inventory")],
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ================================ عرض فئات الأسلحة ================================
async def show_weapons_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, weapons_dict: dict):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        return

    text = f"**『 {category} 』**\n━━━━━━━━━━━━━━━━━━━━━\n"
    buttons = []
    for name, data in weapons_dict.items():
        price = get_current_price(name)
        text += f"{data['emoji']} *{name}* – `{price:,} ¥`\n"
        if data.get("soldiers"):
            text += f"   👥 +{data['soldiers']} جندي\n"
        if data.get("damage"):
            text += f"   💥 +{data['damage']*100:.1f}% ضرر\n"
        if data.get("defense"):
            text += f"   🛡️ +{data['defense']*100:.1f}% دفاع\n"
        buttons.append([InlineKeyboardButton(f"{data['emoji']} شراء {name}", callback_data=f"buy_weapon_{name}")])
    text += "━━━━━━━━━━━━━━━━━━━━━\n💡 *اختر السلاح ثم الكمية.*"
    buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="market_back")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def market_weapons_ground(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_weapons_category(update, context, "🪖 السوق البري", WEAPONS_GROUND)

async def market_weapons_air(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_weapons_category(update, context, "✈️ السوق الجوي", WEAPONS_AIR)

async def market_weapons_naval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_weapons_category(update, context, "🚢 السوق البحري", WEAPONS_NAVAL)

# ================================ المزارع والمباني والحصون والموارد ================================
async def market_farms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "**『 🌾 السوق – المزارع 』**\n━━━━━━━━━━━━━━━━━━━━━\n"
    buttons = []
    for name, data in FARMS_LIST.items():
        text += f"{data['emoji']} *{name}* – `{data['cost']:,} ¥`\n   📦 إنتاج: +{data['production']} طن/دورة\n"
        buttons.append([InlineKeyboardButton(f"{data['emoji']} شراء {name}", callback_data=f"buy_farm_{name}")])
    text += "━━━━━━━━━━━━━━━━━━━━━\n💡 *شراء مزرعة يزيد إنتاجك الزراعي.*"
    buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="market_back")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def market_buildings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "**『 🏭 السوق – المباني 』**\n━━━━━━━━━━━━━━━━━━━━━\n"
    buttons = []
    for name, data in BUILDINGS_LIST.items():
        text += f"{data['emoji']} *{name}* – `{data['cost']:,} ¥`\n   📈 إنتاج: +{data['production']} وحدة/دورة\n"
        buttons.append([InlineKeyboardButton(f"{data['emoji']} شراء {name}", callback_data=f"buy_building_{name}")])
    text += "━━━━━━━━━━━━━━━━━━━━━\n💡 *المباني تزيد دخلك الصناعي والخدمي.*"
    buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="market_back")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def market_fortresses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "**『 🏰 السوق – الحصون 』**\n━━━━━━━━━━━━━━━━━━━━━\n"
    buttons = []
    for name, data in FORTRESS_LIST.items():
        text += f"{data['emoji']} *{name}* – `{data['cost']:,} ¥`\n   🛡️ دفاع إضافي: +{data['defense_bonus']*100:.0f}%\n"
        buttons.append([InlineKeyboardButton(f"{data['emoji']} شراء {name}", callback_data=f"buy_fortress_{name}")])
    text += "━━━━━━━━━━━━━━━━━━━━━\n💡 *الحصون تزيد من قدراتك الدفاعية ضد الهجمات.*"
    buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="market_back")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def market_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "**『 💎 السوق – الموارد 』**\n━━━━━━━━━━━━━━━━━━━━━\n"
    buttons = []
    for name, data in RESOURCES_LIST.items():
        text += f"{data['emoji']} *{name}* – `{data['cost']:,} ¥`\n   📦 إنتاج: +{data['production']} وحدة/دورة\n"
        buttons.append([InlineKeyboardButton(f"{data['emoji']} شراء {name}", callback_data=f"buy_resource_{name}")])
    text += "━━━━━━━━━━━━━━━━━━━━━\n💡 *الموارد تزيد من إنتاجك الصناعي والطاقوي.*"
    buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="market_back")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ================================ عمليات الشراء العامة ================================
async def buy_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, item_type: str, item_name: str, item_data: dict):
    query = update.callback_query
    user = await get_user(query.from_user.id)
    if not user:
        return
    # تحديد السعر الفعلي (قد يكون من MARKET_PRICES للأسلحة)
    if item_type == "weapon":
        price = get_current_price(item_name)
    else:
        price = item_data.get("cost", 0)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data=f"confirm_{item_type}_{item_name}_1"),
         InlineKeyboardButton("5", callback_data=f"confirm_{item_type}_{item_name}_5"),
         InlineKeyboardButton("10", callback_data=f"confirm_{item_type}_{item_name}_10")],
        [InlineKeyboardButton("25", callback_data=f"confirm_{item_type}_{item_name}_25"),
         InlineKeyboardButton("50", callback_data=f"confirm_{item_type}_{item_name}_50"),
         InlineKeyboardButton("100", callback_data=f"confirm_{item_type}_{item_name}_100")],
        [InlineKeyboardButton("✏️ كمية مخصصة", callback_data=f"custom_{item_type}_{item_name}"),
         InlineKeyboardButton("🔙 رجوع", callback_data="market_back")]
    ])
    await query.edit_message_text(
        f"**『 شراء {item_name} 』**\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *السعر:* `{price:,} ¥` للوحدة\n"
        f"📦 *اختر الكمية:*\n━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    context.user_data["pending_purchase"] = (item_type, item_name, {"cost": price, **item_data})

async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    parts = data.split("_")
    if len(parts) < 4:
        await query.answer("⚠️ خطأ في البيانات", show_alert=True)
        return
    item_type = parts[1]
    item_name = parts[2]
    qty = int(parts[3])
    pending = context.user_data.get("pending_purchase")
    if not pending or pending[1] != item_name:
        await query.answer("⚠️ انتهت صلاحية الجلسة، ابدأ من جديد.", show_alert=True)
        return
    item_data = pending[2]

    user = await get_user(query.from_user.id)
    if not user:
        return

    total_cost = item_data["cost"] * qty
    if user["gold"] < total_cost:
        await query.edit_message_text(
            f"❌ *ذهب غير كافٍ!*\n💰 *تحتاج:* `{total_cost:,.0f} ¥`\n💵 *رصيدك:* `{user['gold']:,.0f} ¥`",
            parse_mode="Markdown"
        )
        return

    await deduct_gold(user["user_id"], total_cost)

    if item_type == "weapon":
        new_soldiers = user["soldiers"] + (item_data.get("soldiers", 0) * qty)
        new_damage = round(user["damage_bonus"] + (item_data.get("damage", 0) * qty), 4)
        new_defense = round(user["defense_bonus"] + (item_data.get("defense", 0) * qty), 4)
        await update_user(user["user_id"], soldiers=new_soldiers, damage_bonus=new_damage, defense_bonus=new_defense)
        msg = (
            f"**✅ تم شراء {qty} × {item_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *التكلفة:* `-{total_cost:,.0f} ¥`\n"
            f"⚔️ *جيشك:* `{new_soldiers:,}`\n"
            f"💥 *مضاعف الهجوم:* x{new_damage:.2f}\n"
            f"🛡️ *مضاعف الدفاع:* x{new_defense:.2f}\n"
            f"💵 *رصيدك الجديد:* `{user['gold'] - total_cost:,.0f} ¥`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
    elif item_type in ("farm", "building", "resource"):
        await add_building(user["user_id"], item_name)
        type_emoji = {"farm":"🌾", "building":"🏭", "resource":"💎"}.get(item_type, "📦")
        msg = (
            f"**✅ تم شراء {qty} × {item_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *التكلفة:* `-{total_cost:,.0f} ¥`\n"
            f"{type_emoji} *تمت إضافة {item_name} بنجاح*\n"
            f"💵 *رصيدك الجديد:* `{user['gold'] - total_cost:,.0f} ¥`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
    elif item_type == "fortress":
        new_defense = round(user["defense_bonus"] + (item_data.get("defense_bonus", 0) * qty), 4)
        await update_user(user["user_id"], defense_bonus=new_defense)
        msg = (
            f"**✅ تم شراء {qty} × {item_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *التكلفة:* `-{total_cost:,.0f} ¥`\n"
            f"🛡️ *دفاع إضافي:* +{item_data['defense_bonus']*100*qty:.0f}%\n"
            f"🛡️ *مضاعف الدفاع الكلي:* x{new_defense:.2f}\n"
            f"💵 *رصيدك الجديد:* `{user['gold'] - total_cost:,.0f} ¥`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        msg = "⚠️ *نوع العنصر غير معروف.*"

    await query.edit_message_text(msg, parse_mode="Markdown")
    context.user_data.pop("pending_purchase", None)

# ================================ كمية مخصصة ================================
async def custom_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    if len(parts) < 3:
        return
    item_type = parts[1]
    item_name = parts[2]
    context.user_data["custom_purchase"] = (item_type, item_name)
    await query.edit_message_text(
        f"**『 كمية مخصصة لـ {item_name} 』**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✏️ *أرسل الكمية المطلوبة (رقم فقط)*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def process_custom_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    custom = context.user_data.get("custom_purchase")
    if not custom:
        return
    item_type, item_name = custom
    try:
        qty = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ *الكمية غير صحيحة. أرسل رقماً صحيحاً.*", parse_mode="Markdown")
        return

    # استرجاع بيانات العنصر
    if item_type == "weapon":
        all_weapons = {**WEAPONS_GROUND, **WEAPONS_AIR, **WEAPONS_NAVAL, **WEAPONS_MISSILES}
        item_data = all_weapons.get(item_name)
        if item_data:
            item_data["cost"] = get_current_price(item_name)
    elif item_type == "farm":
        item_data = FARMS_LIST.get(item_name)
    elif item_type == "building":
        item_data = BUILDINGS_LIST.get(item_name)
    elif item_type == "fortress":
        item_data = FORTRESS_LIST.get(item_name)
    elif item_type == "resource":
        item_data = RESOURCES_LIST.get(item_name)
    else:
        await update.message.reply_text("❌ *نوع العنصر غير معروف.*")
        return
    if not item_data:
        await update.message.reply_text("❌ *العنصر غير موجود.*")
        return

    total_cost = item_data["cost"] * qty
    if user["gold"] < total_cost:
        await update.message.reply_text(
            f"❌ *ذهب غير كافٍ!*\n💰 تحتاج `{total_cost:,.0f} ¥`\n💵 رصيدك: `{user['gold']:,.0f} ¥`",
            parse_mode="Markdown"
        )
        return

    await deduct_gold(user["user_id"], total_cost)

    if item_type == "weapon":
        new_soldiers = user["soldiers"] + (item_data.get("soldiers", 0) * qty)
        new_damage = round(user["damage_bonus"] + (item_data.get("damage", 0) * qty), 4)
        new_defense = round(user["defense_bonus"] + (item_data.get("defense", 0) * qty), 4)
        await update_user(user["user_id"], soldiers=new_soldiers, damage_bonus=new_damage, defense_bonus=new_defense)
        msg = f"**✅ تم شراء {qty} × {item_name}**\n━━━━━━━━━━━━━━━━━━━━━\n💰 -{total_cost:,} ¥\n⚔️ جيشك: {new_soldiers:,}\n💥 ضرر: x{new_damage:.2f}\n🛡️ دفاع: x{new_defense:.2f}\n💵 رصيدك: {user['gold'] - total_cost:,.0f} ¥"
    elif item_type in ("farm", "building", "resource"):
        await add_building(user["user_id"], item_name)
        emoji = {"farm":"🌾", "building":"🏭", "resource":"💎"}.get(item_type, "📦")
        msg = f"**✅ تم شراء {qty} × {item_name}**\n━━━━━━━━━━━━━━━━━━━━━\n💰 -{total_cost:,} ¥\n{emoji} تم إضافة {item_name}.\n💵 رصيدك: {user['gold'] - total_cost:,.0f} ¥"
    elif item_type == "fortress":
        new_defense = round(user["defense_bonus"] + (item_data.get("defense_bonus", 0) * qty), 4)
        await update_user(user["user_id"], defense_bonus=new_defense)
        msg = f"**✅ تم شراء {qty} × {item_name}**\n━━━━━━━━━━━━━━━━━━━━━\n💰 -{total_cost:,} ¥\n🛡️ دفاع إضافي: +{item_data['defense_bonus']*100*qty:.0f}%\n🛡️ دفاع كلي: x{new_defense:.2f}\n💵 رصيدك: {user['gold'] - total_cost:,.0f} ¥"
    else:
        msg = "⚠️ خطأ في نوع العنصر."

    await update.message.reply_text(msg, parse_mode="Markdown")
    context.user_data.pop("custom_purchase", None)

# ================================ عرض المخزون والمحاصيل ================================
async def my_inventory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        return
    text = (
        f"**📦 مخزني – {user['country']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ *القوة العسكرية:*\n"
        f"👥 *إجمالي الجنود:* `{user['soldiers']:,}`\n"
        f"💥 *مضاعف الهجوم:* x{user['damage_bonus']:.2f}\n"
        f"🛡️ *مضاعف الدفاع:* x{user['defense_bonus']:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌾 *المحاصيل المملوكة:*\n"
    )
    user_crops = await get_user_crops(user["user_id"])
    if not user_crops:
        text += "• *لا توجد محاصيل.*\n"
    else:
        crops_info = await get_all_crops()
        crops_dict = {c["crop_name"]: c for c in crops_info}
        now = int(time.time())
        for crop_name, data in user_crops.items():
            crop_info = crops_dict.get(crop_name)
            if not crop_info:
                continue
            ready_time = data["last_harvest"] + (crop_info["growth_hours"] * 3600)
            if now >= ready_time:
                status = "✅ **جاهز للحصاد**"
            else:
                remaining = ready_time - now
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                status = f"⏳ ينضج بعد `{hours}h {minutes}m`"
            text += f"• {crop_info['emoji']} *{crop_name}*: الكمية `{data['quantity']}` — {status}\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n💡 *للحصاد:* `حصاد محصول [الاسم]` أو `حصاد الكل`"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع للسوق", callback_data="market_back"),
         InlineKeyboardButton("🌾 حصاد الكل", callback_data="harvest_all")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def harvest_all_crops(update, user):
    user_crops = await get_user_crops(user["user_id"])
    if not user_crops:
        if hasattr(update, 'message'):
            await update.message.reply_text("❌ *ليس لديك أي محاصيل في مزرعتك.*", parse_mode="Markdown")
        else:
            await update.edit_message_text("❌ *ليس لديك أي محاصيل في مزرعتك.*", parse_mode="Markdown")
        return
    crops_info = await get_all_crops()
    crops_dict = {c["crop_name"]: c for c in crops_info}
    now = int(time.time())
    total_profit = 0
    harvested_list = []
    for crop_name, data in user_crops.items():
        crop_info = crops_dict.get(crop_name)
        if not crop_info:
            continue
        ready_time = data["last_harvest"] + (crop_info["growth_hours"] * 3600)
        if now >= ready_time:
            profit_per_unit = crop_info["base_price"] * 1.5
            profit = int(profit_per_unit * data["quantity"])
            total_profit += profit
            harvested_list.append(f"• {crop_info['emoji']} {crop_name}: `+{profit:,.0f} ¥`")
            await update_crop_harvest(user["user_id"], crop_name, now)
    if total_profit == 0:
        msg = "⚠️ *لا توجد محاصيل جاهزة للحصاد حالياً.* انتظر حتى تنضج."
    else:
        await add_gold(user["user_id"], total_profit)
        msg = (
            f"**🌾 حصاد شامل للمزرعة!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(harvested_list) +
            f"\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *إجمالي الربح:* `+{total_profit:,.0f} ¥`\n"
            f"💵 *رصيدك الجديد:* `{user['gold'] + total_profit:,.0f} ¥`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
    if hasattr(update, 'message'):
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.edit_message_text(msg, parse_mode="Markdown")

async def harvest_crop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return
    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `حصاد محصول [الاسم]`\nمثال: `حصاد محصول قمح`", parse_mode="Markdown")
        return
    crop_name = args[0]
    user_crops = await get_user_crops(user["user_id"])
    if crop_name not in user_crops:
        await update.message.reply_text(f"❌ *ليس لديك محصول `{crop_name}` في مزرعتك.*", parse_mode="Markdown")
        return
    crop_data = user_crops[crop_name]
    crops_info = await get_all_crops()
    crop_info = next((c for c in crops_info if c["crop_name"] == crop_name), None)
    if not crop_info:
        return
    now = int(time.time())
    ready_time = crop_data["last_harvest"] + (crop_info["growth_hours"] * 3600)
    if now < ready_time:
        remaining = ready_time - now
        await update.message.reply_text(f"⏳ *المحصول `{crop_name}` لم ينضج بعد.*\n⏱️ متبقي: `{remaining // 3600}` ساعات و `{(remaining % 3600) // 60}` دقائق.", parse_mode="Markdown")
        return
    profit_per_unit = crop_info["base_price"] * 1.5
    total_profit = int(profit_per_unit * crop_data["quantity"])
    await add_gold(user["user_id"], total_profit)
    await update_crop_harvest(user["user_id"], crop_name, now)
    await update.message.reply_text(
        f"**🌾 حصاد ناجح!**\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌱 *المحصول:* `{crop_name}` {crop_info['emoji']}\n"
        f"🔢 *الكمية المحصودة:* `{crop_data['quantity']}`\n"
        f"💰 *الربح:* `+{total_profit:,.0f} ¥`\n"
        f"💵 *رصيدك الجديد:* `{user['gold'] + total_profit:,.0f} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def harvest_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        return
    await harvest_all_crops(query, user)

# ================================ رجوع ================================
async def market_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await market_handler(update, context)

# ================================ معالج الأزرار الرئيسي ================================
async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "market_back":
        await market_back(update, context)
    elif data == "my_inventory":
        await my_inventory_handler(update, context)
    elif data == "harvest_all":
        await harvest_all_callback(update, context)
    elif data.startswith("market_weapons_ground"):
        await market_weapons_ground(update, context)
    elif data.startswith("market_weapons_air"):
        await market_weapons_air(update, context)
    elif data.startswith("market_weapons_naval"):
        await market_weapons_naval(update, context)
    elif data.startswith("market_farms"):
        await market_farms(update, context)
    elif data.startswith("market_buildings"):
        await market_buildings(update, context)
    elif data.startswith("market_fortresses"):
        await market_fortresses(update, context)
    elif data.startswith("market_resources"):
        await market_resources(update, context)
    elif data.startswith("buy_weapon_"):
        weapon_name = data.replace("buy_weapon_", "")
        all_weapons = {**WEAPONS_GROUND, **WEAPONS_AIR, **WEAPONS_NAVAL, **WEAPONS_MISSILES}
        if weapon_name in all_weapons:
            await buy_item_callback(update, context, "weapon", weapon_name, all_weapons[weapon_name])
    elif data.startswith("buy_farm_"):
        farm_name = data.replace("buy_farm_", "")
        if farm_name in FARMS_LIST:
            await buy_item_callback(update, context, "farm", farm_name, FARMS_LIST[farm_name])
    elif data.startswith("buy_building_"):
        building_name = data.replace("buy_building_", "")
        if building_name in BUILDINGS_LIST:
            await buy_item_callback(update, context, "building", building_name, BUILDINGS_LIST[building_name])
    elif data.startswith("buy_fortress_"):
        fortress_name = data.replace("buy_fortress_", "")
        if fortress_name in FORTRESS_LIST:
            await buy_item_callback(update, context, "fortress", fortress_name, FORTRESS_LIST[fortress_name])
    elif data.startswith("buy_resource_"):
        resource_name = data.replace("buy_resource_", "")
        if resource_name in RESOURCES_LIST:
            await buy_item_callback(update, context, "resource", resource_name, RESOURCES_LIST[resource_name])
    elif data.startswith("confirm_"):
        await confirm_purchase(update, context)
    elif data.startswith("custom_"):
        await custom_quantity(update, context)
