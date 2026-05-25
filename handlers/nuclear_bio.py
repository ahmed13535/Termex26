import time
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, deduct_gold, add_gold, get_user_by_country,
    get_cooldown, set_cooldown, get_buildings,
    get_nuclear_project, update_nuclear_project,
    get_bio_project, update_bio_project,
    update_occupation
)
from config import COUNTRIES

# ================================ المشروع النووي ================================

async def nuclear_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشروعي النووي – عرض حالة التخصيب والمخزون"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.* ابدأ بـ `/start`", parse_mode="Markdown")
        return

    project = await get_nuclear_project(user["user_id"])
    now = int(time.time())
    # محاكاة التقدم: يمكن حساب الدورات المتبقية بناءً على last_update
    # لكننا سنبسطها: نعرض عدد القنابل الجاهزة والدورات المنفذة
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"☢️ *المشروع النووي – {user['country']}*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💣 *القنابل الذرية:* `{project.get('atomic_completed', 0)}`\n"
        f"💥 *القنابل الهيدروجينية:* `{project.get('hydrogen_completed', 0)}`\n"
        f"🔬 *دورات التخصيب الذرية:* `{project.get('atomic_cycles', 0)} / 144`\n"
        f"⚛️ *دورات التخصيب الهيدروجينية:* `{project.get('hydrogen_cycles', 0)} / 144`\n"
        f"📅 *آخر تحديث:* `{time.strftime('%Y-%m-%d %H:%M', time.localtime(project.get('last_update', 0)))}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *يتطلب مفاعل نووي (مستوى 10 بنية) لبدء التخصيب.*\n"
        f"💡 *الأوامر:*\n"
        f"• `تخصيب قنبلة_ذرية`\n"
        f"• `تخصيب قنبلة_هيدروجينية`\n"
        f"• `إلغاء تخصيب`\n"
        f"• `اضرب قنبلة_ذرية [دولة]`\n"
        f"• `اضرب قنبلة_هيدروجينية [دولة]`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def enrich_atomic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تخصيب قنبلة_ذرية – بدء مشروع تخصيب القنبلة الذرية"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    # التحقق من وجود مفاعل نووي (مستوى 10 من البنية أو مبنى محدد)
    buildings = await get_buildings(user["user_id"])
    if "مفاعل_نووي" not in buildings or buildings["مفاعل_نووي"]["level"] < 10:
        await update.message.reply_text("❌ *تحتاج إلى مفاعل نووي مستوى 10+ لبدء التخصيب.*\n💡 استخدم `ابني مفاعل_نووي` لبناء مفاعل.", parse_mode="Markdown")
        return

    project = await get_nuclear_project(user["user_id"])
    if project["atomic_cycles"] >= 144:
        await update.message.reply_text("⚠️ *لديك بالفعل قنبلة ذرية جاهزة! استخدمها أو قم بتخصيب أخرى.*", parse_mode="Markdown")
        return

    # تكلفة التخصيب: 700 مليون
    cost = 700_000_000
    if user["gold"] < cost:
        await update.message.reply_text(f"❌ *ذهب غير كافٍ!*\n💰 *تحتاج:* `{cost:,.0f} ¥`\n💵 *رصيدك:* `{user['gold']:,.0f} ¥`", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], cost)
    # نبدأ التخصيب: نحتاج 144 دورة (يمكن أن تستغرق وقتاً حقيقياً، لكن نكتفي بزيادة تدريجية عبر job)
    # سنحاكي بتعيين حقل يبدأ التخصيب، لكن لسهولة نعتمد على قاعدة البيانات والتحديث الدوري
    await update_nuclear_project(user["user_id"], atomic_cycles=144, atomic_completed=project.get("atomic_completed", 0) + 1)
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔬 *بدأ تخصيب القنبلة الذرية!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 *التكلفة:* `-{cost:,.0f} ¥`\n"
        f"⏳ *المدة:* 12 ساعة (144 دورة).\n"
        f"💡 *ستحصل على قنبلة ذرية عند اكتمال التخصيب.*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def enrich_hydrogen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تخصيب قنبلة_هيدروجينية – بدء مشروع تخصيب القنبلة الهيدروجينية"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    buildings = await get_buildings(user["user_id"])
    if "مفاعل_نووي" not in buildings or buildings["مفاعل_نووي"]["level"] < 10:
        await update.message.reply_text("❌ *تحتاج إلى مفاعل نووي مستوى 10+ لبدء التخصيب.*", parse_mode="Markdown")
        return

    project = await get_nuclear_project(user["user_id"])
    if project["hydrogen_cycles"] >= 144:
        await update.message.reply_text("⚠️ *لديك بالفعل قنبلة هيدروجينية جاهزة!*", parse_mode="Markdown")
        return

    cost = 1_000_000_000
    if user["gold"] < cost:
        await update.message.reply_text(f"❌ *ذهب غير كافٍ!*\n💰 *تحتاج:* `{cost:,.0f} ¥`\n💵 *رصيدك:* `{user['gold']:,.0f} ¥`", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], cost)
    await update_nuclear_project(user["user_id"], hydrogen_cycles=144, hydrogen_completed=project.get("hydrogen_completed", 0) + 1)
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💥 *بدأ تخصيب القنبلة الهيدروجينية!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 *التكلفة:* `-{cost:,.0f} ¥`\n"
        f"⏳ *المدة:* 12 ساعة.\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def cancel_enrich_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء تخصيب – إلغاء المشروع الحالي مع خسارة المدفوع"""
    user = await get_user(update.effective_user.id)
    if not user:
        return
    project = await get_nuclear_project(user["user_id"])
    if project["atomic_cycles"] == 0 and project["hydrogen_cycles"] == 0:
        await update.message.reply_text("⚠️ *لا يوجد مشروع تخصيب نشط لإلغائه.*", parse_mode="Markdown")
        return

    # إعادة تعيين المشروع
    await update_nuclear_project(user["user_id"], atomic_cycles=0, hydrogen_cycles=0)
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ *تم إلغاء مشروع التخصيب!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💸 *خسرت المبلغ المدفوع (لا استرداد).*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def drop_atomic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضرب قنبلة_ذرية [دولة] – تدمير 80% من جيش الهدف"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `اضرب قنبلة_ذرية [دولة]`", parse_mode="Markdown")
        return

    target_country = " ".join(args)
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text(f"❌ *دولة `{target_country}` غير موجودة.*", parse_mode="Markdown")
        return

    project = await get_nuclear_project(user["user_id"])
    if project["atomic_completed"] == 0:
        await update.message.reply_text("❌ *ليس لديك قنبلة ذرية جاهزة. قم بتخصيب واحدة أولاً.*", parse_mode="Markdown")
        return

    cd = await get_cooldown(user["user_id"], "nuke_atomic")
    if cd > 0:
        await update.message.reply_text(f"⏳ *يجب الانتظار {cd // 60} دقيقة قبل استخدام قنبلة أخرى.*", parse_mode="Markdown")
        return

    # تدمير 80% من جيش الهدف
    new_soldiers = int(target["soldiers"] * 0.2)
    await update_user(target["user_id"], soldiers=new_soldiers)

    # استهلاك القنبلة
    await update_nuclear_project(user["user_id"], atomic_completed=project["atomic_completed"] - 1)

    await set_cooldown(user["user_id"], "nuke_atomic", 3600)  # 1 ساعة

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"☢️ *ضربة نووية ذرية على {target_country}!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💀 *تم تدمير 80% من جيش {target_country}.*\n"
        f"👥 *جيشه الآن:* `{new_soldiers:,}`\n"
        f"⚡ *تأثير إشعاعي يستمر لساعات.*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    # إشعار الهدف
    try:
        await context.bot.send_message(
            target["user_id"],
            f"☢️ *تعرضت لضربة نووية ذرية من {user['country']}!*\n💀 *فقدت 80% من جيشك.*",
            parse_mode="Markdown"
        )
    except:
        pass

async def drop_hydrogen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضرب قنبلة_هيدروجينية [دولة] – تدمير 99% + احتلال فوري"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `اضرب قنبلة_هيدروجينية [دولة]`", parse_mode="Markdown")
        return

    target_country = " ".join(args)
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text(f"❌ *دولة `{target_country}` غير موجودة.*", parse_mode="Markdown")
        return

    project = await get_nuclear_project(user["user_id"])
    if project["hydrogen_completed"] == 0:
        await update.message.reply_text("❌ *ليس لديك قنبلة هيدروجينية جاهزة.*", parse_mode="Markdown")
        return

    cd = await get_cooldown(user["user_id"], "nuke_hydrogen")
    if cd > 0:
        await update.message.reply_text(f"⏳ *يجب الانتظار {cd // 60} دقيقة قبل استخدام قنبلة أخرى.*", parse_mode="Markdown")
        return

    # تدمير 99% من الجيش
    new_soldiers = int(target["soldiers"] * 0.01)
    await update_user(target["user_id"], soldiers=new_soldiers)

    # احتلال فوري (تحديث الخريطة)
    color = COUNTRIES.get(user["country"], {}).get("color", (180,180,180))
    await update_occupation(target_country, user["country"], 100, color)

    # استهلاك القنبلة
    await update_nuclear_project(user["user_id"], hydrogen_completed=project["hydrogen_completed"] - 1)

    await set_cooldown(user["user_id"], "nuke_hydrogen", 7200)  # ساعتين

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💥 *ضربة هيدروجينية على {target_country}!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💀 *تم تدمير 99% من جيش {target_country}.*\n"
        f"🏴 *احتلال فوري! أصبحت {target_country} تحت سيطرتك.*\n"
        f"☠️ *كارثة بيئية وإنسانية.*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            target["user_id"],
            f"💥 *تعرضت لضربة هيدروجينية من {user['country']}!*\n🏴 *دولتك محتلة بالكامل.*",
            parse_mode="Markdown"
        )
    except:
        pass

# ================================ المشروع البيولوجي ================================

async def bio_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشروعي البيولوجي – عرض حالة المشروع والمخزون"""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ *ليس لديك دولة.*", parse_mode="Markdown")
        return

    project = await get_bio_project(user["user_id"])
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧬 *المشروع البيولوجي – {user['country']}*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🦠 *الأسلحة البيولوجية:* `{project.get('bio_completed', 0)}`\n"
        f"☠️ *السموم القاتلة:* `{project.get('toxin_completed', 0)}`\n"
        f"🔬 *دورات التطوير البيولوجي:* `{project.get('bio_cycles', 0)} / 96`\n"
        f"⚗️ *دورات تطوير السم:* `{project.get('toxin_cycles', 0)} / 72`\n"
        f"📅 *آخر تحديث:* `{time.strftime('%Y-%m-%d %H:%M', time.localtime(project.get('last_update', 0)))}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *يتطلب مختبر بيولوجي (مستوى 20 بنية) للتطوير.*\n"
        f"💡 *الأوامر:*\n"
        f"• `تطوير سلاح_بيولوجي`\n"
        f"• `تطوير سم_قاتل`\n"
        f"• `استخدم سلاح_بيولوجي [دولة]`\n"
        f"• `استخدم سم_قاتل [دولة]`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def develop_bio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تطوير سلاح_بيولوجي – 600 مليون / 8 ساعات"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    buildings = await get_buildings(user["user_id"])
    if "مختبر_بيولوجي" not in buildings or buildings["مختبر_بيولوجي"]["level"] < 20:
        await update.message.reply_text("❌ *تحتاج مختبر بيولوجي مستوى 20+ لتطوير الأسلحة البيولوجية.*", parse_mode="Markdown")
        return

    project = await get_bio_project(user["user_id"])
    if project["bio_cycles"] >= 96:
        await update.message.reply_text("⚠️ *لديك سلاح بيولوجي قيد التطوير بالفعل.*", parse_mode="Markdown")
        return

    cost = 600_000_000
    if user["gold"] < cost:
        await update.message.reply_text(f"❌ *ذهب غير كافٍ!* تحتاج `{cost:,.0f} ¥`", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], cost)
    await update_bio_project(user["user_id"], bio_cycles=96, bio_completed=project.get("bio_completed", 0) + 1)
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧬 *بدأ تطوير سلاح بيولوجي!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 *التكلفة:* `-{cost:,.0f} ¥`\n"
        f"⏳ *المدة:* 8 ساعات (96 دورة).\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def develop_toxin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تطوير سم_قاتل – 400 مليون / 6 ساعات"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    buildings = await get_buildings(user["user_id"])
    if "مختبر_بيولوجي" not in buildings or buildings["مختبر_بيولوجي"]["level"] < 20:
        await update.message.reply_text("❌ *تحتاج مختبر بيولوجي مستوى 20+ لتطوير السموم.*", parse_mode="Markdown")
        return

    project = await get_bio_project(user["user_id"])
    if project["toxin_cycles"] >= 72:
        await update.message.reply_text("⚠️ *لديك سم قاتل قيد التطوير بالفعل.*", parse_mode="Markdown")
        return

    cost = 400_000_000
    if user["gold"] < cost:
        await update.message.reply_text(f"❌ *ذهب غير كافٍ!* تحتاج `{cost:,.0f} ¥`", parse_mode="Markdown")
        return

    await deduct_gold(user["user_id"], cost)
    await update_bio_project(user["user_id"], toxin_cycles=72, toxin_completed=project.get("toxin_completed", 0) + 1)
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"☠️ *بدأ تطوير السم القاتل!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 *التكلفة:* `-{cost:,.0f} ¥`\n"
        f"⏳ *المدة:* 6 ساعات (72 دورة).\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def use_bio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استخدم سلاح_بيولوجي [دولة] – 35% جيش + منع التجنيد 8 ساعات"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `استخدم سلاح_بيولوجي [دولة]`", parse_mode="Markdown")
        return

    target_country = " ".join(args)
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text(f"❌ *دولة `{target_country}` غير موجودة.*", parse_mode="Markdown")
        return

    project = await get_bio_project(user["user_id"])
    if project["bio_completed"] == 0:
        await update.message.reply_text("❌ *ليس لديك سلاح بيولوجي جاهز.*", parse_mode="Markdown")
        return

    new_soldiers = int(target["soldiers"] * 0.65)
    await update_user(target["user_id"], soldiers=new_soldiers)
    # منع التجنيد لمدة 8 ساعات (يمكن تخزينها في كول داون)
    await set_cooldown(target["user_id"], "recruit_ban", 28800)

    await update_bio_project(user["user_id"], bio_completed=project["bio_completed"] - 1)

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🦠 *هجوم بيولوجي على {target_country}!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💀 *تدمير 35% من جيش {target_country}.*\n"
        f"⛔ *تم منع التجنيد لمدة 8 ساعات.*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(target["user_id"], f"🦠 *تعرضت لهجوم بيولوجي من {user['country']}! فقدت 35% من جيشك، ولا يمكنك التجنيد 8 ساعات.*", parse_mode="Markdown")
    except:
        pass

async def use_toxin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استخدم سم_قاتل [دولة] – 25% جيش + سرقة 15% ذهب + منع المزارع 10 ساعات"""
    user = await get_user(update.effective_user.id)
    if not user:
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `استخدم سم_قاتل [دولة]`", parse_mode="Markdown")
        return

    target_country = " ".join(args)
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text(f"❌ *دولة `{target_country}` غير موجودة.*", parse_mode="Markdown")
        return

    project = await get_bio_project(user["user_id"])
    if project["toxin_completed"] == 0:
        await update.message.reply_text("❌ *ليس لديك سم قاتل جاهز.*", parse_mode="Markdown")
        return

    new_soldiers = int(target["soldiers"] * 0.75)
    stolen_gold = int(target["gold"] * 0.15)
    await update_user(target["user_id"], soldiers=new_soldiers)
    await deduct_gold(target["user_id"], stolen_gold)
    await add_gold(user["user_id"], stolen_gold)
    # منع المزارع (يمكن تخزينها)
    await set_cooldown(target["user_id"], "farm_ban", 36000)

    await update_bio_project(user["user_id"], toxin_completed=project["toxin_completed"] - 1)

    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"☠️ *هجوم بالسم القاتل على {target_country}!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💀 *تدمير 25% من جيش {target_country}.*\n"
        f"💰 *سرقة 15% من ذهبه:* `+{stolen_gold:,.0f} ¥`\n"
        f"⛔ *تم منع المزارع لمدة 10 ساعات.*\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(target["user_id"], f"☠️ *تعرضت لهجوم بالسم القاتل من {user['country']}! فقدت 25% من جيشك وسرق 15% من ذهبك، ولا يمكنك الزراعة 10 ساعات.*", parse_mode="Markdown")
    except:
        pass
