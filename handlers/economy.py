from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (get_user, update_user, get_buildings, add_building,
                      deduct_gold, get_all_users, get_leaderboard)
from config import BUILDINGS, BASE_INCOME

# ======================== الاقتصاد ========================
async def economy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة. ابدأ بـ /start")
        return

    buildings = await get_buildings(user["user_id"])
    total_income = BASE_INCOME
    food_rate = 1000
    energy_rate = 500

    for btype, bdata in buildings.items():
        level = bdata["level"]
        binfo = BUILDINGS.get(btype, {})
        if "gold_bonus" in binfo:
            total_income += total_income * binfo["gold_bonus"] * level
        if "food" in binfo:
            food_rate += binfo["food"] * level
        if "energy" in binfo:
            energy_rate += binfo["energy"] * level
        if "production" in binfo:
            total_income += binfo["production"] * 1000 * level

    upkeep = user["soldiers"] * 0.1 + user["tanks"] * 500 + user["aircraft"] * 2000
    net_income = int(total_income - upkeep)

    blist = "\n".join(
        f"  {BUILDINGS[b]['emoji']} {b} (مستوى {d['level']})" for b, d in buildings.items()
    ) or "  ⚠️ لا توجد مبانٍ"

    # ----- إظهار العلم -----
    flag_str = user.get("flag", "🏳️")
    if len(flag_str) <= 5:
        flag_display = flag_str
    else:
        flag_display = "🖼️"

    text = (
        f"{flag_display} *الاقتصاد — {user['country']}*\n"
        f"👑 الحاكم: @{user.get('username', '—')}\n"
        f"———————————————\n"
        f"💵 الرصيد: *{user['gold']:,.0f} ¥*\n"
        f"🌾 الطعام: {user['food']:,} وحدة\n"
        f"⚡ الطاقة: {user['energy']:,} وحدة\n"
        f"———————————————\n"
        f"📈 الدخل كل 10 دقائق:\n"
        f"  💰 +{total_income:,.0f} ¥\n"
        f"  🌾 +{food_rate:,}\n"
        f"  ⚡ +{energy_rate:,}\n"
        f"📉 النفقات العسكرية: -{upkeep:,.0f} ¥\n"
        f"📊 الصافي: *{'+' if net_income >= 0 else ''}{net_income:,} ¥*\n"
        f"———————————————\n"
        f"🏗 المنشآت:\n{blist}\n"
        f"———————————————\n"
        f"💡 اكتب *ابني [مبنى]* لبناء منشأة جديدة"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏗 بناء منشأة", callback_data="build_menu"),
         InlineKeyboardButton("📊 ترقية منشأة", callback_data="upgrade_menu")],
        [InlineKeyboardButton("🌾 حصاد محصول", callback_data="harvest"),
         InlineKeyboardButton("🏦 خدمات بنكية", callback_data="bank_menu")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ======================== أزرار البناء والترقية ========================
async def build_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "harvest":
        user = await get_user(query.from_user.id)
        if not user:
            return
        bonus = int(user["food"] * 0.05)
        if bonus < 100:
            bonus = 100
        await update_user(user["user_id"], food=user["food"] + bonus)
        await query.answer(f"🌾 تم الحصاد! +{bonus:,} طعام", show_alert=True)
        await query.edit_message_text(
            f"✅ *تم حصاد المحصول*\n———————————————\n🌾 +{bonus:,} طعام\n———————————————",
            parse_mode="Markdown"
        )
        return

    elif query.data == "upgrade_menu":
        buildings = await get_buildings(query.from_user.id)
        if not buildings:
            await query.answer("⚠️ ليس لديك مباني لترقيتها!", show_alert=True)
            return
        buttons = []
        for bname, bdata in buildings.items():
            binfo = BUILDINGS.get(bname, {})
            cost = int(binfo["cost"] * (1.5 ** bdata["level"]))
            buttons.append([InlineKeyboardButton(
                f"⬆️ {bname} (مستوى {bdata['level']}) — {cost:,.0f} ¥",
                callback_data=f"upgrade_{bname}"
            )])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="economy_back")])
        await query.edit_message_text(
            "📊 *اختر مبنى لترقيته:*\n———————————————",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    elif query.data.startswith("upgrade_"):
        building = query.data.replace("upgrade_", "")
        user = await get_user(query.from_user.id)
        buildings = await get_buildings(user["user_id"])
        if building not in buildings:
            await query.answer("❌ المبنى غير موجود لديك!", show_alert=True)
            return
        binfo = BUILDINGS.get(building, {})
        current_level = buildings[building]["level"]
        cost = int(binfo["cost"] * (1.5 ** current_level))
        if not await deduct_gold(user["user_id"], cost):
            await query.answer(f"❌ تحتاج {cost:,.0f} ¥ للترقية!", show_alert=True)
            return
        await add_building(user["user_id"], building)
        await query.edit_message_text(
            f"✅ *تمت ترقية {building} إلى مستوى {current_level + 1}*\n"
            f"💰 التكلفة: -{cost:,.0f} ¥\n"
            f"———————————————",
            parse_mode="Markdown"
        )
        return

    elif query.data == "bank_menu":
        user = await get_user(query.from_user.id)
        interest = int(user["gold"] * 0.02)
        text = (
            f"🏦 *الخدمات المصرفية*\n———————————————\n"
            f"💰 رصيدك: {user['gold']:,.0f} ¥\n"
            f"📈 الفائدة اليومية: +{interest:,.0f} ¥\n"
            f"———————————————\n"
            f"🔹 استثمر لتحصل على عوائد أكبر\n"
            f"🔹 القروض قريباً"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 استثمار 10% من الذهب", callback_data="invest_10")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="economy_back")]
        ])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        return

    elif query.data.startswith("invest_"):
        percent = int(query.data.replace("invest_", ""))
        user = await get_user(query.from_user.id)
        amount = int(user["gold"] * percent / 100)
        if amount < 1000:
            await query.answer("⚠️ المبلغ صغير جداً للاستثمار", show_alert=True)
            return
        import random
        if random.random() < 0.8:
            profit = int(amount * random.uniform(0.05, 0.2))
            await update_user(user["user_id"], gold=user["gold"] + profit)
            await query.edit_message_text(
                f"📈 *استثمار ناجح!*\n———————————————\n"
                f"💰 استثمرت: {amount:,.0f} ¥\n"
                f"✅ الربح: +{profit:,.0f} ¥\n"
                f"💵 الرصيد الجديد: {user['gold'] + profit:,.0f} ¥",
                parse_mode="Markdown"
            )
        else:
            loss = int(amount * random.uniform(0.1, 0.5))
            await update_user(user["user_id"], gold=user["gold"] - loss)
            await query.edit_message_text(
                f"📉 *استثمار خاسر!*\n———————————————\n"
                f"💰 استثمرت: {amount:,.0f} ¥\n"
                f"❌ الخسارة: -{loss:,.0f} ¥\n"
                f"💵 الرصيد الجديد: {user['gold'] - loss:,.0f} ¥",
                parse_mode="Markdown"
            )
        return

    # build_menu (قائمة المباني المتاحة للبناء)
    buttons = []
    for bname, binfo in BUILDINGS.items():
        cost = binfo["cost"]
        buttons.append([InlineKeyboardButton(
            f"{binfo['emoji']} {bname} — {cost:,.0f} ¥",
            callback_data=f"build_{bname}"
        )])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="economy_back")])
    await query.edit_message_text(
        "🏗 *اختر منشأة للبناء:*\n———————————————",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def build_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    building = query.data.replace("build_", "")

    if building not in BUILDINGS:
        return

    user = await get_user(query.from_user.id)
    if not user:
        return

    binfo = BUILDINGS[building]
    cost = binfo["cost"]
    buildings = await get_buildings(user["user_id"])
    if building in buildings:
        level = buildings[building]["level"]
        cost = int(cost * (1.5 ** level))

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ نعم، قم بالبناء", callback_data=f"confirm_build_{building}"),
         InlineKeyboardButton("❌ إلغاء", callback_data="build_menu")]
    ])
    await query.edit_message_text(
        f"⚠️ *تأكيد بناء {building}*\n———————————————\n"
        f"💰 التكلفة: {cost:,.0f} ¥\n"
        f"💵 رصيدك: {user['gold']:,.0f} ¥\n"
        f"———————————————\n"
        f"هل تريد المتابعة؟",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def confirm_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    building = query.data.replace("confirm_build_", "")
    user = await get_user(query.from_user.id)
    binfo = BUILDINGS[building]
    buildings = await get_buildings(user["user_id"])
    cost = binfo["cost"]
    if building in buildings:
        level = buildings[building]["level"]
        cost = int(cost * (1.5 ** level))
    if not await deduct_gold(user["user_id"], cost):
        await query.edit_message_text("❌ ذهب غير كافٍ!", parse_mode="Markdown")
        return
    await add_building(user["user_id"], building)
    new_level = buildings.get(building, {}).get("level", 0) + 1
    await query.edit_message_text(
        f"🏗 *تم بناء {building}!*\n———————————————\n"
        f"{binfo['emoji']} المستوى: {new_level}\n"
        f"💰 التكلفة: -{cost:,.0f} ¥\n"
        f"💵 رصيدك: {user['gold'] - cost:,.0f} ¥",
        parse_mode="Markdown"
    )

async def build_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 استخدم: ابني [اسم المبنى]\nمثال: ابني مصنع")
        return

    building = " ".join(args)
    if building not in BUILDINGS:
        blist = "\n".join(f"  {v['emoji']} {k}" for k, v in BUILDINGS.items())
        await update.message.reply_text(
            f"❌ المبنى غير موجود.\n\n🏗 المباني المتاحة:\n{blist}"
        )
        return

    binfo = BUILDINGS[building]
    buildings = await get_buildings(user["user_id"])
    cost = binfo["cost"]
    if building in buildings:
        cost = int(cost * (1.5 ** buildings[building]["level"]))

    if not await deduct_gold(user["user_id"], cost):
        await update.message.reply_text(
            f"❌ *ذهب غير كافٍ!*\nالتكلفة: {cost:,.0f} ¥\nرصيدك: {user['gold']:,.0f} ¥",
            parse_mode="Markdown"
        )
        return

    await add_building(user["user_id"], building)
    new_level = buildings.get(building, {}).get("level", 0) + 1
    await update.message.reply_text(
        f"🏗 *تم بناء {building}!*\n———————————————\n"
        f"{binfo['emoji']} المستوى: {new_level}\n"
        f"💰 التكلفة: -{cost:,.0f} ¥\n"
        f"💵 رصيدك: {user['gold'] - cost:,.0f} ¥",
        parse_mode="Markdown"
    )

# ======================== لوحة المتصدرين (محسّنة) ========================
async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # جلب المتصدرين وجميع المستخدمين لتحديد الدول المحجوزة
    leaders = await get_leaderboard()
    if not leaders:
        await update.message.reply_text("⚠️ لا يوجد لاعبون بعد.")
        return

    all_users = await get_all_users()
    occupied = {u["country"] for u in all_users}

    text = "🏆 *لوحة المتصدرين — عصر الأمم*\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."

        # ---- معالجة العلم ----
        flag_str = u.get("flag", "🏳️")
        if len(flag_str) <= 5:          # إيموجي
            flag_display = flag_str
        else:                           # صورة (file_id)
            flag_display = "🖼️"

        # ---- هل الدولة محجوزة؟ ----
        country = u["country"]
        lock_icon = "🔒" if country in occupied else "🌫️"

        text += (
            f"{medal} {flag_display} {lock_icon} *{country}*\n"
            f"   👑 @{u.get('username', '—')}\n"
            f"   💰 {u['gold']:,.0f} ¥  |  ⚔️ {u['soldiers']:,}\n"
            f"   🌟 المستوى {u['level']}  |  🏆 {u['prestige']:,} هيبة\n"
        )
        if i < len(leaders) - 1:
            text += "   — — — — — — — —\n"

    text += "━━━━━━━━━━━━━━━━━━━━━"
    await update.message.reply_text(text, parse_mode="Markdown")
