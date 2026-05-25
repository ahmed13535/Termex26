import random
import time
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, update_user, deduct_gold, add_gold, get_user_by_country

# مستويات المخابرات وخبراتها
INTEL_LEVELS = {
    0: {"name": "مبتدئ 🔍", "exp_needed": 0, "spy_chance": 20, "sabotage_chance": 0, "assassinate_chance": 0, "infiltrate": False},
    1: {"name": "جاسوس 🕵️", "exp_needed": 3, "spy_chance": 35, "sabotage_chance": 0, "assassinate_chance": 0, "infiltrate": False},
    2: {"name": "عميل ميداني 🥷", "exp_needed": 7, "spy_chance": 50, "sabotage_chance": 25, "assassinate_chance": 0, "infiltrate": False},
    3: {"name": "قائد مخابرات 🧠", "exp_needed": 12, "spy_chance": 65, "sabotage_chance": 40, "assassinate_chance": 15, "infiltrate": True},
    4: {"name": "مدير جهاز 🏛️", "exp_needed": 18, "spy_chance": 75, "sabotage_chance": 55, "assassinate_chance": 30, "infiltrate": True},
    5: {"name": "أسطورة تجسس 👑", "exp_needed": 25, "spy_chance": 85, "sabotage_chance": 70, "assassinate_chance": 50, "infiltrate": True},
}

async def get_intel_level(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على مستوى المخابرات من user_data أو قاعدة البيانات"""
    if "intel_level" not in context.user_data:
        context.user_data["intel_level"] = 0
        context.user_data["intel_exp"] = 0
    return context.user_data["intel_level"], context.user_data["intel_exp"]

async def update_intel_level(user_id: int, context: ContextTypes.DEFAULT_TYPE, exp_gain: int):
    """زيادة الخبرة وترقية المستوى تلقائياً"""
    new_exp = context.user_data.get("intel_exp", 0) + exp_gain
    context.user_data["intel_exp"] = new_exp
    current_level = context.user_data.get("intel_level", 0)
    for level, data in INTEL_LEVELS.items():
        if new_exp >= data["exp_needed"] and level > current_level:
            context.user_data["intel_level"] = level
            return True  # تمت الترقية
    return False

async def intelligence_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ ليس لديك دولة. ابدأ بـ /start")
        return
    intel_level, intel_exp = await get_intel_level(user["user_id"], context)
    level_info = INTEL_LEVELS.get(intel_level, INTEL_LEVELS[0])
    next_level = intel_level + 1
    next_exp = INTEL_LEVELS.get(next_level, {}).get("exp_needed", "MAX")
    text = (
        f"🕵️ *جهاز المخابرات — {user['country']}*\n———————————————\n"
        f"📊 المستوى: {level_info['name']} (Lv.{intel_level})\n"
        f"⭐ خبرة مخابرات: {intel_exp}/{next_exp}\n"
        f"———————————————\n"
        f"🎯 فرصة نجاح التجسس: {level_info['spy_chance']}%\n"
        f"💣 فرصة تخريب: {level_info['sabotage_chance']}%\n"
        f"🗡️ فرصة اغتيال: {level_info['assassinate_chance']}%\n"
        f"🔍 زرع عميل: {'✅ متاح' if level_info['infiltrate'] else '❌ غير متاح (Lv.3+)'}\n"
        f"———————————————\n"
        f"💡 الأوامر:\n"
        f"  🔍 تجسس على [دولة]\n"
        f"  💣 تخريب [دولة]\n"
        f"  🗡️ اغتيال [دولة]\n"
        f"  🕵️ زرع عميل [دولة]\n"
        f"  🛡️ مضادة تجسس\n"
        f"  🎭 معلومات مزيفة\n"
        f"  📋 جواسيس مكشوفون\n"
        f"  🧱 تحصين"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def spy_operation(update: Update, context: ContextTypes.DEFAULT_TYPE, operation: str):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    args = context.args
    if not args:
        await update.message.reply_text(f"💡 استخدم: {operation} [دولة]")
        return
    target_country = " ".join(args)
    target = await get_user_by_country(target_country)
    if not target:
        await update.message.reply_text("❌ دولة غير موجودة أو ليس لها حاكم.")
        return

    intel_level, _ = await get_intel_level(user["user_id"], context)
    level_info = INTEL_LEVELS.get(intel_level, INTEL_LEVELS[0])
    
    # فرصة الانكشاف (تزداد مع المستوى)
    detection_chance = min(80, 30 + intel_level * 8)
    
    if operation == "تجسس على":
        if intel_level < 1:
            await update.message.reply_text("🔒 تحتاج مستوى مخابرات 1+ للتجسس.")
            return
        success_chance = level_info["spy_chance"]
        success = random.randint(1, 100) <= success_chance
        detected = random.randint(1, 100) <= detection_chance
        
        if detected:
            fine = 75000
            await deduct_gold(user["user_id"], fine)
            await update_intel_level(user["user_id"], context, -1)
            await update.message.reply_text(
                f"🚨 *جاسوسك انكشف!*\n————————————————\n"
                f"اعتُقل في {target_country}\n"
                f"💸 خسرت {fine:,} ¥\n"
                f"⚠️ فرصة الانكشاف {detection_chance}%\n"
                f"📉 -1 XP مخابرات",
                parse_mode="Markdown"
            )
            return
        if success:
            stolen_gold = int(target["gold"] * random.uniform(0.01, 0.05))
            await add_gold(user["user_id"], stolen_gold)
            await deduct_gold(target["user_id"], stolen_gold)
            upgraded = await update_intel_level(user["user_id"], context, 1)
            msg = f"🔍 *تجسس ناجح!*\n————————————————\n🎯 {target_country}\n💰 +{stolen_gold:,} ¥\n⭐ +1 XP مخابرات"
            if upgraded:
                new_level, _ = await get_intel_level(user["user_id"], context)
                msg += f"\n🎉 *ترقية!* المستوى {new_level}"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ فشل التجسس على {target_country}")
    
    elif operation == "تخريب":
        if intel_level < 2:
            await update.message.reply_text("🔒 تحتاج مستوى مخابرات 2+ للتخريب.")
            return
        success_chance = level_info["sabotage_chance"]
        success = random.randint(1, 100) <= success_chance
        detected = random.randint(1, 100) <= detection_chance
        if detected:
            await deduct_gold(user["user_id"], 100000)
            await update.message.reply_text(f"🚨 تم كشف مخربك في {target_country}! خسرت 100,000¥")
            return
        if success:
            sabotage_type = random.choice(["gold", "soldiers", "building"])
            if sabotage_type == "gold":
                stolen = int(target["gold"] * 0.1)
                await deduct_gold(target["user_id"], stolen)
                await add_gold(user["user_id"], stolen)
                msg = f"💣 *تخريب ناجح!* سرقت {stolen:,} ¥ من {target_country}"
            elif sabotage_type == "soldiers":
                loss = int(target["soldiers"] * 0.15)
                await update_user(target["user_id"], soldiers=max(0, target["soldiers"] - loss))
                msg = f"💣 *تخريب ناجح!* دمّرت {loss:,} جندي من {target_country}"
            else:
                msg = f"💣 *تخريب ناجح!* دمّرت منشأة عشوائية في {target_country}"
            await update_intel_level(user["user_id"], context, 2)
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ فشل التخريب في {target_country}")
    
    elif operation == "اغتيال":
        if intel_level < 3:
            await update.message.reply_text("🔒 تحتاج مستوى مخابرات 3+ للاغتيال.")
            return
        success_chance = level_info["assassinate_chance"]
        success = random.randint(1, 100) <= success_chance
        if success:
            kill = int(target["soldiers"] * 0.3)
            await update_user(target["user_id"], soldiers=max(0, target["soldiers"] - kill))
            await update_intel_level(user["user_id"], context, 3)
            await update.message.reply_text(f"🗡️ *اغتيال ناجح!* قتلت {kill:,} جندي من {target_country}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ فشل الاغتيال في {target_country}")
    
    else:
        await update.message.reply_text("❌ عملية غير معروفة.")

async def counter_intelligence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["counter_intel"] = int(time.time()) + 3600
    await update.message.reply_text("🛡️ *تفعيل مضادة التجسس!* لمدة ساعة، يصعّب اكتشاف عملياتك.", parse_mode="Markdown")

async def fake_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fake_info"] = int(time.time()) + 3600
    await update.message.reply_text("🎭 *معلومات مزيفة!* لمدة ساعة، من يتجسس عليك سيحصل على بيانات خاطئة.", parse_mode="Markdown")

async def exposed_spies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # في التطوير المستقبلي يمكن تخزين السجل في قاعدة البيانات
    await update.message.reply_text("📋 *جواسيس مكشوفون:* لا توجد عمليات مسجلة بعد.", parse_mode="Markdown")

async def fortify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user:
        return
    fortify_level = context.user_data.get("fortify", 0)
    if fortify_level >= 3:
        await update.message.reply_text("❌ وصلت للحد الأقصى من التحصين (3).")
        return
    cost = 5000000 * (fortify_level + 1)
    if user["gold"] < cost:
        await update.message.reply_text(f"❌ تحتاج {cost:,} ¥ للتحصين.")
        return
    await deduct_gold(user["user_id"], cost)
    context.user_data["fortify"] = fortify_level + 1
    new_defense = user["defense_bonus"] + 0.15
    await update_user(user["user_id"], defense_bonus=new_defense)
    await update.message.reply_text(f"🧱 *تحصين ناجح!* +15% دفاع (المستوى {fortify_level + 1}/3).", parse_mode="Markdown")
