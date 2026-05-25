import random
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (get_user, get_user_by_country, update_user, get_cooldown,
                       set_cooldown, create_war, get_active_war, end_war,
                       get_wars_for_user, update_occupation, deduct_gold)
from map_renderer import render_war_map
from config import COUNTRIES, ATTACK_COOLDOWN, WAR_COOLDOWN

async def military_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة. ابدأ بـ /start")
        return

    wars = await get_wars_for_user(user["user_id"])
    war_list = "\n".join(
        f"  ⚔️ {w['attacker_country']} ضد {w['defender_country']}" for w in wars
    ) or "  ✅ لا توجد حروب نشطة"

    text = (
        f"⚔️ *القيادة العسكرية — {user['country']}*\n"
        f"———————————————\n"
        f"👤 الجنود: *{user['soldiers']:,}*\n"
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
        f"💪 المعنويات: {user['morale']}%\n"
        f"🔰 مضاعف الهجوم: x{user['damage_bonus']:.2f}\n"
        f"🛡 مضاعف الدفاع: x{user['defense_bonus']:.2f}\n"
        f"———————————————\n"
        f"🔥 الحروب النشطة:\n{war_list}\n"
        f"———————————————\n"
        f"💡 الأوامر:\n  هجوم [دولة]\n  تجنيد [عدد]\n  احتل [دولة]\n  هدنة [دولة]"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ إعلان حرب", callback_data="war_menu"),
         InlineKeyboardButton("🛡 وضع دفاعي", callback_data="defensive_mode")],
        [InlineKeyboardButton("🏳️ طلب هدنة", callback_data="truce_menu"),
         InlineKeyboardButton("📋 سجل الحروب", callback_data="war_history")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def recruit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة.")
        return

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "💡 استخدم: تجنيد [عدد]\nمثال: تجنيد 5000\nالتكلفة: 1,000 ¥ لكل جندي"
        )
        return

    amount = int(args[0])
    if amount <= 0 or amount > 100000:
        await update.message.reply_text("❌ العدد يجب أن يكون بين 1 و 100,000")
        return

    cost = amount * 1000
    if user["gold"] < cost:
        await update.message.reply_text(
            f"❌ *ذهب غير كافٍ!*\nالتكلفة: {cost:,.0f} ¥\nرصيدك: {user['gold']:,.0f} ¥",
            parse_mode="Markdown"
        )
        return

    await deduct_gold(user["user_id"], cost)
    new_soldiers = user["soldiers"] + amount
    await update_user(user["user_id"], soldiers=new_soldiers)

    await update.message.reply_text(
        f"👤 *تم التجنيد!*\n———————————————\n"
        f"➕ مجنّدون جدد: {amount:,}\n"
        f"👥 إجمالي الجيش: {new_soldiers:,}\n"
        f"💰 التكلفة: -{cost:,.0f} ¥\n"
        f"———————————————",
        parse_mode="Markdown"
    )

async def attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 استخدم: هجوم [دولة]\nمثال: هجوم فرنسا")
        return

    target_country = " ".join(args)
    if target_country not in COUNTRIES:
        close = [c for c in COUNTRIES if target_country in c]
        if close:
            await update.message.reply_text(f"❓ هل تقصد: {', '.join(close[:3])}؟")
        else:
            await update.message.reply_text("❌ دولة غير موجودة.")
        return

    if target_country == user["country"]:
        await update.message.reply_text("❌ لا يمكنك مهاجمة دولتك!")
        return

    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text(f"⚠️ دولة *{target_country}* ليس لها حاكم.", parse_mode="Markdown")
        return

    cd = await get_cooldown(user["user_id"], "attack")
    if cd > 0:
        await update.message.reply_text(f"⏳ يجب الانتظار {cd // 60} دقيقة قبل الهجوم التالي.")
        return

    # تأكيد الحرب
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ نعم، أعلن الحرب", callback_data=f"confirm_attack_{target_country}"),
         InlineKeyboardButton("❌ إلغاء", callback_data="military_back")]
    ])
    await update.message.reply_text(
        f"⚠️ *تأكيد الهجوم على {target_country}*\n———————————————\n"
        f"🔴 المهاجم: {user['country']} (جيشك: {user['soldiers']:,})\n"
        f"🔵 المدافع: {target_country} (جيشه: {target['soldiers']:,})\n"
        f"———————————————\n"
        f"هل تريد شن الهجوم؟",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def confirm_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target_country = query.data.replace("confirm_attack_", "")
    user = await get_user(query.from_user.id)
    target = await get_user_by_country(target_country)
    if not user or not target:
        await query.edit_message_text("❌ خطأ في البيانات")
        return

    # التحقق من الكول داون مرة أخرى
    cd = await get_cooldown(user["user_id"], "attack")
    if cd > 0:
        await query.edit_message_text(f"⏳ يجب الانتظار {cd // 60} دقيقة")
        return

    war = await get_active_war(user["user_id"], target["user_id"])
    if not war:
        await create_war(user["user_id"], target["user_id"], user["country"], target_country)

    result = calculate_battle(user, target)
    await set_cooldown(user["user_id"], "attack", ATTACK_COOLDOWN)

    atk_loss = result["attacker_losses"]
    def_loss = result["defender_losses"]
    attacker_wins = result["attacker_wins"]

    new_atk_soldiers = max(0, user["soldiers"] - atk_loss)
    new_def_soldiers = max(0, target["soldiers"] - def_loss)
    await update_user(user["user_id"], soldiers=new_atk_soldiers, xp=user["xp"] + 50)
    await update_user(target["user_id"], soldiers=new_def_soldiers)

    occ_progress = result["occupation"]
    if attacker_wins and occ_progress > 0:
        atk_info = COUNTRIES[user["country"]]
        color = atk_info["color"]
        await update_occupation(target_country, user["country"], occ_progress, color)

    war_map = await render_war_map(user["country"], target_country)
    outcome = "✅ *انتصار ساحق!*" if attacker_wins else "❌ *هزيمة نكراء!*"
    occ_text = f"\n🏴 تقدم الاحتلال: {occ_progress:.1f}%" if occ_progress > 0 else ""

    caption = (
        f"⚔️ {outcome}\n"
        f"———————————————\n"
        f"🔴 {user['country']} ← المهاجم\n"
        f"🔵 {target_country} ← المدافع\n"
        f"———————————————\n"
        f"💥 خسائرك: {atk_loss:,} جندي\n"
        f"💀 خسائر العدو: {def_loss:,} جندي\n"
        f"———————————————\n"
        f"👥 جيشك المتبقي: {new_atk_soldiers:,}\n"
        f"👥 جيش العدو: {new_def_soldiers:,}\n"
        f"{occ_text}\n"
        f"———————————————\n"
        f"⏳ الهجوم القادم بعد 5 دقائق"
    )

    try:
        await context.bot.send_message(
            target["user_id"],
            f"🚨 *{user['country']} يهاجمك!*\n———————————————\n"
            f"💀 خسرت: {def_loss:,} جندي\n"
            f"👥 جيشك: {new_def_soldiers:,}\n"
            f"{'🏴 أراضيك تُحتل!' if occ_progress > 0 else '✅ صددت الهجوم!'}",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await query.edit_message_caption(caption=caption, parse_mode="Markdown")
    await query.message.reply_photo(photo=war_map, caption=caption, parse_mode="Markdown")

def calculate_battle(attacker: dict, defender: dict) -> dict:
    atk_power = (
        attacker["soldiers"] * 1 +
        attacker["tanks"] * 25 +
        attacker["artillery"] * 50 +
        attacker["aircraft"] * 120 +
        attacker["missiles"] * 200 +
        attacker["bio_weapons"] * 800 +
        attacker["nukes"] * 5000
    ) * attacker["damage_bonus"] * (attacker["morale"] / 100)

    def_power = (
        defender["soldiers"] * 1.2 +
        defender["tanks"] * 30 +
        defender["artillery"] * 55 +
        defender["aircraft"] * 130 +
        defender["air_defense"] * 80 +
        defender["bio_weapons"] * 800 +
        defender["nukes"] * 5000
    ) * defender["defense_bonus"] * (defender["morale"] / 100)

    atk_power *= random.uniform(0.85, 1.15)
    def_power *= random.uniform(0.85, 1.15)

    attacker_wins = atk_power > def_power
    ratio = atk_power / max(def_power, 1)

    if attacker_wins:
        atk_loss_pct = random.uniform(0.05, 0.15)
        def_loss_pct = random.uniform(0.15, 0.35)
        occ = min(25.0, ratio * 5)
    else:
        atk_loss_pct = random.uniform(0.15, 0.35)
        def_loss_pct = random.uniform(0.05, 0.15)
        occ = 0.0

    return {
        "attacker_wins": attacker_wins,
        "attacker_losses": int(attacker["soldiers"] * atk_loss_pct),
        "defender_losses": int(defender["soldiers"] * def_loss_pct),
        "occupation": occ,
    }

async def declare_war_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "war_menu":
        buttons = []
        for country in COUNTRIES:
            buttons.append([InlineKeyboardButton(
                f"{COUNTRIES[country]['emoji']} {country}",
                callback_data=f"declare_war_{country}"
            )])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="military_back")])
        await query.edit_message_text(
            "⚔️ *اختر الدولة لإعلان الحرب عليها:*\n———————————————",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons[:20])
        )

async def war_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wars = await get_wars_for_user(query.from_user.id)
    if not wars:
        await query.edit_message_text("✅ لا توجد حروب نشطة حالياً.", parse_mode="Markdown")
        return
    text = "📋 *الحروب النشطة:*\n———————————————\n"
    for w in wars:
        text += f"⚔️ {w['attacker_country']} ضد {w['defender_country']}\n"
    await query.edit_message_text(text, parse_mode="Markdown")

async def truce_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    args = context.args
    if not args:
        await update.message.reply_text("💡 استخدم: هدنة [دولة]")
        return
    target_country = " ".join(args)
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text("❌ دولة غير موجودة أو ليس لها حاكم.")
        return
    war = await get_active_war(user["user_id"], target["user_id"])
    if not war:
        await update.message.reply_text("❌ لا توجد حرب نشطة بينكما.")
        return
    await end_war(war["id"], 0)
    try:
        await context.bot.send_message(
            target["user_id"],
            f"🕊 *{user['country']} تطلب هدنة!*\nتم قبول الهدنة تلقائياً.",
            parse_mode="Markdown"
        )
    except Exception:
        pass
    await update.message.reply_text(
        f"🕊 *تم إعلان الهدنة مع {target_country}*\n———————————————",
        parse_mode="Markdown"
    )

async def occupy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    args = context.args
    if not args:
        await update.message.reply_text("💡 استخدم: احتل [دولة]")
        return
    target_country = " ".join(args)
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text("❌ دولة غير موجودة.")
        return
    war = await get_active_war(user["user_id"], target["user_id"])
    if not war:
        await update.message.reply_text("❌ يجب إعلان الحرب أولاً.")
        return
    if user["soldiers"] < target["soldiers"] * 0.5:
        await update.message.reply_text("❌ جيشك أضعف من احتلال هذه الدولة!")
        return
    atk_info = COUNTRIES.get(user["country"], {})
    color = atk_info.get("color", (180, 180, 180))
    await update_occupation(target_country, user["country"], 100.0, color)
    gold_loot = int(target["gold"] * 0.1)
    await deduct_gold(target["user_id"], gold_loot)
    await update_user(user["user_id"], gold=user["gold"] + gold_loot, prestige=user["prestige"] + 500, xp=user["xp"] + 200)
    await update.message.reply_text(
        f"🏴 *تم احتلال {target_country}!*\n———————————————\n"
        f"💰 غنائم: +{gold_loot:,.0f} ¥\n"
        f"🏆 هيبة: +500\n———————————————",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            target["user_id"],
            f"🚨 *{user['country']} احتلت أراضيك!*\n💰 خسرت: {gold_loot:,.0f} ¥",
            parse_mode="Markdown"
        )
    except Exception:
        pass
