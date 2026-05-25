import random
import time
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    get_user, update_user, get_all_users, deduct_gold, add_gold,
    get_buildings, add_building, log_disaster, get_user_by_country
)
from config import COUNTRIES

# قائمة الكوارث مع تأثيراتها المختلفة
DISASTERS = [
    {
        "name": "🌊 زلزال مدمر",
        "description": "هزت الأرض بقوة، مما أدى إلى دمار واسع.",
        "effects": [
            {"type": "gold", "ratio": -0.10, "message": "تدمير جزء من البنية التحتية الاقتصادية"},
            {"type": "soldiers", "ratio": -0.05, "message": "خسائر بشرية"},
            {"type": "buildings", "chance": 0.3, "message": "تدمير مباني عشوائية"}
        ]
    },
    {
        "name": "🌪️ إعصار قوي",
        "description": "رياح عاتية وأمطار غزيرة اجتاحت المنطقة.",
        "effects": [
            {"type": "food", "ratio": -0.15, "message": "تدمير المحاصيل الزراعية"},
            {"type": "energy", "ratio": -0.10, "message": "انقطاع التيار الكهربائي"},
            {"type": "soldiers", "ratio": -0.03, "message": "خسائر في صفوف الجيش"}
        ]
    },
    {
        "name": "🔥 حرائق غابات",
        "description": "حرائق هائلة التهمت الغابات والمزارع.",
        "effects": [
            {"type": "food", "ratio": -0.20, "message": "تدمير المحاصيل والمزارع"},
            {"type": "gold", "ratio": -0.05, "message": "خسائر مالية فادحة"},
            {"type": "soldiers", "ratio": -0.02, "message": "جنود مصابون"}
        ]
    },
    {
        "name": "💧 فيضان عارم",
        "description": "ارتفاع منسوب الأنهار والبحيرات أدى إلى غمر الأراضي.",
        "effects": [
            {"type": "food", "ratio": -0.12, "message": "تدمير المحاصيل الزراعية"},
            {"type": "energy", "ratio": -0.08, "message": "تعطل محطات الطاقة"},
            {"type": "gold", "ratio": -0.06, "message": "خسائر في الممتلكات العامة"}
        ]
    },
    {
        "name": "🍂 مجاعة",
        "description": "نقص حاد في الموارد الغذائية بسبب الجفاف.",
        "effects": [
            {"type": "food", "ratio": -0.25, "message": "نقص حاد في المواد الغذائية"},
            {"type": "morale", "ratio": -0.10, "message": "انخفاض معنويات الشعب"},
            {"type": "soldiers", "ratio": -0.05, "message": "هجرة الجنود بحثاً عن الطعام"}
        ]
    },
    {
        "name": "🦠 وباء",
        "description": "انتشار مرض معدٍ بسرعة بين السكان.",
        "effects": [
            {"type": "soldiers", "ratio": -0.12, "message": "نفوق الجنود"},
            {"type": "morale", "ratio": -0.15, "message": "انخفاض الروح المعنوية"},
            {"type": "food", "ratio": -0.05, "message": "توقف الإنتاج الزراعي"}
        ]
    },
    {
        "name": "📉 انهيار اقتصادي",
        "description": "تدهور حاد في الأسواق المالية.",
        "effects": [
            {"type": "gold", "ratio": -0.30, "message": "خسائر مالية ضخمة"},
            {"type": "energy", "ratio": -0.05, "message": "توقف المصانع"},
            {"type": "food", "ratio": -0.05, "message": "ارتفاع أسعار المواد الغذائية"}
        ]
    },
    {
        "name": "❄️ عاصفة ثلجية قارسة",
        "description": "تساقط كثيف للثلوج مع انخفاض قياسي في درجات الحرارة.",
        "effects": [
            {"type": "energy", "ratio": -0.20, "message": "انقطاع الكهرباء والتدفئة"},
            {"type": "soldiers", "ratio": -0.08, "message": "جنود مصابون بقضمة الصقيع"},
            {"type": "food", "ratio": -0.10, "message": "تلف المحاصيل الشتوية"}
        ]
    }
]

# ================================ تشغيل كارثة عشوائية (تُستدعى من game_loop) ================================
async def trigger_random_disaster(context: ContextTypes.DEFAULT_TYPE):
    """اختيار دولة عشوائية ووقوع كارثة عليها (تُستدعى كل فترة)"""
    users = await get_all_users()
    if not users:
        return

    # اختيار دولة عشوائية
    target_user = random.choice(users)
    disaster = random.choice(DISASTERS)

    # تطبيق التأثيرات على المستخدم
    effect_messages = []
    for effect in disaster["effects"]:
        if effect["type"] == "gold":
            new_gold = int(target_user["gold"] * (1 + effect["ratio"]))
            new_gold = max(0, new_gold)
            await update_user(target_user["user_id"], gold=new_gold)
            effect_messages.append(f"💰 {effect['message']}: `{abs(int(target_user['gold'] * effect['ratio'])):,.0f} ¥`")

        elif effect["type"] == "food":
            new_food = int(target_user["food"] * (1 + effect["ratio"]))
            new_food = max(0, new_food)
            await update_user(target_user["user_id"], food=new_food)
            effect_messages.append(f"🌾 {effect['message']}: `{abs(int(target_user['food'] * effect['ratio'])):,} وحدة`")

        elif effect["type"] == "energy":
            new_energy = int(target_user["energy"] * (1 + effect["ratio"]))
            new_energy = max(0, new_energy)
            await update_user(target_user["user_id"], energy=new_energy)
            effect_messages.append(f"⚡ {effect['message']}: `{abs(int(target_user['energy'] * effect['ratio'])):,} وحدة`")

        elif effect["type"] == "soldiers":
            new_soldiers = int(target_user["soldiers"] * (1 + effect["ratio"]))
            new_soldiers = max(0, new_soldiers)
            await update_user(target_user["user_id"], soldiers=new_soldiers)
            effect_messages.append(f"⚔️ {effect['message']}: `{abs(int(target_user['soldiers'] * effect['ratio'])):,} جندي`")

        elif effect["type"] == "morale":
            new_morale = int(target_user["morale"] * (1 + effect["ratio"]))
            new_morale = max(0, min(100, new_morale))
            await update_user(target_user["user_id"], morale=new_morale)
            effect_messages.append(f"💪 {effect['message']}: `{abs(int(target_user['morale'] * effect['ratio']))}%`")

        elif effect["type"] == "buildings" and random.random() < effect.get("chance", 0.3):
            buildings = await get_buildings(target_user["user_id"])
            if buildings:
                destroyed = random.choice(list(buildings.keys()))
                # لا يمكن حذف المبنى مباشرة، لكن يمكن خفض مستواه (سنكتفي بتأثير معنوي)
                effect_messages.append(f"🏗️ {effect['message']}: تم تدمير مبنى `{destroyed}` بشكل جزئي (خسارة مستوى واحد).")
                # هنا يمكن خفض مستوى المبنى إذا أردت (اختياري)

    # تسجيل الكارثة في قاعدة البيانات
    await log_disaster(disaster["name"], target_user["country"], ", ".join(effect_messages))

    # إرسال إشعار للاعب المتضرر
    try:
        text = (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *كارثة طبيعية في {target_user['country']}!*\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"{disaster['name']}\n"
            f"📝 *الوصف:* {disaster['description']}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"*التأثيرات:*\n"
        )
        for msg in effect_messages:
            text += f"• {msg}\n"
        text += "━━━━━━━━━━━━━━━━━━━━━"
        await context.bot.send_message(chat_id=target_user["user_id"], text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"فشل إرسال إشعار الكارثة: {e}")

# ================================ كارثة مستهدفة من أدمن ================================
async def targeted_disaster_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسريع الكوارث [دولة] – إحداث كارثة على دولة محددة (لأدمن)"""
    from handlers.admin import is_admin
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 *ليس لديك صلاحية الأدمن!*", parse_mode="Markdown")
        return

    args = context.args
    if not args:
        await update.message.reply_text("💡 *استخدم:* `تسريع الكوارث [دولة]`", parse_mode="Markdown")
        return

    target_country = " ".join(args)
    target_user = await get_user_by_country(target_country)
    if not target_user:
        await update.message.reply_text(f"❌ *دولة `{target_country}` غير موجودة.*", parse_mode="Markdown")
        return

    disaster = random.choice(DISASTERS)
    effect_messages = []
    for effect in disaster["effects"]:
        if effect["type"] == "gold":
            new_gold = int(target_user["gold"] * (1 + effect["ratio"]))
            new_gold = max(0, new_gold)
            await update_user(target_user["user_id"], gold=new_gold)
            effect_messages.append(f"💰 {effect['message']}: `{abs(int(target_user['gold'] * effect['ratio'])):,.0f} ¥`")

        elif effect["type"] == "food":
            new_food = int(target_user["food"] * (1 + effect["ratio"]))
            new_food = max(0, new_food)
            await update_user(target_user["user_id"], food=new_food)
            effect_messages.append(f"🌾 {effect['message']}: `{abs(int(target_user['food'] * effect['ratio'])):,} وحدة`")

        elif effect["type"] == "energy":
            new_energy = int(target_user["energy"] * (1 + effect["ratio"]))
            new_energy = max(0, new_energy)
            await update_user(target_user["user_id"], energy=new_energy)
            effect_messages.append(f"⚡ {effect['message']}: `{abs(int(target_user['energy'] * effect['ratio'])):,} وحدة`")

        elif effect["type"] == "soldiers":
            new_soldiers = int(target_user["soldiers"] * (1 + effect["ratio"]))
            new_soldiers = max(0, new_soldiers)
            await update_user(target_user["user_id"], soldiers=new_soldiers)
            effect_messages.append(f"⚔️ {effect['message']}: `{abs(int(target_user['soldiers'] * effect['ratio'])):,} جندي`")

        elif effect["type"] == "morale":
            new_morale = int(target_user["morale"] * (1 + effect["ratio"]))
            new_morale = max(0, min(100, new_morale))
            await update_user(target_user["user_id"], morale=new_morale)
            effect_messages.append(f"💪 {effect['message']}: `{abs(int(target_user['morale'] * effect['ratio']))}%`")

        elif effect["type"] == "buildings" and random.random() < effect.get("chance", 0.3):
            buildings = await get_buildings(target_user["user_id"])
            if buildings:
                destroyed = random.choice(list(buildings.keys()))
                effect_messages.append(f"🏗️ {effect['message']}: تم تدمير مبنى `{destroyed}` بشكل جزئي.")

    await log_disaster(disaster["name"], target_country, ", ".join(effect_messages))

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *كارثة مفاجئة في {target_country}!*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"{disaster['name']}\n"
        f"📝 *الوصف:* {disaster['description']}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"*التأثيرات:*\n"
    )
    for msg in effect_messages:
        text += f"• {msg}\n"
    text += "━━━━━━━━━━━━━━━━━━━━━"
    await update.message.reply_text(text, parse_mode="Markdown")

    # إشعار اللاعب المتضرر
    try:
        await context.bot.send_message(chat_id=target_user["user_id"], text=text, parse_mode="Markdown")
    except:
        pass
