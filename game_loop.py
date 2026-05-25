import random
import time
import logging
from telegram.ext import ContextTypes
from database import (
    get_all_users, update_user, get_buildings, add_gold, get_user,
    get_nuclear_project, update_nuclear_project,
    get_bio_project, update_bio_project
)
from config import BUILDINGS, BASE_INCOME, TAX_INTERVAL

logger = logging.getLogger(__name__)

# ================================ جمع الضرائب والإنتاج ================================
async def tax_collection(context: ContextTypes.DEFAULT_TYPE):
    """جمع الضرائب والإنتاج من المباني كل 10 دقائق"""
    users = await get_all_users()
    for user in users:
        if user["is_frozen"] or user["is_banned"]:
            continue
        buildings = await get_buildings(user["user_id"])
        income = BASE_INCOME
        food_prod = 1000
        energy_prod = 500
        for btype, bdata in buildings.items():
            level = bdata.get("level", 1)
            binfo = BUILDINGS.get(btype, {})
            if "gold_bonus" in binfo:
                income += income * binfo["gold_bonus"] * level
            if "food" in binfo:
                food_prod += binfo["food"] * level
            if "energy" in binfo:
                energy_prod += binfo["energy"] * level
            if "production" in binfo:
                income += binfo["production"] * 1000 * level
        tax_rate = 0.15
        income = int(income * (1 + tax_rate))
        upkeep = int(user["soldiers"] * 0.1 + user["tanks"] * 500 + user["aircraft"] * 2000)
        net = income - upkeep
        new_gold = max(0, user["gold"] + net)
        new_food = min(user["food"] + food_prod, 9999999)
        new_energy = min(user["energy"] + energy_prod, 9999999)
        await update_user(user["user_id"], gold=new_gold, food=new_food, energy=new_energy)

# ================================ تحديث البورصة ================================
async def update_stock_market(context: ContextTypes.DEFAULT_TYPE):
    """تحديث أسعار البورصة كل ساعة"""
    from handlers.stock_market import update_stock_prices
    await update_stock_prices()
    logger.info("📈 تم تحديث أسعار البورصة")

# ================================ الكوارث العشوائية ================================
async def random_disasters(context: ContextTypes.DEFAULT_TYPE):
    """تشغيل كارثة عشوائية كل 30 دقيقة"""
    from handlers.disasters import trigger_random_disaster
    await trigger_random_disaster(context)
    logger.info("🌪️ تم تشغيل كارثة عشوائية")

# ================================ تقدم المشاريع النووية والبيولوجية (محاكاة الدورات) ================================
async def advance_projects(context: ContextTypes.DEFAULT_TYPE):
    """تقدم مشاريع التخصيب والتطوير كل دقيقة (محاكاة الدورات)"""
    users = await get_all_users()
    for user in users:
        # المشروع النووي
        nuke = await get_nuclear_project(user["user_id"])
        updated = False
        if nuke["atomic_cycles"] > 0:
            new_cycles = nuke["atomic_cycles"] - 1
            if new_cycles == 0:
                # إتمام القنبلة الذرية
                await update_nuclear_project(user["user_id"], atomic_cycles=0, atomic_completed=nuke["atomic_completed"] + 1)
                try:
                    await context.bot.send_message(user["user_id"], "🔬 *اكتمل تخصيب القنبلة الذرية!* استخدم `اضرب قنبلة_ذرية [دولة]` لتدمير أعدائك.", parse_mode="Markdown")
                except:
                    pass
            else:
                await update_nuclear_project(user["user_id"], atomic_cycles=new_cycles)
            updated = True
        if nuke["hydrogen_cycles"] > 0:
            new_cycles = nuke["hydrogen_cycles"] - 1
            if new_cycles == 0:
                await update_nuclear_project(user["user_id"], hydrogen_cycles=0, hydrogen_completed=nuke["hydrogen_completed"] + 1)
                try:
                    await context.bot.send_message(user["user_id"], "💥 *اكتمل تخصيب القنبلة الهيدروجينية!* استخدم `اضرب قنبلة_هيدروجينية [دولة]` لدمار شامل.", parse_mode="Markdown")
                except:
                    pass
            else:
                await update_nuclear_project(user["user_id"], hydrogen_cycles=new_cycles)
            updated = True
        if updated:
            await update_nuclear_project(user["user_id"], last_update=int(time.time()))

        # المشروع البيولوجي
        bio = await get_bio_project(user["user_id"])
        updated_bio = False
        if bio["bio_cycles"] > 0:
            new_cycles = bio["bio_cycles"] - 1
            if new_cycles == 0:
                await update_bio_project(user["user_id"], bio_cycles=0, bio_completed=bio["bio_completed"] + 1)
                try:
                    await context.bot.send_message(user["user_id"], "🧬 *اكتمل تطوير السلاح البيولوجي!* استخدم `استخدم سلاح_بيولوجي [دولة]` لنشر الوباء.", parse_mode="Markdown")
                except:
                    pass
            else:
                await update_bio_project(user["user_id"], bio_cycles=new_cycles)
            updated_bio = True
        if bio["toxin_cycles"] > 0:
            new_cycles = bio["toxin_cycles"] - 1
            if new_cycles == 0:
                await update_bio_project(user["user_id"], toxin_cycles=0, toxin_completed=bio["toxin_completed"] + 1)
                try:
                    await context.bot.send_message(user["user_id"], "☠️ *اكتمل تطوير السم القاتل!* استخدم `استخدم سم_قاتل [دولة]` لاغتيال القادة.", parse_mode="Markdown")
                except:
                    pass
            else:
                await update_bio_project(user["user_id"], toxin_cycles=new_cycles)
            updated_bio = True
        if updated_bio:
            await update_bio_project(user["user_id"], last_update=int(time.time()))

# ================================ إنتاج الأسلحة من المصانع ================================
async def weapon_manufacturing(context: ContextTypes.DEFAULT_TYPE):
    """إنتاج أسلحة تلقائي من المصانع كل ساعة"""
    users = await get_all_users()
    for user in users:
        buildings = await get_buildings(user["user_id"])
        if "مصنع" in buildings:
            level = buildings["مصنع"]["level"]
            bonus_soldiers = level * 50
            new_soldiers = user["soldiers"] + bonus_soldiers
            await update_user(user["user_id"], soldiers=new_soldiers)

# ================================ انتهاء الهدن (توسعة مستقبلية) ================================
async def check_treaty_expirations(context: ContextTypes.DEFAULT_TYPE):
    """التحقق من انتهاء معاهدات السلام (ستضاف لاحقاً)"""
    pass

# ================================ تحديث الروح المعنوية أثناء الحروب ================================
async def update_war_progress(context: ContextTypes.DEFAULT_TYPE):
    """خفض الروح المعنوية للدول في حالة حرب كل 10 دقائق"""
    from database import get_wars_for_user
    users = await get_all_users()
    for user in users:
        wars = await get_wars_for_user(user["user_id"])
        if wars:
            morale = max(40, user.get("morale", 100) - 1)
            await update_user(user["user_id"], morale=morale)

# ================================ إعداد جميع المهام الدورية ================================
def setup_jobs(app):
    jq = app.job_queue
    if jq is None:
        logger.warning("JobQueue not available")
        return

    # جدولة المهام الأساسية
    jq.run_repeating(tax_collection, interval=TAX_INTERVAL, first=30)
    jq.run_repeating(weapon_manufacturing, interval=3600, first=600)
    jq.run_repeating(check_treaty_expirations, interval=3600, first=120)
    jq.run_repeating(update_war_progress, interval=600, first=60)

    # جدولة المهام الجديدة
    jq.run_repeating(update_stock_market, interval=3600, first=300)      # كل ساعة
    jq.run_repeating(random_disasters, interval=1800, first=450)         # كل 30 دقيقة
    jq.run_repeating(advance_projects, interval=60, first=10)            # كل دقيقة (لتقدم المشاريع)

    logger.info("✅ تم تفعيل جميع المهام الدورية (الاقتصاد، البورصة، الكوارث، المشاريع)")
