"""
handlers/notifications.py – نظام الإشعارات المتكامل لبوت عصر الأمم

يتولى هذا الملف:
  - إرسال إشعارات فورية للاعبين عبر البوت
  - دعم أزرار تفاعلية (قبول/رفض)
  - إعدادات إشعارات مخصصة لكل لاعب
  - تسجيل الإشعارات في قاعدة البيانات
"""

import logging
import time
from enum import Enum
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.error import TelegramError
import aiosqlite
from config import DB_PATH
from utils import safe_send, fmt_gold, fmt_soldiers, fmt_time_remaining, log_error

logger = logging.getLogger(__name__)


# ==============================
# 📂 أنواع الإشعارات
# ==============================

class NotifType(str, Enum):
    WAR_DECLARED       = "war_declared"
    ATTACKED           = "attacked"
    DISASTER           = "disaster"
    ALLIANCE_INVITE    = "alliance_invite"
    PEACE_OFFER        = "peace_offer"
    PROTECTION_OFFER   = "protection_offer"
    UNFREEZE           = "unfreeze"
    PROJECT_COMPLETE   = "project_complete"
    STOCK_ALERT        = "stock_alert"
    STRAIT_BLOCKED     = "strait_blocked"
    TRUCE_ENDING       = "truce_ending"
    COLONY_REVOLT      = "colony_revolt"
    ADMIN_MESSAGE      = "admin_message"


# ==============================
# 🗄️ قاعدة بيانات الإشعارات
# ==============================

async def init_notifications_table():
    """إنشاء جداول نظام الإشعارات إذا لم تكن موجودة"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notif_type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            data TEXT DEFAULT '{}',
            is_read INTEGER DEFAULT 0,
            sent INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id);
        CREATE INDEX IF NOT EXISTS idx_notif_type ON notifications(notif_type);

        CREATE TABLE IF NOT EXISTS user_notif_settings (
            user_id INTEGER PRIMARY KEY,
            war_declared INTEGER DEFAULT 1,
            attacked INTEGER DEFAULT 1,
            disaster INTEGER DEFAULT 1,
            alliance_invite INTEGER DEFAULT 1,
            peace_offer INTEGER DEFAULT 1,
            protection_offer INTEGER DEFAULT 1,
            unfreeze INTEGER DEFAULT 1,
            project_complete INTEGER DEFAULT 1,
            stock_alert INTEGER DEFAULT 1,
            strait_blocked INTEGER DEFAULT 1,
            truce_ending INTEGER DEFAULT 1,
            colony_revolt INTEGER DEFAULT 1,
            admin_message INTEGER DEFAULT 1
        );
        """)
        await db.commit()


async def get_user_notif_settings(user_id: int) -> dict:
    """
    جلب إعدادات الإشعارات للمستخدم.

    Args:
        user_id: معرف المستخدم
    Returns:
        قاموس بإعدادات الإشعارات (كل نوع: 0 أو 1)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_notif_settings WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
    # الإعدادات الافتراضية: كل الإشعارات مفعّلة
    return {nt.value: 1 for nt in NotifType} | {"user_id": user_id}


async def update_notif_setting(user_id: int, notif_type: str, enabled: int):
    """
    تحديث إعداد إشعار واحد.

    Args:
        user_id: معرف المستخدم
        notif_type: نوع الإشعار (من NotifType)
        enabled: 0 أو 1
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # تأكد من وجود سطر للمستخدم
        await db.execute(
            "INSERT OR IGNORE INTO user_notif_settings (user_id) VALUES (?)", (user_id,)
        )
        # تحديث الإعداد المحدد
        safe_col = notif_type.replace("-", "_")  # تأمين اسم العمود
        allowed = {nt.value for nt in NotifType}
        if safe_col not in allowed:
            return
        await db.execute(
            f"UPDATE user_notif_settings SET {safe_col}=? WHERE user_id=?",
            (enabled, user_id)
        )
        await db.commit()


async def is_notif_enabled(user_id: int, notif_type: NotifType) -> bool:
    """هل هذا النوع من الإشعارات مفعّل لهذا المستخدم؟"""
    settings = await get_user_notif_settings(user_id)
    return bool(settings.get(notif_type.value, 1))


async def log_notification(
    user_id: int, notif_type: NotifType, title: str, body: str, data: str = "{}", sent: bool = False
):
    """
    تسجيل إشعار في قاعدة البيانات.

    Args:
        user_id: معرف المستخدم
        notif_type: نوع الإشعار
        title: عنوان الإشعار
        body: نص الإشعار
        data: بيانات إضافية (JSON string)
        sent: هل تم إرساله؟
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO notifications (user_id, notif_type, title, body, data, sent, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, notif_type.value, title, body, data, int(sent), int(time.time()))
        )
        await db.commit()


# ==============================
# 📨 إرسال الإشعارات
# ==============================

async def _send_notification(
    bot: Bot,
    user_id: int,
    notif_type: NotifType,
    title: str,
    body: str,
    data: str = "{}",
    keyboard: InlineKeyboardMarkup = None
) -> bool:
    """
    الدالة الداخلية لإرسال إشعار.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم المستقبل
        notif_type: نوع الإشعار
        title: العنوان
        body: نص الإشعار
        data: بيانات JSON
        keyboard: لوحة مفاتيح اختيارية
    Returns:
        True عند النجاح، False عند الفشل
    """
    # تحقق من إعدادات المستخدم
    if not await is_notif_enabled(user_id, notif_type):
        return False

    text = f"{title}\n\n{body}"
    try:
        kwargs = {"parse_mode": "Markdown"}
        if keyboard:
            kwargs["reply_markup"] = keyboard
        await bot.send_message(user_id, text, **kwargs)
        await log_notification(user_id, notif_type, title, body, data, sent=True)
        return True
    except TelegramError as e:
        log_error("notifications._send_notification", e, f"user_id={user_id}")
        await log_notification(user_id, notif_type, title, body, data, sent=False)
        return False


# ==============================
# 🔔 دوال الإشعارات المتخصصة
# ==============================

async def notify_war_declared(bot: Bot, defender_id: int, attacker_country: str, attacker_soldiers: int):
    """
    إشعار: تم إعلان حرب عليك.

    Args:
        bot: كائن البوت
        defender_id: معرف المدافع
        attacker_country: اسم دولة المهاجم
        attacker_soldiers: حجم جيش المهاجم
    """
    title = "⚔️ *تحذير: تم إعلان الحرب عليك!*"
    body = (
        f"🚨 دولة *{attacker_country}* أعلنت الحرب على دولتك!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 حجم جيشهم: *{fmt_soldiers(attacker_soldiers)}*\n"
        f"⚡ تصرف الآن — جهّز دفاعاتك وعزز جيشك!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 اكتب `جيشي` لعرض قواتك الحالية"
    )
    await _send_notification(bot, defender_id, NotifType.WAR_DECLARED, title, body)


async def notify_attacked(
    bot: Bot, defender_id: int, attacker_country: str,
    defender_losses: int, attacker_wins: bool, occupation_progress: float = 0.0
):
    """
    إشعار: تعرضت لهجوم.

    Args:
        bot: كائن البوت
        defender_id: معرف المدافع
        attacker_country: دولة المهاجم
        defender_losses: خسائر المدافع
        attacker_wins: هل انتصر المهاجم؟
        occupation_progress: نسبة تقدم الاحتلال
    """
    result_emoji = "💀" if attacker_wins else "✅"
    result_text = "هُزمت في هذه المعركة!" if attacker_wins else "صددت الهجوم بنجاح!"
    occ_text = (
        f"\n🏴 *تقدم الاحتلال: {occupation_progress:.1f}%* — أراضيك في خطر!"
        if occupation_progress > 0 else ""
    )
    title = f"{result_emoji} *تقرير المعركة*"
    body = (
        f"⚔️ تعرضت لهجوم من *{attacker_country}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💥 خسائرك: *{fmt_soldiers(defender_losses)}* جندي\n"
        f"🎯 النتيجة: {result_text}{occ_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 اكتب `جيشي` لعرض وضعك العسكري"
    )
    await _send_notification(bot, defender_id, NotifType.ATTACKED, title, body)


async def notify_disaster(bot: Bot, user_id: int, disaster_type: str, effects: dict):
    """
    إشعار: كارثة طبيعية أصابت دولتك.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        disaster_type: نوع الكارثة
        effects: قاموس بالخسائر {food_loss, gold_loss, soldier_loss}
    """
    from constants import DISASTERS
    disaster_info = DISASTERS.get(disaster_type, {})
    emoji = disaster_info.get("emoji", "🌪️")

    food_pct = effects.get("food_loss", 0) * 100
    gold_pct = effects.get("gold_loss", 0) * 100
    soldiers_pct = effects.get("soldier_loss", 0) * 100

    effects_lines = []
    if food_pct > 0:
        effects_lines.append(f"🌾 فقدت {food_pct:.0f}% من مخزون الغذاء")
    if gold_pct > 0:
        effects_lines.append(f"💰 فقدت {gold_pct:.0f}% من الذهب")
    if soldiers_pct > 0:
        effects_lines.append(f"👥 فقدت {soldiers_pct:.0f}% من الجيش")

    title = f"{emoji} *كارثة: {disaster_type}*"
    body = (
        f"دولتك تعرضت لـ *{disaster_type}*!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        + ("\n".join(effects_lines) or "لا خسائر تذكر") +
        f"\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 تحقق من وضعك بـ `دولتي`"
    )
    await _send_notification(bot, user_id, NotifType.DISASTER, title, body)


async def notify_alliance_invite(
    bot: Bot, invitee_id: int, alliance_name: str, inviter_country: str, alliance_id: int
):
    """
    إشعار: دعوة للانضمام إلى حلف (مع أزرار قبول/رفض).

    Args:
        bot: كائن البوت
        invitee_id: معرف المدعو
        alliance_name: اسم الحلف
        inviter_country: دولة المدعو
        alliance_id: معرف الحلف
    """
    title = "🤝 *دعوة للانضمام إلى حلف*"
    body = (
        f"دعتك دولة *{inviter_country}* للانضمام إلى حلف:\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏴 اسم الحلف: *{alliance_name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"اختر ردك:"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"accept_invite_{alliance_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"decline_invite_{alliance_id}"),
        ]
    ])
    await _send_notification(
        bot, invitee_id, NotifType.ALLIANCE_INVITE, title, body,
        keyboard=keyboard
    )


async def notify_peace_offer(bot: Bot, receiver_id: int, sender_country: str, war_id: int):
    """
    إشعار: عرض معاهدة سلام (مع أزرار قبول/رفض).

    Args:
        bot: كائن البوت
        receiver_id: معرف المستقبل
        sender_country: دولة المرسل
        war_id: معرف الحرب
    """
    title = "🕊️ *عرض معاهدة سلام*"
    body = (
        f"دولة *{sender_country}* تعرض عليك معاهدة سلام!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"بقبولها ستنتهي الحرب وتعود الأمور لطبيعتها.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"اختر ردك:"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قبول السلام", callback_data=f"accept_peace_{war_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"decline_peace_{war_id}"),
        ]
    ])
    await _send_notification(
        bot, receiver_id, NotifType.PEACE_OFFER, title, body,
        keyboard=keyboard
    )


async def notify_protection_offer(bot: Bot, receiver_id: int, sender_country: str):
    """
    إشعار: عرض معاهدة حماية.

    Args:
        bot: كائن البوت
        receiver_id: معرف المستقبل
        sender_country: دولة المرسل
    """
    title = "🛡️ *عرض معاهدة حماية*"
    body = (
        f"دولة *{sender_country}* تعرض عليك الحماية!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"بقبولها ستُحمى دولتك من الهجمات الخارجية.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"اكتب `قبول الحماية` للقبول أو `رفض الحماية` للرفض"
    )
    await _send_notification(bot, receiver_id, NotifType.PROTECTION_OFFER, title, body)


async def notify_unfreeze(bot: Bot, user_id: int):
    """
    إشعار: انتهت فترة التجميد.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
    """
    title = "✅ *تم رفع التجميد عن حسابك*"
    body = (
        "🎉 حسابك أصبح نشطاً مجدداً!\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "يمكنك الآن المشاركة في جميع أنشطة اللعبة.\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 اكتب `دولتي` لعرض حالتك"
    )
    await _send_notification(bot, user_id, NotifType.UNFREEZE, title, body)


async def notify_project_complete(bot: Bot, user_id: int, project_name: str, usage_cmd: str):
    """
    إشعار: اكتمل مشروع نووي أو بيولوجي.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        project_name: اسم المشروع
        usage_cmd: أمر الاستخدام
    """
    title = f"🔬 *اكتمل المشروع: {project_name}*"
    body = (
        f"🎯 مشروعك *{project_name}* جاهز للاستخدام!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ للاستخدام: `{usage_cmd}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ استخدم هذا السلاح بحكمة — له عواقب دبلوماسية وخيمة."
    )
    await _send_notification(bot, user_id, NotifType.PROJECT_COMPLETE, title, body)


async def notify_stock_alert(bot: Bot, user_id: int, resource: str, old_price: float, new_price: float):
    """
    إشعار: تغيّر حاد في أسعار البورصة.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        resource: المورد
        old_price: السعر القديم
        new_price: السعر الجديد
    """
    change = ((new_price - old_price) / old_price) * 100
    direction = "📈 ارتفع" if change > 0 else "📉 انخفض"
    emoji = "🟢" if change > 0 else "🔴"

    title = f"{emoji} *تنبيه بورصة: {resource}*"
    body = (
        f"سعر *{resource}* {direction} بشكل حاد!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 السعر القديم: {fmt_gold(old_price)}\n"
        f"💰 السعر الجديد: {fmt_gold(new_price)}\n"
        f"📊 التغيّر: {change:+.1f}%\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 اكتب `بورصة` لعرض جميع الأسعار"
    )
    await _send_notification(bot, user_id, NotifType.STOCK_ALERT, title, body)


async def notify_strait_blocked(bot: Bot, user_id: int, strait_name: str, controller_country: str, duration_hours: float):
    """
    إشعار: مضيق مرتبط بدولة المستخدم تم إغلاقه.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        strait_name: اسم المضيق
        controller_country: الدولة المسيطرة
        duration_hours: مدة الإغلاق بالساعات
    """
    title = f"⚓ *إغلاق مضيق: {strait_name}*"
    body = (
        f"دولة *{controller_country}* أغلقت مضيق *{strait_name}*!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ مدة الإغلاق: {duration_hours:.0f} ساعة\n"
        f"🚢 هذا يؤثر على حركة سفنك البحرية.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 اكتب `المضائق` لعرض الوضع الراهن"
    )
    await _send_notification(bot, user_id, NotifType.STRAIT_BLOCKED, title, body)


async def notify_truce_ending(bot: Bot, user_id: int, enemy_country: str, seconds_left: int):
    """
    إشعار: هدنة على وشك الانتهاء.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        enemy_country: اسم دولة العدو
        seconds_left: الثواني المتبقية
    """
    title = "⚠️ *تحذير: الهدنة على وشك الانتهاء*"
    body = (
        f"هدنتك مع *{enemy_country}* ستنتهي خلال:\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ {fmt_time_remaining(seconds_left)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ استعد للمعركة أو تفاوض على سلام دائم!"
    )
    await _send_notification(bot, user_id, NotifType.TRUCE_ENDING, title, body)


async def notify_colony_revolt(bot: Bot, user_id: int, colony_name: str):
    """
    إشعار: ثورة في مستعمرة.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        colony_name: اسم المستعمرة
    """
    title = "🔥 *ثورة في مستعمرتك!*"
    body = (
        f"مستعمرتك *{colony_name}* شهدت ثورة شعبية!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ قد تفقد السيطرة عليها إذا لم تتدخل.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 اكتب `احصد دولي` لمراجعة مستعمراتك"
    )
    await _send_notification(bot, user_id, NotifType.COLONY_REVOLT, title, body)


async def notify_admin_message(bot: Bot, user_id: int, message: str):
    """
    إشعار: رسالة من الأدمن.

    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        message: نص الرسالة
    """
    title = "📢 *رسالة من الإدارة*"
    body = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{message}\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    await _send_notification(bot, user_id, NotifType.ADMIN_MESSAGE, title, body)


# ==============================
# 📋 عرض إعدادات الإشعارات
# ==============================

async def show_notif_settings(update, user_id: int):
    """
    عرض لوحة إعدادات الإشعارات للمستخدم مع أزرار تفعيل/تعطيل.

    Args:
        update: كائن التحديث
        user_id: معرف المستخدم
    """
    settings = await get_user_notif_settings(user_id)

    label_map = {
        "war_declared":     "⚔️ إعلان حرب",
        "attacked":         "💥 تعرض لهجوم",
        "disaster":         "🌪️ كوارث طبيعية",
        "alliance_invite":  "🤝 دعوة حلف",
        "peace_offer":      "🕊️ عرض سلام",
        "protection_offer": "🛡️ عرض حماية",
        "unfreeze":         "✅ رفع التجميد",
        "project_complete": "🔬 اكتمال مشروع",
        "stock_alert":      "📈 تنبيه بورصة",
        "strait_blocked":   "⚓ إغلاق مضيق",
        "truce_ending":     "⚠️ انتهاء هدنة",
        "colony_revolt":    "🔥 ثورة مستعمرة",
    }

    buttons = []
    for key, label in label_map.items():
        enabled = bool(settings.get(key, 1))
        status = "✅" if enabled else "❌"
        action = "disable" if enabled else "enable"
        buttons.append([
            InlineKeyboardButton(
                f"{status} {label}",
                callback_data=f"notif_{action}_{key}"
            )
        ])

    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="settings_back")])

    text = (
        "🔔 *إعدادات الإشعارات*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "اضغط على أي إشعار لتفعيله أو تعطيله:\n"
        "✅ = مفعّل | ❌ = معطّل\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(buttons)
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_notif_settings_callback(update, context):
    """
    معالجة ضغطات أزرار إعدادات الإشعارات.
    يُسجّل في callback_data: notif_{enable/disable}_{type}
    """
    query = update.callback_query
    await query.answer()
    data = query.data  # مثال: notif_disable_war_declared

    parts = data.split("_", 2)
    if len(parts) < 3:
        return

    _, action, notif_key = parts
    user_id = query.from_user.id
    enabled = 1 if action == "enable" else 0

    await update_notif_setting(user_id, notif_key, enabled)
    # أعد عرض الإعدادات بعد التغيير
    await show_notif_settings(update, user_id)


# ==============================
# 📊 سجل الإشعارات
# ==============================

async def get_unread_notifications(user_id: int, limit: int = 10) -> list[dict]:
    """
    جلب الإشعارات غير المقروءة للمستخدم.

    Args:
        user_id: معرف المستخدم
        limit: عدد الإشعارات
    Returns:
        قائمة بالإشعارات
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM notifications WHERE user_id=? AND is_read=0
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def mark_notifications_read(user_id: int):
    """وضع علامة 'مقروء' على جميع إشعارات المستخدم"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,)
        )
        await db.commit()


async def broadcast_notification(
    bot: Bot, user_ids: list[int], title: str, body: str
):
    """
    إرسال إشعار جماعي لقائمة من المستخدمين.

    Args:
        bot: كائن البوت
        user_ids: قائمة بمعرفات المستخدمين
        title: العنوان
        body: النص
    """
    success = 0
    failed = 0
    for uid in user_ids:
        ok = await safe_send(bot, uid, f"{title}\n\n{body}", parse_mode="Markdown")
        if ok:
            success += 1
        else:
            failed += 1
    logger.info(f"broadcast_notification: {success} sent, {failed} failed")
    return success, failed
