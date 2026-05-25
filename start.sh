#!/data/data/com.termux/files/usr/bin/bash
# =============================================
#   عصر الأمم – سكريبت التشغيل على تيرمكس
# =============================================

echo "🚀 جاري تشغيل بوت عصر الأمم..."

# تحقق من وجود Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python غير مثبت. نفّذ: pkg install python"
    exit 1
fi

# تحقق من وجود ملف .env
if [ ! -f ".env" ]; then
    echo "❌ ملف .env غير موجود!"
    echo "📋 أنشئه بالشكل التالي:"
    echo "   BOT_TOKEN=توكن_البوت"
    echo "   ADMIN_IDS=123456789,987654321"
    exit 1
fi

# تثبيت المتطلبات إذا لم تكن مثبتة
if ! python3 -c "import telegram" &>/dev/null; then
    echo "📦 تثبيت المتطلبات..."
    pip install -r requirements.txt
fi

echo "✅ تشغيل البوت..."
python3 main.py
