"""
utils.py – الدوال المساعدة العامة لبوت عصر الأمم
دوال مشتركة تُستخدم في جميع الوحدات.
"""

import time
import logging
import os
from functools import wraps
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from constants import RATE_LIMIT_ATTACKS_PER_MINUTE, RATE_LIMIT_WINDOW

logger = logging.getLogger(__name__)

# ==============================
# 🔐 فحص الأدمن
# ==============================

def is_admin(user_id: int) -> bool:
    """
    التحقق مما إذا كان المستخدم أدمن.

    Args:
        user_id: معرف المستخدم
    Returns:
        True إذا كان أدمن، False خلاف ذلك
    """
    return user_id in ADMIN_IDS


def admin_required(func):
    """
    ديكوريتور: يرفض تنفيذ الدالة إذا لم يكن المستخدم أدمن.
    يعمل مع handlers التيليجرام (update, context).
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else 0
        if not is_admin(user_id):
            msg = "❌ *هذا الأمر للأدمن فقط.*"
            if update.message:
                await update.message.reply_text(msg, parse_mode="Markdown")
            elif update.callback_query:
                await update.callback_query.answer("❌ غير مصرح لك", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def registered_required(func):
    """
    ديكوريتور: يرفض التنفيذ إذا لم يكن اللاعب مسجلاً.
    يضيف `user` إلى kwargs تلقائياً.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from database import get_user
        user_id = update.effective_user.id if update.effective_user else 0
        user = await get_user(user_id)
        if not user:
            msg = "❌ ليس لديك دولة بعد. ابدأ بـ /start أو اكتب `انضم`"
            if update.message:
                await update.message.reply_text(msg, parse_mode="Markdown")
            elif update.callback_query:
                await update.callback_query.answer("❌ لا يوجد تسجيل", show_alert=True)
            return
        if user.get("is_banned"):
            msg = "🚫 *حسابك محظور.* تواصل مع الأدمن."
            if update.message:
                await update.message.reply_text(msg, parse_mode="Markdown")
            return
        if user.get("is_frozen"):
            msg = "❄️ *حسابك مجمّد مؤقتاً.* انتظر أو تواصل مع الأدمن."
            if update.message:
                await update.message.reply_text(msg, parse_mode="Markdown")
            return
        kwargs["user"] = user
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==============================
# 💰 تنسيق الأرقام
# ==============================

def fmt_num(n: float, decimals: int = 0) -> str:
    """
    تنسيق رقم بفواصل الآلاف.

    Args:
        n: الرقم
        decimals: عدد المنازل العشرية
    Returns:
        النص المنسق (مثال: "1,500,000")
    """
    fmt = f"{n:,.{decimals}f}"
    return fmt


def fmt_gold(amount: float) -> str:
    """تنسيق مبلغ الذهب مع الرمز ¥"""
    return f"{fmt_num(amount)} ¥"


def fmt_soldiers(n: int) -> str:
    """تنسيق عدد الجنود"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_time_remaining(seconds: int) -> str:
    """
    تحويل ثوانٍ إلى نص عربي مقروء.

    Args:
        seconds: عدد الثواني المتبقية
    Returns:
        نص مثل: "2 ساعة و15 دقيقة"
    """
    if seconds <= 0:
        return "0 ثانية"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours:
        parts.append(f"{hours} ساعة")
    if minutes:
        parts.append(f"{minutes} دقيقة")
    if secs and not hours:
        parts.append(f"{secs} ثانية")
    return " و".join(parts) if parts else "0 ثانية"


def fmt_percentage(value: float, total: float) -> str:
    """احسب وأظهر النسبة المئوية"""
    if total == 0:
        return "0%"
    return f"{(value / total * 100):.1f}%"

# ==============================
# ⏱️ الوقت والتهدئة
# ==============================

def now() -> int:
    """الوقت الحالي بالثواني (Unix timestamp)"""
    return int(time.time())


def cooldown_expired(expires_at: int) -> bool:
    """هل انتهت مدة التهدئة؟"""
    return now() >= expires_at


def seconds_until(timestamp: int) -> int:
    """كم ثانية حتى وقت معين؟"""
    return max(0, timestamp - now())

# ==============================
# 🛡️ حد الطلبات (Rate Limiting)
# ==============================

# مخزن مؤقت: {user_id: [(timestamp, action), ...]}
_rate_store: dict[int, list] = defaultdict(list)


def check_rate_limit(user_id: int, action: str, max_per_window: int = 5) -> bool:
    """
    التحقق من حد الطلبات.

    Args:
        user_id: معرف المستخدم
        action: نوع الإجراء (مثل "attack", "buy")
        max_per_window: أقصى عدد مسموح خلال النافذة الزمنية
    Returns:
        True إذا كان مسموحاً، False إذا تجاوز الحد
    """
    key = f"{user_id}:{action}"
    current = now()
    window_start = current - RATE_LIMIT_WINDOW

    # إزالة السجلات القديمة
    _rate_store[key] = [t for t in _rate_store[key] if t > window_start]

    if len(_rate_store[key]) >= max_per_window:
        return False

    _rate_store[key].append(current)
    return True

# ==============================
# 🧹 تنقية نص MarkdownV2
# ==============================

_MD2_SPECIAL = r"\_*[]()~`>#+-=|{}.!"


def escape_md2(text: str) -> str:
    """
    تهروب الأحرف الخاصة في MarkdownV2.

    Args:
        text: النص الأصلي
    Returns:
        النص بعد التهروب
    """
    for ch in _MD2_SPECIAL:
        text = text.replace(ch, f"\\{ch}")
    return text

# ==============================
# 🔍 البحث في الدول
# ==============================

def find_country(query: str, countries: dict) -> str | None:
    """
    البحث عن دولة بالاسم الكامل أو جزء منه.

    Args:
        query: نص البحث
        countries: قاموس الدول
    Returns:
        اسم الدولة إذا وُجدت، None خلاف ذلك
    """
    # مطابقة كاملة أولاً
    if query in countries:
        return query
    # مطابقة جزئية
    matches = [c for c in countries if query in c or c in query]
    if len(matches) == 1:
        return matches[0]
    return None


def suggest_countries(query: str, countries: dict, limit: int = 3) -> list[str]:
    """
    اقتراح أسماء دول مشابهة.

    Args:
        query: نص البحث
        countries: قاموس الدول
        limit: عدد الاقتراحات
    Returns:
        قائمة باقتراحات الدول
    """
    return [c for c in countries if query in c][:limit]

# ==============================
# 📝 بناء الرسائل
# ==============================

def build_header(title: str, country: str = None, emoji: str = "📋") -> str:
    """
    بناء ترويسة رسالة موحدة.

    Args:
        title: العنوان
        country: اسم الدولة (اختياري)
        emoji: الإيموجي
    Returns:
        نص الترويسة
    """
    header = f"{emoji} *{title}*"
    if country:
        header += f" — {country}"
    header += "\n━━━━━━━━━━━━━━━━━━━━━\n"
    return header


def build_separator() -> str:
    """خط فاصل موحد"""
    return "━━━━━━━━━━━━━━━━━━━━━\n"


def build_field(label: str, value: str, emoji: str = "") -> str:
    """
    بناء سطر معلومات منسق.

    Args:
        label: التسمية
        value: القيمة
        emoji: الإيموجي
    Returns:
        سطر منسق
    """
    prefix = f"{emoji} " if emoji else ""
    return f"{prefix}{label}: *{value}*\n"

# ==============================
# 🗃️ ملفات
# ==============================

def ensure_dir(path: str):
    """إنشاء مجلد إذا لم يكن موجوداً"""
    os.makedirs(path, exist_ok=True)


def get_flag_path(cache_dir: str, user_id: int) -> str:
    """مسار ملف العلم المؤقت"""
    return os.path.join(cache_dir, f"flag_{user_id}.png")


def flag_exists(cache_dir: str, user_id: int) -> bool:
    """هل يوجد علم محفوظ لهذا المستخدم؟"""
    return os.path.isfile(get_flag_path(cache_dir, user_id))

# ==============================
# ⚠️ معالجة الأخطاء
# ==============================

async def safe_send(bot, chat_id: int, text: str, **kwargs) -> bool:
    """
    إرسال رسالة بأمان مع معالجة الأخطاء.

    Args:
        bot: كائن البوت
        chat_id: معرف الدردشة
        text: نص الرسالة
        **kwargs: معاملات إضافية
    Returns:
        True عند النجاح، False عند الفشل
    """
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logger.warning(f"safe_send failed for {chat_id}: {e}")
        return False


def log_error(context: str, error: Exception, extra: str = ""):
    """
    تسجيل خطأ بتنسيق موحد.

    Args:
        context: السياق (اسم الدالة)
        error: الخطأ
        extra: معلومات إضافية
    """
    logger.error(f"[{context}] {type(error).__name__}: {error}" + (f" | {extra}" if extra else ""))
