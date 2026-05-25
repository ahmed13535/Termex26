#!/data/data/com.termux/files/usr/bin/bash
# =============================================
#   إعداد تيرمكس من الصفر
# =============================================

echo "📦 تحديث الحزم..."
pkg update -y && pkg upgrade -y

echo "🐍 تثبيت Python..."
pkg install python -y

echo "🔧 تثبيت المتطلبات الإضافية..."
pkg install libpng libjpeg-turbo freetype -y

echo "📚 تثبيت مكتبات Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ الإعداد اكتمل!"
echo ""
echo "📋 الخطوات التالية:"
echo "   1. أنشئ ملف .env وأضف:"
echo "      BOT_TOKEN=توكن_البوت_من_BotFather"
echo "      ADMIN_IDS=معرفك_الرقمي"
echo ""
echo "   2. شغّل البوت:"
echo "      bash start.sh"
echo "      أو مباشرةً: python3 main.py"
