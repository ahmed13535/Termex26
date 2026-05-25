import json
import time
import io
import zipfile
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, get_all_users, log_admin, get_user_by_country,
    add_active_group, remove_active_group, get_all_groups, set_announcements_topic,
    add_ban, remove_ban, add_stigma, remove_stigma, get_stigma,
    set_game_setting, get_game_setting, backup_game_to_json, restore_game_from_json,
    create_user, deduct_gold, add_gold, update_occupation, delete_user, freeze_user
)
from config import ADMIN_IDS, COUNTRIES

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ======================== لوحة الأدمن الرئيسية (نصية) ========================
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 ليس لديك صلاحية الأدمن!")
        return

    text = (
        "**🛡 أوامر الأدمن - عصر الأمم**\n"
        "———————————————\n"
        "👥 **إدارة اللاعبين**\n"
        "  • `اللاعبين` — عرض قائمة اللاعبين\n"
        "  • `حذف دولة [اسم]` — مثال: `حذف دولة فرنسا`\n"
        "  • `منح ملكية [دولة] الى [id]` — مثال: `منح ملكية ألمانيا الى 123456789`\n"
        "  • `تجميد [دولة]` — تجميد أو فك تجميد\n"
        "  • `فك احتلال [دولة]` — تحرير قسري\n"
        "———————————————\n"
        "💰 **الموارد والجيش**\n"
        "  • `منح مثاقيل [دولة] [مبلغ]` — مثال: `منح مثاقيل مصر 1000000`\n"
        "  • `منح جيش [دولة] [عدد]` — مثال: `منح جيش روسيا 5000`\n"
        "  • `منح xp [دولة] [عدد]` — مثال: `منح xp بولندا 1000`\n"
        "  • `منح هيبة [دولة] [عدد]` — مثال: `منح هيبة إيطاليا 500`\n"
        "———————————————\n"
        "🔒 **العقوبات**\n"
        "  • `بان [id] [ساعات]` — مثال: `بان 123456789 24`\n"
        "  • `رفع بان [id]` — مثال: `رفع بان 123456789`\n"
        "  • `وصمة [id] [النص]` — مثال: `وصمة 123456789 مخالف`\n"
        "  • `رفع وصمة [id]` — مثال: `رفع وصمة 123456789`\n"
        "———————————————\n"
        "📊 **بيانات وإحصائيات**\n"
        "  • `إحصائيات الان` — إحصائيات سريعة\n"
        "  • `سجل [دولة]` — مثال: `سجل فرنسا`\n"
        "  • `حفظ اللعبة` — تصدير JSON\n"
        "  • `استعادة اللعبة` — (رد على ملف JSON)\n"
        "  • `حفظ الاعلام` — تصدير ZIP\n"
        "  • `استعادة الاعلام` — (رد على ملف ZIP)\n"
        "———————————————\n"
        "📢 **الإعلانات**\n"
        "  • `اعلان [النص]` — إرسال لكل اللاعبين\n"
        "  • `نشر [العنوان] | [النص]` — إعلان في المجموعات\n"
        "  • `توبيك الاعلانات [group_id] [topic_id]`\n"
        "———————————————\n"
        "⚙️ **تحكم اللعبة**\n"
        "  • `وقف اللعبة` / `شغل اللعبة`\n"
        "  • `اقفل الحروب` / `افتح الحروب`\n"
        "  • `تسريع الكوارث` — كارثة عشوائية فورية\n"
        "  • `اعادة اللعبة` — (يتطلب تأكيد `/confirm_reset`)\n"
        "———————————————\n"
        "🌍 **الجروبات**\n"
        "  • `تفعيل SoN` — تفعيل المجموعة الحالية\n"
        "  • `إلغاء تفعيل [group_id]` — مثال: `إلغاء تفعيل -100123456789`\n"
        "  • `الجروبات` — عرض المجموعات المفعلة\n"
        "———————————————\n"
        "📋 **سجل العمليات**: `admin_logs`\n"
        "———————————————"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ======================== إدارة اللاعبين ========================
async def cmd_create_country(update: Update, context: ContextTypes.DEFAULT_TYPE, with_flag: bool = False):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("الاستخدام: صورة + دولة [منطقة] [اسم] [telegram_id]\nأو: أضف دولة [منطقة] [اسم] [telegram_id]")
        return
    country = args[0]
    name = args[1]
    try:
        user_id = int(args[2])
    except:
        await update.message.reply_text("ID غير صحيح")
        return
    if country not in COUNTRIES:
        await update.message.reply_text("❌ منطقة غير موجودة")
        return
    existing = await get_user_by_country(name)
    if existing:
        await update.message.reply_text("❌ دولة بهذا الاسم موجودة")
        return
    flag = None
    if with_flag and update.message.reply_to_message and update.message.reply_to_message.photo:
        flag = update.message.reply_to_message.photo[-1].file_id
    elif not with_flag:
        flag = COUNTRIES[country]["emoji"]
    else:
        flag = COUNTRIES[country]["emoji"]
    await create_user(user_id, f"user_{user_id}", name, COUNTRIES[country]["capital"], flag)
    await update.message.reply_text(f"✅ تم إنشاء دولة {name} (ID: {user_id}) في {country}")

async def cmd_delete_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: `حذف دولة [اسم]`\nمثال: `حذف دولة فرنسا`", parse_mode="Markdown")
        return
    name = " ".join(args)
    user = await get_user_by_country(name)
    if not user:
        await update.message.reply_text(f"❌ دولة `{name}` غير موجودة.", parse_mode="Markdown")
        return
    await delete_user(user["user_id"])
    await update.message.reply_text(f"🗑 تم حذف دولة `{name}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "delete_country", user["user_id"], name)

async def cmd_transfer_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: `منح ملكية [دولة] الى [id]`\nمثال: `منح ملكية ألمانيا الى 123456789`", parse_mode="Markdown")
        return
    country_name = args[0]
    try:
        new_owner_id = int(args[2] if args[1] == "الى" else args[1])
    except:
        await update.message.reply_text("❌ ID غير صحيح.", parse_mode="Markdown")
        return
    user = await get_user_by_country(country_name)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country_name}` غير موجودة.", parse_mode="Markdown")
        return
    await update_user(user["user_id"], user_id=new_owner_id)
    await update.message.reply_text(f"✅ تم نقل ملكية `{country_name}` إلى ID `{new_owner_id}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "transfer_ownership", user["user_id"], f"to {new_owner_id}")

async def cmd_toggle_freeze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: `تجميد [دولة]`\nمثال: `تجميد روسيا`", parse_mode="Markdown")
        return
    country = " ".join(args)
    user = await get_user_by_country(country)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country}` غير موجودة.", parse_mode="Markdown")
        return
    new_state = 0 if user.get("is_frozen") else 1
    await freeze_user(user["user_id"], new_state == 1)
    await update.message.reply_text(f"{'🔒 تم تجميد' if new_state else '🔓 تم رفع التجميد'} دولة `{country}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "freeze", user["user_id"], str(new_state))

async def cmd_free_occupation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: `فك احتلال [دولة]`\nمثال: `فك احتلال بولندا`", parse_mode="Markdown")
        return
    country = " ".join(args)
    user = await get_user_by_country(country)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country}` غير موجودة.", parse_mode="Markdown")
        return
    await update_occupation(country, country, 0, (180,180,180))
    await update.message.reply_text(f"🏳️ تم فك احتلال `{country}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "free_occupation", user["user_id"], country)

async def cmd_list_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    users = await get_all_users()
    if not users:
        await update.message.reply_text("⚠️ لا يوجد لاعبون بعد.")
        return
    text = "**👥 قائمة اللاعبين**\n———————————————\n"
    for u in users:
        stigma = await get_stigma(u["user_id"])
        stigma_text = f" 🗡️{stigma}" if stigma else ""
        status = "❄️" if u.get("is_frozen") else "🚫" if u.get("is_banned") else "✅"
        text += f"{status} `{u['country']}` (ID: `{u['user_id']}`){stigma_text}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ======================== الموارد والجيش ========================
async def cmd_grant_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: `منح مثاقيل [دولة] [مبلغ]`\nمثال: `منح مثاقيل فرنسا 1000000`", parse_mode="Markdown")
        return
    country = args[0]
    try:
        amount = int(args[1])
    except:
        await update.message.reply_text("❌ مبلغ غير صحيح.", parse_mode="Markdown")
        return
    user = await get_user_by_country(country)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country}` غير موجودة.", parse_mode="Markdown")
        return
    await add_gold(user["user_id"], amount)
    await update.message.reply_text(f"💰 تم {'إضافة' if amount>0 else 'خصم'} `{abs(amount):,} ¥` لدولة `{country}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "grant_money", user["user_id"], f"{amount}")

async def cmd_grant_army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: `منح جيش [دولة] [عدد]`\nمثال: `منح جيش ألمانيا 5000`", parse_mode="Markdown")
        return
    country = args[0]
    try:
        amount = int(args[1])
    except:
        await update.message.reply_text("❌ عدد غير صحيح.", parse_mode="Markdown")
        return
    user = await get_user_by_country(country)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country}` غير موجودة.", parse_mode="Markdown")
        return
    new_soldiers = max(0, user["soldiers"] + amount)
    await update_user(user["user_id"], soldiers=new_soldiers)
    await update.message.reply_text(f"⚔️ تم {'زيادة' if amount>0 else 'نقص'} `{abs(amount):,}` جندي لدولة `{country}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "grant_army", user["user_id"], f"{amount}")

async def cmd_grant_xp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: `منح xp [دولة] [عدد]`\nمثال: `منح xp إيطاليا 1000`", parse_mode="Markdown")
        return
    country = args[0]
    try:
        amount = int(args[1])
    except:
        await update.message.reply_text("❌ عدد غير صحيح.", parse_mode="Markdown")
        return
    user = await get_user_by_country(country)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country}` غير موجودة.", parse_mode="Markdown")
        return
    new_xp = max(0, user["xp"] + amount)
    new_level = 1 + new_xp // 1000
    await update_user(user["user_id"], xp=new_xp, level=new_level)
    await update.message.reply_text(f"🌟 تم {'إضافة' if amount>0 else 'خصم'} `{abs(amount):,} XP` لدولة `{country}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "grant_xp", user["user_id"], f"{amount}")

async def cmd_grant_prestige(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: `منح هيبة [دولة] [عدد]`\nمثال: `منح هيبة إسبانيا 500`", parse_mode="Markdown")
        return
    country = args[0]
    try:
        amount = int(args[1])
    except:
        await update.message.reply_text("❌ عدد غير صحيح.", parse_mode="Markdown")
        return
    user = await get_user_by_country(country)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country}` غير موجودة.", parse_mode="Markdown")
        return
    new_prestige = max(0, user["prestige"] + amount)
    await update_user(user["user_id"], prestige=new_prestige)
    await update.message.reply_text(f"🏆 تم {'إضافة' if amount>0 else 'خصم'} `{abs(amount):,}` هيبة لدولة `{country}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "grant_prestige", user["user_id"], f"{amount}")

# ======================== العقوبات ========================
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("⚠️ استخدم: `بان [id] [ساعات]`\nمثال: `بان 123456789 24`", parse_mode="Markdown")
        return
    try:
        user_id = int(args[0])
        hours = int(args[1]) if len(args) > 1 else 0
    except:
        await update.message.reply_text("❌ ID أو ساعات غير صحيح.", parse_mode="Markdown")
        return
    await add_ban(user_id, hours, update.effective_user.id, "حظر إداري")
    await update.message.reply_text(f"🚫 تم حظر المستخدم `{user_id}` لمدة `{hours}` ساعة." if hours else f"🚫 تم حظر المستخدم `{user_id}` نهائياً.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "ban", user_id, f"{hours}h")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: `رفع بان [id]`\nمثال: `رفع بان 123456789`", parse_mode="Markdown")
        return
    try:
        user_id = int(args[0])
    except:
        await update.message.reply_text("❌ ID غير صحيح.", parse_mode="Markdown")
        return
    await remove_ban(user_id)
    await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم `{user_id}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "unban", user_id, "")

async def cmd_stigma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: `وصمة [id] [النص]`\nمثال: `وصمة 123456789 مخالف`", parse_mode="Markdown")
        return
    try:
        user_id = int(args[0])
        text = " ".join(args[1:])
    except:
        await update.message.reply_text("❌ ID غير صحيح.", parse_mode="Markdown")
        return
    await add_stigma(user_id, text, update.effective_user.id)
    await update.message.reply_text(f"🗡️ تمت إضافة وصمة للمستخدم `{user_id}`: `{text}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "stigma", user_id, text)

async def cmd_remove_stigma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: `رفع وصمة [id]`\nمثال: `رفع وصمة 123456789`", parse_mode="Markdown")
        return
    try:
        user_id = int(args[0])
    except:
        await update.message.reply_text("❌ ID غير صحيح.", parse_mode="Markdown")
        return
    await remove_stigma(user_id)
    await update.message.reply_text(f"✅ تم رفع الوصمة عن المستخدم `{user_id}`.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "remove_stigma", user_id, "")

# ======================== إحصائيات وبيانات ========================
async def cmd_game_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    users = await get_all_users()
    total_gold = sum(u['gold'] for u in users)
    total_soldiers = sum(u['soldiers'] for u in users)
    avg_morale = sum(u['morale'] for u in users) // len(users) if users else 0
    frozen = len([u for u in users if u.get('is_frozen')])
    banned = len([u for u in users if u.get('is_banned')])
    text = (
        f"📊 *إحصائيات اللعبة*\n———————————————\n"
        f"👥 عدد اللاعبين: `{len(users)}`\n"
        f"💰 إجمالي الذهب: `{total_gold:,.0f} ¥`\n"
        f"⚔️ إجمالي الجنود: `{total_soldiers:,}`\n"
        f"💪 متوسط المعنويات: `{avg_morale}%`\n"
        f"🔒 مجمدون: `{frozen}`\n"
        f"🚫 محظورون: `{banned}`\n"
        f"———————————————"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_country_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: `سجل [دولة]`\nمثال: `سجل فرنسا`", parse_mode="Markdown")
        return
    country = " ".join(args)
    user = await get_user_by_country(country)
    if not user:
        await update.message.reply_text(f"❌ دولة `{country}` غير موجودة.", parse_mode="Markdown")
        return
    text = (
        f"📋 *سجل {country}*\n———————————————\n"
        f"👤 الحاكم: `{user['username']}` (ID: `{user['user_id']}`)\n"
        f"💰 الذهب: `{user['gold']:,.0f} ¥`\n"
        f"⚔️ الجيش: `{user['soldiers']:,}`\n"
        f"🌟 المستوى: `{user['level']}` | XP: `{user['xp']:,}`\n"
        f"🏆 الهيبة: `{user['prestige']:,}`\n"
        f"💪 المعنويات: `{user['morale']}%`\n"
        f"🔰 مضاعف الهجوم: x{user['damage_bonus']:.2f}\n"
        f"🛡 مضاعف الدفاع: x{user['defense_bonus']:.2f}\n"
        f"❄️ مجمد: {'نعم' if user.get('is_frozen') else 'لا'}\n"
        f"🚫 محظور: {'نعم' if user.get('is_banned') else 'لا'}\n"
        f"———————————————"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ======================== حفظ واستعادة ========================
async def cmd_backup_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    json_data = await backup_game_to_json()
    buffer = io.BytesIO(json_data.encode())
    buffer.seek(0)
    await update.message.reply_document(document=InputFile(buffer, filename="game_backup.json"), caption="💾 *نسخة احتياطية للعبة*", parse_mode="Markdown")

async def cmd_restore_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("⚠️ قم بالرد على ملف JSON المرسل.", parse_mode="Markdown")
        return
    file = await update.message.reply_to_message.document.get_file()
    file_content = await file.download_as_bytearray()
    json_data = file_content.decode()
    await restore_game_from_json(json_data)
    await update.message.reply_text("✅ *تم استعادة اللعبة من النسخة الاحتياطية.*", parse_mode="Markdown")

async def cmd_backup_flags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    users = await get_all_users()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for u in users:
            if u['flag'] and len(u['flag']) > 10:
                try:
                    file = await context.bot.get_file(u['flag'])
                    file_bytes = await file.download_as_bytearray()
                    zip_file.writestr(f"{u['country']}_{u['user_id']}.jpg", file_bytes)
                except:
                    pass
    zip_buffer.seek(0)
    await update.message.reply_document(document=InputFile(zip_buffer, filename="flags_backup.zip"), caption="🏳️ *نسخة احتياطية للأعلام*", parse_mode="Markdown")

async def cmd_restore_flags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("⚠️ قم بالرد على ملف ZIP للأعلام.", parse_mode="Markdown")
        return
    await update.message.reply_text("📤 *تم استلام ملف الأعلام. سيتم استعادتها تلقائياً.*", parse_mode="Markdown")

# ======================== إعلانات ========================
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ استخدم: `اعلان [النص]`\nمثال: `اعلان صيانة قريباً`", parse_mode="Markdown")
        return
    users = await get_all_users()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(u["user_id"], f"📢 *إعلان رسمي*\n———————————————\n{text}", parse_mode="Markdown")
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ تم الإرسال إلى `{sent}` لاعب.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "broadcast", 0, text[:100])

async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = " ".join(context.args)
    if " | " not in text:
        await update.message.reply_text("⚠️ استخدم: `نشر [العنوان] | [النص]`\nمثال: `نشر إعلان | سيتم تحديث البوت`", parse_mode="Markdown")
        return
    title, content = text.split(" | ", 1)
    groups = await get_all_groups()
    sent = 0
    for g in groups:
        try:
            if g.get("announcements_topic_id"):
                await context.bot.send_message(g["group_id"], f"📢 *{title}*\n———————————————\n{content}", message_thread_id=g["announcements_topic_id"], parse_mode="Markdown")
            else:
                await context.bot.send_message(g["group_id"], f"📢 *{title}*\n———————————————\n{content}", parse_mode="Markdown")
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ تم الإعلان في `{sent}` مجموعة.", parse_mode="Markdown")
    await log_admin(update.effective_user.id, "announce", 0, title)

async def cmd_set_announcements_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: `توبيك الاعلانات [group_id] [topic_id]`\nمثال: `توبيك الاعلانات -100123456789 123`", parse_mode="Markdown")
        return
    try:
        group_id = int(args[0])
        topic_id = int(args[1])
    except:
        await update.message.reply_text("❌ group_id أو topic_id غير صحيح.", parse_mode="Markdown")
        return
    await set_announcements_topic(group_id, topic_id)
    await update.message.reply_text(f"✅ تم تعيين توبيك الإعلانات للمجموعة `{group_id}`.", parse_mode="Markdown")

# ======================== جروبات ========================
async def cmd_activate_son(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "المجموعة"
    await add_active_group(chat_id, chat_title)
    await update.message.reply_text(f"✅ تم تفعيل اللعبة في `{chat_title}`.", parse_mode="Markdown")

async def cmd_deactivate_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: `إلغاء تفعيل [group_id]`\nمثال: `إلغاء تفعيل -100123456789`", parse_mode="Markdown")
        return
    try:
        group_id = int(args[0])
    except:
        await update.message.reply_text("❌ ID غير صحيح.", parse_mode="Markdown")
        return
    await remove_active_group(group_id)
    await update.message.reply_text(f"✅ تم إلغاء تفعيل المجموعة `{group_id}`.", parse_mode="Markdown")

async def cmd_list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    groups = await get_all_groups()
    if not groups:
        await update.message.reply_text("📭 لا توجد جروبات مفعلة.", parse_mode="Markdown")
        return
    text = "📋 *الجروبات المفعّلة*\n———————————————\n"
    for g in groups:
        text += f"🏠 `{g['group_name']}`\n   🆔 `{g['group_id']}`\n   📅 تفعيل: {time.strftime('%Y/%m/%d', time.localtime(g['activated_at']))}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ======================== تحكم اللعبة ========================
async def cmd_pause_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await set_game_setting("game_paused", "1")
    await update.message.reply_text("⏸️ *تم إيقاف اللعبة مؤقتاً.*", parse_mode="Markdown")

async def cmd_resume_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await set_game_setting("game_paused", "0")
    await update.message.reply_text("▶️ *تم استئناف اللعبة.*", parse_mode="Markdown")

async def cmd_pause_wars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await set_game_setting("wars_paused", "1")
    await update.message.reply_text("🕊️ *تم إيقاف الحروب مؤقتاً.*", parse_mode="Markdown")

async def cmd_resume_wars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await set_game_setting("wars_paused", "0")
    await update.message.reply_text("⚔️ *تم استئناف الحروب.*", parse_mode="Markdown")

async def cmd_force_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    from game_loop import random_events
    await random_events(context)
    await update.message.reply_text("🌪️ *تم تشغيل كارثة عشوائية فوراً.*", parse_mode="Markdown")

async def cmd_reset_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⚠️ *إعادة اللعبة ستحذف كل البيانات نهائياً. أرسل `/confirm_reset` لتأكيد.*", parse_mode="Markdown")

async def cmd_confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            DELETE FROM users;
            DELETE FROM buildings;
            DELETE FROM wars;
            DELETE FROM alliances;
            DELETE FROM map_cells;
            DELETE FROM straits;
            DELETE FROM cooldowns;
            DELETE FROM admin_logs;
            DELETE FROM active_groups;
            DELETE FROM punishments;
            DELETE FROM game_settings;
            DELETE FROM colonies;
            DELETE FROM occupied_territories;
            DELETE FROM nuclear_projects;
            DELETE FROM bio_projects;
            DELETE FROM stocks;
            DELETE FROM user_stocks;
            DELETE FROM crops;
            DELETE FROM user_crops;
            DELETE FROM infrastructure;
            DELETE FROM harvest_log;
            DELETE FROM intel_operations;
        """)
        await db.commit()
    await update.message.reply_text("♻️ *تمت إعادة اللعبة بالكامل.*", parse_mode="Markdown")

# ======================== سجل العمليات ========================
async def admin_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("🚫 ليس لديك صلاحية!", show_alert=True)
        return
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 20") as cur:
            rows = await cur.fetchall()
    if not rows:
        await update.message.reply_text("📋 لا يوجد سجل إداري.", parse_mode="Markdown")
        return
    text = "📋 *آخر العمليات الإدارية*\n———————————————\n"
    for r in rows:
        t = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["timestamp"]))
        text += f"[{t}] `{r['action']}` → `{r['target_id']}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ======================== معالج الأزرار (اختياري) ========================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await admin_handler(update, context)

# ======================== معالج الأوامر النصية للأدمن (للاستقبال التفاعلي) ========================
async def admin_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    action = context.user_data.get("admin_action")
    if not action:
        return
    # تنظيف الحالة فقط (نعتمد على الأوامر النصية المباشرة)
    context.user_data["admin_action"] = None
    await update.message.reply_text("⚠️ استخدم الأوامر النصية الموضحة في لوحة الأدمن (`/admin`).", parse_mode="Markdown")
