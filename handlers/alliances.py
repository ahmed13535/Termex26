import json
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (
    get_user, get_alliance_by_name, get_alliance_by_member,
    create_alliance, add_member_to_alliance, remove_member_from_alliance,
    delete_alliance, get_user_by_country, get_all_users, add_gold, update_user
)
from config import ADMIN_IDS

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ================================ إنشاء حلف ================================
async def create_alliance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انشاء حلف [اسم]"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "> 💡 *الاستخدام:*\n"
            "`انشاء حلف [اسم الحلف]`\n"
            "📌 *مثال:* `انشاء حلف المحور`",
            parse_mode="Markdown"
        )
        return

    alliance_name = " ".join(args)
    existing = await get_alliance_by_name(alliance_name)
    if existing:
        await update.message.reply_text(f"❌ *حلف `{alliance_name}` موجود بالفعل.*", parse_mode="Markdown")
        return

    my_alliance = await get_alliance_by_member(user["user_id"])
    if my_alliance:
        await update.message.reply_text(f"⚠️ *أنت بالفعل في حلف:* `{my_alliance['name']}`\nمغادرة الحلف أولاً باستخدام `مغادره حلف {my_alliance['name']}`", parse_mode="Markdown")
        return

    await create_alliance(alliance_name, user["user_id"])
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *تم إنشاء حلف `{alliance_name}` بنجاح!*\n"
        f"👑 *أنت القائد.*\n"
        f"📌 *للدعوة:* `دعوه {alliance_name} [دولة]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

# ================================ دعوة عضو ================================
async def invite_alliance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دعوه [حلف] [دولة]"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "> 💡 *الاستخدام:*\n"
            "`دعوه [اسم الحلف] [الدولة المستهدفة]`\n"
            "📌 *مثال:* `دعوه المحور فرنسا`",
            parse_mode="Markdown"
        )
        return

    alliance_name = args[0]
    target_country = args[1]

    alliance = await get_alliance_by_name(alliance_name)
    if not alliance:
        await update.message.reply_text(f"❌ *حلف `{alliance_name}` غير موجود.*", parse_mode="Markdown")
        return

    # التحقق من أن المستخدم هو القائد أو أدمن
    if alliance["leader_id"] != user["user_id"] and not is_admin(user["user_id"]):
        await update.message.reply_text("🚫 *فقط قائد الحلف أو الأدمن يمكنه دعوة أعضاء جدد.*", parse_mode="Markdown")
        return

    target_user = await get_user_by_country(target_country)
    if not target_user:
        await update.message.reply_text(f"❌ *الدولة `{target_country}` غير موجودة أو ليس لها حاكم.*", parse_mode="Markdown")
        return

    # التحقق من أن الهدف ليس في حلف آخر
    target_alliance = await get_alliance_by_member(target_user["user_id"])
    if target_alliance:
        await update.message.reply_text(f"⚠️ *الدولة `{target_country}` موجودة بالفعل في حلف `{target_alliance['name']}`.*", parse_mode="Markdown")
        return

    # إرسال طلب الدعوة (يمكن تخزينه في قاعدة البيانات لكن نبسطها حالياً)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول الدعوة", callback_data=f"accept_invite_{alliance_name}_{target_user['user_id']}"),
         InlineKeyboardButton("❌ رفض", callback_data="decline_invite")]
    ])
    try:
        await context.bot.send_message(
            target_user["user_id"],
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎉 *لديك دعوة للانضمام إلى حلف `{alliance_name}`!*\n"
            f"👑 *القائد:* `{user['country']}`\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"*اختر من الأزرار أدناه:*",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await update.message.reply_text(f"✅ *تم إرسال الدعوة إلى `{target_country}`.*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ *فشل إرسال الدعوة:* قد يكون المستخدم قد حظر البوت.", parse_mode="Markdown")

# ================================ قبول الدعوة (كول باك) ================================
async def accept_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    _, _, alliance_name, user_id_str = data.split("_")
    user_id = int(user_id_str)
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ *حدث خطأ: المستخدم غير موجود.*", parse_mode="Markdown")
        return

    success = await add_member_to_alliance(alliance_name, user_id)
    if success:
        await query.edit_message_text(
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ *انضممت إلى حلف `{alliance_name}` بنجاح!*\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"👥 *يمكنك الآن التنسيق مع حلفائك.*",
            parse_mode="Markdown"
        )
        # إشعار القائد
        alliance = await get_alliance_by_name(alliance_name)
        if alliance:
            leader = await get_user(alliance["leader_id"])
            if leader:
                try:
                    await context.bot.send_message(
                        leader["user_id"],
                        f"🎉 *انضم `{user['country']}` إلى حلف `{alliance_name}`.*",
                        parse_mode="Markdown"
                    )
                except:
                    pass
    else:
        await query.edit_message_text(f"❌ *فشل الانضمام إلى الحلف `{alliance_name}`.*", parse_mode="Markdown")

# ================================ عرض معلومات حلفي ================================
async def my_alliance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حلفي – عرض معلومات حلفك"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    alliance = await get_alliance_by_member(user["user_id"])
    if not alliance:
        await update.message.reply_text("⚠️ *أنت لست في أي حلف حالياً.*\n💡 استخدم `انشاء حلف [اسم]` لإنشاء حلف جديد.", parse_mode="Markdown")
        return

    members = json.loads(alliance["members"])
    members_list = []
    for uid in members:
        u = await get_user(uid)
        if u:
            members_list.append(f"• `{u['country']}` (ID: `{u['user_id']}`)")
    members_text = "\n".join(members_list) if members_list else "• *لا يوجد أعضاء*"

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤝 *معلومات الحلف* – `{alliance['name']}`\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"👑 *القائد:* `{alliance['leader_id']}`\n"
        f"👥 *الأعضاء ({len(members)}):*\n{members_text}\n"
        f"📅 *تاريخ الإنشاء:* `{time.strftime('%Y-%m-%d', time.localtime(alliance['created_at']))}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *الأوامر المتاحة:*\n"
        f"• `دعوه {alliance['name']} [دولة]`\n"
        f"• `مغادره حلف {alliance['name']}`\n"
        f"• `اطرد [دولة] من {alliance['name']}` (للقائد)\n"
        f"• `حل حلف {alliance['name']}` (للقائد)\n"
        f"• `هجوم جماعي {alliance['name']} علي [دولة]` (للقائد)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ================================ مغادرة الحلف ================================
async def leave_alliance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مغادره حلف [اسم]"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `مغادره حلف [اسم الحلف]`", parse_mode="Markdown")
        return

    alliance_name = " ".join(args)
    alliance = await get_alliance_by_name(alliance_name)
    if not alliance:
        await update.message.reply_text(f"❌ *حلف `{alliance_name}` غير موجود.*", parse_mode="Markdown")
        return

    # التحقق من أن المستخدم عضو في الحلف
    members = json.loads(alliance["members"])
    if user["user_id"] not in members and alliance["leader_id"] != user["user_id"]:
        await update.message.reply_text(f"⚠️ *أنت لست عضواً في حلف `{alliance_name}`.*", parse_mode="Markdown")
        return

    # إذا كان القائد يغادر، يجب نقل القيادة أو حل الحلف
    if alliance["leader_id"] == user["user_id"]:
        await update.message.reply_text(
            f"⚠️ *أنت قائد الحلف!* لا يمكنك المغادرة دون نقل القيادة أو حل الحلف.\n"
            f"💡 استخدم `حل حلف {alliance_name}` لحل الحلف بالكامل.",
            parse_mode="Markdown"
        )
        return

    await remove_member_from_alliance(alliance_name, user["user_id"])
    await update.message.reply_text(f"✅ *غادرت حلف `{alliance_name}`.*", parse_mode="Markdown")

# ================================ طرد عضو ================================
async def kick_alliance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اطرد [دولة] من [حلف]"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("💡 *استخدم:* `اطرد [دولة] من [حلف]`\nمثال: `اطرد فرنسا من المحور`", parse_mode="Markdown")
        return

    target_country = args[0]
    # نتخطى كلمة "من" إذا وجدت
    if args[1] == "من":
        alliance_name = " ".join(args[2:])
    else:
        alliance_name = " ".join(args[1:])

    alliance = await get_alliance_by_name(alliance_name)
    if not alliance:
        await update.message.reply_text(f"❌ *حلف `{alliance_name}` غير موجود.*", parse_mode="Markdown")
        return

    # التحقق من أن المستخدم هو القائد أو أدمن
    if alliance["leader_id"] != user["user_id"] and not is_admin(user["user_id"]):
        await update.message.reply_text("🚫 *فقط قائد الحلف أو الأدمن يمكنه طرد الأعضاء.*", parse_mode="Markdown")
        return

    target_user = await get_user_by_country(target_country)
    if not target_user:
        await update.message.reply_text(f"❌ *الدولة `{target_country}` غير موجودة.*", parse_mode="Markdown")
        return

    members = json.loads(alliance["members"])
    if target_user["user_id"] not in members:
        await update.message.reply_text(f"⚠️ *`{target_country}` ليس عضواً في حلف `{alliance_name}`.*", parse_mode="Markdown")
        return

    await remove_member_from_alliance(alliance_name, target_user["user_id"])
    await update.message.reply_text(f"✅ *تم طرد `{target_country}` من حلف `{alliance_name}`.*", parse_mode="Markdown")
    try:
        await context.bot.send_message(
            target_user["user_id"],
            f"⚠️ *لقد طُردت من حلف `{alliance_name}` بواسطة `{user['country']}`.*",
            parse_mode="Markdown"
        )
    except:
        pass

# ================================ حل الحلف ================================
async def dissolve_alliance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حل حلف [اسم]"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `حل حلف [اسم الحلف]`", parse_mode="Markdown")
        return

    alliance_name = " ".join(args)
    alliance = await get_alliance_by_name(alliance_name)
    if not alliance:
        await update.message.reply_text(f"❌ *حلف `{alliance_name}` غير موجود.*", parse_mode="Markdown")
        return

    if alliance["leader_id"] != user["user_id"] and not is_admin(user["user_id"]):
        await update.message.reply_text("🚫 *فقط قائد الحلف أو الأدمن يمكنه حل الحلف.*", parse_mode="Markdown")
        return

    await delete_alliance(alliance_name)
    await update.message.reply_text(f"🗑 *تم حل حلف `{alliance_name}`.*", parse_mode="Markdown")

# ================================ هجوم جماعي ================================
async def alliance_attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هجوم جماعي [حلف] علي [دولة]"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "> 💡 *الاستخدام:*\n"
            "`هجوم جماعي [اسم الحلف] علي [الدولة المستهدفة]`\n"
            "📌 *مثال:* `هجوم جماعي المحور علي فرنسا`",
            parse_mode="Markdown"
        )
        return

    alliance_name = args[0]
    # نتخطى كلمة "علي"
    target_country = args[2] if args[1] == "علي" else " ".join(args[1:])

    alliance = await get_alliance_by_name(alliance_name)
    if not alliance:
        await update.message.reply_text(f"❌ *حلف `{alliance_name}` غير موجود.*", parse_mode="Markdown")
        return

    if alliance["leader_id"] != user["user_id"] and not is_admin(user["user_id"]):
        await update.message.reply_text("🚫 *فقط قائد الحلف أو الأدمن يمكنه شن هجوم جماعي.*", parse_mode="Markdown")
        return

    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text(f"❌ *الدولة `{target_country}` غير موجودة أو ليس لها حاكم.*", parse_mode="Markdown")
        return

    members = json.loads(alliance["members"])
    # إشعار جميع الأعضاء بالهجوم
    sent = 0
    for uid in members:
        if uid == user["user_id"]:
            continue
        u = await get_user(uid)
        if u:
            try:
                await context.bot.send_message(
                    uid,
                    f"⚔️ *هجوم جماعي!*\n"
                    f"➖➖➖➖➖➖➖➖➖➖\n"
                    f"👑 *قائد حلف `{alliance_name}` (`{user['country']}`) أعلن هجوماً على `{target_country}`.*\n"
                    f"💡 *يمكنك الهجوم باستخدام:* `هجوم علي {target_country}`",
                    parse_mode="Markdown"
                )
                sent += 1
            except:
                pass
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ *تم إشعار {sent} عضو في الحلف بالهجوم على `{target_country}`.*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🗡️ *الغنائم ستوزع حسب مساهمة كل عضو.*",
        parse_mode="Markdown"
    )

# ================================ جيش الحلف ================================
async def alliance_army_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جيش الحلف [اسم] – عرض القوة العسكرية للحلف"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `جيش الحلف [اسم الحلف]`", parse_mode="Markdown")
        return

    alliance_name = " ".join(args)
    alliance = await get_alliance_by_name(alliance_name)
    if not alliance:
        await update.message.reply_text(f"❌ *حلف `{alliance_name}` غير موجود.*", parse_mode="Markdown")
        return

    members = json.loads(alliance["members"])
    total_soldiers = 0
    total_gold = 0
    for uid in members:
        u = await get_user(uid)
        if u:
            total_soldiers += u["soldiers"]
            total_gold += u["gold"]
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ *القوة العسكرية للحلف* – `{alliance_name}`\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"👥 *عدد الأعضاء:* `{len(members)}`\n"
        f"⚔️ *إجمالي الجنود:* `{total_soldiers:,}`\n"
        f"💰 *إجمالي الذهب:* `{total_gold:,.0f} ¥`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ================================ قائمة الأحلاف ================================
async def list_alliances_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة الاحلاف – عرض جميع الأحلاف المسجلة"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT name, leader_id, members, created_at FROM alliances") as cur:
            rows = await cur.fetchall()

    if not rows:
        await update.message.reply_text("📭 *لا توجد أحلاف مسجلة حالياً.*", parse_mode="Markdown")
        return

    text = "━━━━━━━━━━━━━━━━━━━━━\n🏛️ *قائمة الأحلاف*\n➖➖➖➖➖➖➖➖➖➖\n"
    for row in rows:
        leader = await get_user(row["leader_id"])
        leader_name = leader["country"] if leader else "غير معروف"
        members = json.loads(row["members"])
        text += f"• **{row['name']}**\n  👑 القائد: `{leader_name}`\n  👥 الأعضاء: `{len(members)}`\n  ━━━━━━━━━━━━━━━━━━━\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ================================ معالج الكول باك الخاص بالدعوات ================================
async def alliances_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("accept_invite_"):
        await accept_invite_callback(update, context)
    elif data == "decline_invite":
        await query.answer("❌ تم رفض الدعوة.")
        await query.edit_message_text("❌ *لقد رفضت الدعوة.*", parse_mode="Markdown")
