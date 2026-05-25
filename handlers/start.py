import time
from telegram import (Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
                       InlineKeyboardMarkup, InlineKeyboardButton)
from telegram.ext import (ContextTypes, ConversationHandler, CommandHandler,
                          MessageHandler, CallbackQueryHandler, filters)
from database import get_user, create_user, get_user_by_country
from config import COUNTRIES
from bot_filters import admin_reply_only

# ===================== حالات المحادثة =====================
(CHOOSE_COUNTRY, CONFIRM_COUNTRY, ENTER_COUNTRY_NAME,
 ENTER_CAPITAL, CHOOSE_GOV, CHOOSE_RELIGION, UPLOAD_FLAG) = range(7)

# ===================== خيارات التسجيل =====================
GOV_SYSTEMS = ["🏛️ جمهورية", "👑 مملكة", "⚜️ إمبراطورية",
               "☪️ خلافة", "🗳️ ديمقراطية", "🎖️ دكتاتورية"]

RELIGIONS = ["☪️ إسلام", "✝️ مسيحية", "✡️ يهودية",
             "🕉️ هندوسية", "☸️ بوذية", "⚡ إلحاد"]

# ===================== لوحات المفاتيح =====================
def countries_keyboard(exclude=None):
    """عرض الدول غير المحجوزة"""
    exclude = exclude or set()
    names = [n for n in COUNTRIES.keys() if n not in exclude]
    rows = [names[i:i+3] for i in range(0, len(names), 3)]
    rows.append(["❌ إلغاء"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def gov_keyboard():
    rows = [GOV_SYSTEMS[i:i+2] for i in range(0, len(GOV_SYSTEMS), 2)]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def religion_keyboard():
    rows = [RELIGIONS[i:i+2] for i in range(0, len(RELIGIONS), 2)]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["🗺 خريطة", "📊 حالتي", "💰 اقتصاد"],
        ["⚔️ عسكري", "🤝 دبلوماسية", "🏪 متجر"],
        ["🏆 ترتيب", "🌊 مضائق", "📋 مساعدة"]
    ], resize_keyboard=True)

# ===================== أوامر البدء =====================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # في المجموعة: عرض زر التسجيل
    if update.effective_chat.type in ("group", "supergroup"):
        from database import get_all_groups
        groups = await get_all_groups()
        active_ids = {g["group_id"] for g in groups}
        if update.effective_chat.id not in active_ids:
            return  # مجموعة غير مفعلة
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎮 سجل هنا", url=f"https://t.me/{context.bot.username}?start=register")
        ]])
        await update.message.reply_text(
            "🌍 *عصر الأمم* — ابدأ رحلتك نحو المجد!\n"
            "اضغط الزر للتسجيل في الخاص:",
            parse_mode="Markdown", reply_markup=keyboard
        )
        return

    # في الخاص: التحقق من وجود حساب
    user = await get_user(update.effective_user.id)
    if user:
        await show_main_menu(update, context, user)
        return ConversationHandler.END

    # رسالة الترحيب
    await update.message.reply_text(
        "『 نِضال الأُمم 』\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"> **• أهلاً بك يا {update.effective_user.first_name}**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "> ┊🏛 ابدأ من قرية صغيرة… وابنِ إمبراطورية عظيمة\n"
        "> ┊⚔ جنّد الجيوش وطوّر قوتك العسكرية\n"
        "> ┊⛨ كوّن تحالفات استراتيجية وشارك بالحروب الكبرى\n"
        "> ┊🌾 طوّر الاقتصاد والزراعة والبنية التحتية\n"
        "> ┊🏭 ابنِ المصانع والموانئ والقواعد العسكرية\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "> 📜 **اصنع تاريخ أمتك بنفسك**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🌍 **اختر دولتك لتبدأ:**",
        parse_mode="Markdown"
    )

    # جلب الدول المحجوزة
    from database import get_all_users
    users = await get_all_users()
    occupied = {u["country"] for u in users}
    await update.message.reply_text(
        "👇 اختر من الدول المتاحة:",
        reply_markup=countries_keyboard(exclude=occupied)
    )
    return CHOOSE_COUNTRY

# ===================== خطوات التسجيل =====================
async def choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "❌ إلغاء":
        await update.message.reply_text("تم الإلغاء.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if text not in COUNTRIES:
        await update.message.reply_text("❌ اختر دولة من القائمة:")
        return CHOOSE_COUNTRY

    existing = await get_user_by_country(text)
    if existing:
        await update.message.reply_text(f"⚠️ *{text}* محجوزة! اختر دولة أخرى:", parse_mode="Markdown")
        return CHOOSE_COUNTRY

    context.user_data["reg_base_country"] = text
    info = COUNTRIES[text]

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد الاختيار", callback_data=f"confirm_country_{text}")],
        [InlineKeyboardButton("🔄 اختيار آخر", callback_data="restart_country")]
    ])
    await update.message.reply_text(
        f"🌍 *{text}* {info['emoji']}\n"
        f"🏛️ العاصمة الافتراضية: *{info['capital']}*\n\n"
        "هل تريد تأكيد هذه الدولة؟",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text("👇", reply_markup=keyboard)
    return CONFIRM_COUNTRY

async def confirm_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "restart_country":
        from database import get_all_users
        users = await get_all_users()
        occupied = {u["country"] for u in users}
        await query.edit_message_text("🔄 اختر دولة أخرى:")
        await context.bot.send_message(
            query.message.chat_id,
            "👇 الدول المتاحة:",
            reply_markup=countries_keyboard(exclude=occupied)
        )
        return CHOOSE_COUNTRY

    country = query.data.replace("confirm_country_", "")
    context.user_data["reg_base_country"] = country
    await query.edit_message_text(f"✅ تم اختيار *{country}*", parse_mode="Markdown")
    await context.bot.send_message(
        query.message.chat_id,
        "📝 *أدخل اسماً لدولتك* (أو أرسل نقطة `.` للاحتفاظ بالاسم الحالي):",
        parse_mode="Markdown"
    )
    return ENTER_COUNTRY_NAME

async def enter_country_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    base = context.user_data.get("reg_base_country", "")

    if text == ".":
        context.user_data["reg_country_name"] = base
    else:
        if len(text) < 2 or len(text) > 30:
            await update.message.reply_text("❌ الاسم يجب أن يكون بين 2-30 حرف. حاول مرة أخرى:")
            return ENTER_COUNTRY_NAME
        context.user_data["reg_country_name"] = text

    info = COUNTRIES.get(base, {})
    await update.message.reply_text(
        f"🏛️ *أدخل اسم العاصمة* (أو نقطة `.` للاحتفاظ بـ {info.get('capital', 'الافتراضي')}):",
        parse_mode="Markdown"
    )
    return ENTER_CAPITAL

async def enter_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    base = context.user_data.get("reg_base_country", "")
    info = COUNTRIES.get(base, {})

    if text == ".":
        context.user_data["reg_capital"] = info.get("capital", "العاصمة")
    else:
        if len(text) < 2 or len(text) > 25:
            await update.message.reply_text("❌ اسم العاصمة يجب أن يكون بين 2-25 حرف:")
            return ENTER_CAPITAL
        context.user_data["reg_capital"] = text

    await update.message.reply_text(
        "⚖️ *اختر نظام الحكم لدولتك:*",
        parse_mode="Markdown",
        reply_markup=gov_keyboard()
    )
    return CHOOSE_GOV

async def choose_gov(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in GOV_SYSTEMS:
        await update.message.reply_text("❌ اختر من الخيارات المتاحة:", reply_markup=gov_keyboard())
        return CHOOSE_GOV

    context.user_data["reg_gov"] = text
    await update.message.reply_text(
        "🕌 *اختر الدين الرسمي لدولتك:*",
        parse_mode="Markdown",
        reply_markup=religion_keyboard()
    )
    return CHOOSE_RELIGION

async def choose_religion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in RELIGIONS:
        await update.message.reply_text("❌ اختر من الخيارات المتاحة:", reply_markup=religion_keyboard())
        return CHOOSE_RELIGION

    context.user_data["reg_religion"] = text
    base = context.user_data.get("reg_base_country", "")
    info = COUNTRIES.get(base, {})
    emoji = info.get("emoji", "🏳️")

    await update.message.reply_text(
        f"🏳️ *أرسل صورة علم دولتك!*\n"
        f"_(أو أرسل أي إيموجي كبديل سريع، مثل: {emoji})_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data["awaiting_flag"] = True
    return UPLOAD_FLAG

async def process_flag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة العلم (صورة أو إيموجي)"""
    flag_value = None

    if update.message.photo:
        flag_value = update.message.photo[-1].file_id
    elif update.message.text:
        flag_value = update.message.text.strip()
        if len(flag_value) > 10:
            await update.message.reply_text("❌ أرسل إيموجياً واحداً أو صورة.")
            return UPLOAD_FLAG

    if not flag_value:
        await update.message.reply_text("❌ أرسل صورة أو إيموجي:")
        return UPLOAD_FLAG

    context.user_data["awaiting_flag"] = False

    # إتمام التسجيل
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    country_name = context.user_data.get("reg_country_name", "")
    capital = context.user_data.get("reg_capital", "")
    gov = context.user_data.get("reg_gov", "جمهورية")
    religion = context.user_data.get("reg_religion", "إسلام")

    try:
        await create_user(user_id, username, country_name, capital, flag_value)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في التسجيل: {e}\nتأكد من اختيار دولة غير محجوزة.")
        return ConversationHandler.END

    # رسالة التأكيد
    flag_display = "🖼️ (صورة)" if len(flag_value) > 10 else flag_value
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *تم تسجيل دولتك بنجاح!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 *الدولة:* {country_name}\n"
        f"🏛️ *العاصمة:* {capital}\n"
        f"⚖️ *نظام الحكم:* {gov}\n"
        f"🕌 *الدين:* {religion}\n"
        f"🏳️ *العلم:* {flag_display}\n"
        f"💰 *رأس المال الابتدائي:* 50,000,000 ¥\n"
        f"⚔️ *الجيش الابتدائي:* 10,000 جندي\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 *انطلق نحو المجد!*",
        parse_mode="Markdown"
    )

    user = await get_user(user_id)
    if user:
        await show_main_menu(update, context, user)

    # تنظيف بيانات التسجيل
    for key in ["reg_base_country", "reg_country_name", "reg_capital", "reg_gov", "reg_religion"]:
        context.user_data.pop(key, None)

    return ConversationHandler.END

# ===================== اللوحة الرئيسية =====================
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict):
    flag = user.get("flag", "🏳️")
    flag_display = "🖼️" if len(str(flag)) > 10 else flag
    text = (
        f"🌍 *{user['country']}* {flag_display} — لوحة التحكم\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 الذهب: *{user['gold']:,.0f} ¥*\n"
        f"⚔️ الجيش: *{user['soldiers']:,} جندي*\n"
        f"🌾 الطعام: {user['food']:,}\n"
        f"🌟 المستوى: *{user['level']}* | XP: {user['xp']:,}\n"
        f"🏆 الهيبة: {user['prestige']:,}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"اختر أمراً من القائمة:"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# ===================== ConversationHandler (التعديل هنا) =====================
def get_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", admin_reply_only(start_cmd))],
        states={
            CHOOSE_COUNTRY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_only(choose_country))],
            CONFIRM_COUNTRY:    [CallbackQueryHandler(confirm_country_callback)],
            ENTER_COUNTRY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_only(enter_country_name))],
            ENTER_CAPITAL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_only(enter_capital))],
            CHOOSE_GOV:         [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_only(choose_gov))],
            CHOOSE_RELIGION:    [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_only(choose_religion))],
            UPLOAD_FLAG: [
                MessageHandler(filters.PHOTO, admin_reply_only(process_flag)),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_only(process_flag)),
            ],
        },
        fallbacks=[CommandHandler("start", admin_reply_only(start_cmd))],
        per_message=False,
        allow_reentry=True,
    )
