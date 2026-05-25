import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (get_user, get_user_by_country, get_alliance, create_alliance,
                       join_alliance, update_user)
from config import COUNTRIES

async def diplomacy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة. ابدأ بـ /start")
        return

    alliance = await get_alliance(user["user_id"])
    if alliance:
        members = json.loads(alliance["members"])
        alliance_text = (
            f"🤝 *{alliance['name']}*\n"
            f"👑 القائد: {alliance['leader_id']}\n"
            f"👥 الأعضاء: {len(members)}"
        )
    else:
        alliance_text = "⚠️ لست في أي حلف"

    text = (
        f"🌍 *الدبلوماسية — {user['country']}*\n———————————————\n"
        f"{alliance_text}\n———————————————\n"
        f"📌 الأوامر المتاحة:\n"
        f"  🤝 انشئ حلف [اسم]\n"
        f"  🤝 انضم حلف [رمز]\n"
        f"  🕊 معاهدة سلام [دولة]\n"
        f"  📨 مساعدة [دولة] [ذهب]\n"
        f"  🔒 اتفاقية عدم اعتداء [دولة]"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 إنشاء حلف", callback_data="create_alliance"),
         InlineKeyboardButton("📋 أعضاء حلفي", callback_data="alliance_members")],
        [InlineKeyboardButton("🕊 معاهدة سلام", callback_data="peace_menu"),
         InlineKeyboardButton("📊 علاقات دبلوماسية", callback_data="diplomatic_status")],
        [InlineKeyboardButton("🏆 مجلس الحلف", callback_data="alliance_council"),
         InlineKeyboardButton("🔒 اتفاقية عدم اعتداء", callback_data="non_aggression_menu")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="diplomacy_back")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def diplomacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user:
        return

    data = query.data

    if data == "create_alliance":
        context.user_data["awaiting_alliance_name"] = True
        await query.edit_message_text(
            "🤝 *إنشاء حلف جديد*\n———————————————\nاكتب اسم الحلف:",
            parse_mode="Markdown"
        )
        return

    if data == "alliance_members":
        alliance = await get_alliance(user["user_id"])
        if not alliance:
            await query.answer("⚠️ لست في أي حلف!", show_alert=True)
            return
        members = json.loads(alliance["members"])
        text = f"🤝 *حلف {alliance['name']}*\n———————————————\n"
        text += f"👑 القائد: `{alliance['leader_id']}`\n"
        text += f"👥 الأعضاء: {len(members)}\n"
        for m in members:
            m_user = await get_user(m)
            if m_user:
                text += f"  🏳️ {m_user['country']} {m_user['flag']}\n"
        await query.edit_message_text(text, parse_mode="Markdown")
        return

    if data == "peace_menu":
        buttons = []
        for country in COUNTRIES:
            if country == user["country"]:
                continue
            buttons.append([InlineKeyboardButton(
                f"{COUNTRIES[country]['emoji']} {country}",
                callback_data=f"peace_{country}"
            )])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="diplomacy_back")])
        await query.edit_message_text(
            "🕊 *اختر دولة لعقد معاهدة سلام:*\n———————————————",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons[:20])
        )
        return

    if data.startswith("peace_"):
        target_country = data.replace("peace_", "")
        target = await get_user_by_country(target_country)
        if not target:
            await query.answer("⚠️ لا يوجد حاكم لهذه الدولة", show_alert=True)
            return
        # تخزين طلب السلام في قاعدة البيانات (لاحقاً)
        try:
            await context.bot.send_message(
                target["user_id"],
                f"🕊 *{user['country']} تعرض معاهدة سلام!*\n"
                f"اكتب: قبول سلام {user['country']} أو رفض سلام {user['country']}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(
            f"✅ تم إرسال عرض السلام إلى *{target_country}*",
            parse_mode="Markdown"
        )
        return

    if data == "alliance_council":
        alliance = await get_alliance(user["user_id"])
        if not alliance:
            await query.answer("⚠️ لست في أي حلف!", show_alert=True)
            return
        members = json.loads(alliance["members"])
        text = (
            f"🏆 *مجلس حلف {alliance['name']}*\n———————————————\n"
            f"👑 القائد يتحكم في قرارات الحلف.\n"
            f"👥 الأعضاء: {len(members)}\n"
            f"———————————————\n"
            f"⚙️ الأوامر المتاحة للقائد:\n"
            f"  /invite [دولة] - دعوة دولة\n"
            f"  /kick [عضو] - طرد عضو\n"
            f"  /declare_war [دولة] - حرب مشتركة\n"
            f"———————————————"
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        return

    if data == "diplomatic_status":
        # عرض علاقات دبلوماسية مبسطة (يمكن توسيعها لاحقاً)
        await query.edit_message_text(
            "📊 *العلاقات الدبلوماسية*\n———————————————\n"
            "🔹 معاهدات السلام: لا توجد\n"
            "🔹 اتفاقيات عدم اعتداء: لا توجد\n"
            "🔹 تحالفات: " + ("موجود" if await get_alliance(user["user_id"]) else "لا يوجد") + "\n"
            "———————————————\n"
            "💡 يمكنك إرسال طلب سلام عبر القائمة.",
            parse_mode="Markdown"
        )
        return

    if data == "non_aggression_menu":
        buttons = []
        for country in COUNTRIES:
            if country == user["country"]:
                continue
            buttons.append([InlineKeyboardButton(
                f"{COUNTRIES[country]['emoji']} {country}",
                callback_data=f"non_aggression_{country}"
            )])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="diplomacy_back")])
        await query.edit_message_text(
            "🔒 *اختر دولة لاتفاقية عدم اعتداء:*\n———————————————\n"
            "⚠️ الاتفاقية تمنع الهجوم المتبادل لمدة 7 أيام.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons[:20])
        )
        return

    if data.startswith("non_aggression_"):
        target_country = data.replace("non_aggression_", "")
        target = await get_user_by_country(target_country)
        if not target:
            await query.answer("⚠️ لا يوجد حاكم لهذه الدولة", show_alert=True)
            return
        # إرسال طلب اتفاقية عدم اعتداء
        try:
            await context.bot.send_message(
                target["user_id"],
                f"🔒 *{user['country']} تعرض اتفاقية عدم اعتداء لمدة 7 أيام!*\n"
                f"اكتب: قبول عدم اعتداء {user['country']} أو رفض عدم اعتداء {user['country']}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(
            f"✅ تم إرسال طلب اتفاقية عدم الاعتداء إلى *{target_country}*",
            parse_mode="Markdown"
        )
        return

    if data == "diplomacy_back":
        await diplomacy_handler(update, context)
        return

    # أي زر آخر
    await query.edit_message_text("⚠️ هذه الخاصية قيد التطوير قريباً.")

async def create_alliance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return

    if not context.user_data.get("awaiting_alliance_name"):
        return

    name = update.message.text.strip()
    context.user_data["awaiting_alliance_name"] = False

    existing = await get_alliance(user["user_id"])
    if existing:
        await update.message.reply_text("❌ أنت بالفعل في حلف!")
        return

    await create_alliance(name, user["user_id"])
    await update.message.reply_text(
        f"🤝 *تم إنشاء حلف '{name}'!*\n———————————————\n"
        f"👑 أنت القائد\n"
        f"📋 ادعُ دولاً أخرى للانضمام عبر /invite [دولة]\n"
        f"———————————————",
        parse_mode="Markdown"
    )

async def send_aid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("💡 استخدم: مساعدة [دولة] [مبلغ]\nمثال: مساعدة فرنسا 1000000")
        return

    target_country = args[0]
    try:
        amount = float(args[1].replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ مبلغ غير صحيح.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر.")
        return

    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text("❌ دولة غير موجودة أو ليس لها حاكم.")
        return

    if user["gold"] < amount:
        await update.message.reply_text(f"❌ رصيدك غير كافٍ: {user['gold']:,.0f} ¥")
        return

    from database import deduct_gold, add_gold
    await deduct_gold(user["user_id"], amount)
    await add_gold(target["user_id"], amount)

    await update.message.reply_text(
        f"📨 *تم إرسال المساعدة!*\n———————————————\n"
        f"🎯 إلى: {target_country}\n"
        f"💰 المبلغ: {amount:,.0f} ¥\n"
        f"💵 رصيدك الجديد: {user['gold'] - amount:,.0f} ¥\n"
        f"———————————————",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            target["user_id"],
            f"🎁 *{user['country']} أرسلت لك مساعدة!*\n💰 +{amount:,.0f} ¥",
            parse_mode="Markdown"
        )
    except Exception:
        pass
