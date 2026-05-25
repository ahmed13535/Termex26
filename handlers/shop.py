"""
handlers/shop.py – السوق الإمبراطوري الموحّد
يجمع الأسلحة البرية والجوية والبحرية والصواريخ وأسلحة الدمار الشامل
والمباني والتحصينات في واجهة واحدة احترافية.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import get_user, update_user, deduct_gold, add_building, get_buildings
from constants import (
    LAND_WEAPONS, AIR_WEAPONS, NAVAL_WEAPONS, MISSILE_WEAPONS, WMD_WEAPONS,
    BUILDINGS
)

# ═══════════════════════════════════════════════════════
#  كتالوج التحصينات (مستقلة عن constants)
# ═══════════════════════════════════════════════════════
FORTRESSES = {
    "برج_دفاع":     {"cost": 3_000_000,  "defense": 0.10, "emoji": "🗼", "desc": "يرفع الدفاع +10%"},
    "جدار_حماية":   {"cost": 5_000_000,  "defense": 0.15, "emoji": "🧱", "desc": "يرفع الدفاع +15%"},
    "قاعدة_عسكرية": {"cost": 10_000_000, "defense": 0.25, "emoji": "🏰", "desc": "يرفع الدفاع +25%"},
}

# ═══════════════════════════════════════════════════════
#  تعريف الفئات وترتيبها
# ═══════════════════════════════════════════════════════
CATEGORIES = [
    ("land",      "🪖",  "الأسلحة البرية",              LAND_WEAPONS),
    ("air",       "✈️",  "الأسلحة الجوية",              AIR_WEAPONS),
    ("naval",     "⚓",  "الأسلحة البحرية",             NAVAL_WEAPONS),
    ("missile",   "🚀",  "الصواريخ الاستراتيجية",       MISSILE_WEAPONS),
    ("wmd",       "☢️",  "أسلحة الدمار الشامل",         WMD_WEAPONS),
    ("buildings", "🏗️",  "المباني والمنشآت",            BUILDINGS),
    ("fortress",  "🏰",  "التحصينات الدفاعية",          FORTRESSES),
]

CAT_MAP = {key: (emoji, name, data) for key, emoji, name, data in CATEGORIES}

# ═══════════════════════════════════════════════════════
#  مساعدات التصيير
# ═══════════════════════════════════════════════════════
def _header(user: dict) -> str:
    return (
        "╔══════════════════════════════╗\n"
        "║   🏛️  السوق الإمبراطوري العالمي   ║\n"
        "╚══════════════════════════════╝\n"
        f"💰 *الخزينة:* `{user['gold']:,.0f} ¥`\n"
        f"⚔️ *الجيش:* `{user['soldiers']:,}` جندي\n"
        f"💥 *هجوم:* ×`{user['damage_bonus']:.2f}` "
        f"│ 🛡️ *دفاع:* ×`{user['defense_bonus']:.2f}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

def _main_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(CATEGORIES) - 1, 2):
        row = []
        for key, emoji, name, _ in CATEGORIES[i:i+2]:
            row.append(InlineKeyboardButton(f"{emoji} {name}", callback_data=f"s_cat_{key}"))
        rows.append(row)
    # آخر فئة إذا كانت عدداً فردياً
    if len(CATEGORIES) % 2 != 0:
        last = CATEGORIES[-1]
        rows.append([InlineKeyboardButton(f"{last[1]} {last[2]}", callback_data=f"s_cat_{last[0]}")])
    rows.append([InlineKeyboardButton("📦 ترسانتي وأسلحتي", callback_data="s_arsenal")])
    return InlineKeyboardMarkup(rows)

def _cat_keyboard(cat_key: str, items: dict) -> InlineKeyboardMarkup:
    rows = []
    for name, info in items.items():
        emoji = info.get("emoji", "🔹")
        cost  = info.get("cost", 0)
        rows.append([InlineKeyboardButton(
            f"{emoji} {name.replace('_', ' ')} — {cost:,.0f} ¥",
            callback_data=f"s_item_{cat_key}_{name}"
        )])
    rows.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="s_main")])
    return InlineKeyboardMarkup(rows)

def _qty_keyboard(cat_key: str, item: str) -> InlineKeyboardMarkup:
    qtys = [1, 5, 10, 25, 50, 100]
    rows = [
        [InlineKeyboardButton(str(q), callback_data=f"s_qty_{cat_key}_{item}_{q}") for q in qtys[:3]],
        [InlineKeyboardButton(str(q), callback_data=f"s_qty_{cat_key}_{item}_{q}") for q in qtys[3:]],
        [InlineKeyboardButton("✏️ كمية مخصصة", callback_data=f"s_custom_{cat_key}_{item}"),
         InlineKeyboardButton("🔙 رجوع", callback_data=f"s_cat_{cat_key}")],
    ]
    return InlineKeyboardMarkup(rows)

def _item_stats(info: dict) -> str:
    lines = []
    if info.get("soldiers"):
        lines.append(f"👥 جنود: +{info['soldiers']}")
    if info.get("damage"):
        lines.append(f"💥 ضرر: +{info['damage']:.2f}%")
    if info.get("defense"):
        lines.append(f"🛡️ دفاع: +{info['defense']:.2f}%")
    if info.get("food"):
        lines.append(f"🌾 غذاء: +{info['food']}")
    if info.get("energy"):
        lines.append(f"⚡ طاقة: +{info['energy']}")
    if info.get("gold_bonus"):
        lines.append(f"💰 دخل: +{info['gold_bonus']*100:.0f}%")
    if info.get("production"):
        lines.append(f"🏭 إنتاج: +{info['production']}")
    if info.get("desc"):
        lines.append(f"📌 {info['desc']}")
    if info.get("requires"):
        req = ", ".join(f"{v}× {k}" for k, v in info["requires"].items())
        lines.append(f"🔒 يتطلب: {req}")
    return "\n".join(f"   {l}" for l in lines) if lines else "   —"

# ═══════════════════════════════════════════════════════
#  الواجهات الرئيسية
# ═══════════════════════════════════════════════════════
async def shop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يُطلق بأمر: متجر / 🏪 متجر / /shop"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    text = (
        f"{_header(user)}\n"
        "🛒 *اختر الفئة التي تريد التسوق منها:*"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_main_keyboard())

# ═══════════════════════════════════════════════════════
#  معالج الـ callbacks الرئيسي
# ═══════════════════════════════════════════════════════
async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    uid   = query.from_user.id
    user  = await get_user(uid)
    if not user:
        return

    # ── العودة للقائمة الرئيسية ──────────────────────
    if data == "s_main":
        text = (
            f"{_header(user)}\n"
            "🛒 *اختر الفئة التي تريد التسوق منها:*"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=_main_keyboard())
        return

    # ── عرض الفئة ────────────────────────────────────
    if data.startswith("s_cat_"):
        cat_key = data[6:]
        if cat_key not in CAT_MAP:
            return
        emoji, name, items = CAT_MAP[cat_key]
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  {emoji}  {name}  ║\n"
            f"╚══════════════════════════════╝\n"
            f"💰 *خزينتك:* `{user['gold']:,.0f} ¥`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        for item_name, info in items.items():
            em = info.get("emoji", "🔹")
            cost = info.get("cost", 0)
            text += f"{em} *{item_name.replace('_', ' ')}* — `{cost:,.0f} ¥`\n"
            text += _item_stats(info) + "\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 *اضغط على السلاح لاختيار الكمية*"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=_cat_keyboard(cat_key, items))
        return

    # ── عرض تفاصيل السلعة واختيار الكمية ────────────
    if data.startswith("s_item_"):
        parts = data[7:].split("_", 1)
        if len(parts) < 2:
            return
        cat_key, item_name = parts[0], parts[1]
        if cat_key not in CAT_MAP:
            return
        _, cat_label, items = CAT_MAP[cat_key]
        info = items.get(item_name)
        if not info:
            return
        em = info.get("emoji", "🔹")
        cost = info.get("cost", 0)
        text = (
            f"╔══════════════════════════════╗\n"
            f"║  {em}  {item_name.replace('_', ' ')}  ║\n"
            f"╚══════════════════════════════╝\n"
            f"💰 *السعر:* `{cost:,.0f} ¥` / الوحدة\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_item_stats(info)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *خزينتك:* `{user['gold']:,.0f} ¥`\n"
            f"📦 *كم وحدة تريد شراءها؟*"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=_qty_keyboard(cat_key, item_name))
        return

    # ── شراء بكمية محددة ─────────────────────────────
    if data.startswith("s_qty_"):
        parts = data[6:].rsplit("_", 1)
        if len(parts) < 2:
            return
        prefix, qty_str = parts
        try:
            qty = int(qty_str)
        except ValueError:
            return
        sub = prefix.split("_", 1)
        if len(sub) < 2:
            return
        cat_key, item_name = sub[0], sub[1]
        await _execute_purchase(query, context, user, cat_key, item_name, qty)
        return

    # ── طلب كمية مخصصة ───────────────────────────────
    if data.startswith("s_custom_"):
        rest = data[9:].split("_", 1)
        if len(rest) < 2:
            return
        cat_key, item_name = rest[0], rest[1]
        context.user_data["s_pending"] = (cat_key, item_name)
        await query.edit_message_text(
            f"✏️ *أدخل الكمية المطلوبة لـ* `{item_name.replace('_', ' ')}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 أرسل رقماً صحيحاً (مثال: `15`)",
            parse_mode="Markdown"
        )
        context.user_data["s_awaiting_qty"] = True
        return

    # ── ترسانتي ───────────────────────────────────────
    if data == "s_arsenal":
        text = (
            "╔══════════════════════════════╗\n"
            "║      📦  ترسانتي وأسلحتي      ║\n"
            "╚══════════════════════════════╝\n"
            f"🌍 *دولة:* {user['country']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪖 *القوات البرية*\n"
            f"   👥 جنود: `{user['soldiers']:,}`\n"
            f"   🚛 دبابات: `{user.get('tanks', 0):,}`\n"
            f"   💥 مدفعية: `{user.get('artillery', 0):,}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✈️ *القوات الجوية*\n"
            f"   ✈️ طائرات: `{user.get('aircraft', 0):,}`\n"
            f"   🛸 مسيّرات: `{user.get('drones', 0):,}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚓ *القوات البحرية*\n"
            f"   🚢 حاملات: `{user.get('carriers', 0):,}`\n"
            f"   🌊 غواصات: `{user.get('submarines', 0):,}`\n"
            f"   ⛵ مدمرات: `{user.get('destroyers', 0):,}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 *الصواريخ*\n"
            f"   🚀 صواريخ: `{user.get('missiles', 0):,}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"☢️ *أسلحة الدمار الشامل*\n"
            f"   ☢️ رؤوس نووية: `{user.get('nukes', 0):,}`\n"
            f"   ☣️ بيولوجي: `{user.get('bio_weapons', 0):,}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *مؤشرات القوة*\n"
            f"   💥 مضاعف الهجوم: ×`{user['damage_bonus']:.3f}`\n"
            f"   🛡️ مضاعف الدفاع: ×`{user['defense_bonus']:.3f}`\n"
            f"   ⚡ روح المعنوية: `{user.get('morale', 100)}%`"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 رجوع للسوق", callback_data="s_main")
        ]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        return

# ═══════════════════════════════════════════════════════
#  معالج الكمية المخصصة (من الرسائل النصية)
# ═══════════════════════════════════════════════════════
async def handle_custom_qty_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """تُعيد True إذا عالجت رسالة الكمية المخصصة."""
    if not context.user_data.get("s_awaiting_qty"):
        return False
    pending = context.user_data.get("s_pending")
    if not pending:
        return False

    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ *أدخل رقماً صحيحاً أكبر من صفر.*", parse_mode="Markdown")
        return True

    cat_key, item_name = pending
    user = await get_user(update.effective_user.id)
    if not user:
        return True

    if cat_key not in CAT_MAP:
        return True
    _, _, items = CAT_MAP[cat_key]
    info = items.get(item_name)
    if not info:
        return True

    cost = info.get("cost", 0)
    total = cost * qty
    if user["gold"] < total:
        await update.message.reply_text(
            f"❌ *ذهب غير كافٍ!*\n"
            f"💰 *تحتاج:* `{total:,.0f} ¥`\n"
            f"💵 *رصيدك:* `{user['gold']:,.0f} ¥`",
            parse_mode="Markdown"
        )
        context.user_data.pop("s_awaiting_qty", None)
        context.user_data.pop("s_pending", None)
        return True

    success, msg = await _apply_purchase(user, cat_key, item_name, info, qty)
    if success:
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {msg}", parse_mode="Markdown")

    context.user_data.pop("s_awaiting_qty", None)
    context.user_data.pop("s_pending", None)
    return True

# ═══════════════════════════════════════════════════════
#  منطق الشراء المشترك
# ═══════════════════════════════════════════════════════
async def _execute_purchase(query, context, user: dict, cat_key: str, item_name: str, qty: int):
    if cat_key not in CAT_MAP:
        return
    _, _, items = CAT_MAP[cat_key]
    info = items.get(item_name)
    if not info:
        return

    cost  = info.get("cost", 0)
    total = cost * qty

    if user["gold"] < total:
        await query.answer(f"❌ ذهب غير كافٍ! تحتاج {total:,.0f} ¥", show_alert=True)
        return

    success, msg = await _apply_purchase(user, cat_key, item_name, info, qty)
    if not success:
        await query.edit_message_text(f"❌ {msg}", parse_mode="Markdown")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 مواصلة التسوق", callback_data=f"s_cat_{cat_key}"),
         InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="s_main")]
    ])
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)

async def _apply_purchase(user: dict, cat_key: str, item_name: str, info: dict, qty: int):
    """تنفّذ الشراء وتعيد (نجاح, نص_الرد)."""
    cost  = info.get("cost", 0)
    total = cost * qty
    uid   = user["user_id"]

    # خصم الذهب
    if not await deduct_gold(uid, total):
        return False, "فشل خصم الذهب."

    em = info.get("emoji", "🔹")
    new_gold = user["gold"] - total

    # ─ أسلحة عسكرية ─────────────────────────────────
    if cat_key in ("land", "air", "naval", "missile", "wmd"):
        soldiers_gain = info.get("soldiers", 0) * qty
        damage_gain   = round(info.get("damage",  0) * qty * 0.001, 6)
        defense_gain  = round(info.get("defense", 0) * qty * 0.001, 6)

        new_soldiers = user["soldiers"] + soldiers_gain
        new_damage   = round(user["damage_bonus"]  + damage_gain,  4)
        new_defense  = round(user["defense_bonus"] + defense_gain, 4)

        await update_user(uid,
            soldiers=new_soldiers,
            damage_bonus=new_damage,
            defense_bonus=new_defense
        )
        msg = (
            f"╔══════════════════════════════╗\n"
            f"║  ✅  تمّ الشراء بنجاح  ║\n"
            f"╚══════════════════════════════╝\n"
            f"{em} *{qty:,} × {item_name.replace('_', ' ')}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *التكلفة:* `-{total:,.0f} ¥`\n"
            f"💵 *الخزينة:* `{new_gold:,.0f} ¥`\n"
        )
        if soldiers_gain:
            msg += f"👥 *الجيش:* `{new_soldiers:,}` (+{soldiers_gain:,})\n"
        if damage_gain > 0:
            msg += f"💥 *مضاعف الهجوم:* ×`{new_damage:.3f}`\n"
        if defense_gain > 0:
            msg += f"🛡️ *مضاعف الدفاع:* ×`{new_defense:.3f}`\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return True, msg

    # ─ مباني ─────────────────────────────────────────
    if cat_key == "buildings":
        await add_building(uid, item_name)
        food_gain   = info.get("food", 0)
        energy_gain = info.get("energy", 0)
        prod_gain   = info.get("production", 0)
        gold_bonus  = info.get("gold_bonus", 0)
        extra = ""
        if food_gain:   extra += f"🌾 *طعام:* +{food_gain}\n"
        if energy_gain: extra += f"⚡ *طاقة:* +{energy_gain}\n"
        if prod_gain:   extra += f"🏭 *إنتاج:* +{prod_gain}\n"
        if gold_bonus:  extra += f"💰 *دخل:* +{gold_bonus*100:.0f}%\n"
        msg = (
            f"╔══════════════════════════════╗\n"
            f"║  ✅  تمّ البناء بنجاح  ║\n"
            f"╚══════════════════════════════╝\n"
            f"{em} *{qty:,} × {item_name.replace('_', ' ')}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *التكلفة:* `-{total:,.0f} ¥`\n"
            f"💵 *الخزينة:* `{new_gold:,.0f} ¥`\n"
            f"{extra}"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return True, msg

    # ─ تحصينات ───────────────────────────────────────
    if cat_key == "fortress":
        def_gain    = round(info.get("defense", 0) * qty, 4)
        new_defense = round(user["defense_bonus"] + def_gain, 4)
        await update_user(uid, defense_bonus=new_defense)
        msg = (
            f"╔══════════════════════════════╗\n"
            f"║  ✅  تمّ التحصين بنجاح  ║\n"
            f"╚══════════════════════════════╝\n"
            f"{em} *{qty:,} × {item_name.replace('_', ' ')}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *التكلفة:* `-{total:,.0f} ¥`\n"
            f"💵 *الخزينة:* `{new_gold:,.0f} ¥`\n"
            f"🛡️ *دفاع مُضاف:* +{def_gain*100:.1f}%\n"
            f"🛡️ *مضاعف الدفاع:* ×`{new_defense:.3f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return True, msg

    return False, "نوع عنصر غير معروف."

# للتوافق مع الاستيرادات القديمة في main.py
async def finalize_purchase(update, context, item, qty):
    pass
