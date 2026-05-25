import logging
import re
import asyncio
from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from config import BOT_TOKEN
from database import init_db, get_user
from game_loop import setup_jobs
from handlers.start import get_conversation_handler, process_flag, confirm_country_callback, start_cmd
from handlers.map import map_handler, map_callback, status_handler
from handlers.economy import (economy_handler, build_menu_callback, build_action_callback,
                               build_handler, leaderboard_handler, confirm_build)
from handlers.shop import shop_handler, shop_callback, handle_custom_qty_message
from handlers.military import (military_handler, attack_handler, recruit_handler,
                                declare_war_callback, war_history_callback,
                                truce_handler, occupy_handler, confirm_attack)
from handlers.diplomacy import (diplomacy_handler, diplomacy_callback,
                                 create_alliance_handler, send_aid_handler)
from handlers.straits import (straits_handler, straits_callback,
                               close_strait_command, open_strait_command)
from handlers.admin import (
    admin_handler, admin_callback, admin_action_handler, admin_logs_callback,
    cmd_create_country, cmd_delete_country, cmd_transfer_ownership,
    cmd_grant_money, cmd_grant_army, cmd_grant_xp, cmd_grant_prestige,
    cmd_free_occupation, cmd_toggle_freeze, cmd_list_players, cmd_ban, cmd_unban,
    cmd_stigma, cmd_remove_stigma, cmd_game_stats, cmd_country_log,
    cmd_backup_game, cmd_restore_game, cmd_backup_flags, cmd_restore_flags,
    cmd_announce, cmd_set_announcements_topic, cmd_broadcast,
    cmd_pause_game, cmd_resume_game, cmd_pause_wars, cmd_resume_wars,
    cmd_activate_son, cmd_deactivate_group, cmd_list_groups,
    cmd_force_event, cmd_reset_game, cmd_confirm_reset
)
from handlers.intelligence import (
    intelligence_handler, spy_operation, counter_intelligence,
    fake_info, exposed_spies, fortify
)
from handlers.alliances import (
    create_alliance_handler, invite_alliance_handler, my_alliance_handler,
    leave_alliance_handler, kick_alliance_handler, dissolve_alliance_handler,
    alliance_attack_handler, alliance_army_handler, list_alliances_handler,
    alliances_callback
)
from handlers.nuclear_bio import (
    nuclear_status_handler, enrich_atomic_handler, enrich_hydrogen_handler,
    cancel_enrich_handler, drop_atomic_handler, drop_hydrogen_handler,
    bio_status_handler, develop_bio_handler, develop_toxin_handler,
    use_bio_handler, use_toxin_handler
)
from handlers.stock_market import (
    stock_market_handler, buy_stock_handler, sell_stock_handler,
    my_portfolio_handler, stock_callback
)
from handlers.disasters import (
    trigger_random_disaster, targeted_disaster_handler
)
from handlers.advanced_shop import (
    market_handler, shop_callback as advanced_shop_callback,
    harvest_all_crops, harvest_crop_handler, my_inventory_handler, harvest_all_callback
)
from handlers.infrastructure import (
    infrastructure_handler, upgrade_infra_callback, infra_stats_callback,
    back_to_infra_callback, build_infrastructure_command
)
from handlers.colonization import (
    invade_handler, merge_handler, colonize_handler, harvest_empire_handler,
    revolt_handler, independence_handler, gift_colony_handler
)
from handlers.invasion import (
    invasion_handler, attack_city_handler, merge_city_handler
)

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================================ الأنماط العربية الموسعة ================================
ARABIC_PATTERNS = [
    # أزرار القائمة الرئيسية (مع إيموجي أو بدونه)
    (r"^🗺\s*خريطة$", "map"),
    (r"^خريطة$", "map"),
    (r"^📊\s*حالتي$", "status"),
    (r"^حالتي$", "status"),
    (r"^💰\s*اقتصاد$", "economy"),
    (r"^اقتصاد$", "economy"),
    (r"^⚔️\s*عسكري$", "military"),
    (r"^عسكري$", "military"),
    (r"^🤝\s*دبلوماسية$", "diplomacy"),
    (r"^دبلوماسية$", "diplomacy"),
    (r"^🏪\s*متجر$", "shop"),
    (r"^متجر$", "shop"),
    (r"^🏆\s*ترتيب$", "leaderboard"),
    (r"^ترتيب$", "leaderboard"),
    (r"^🌊\s*مضائق$", "straits"),
    (r"^مضائق$", "straits"),
    (r"^📋\s*مساعدة$", "help"),
    (r"^مساعدة$", "help"),

    # البداية والمعلومات
    (r"^انضم$", "join"),
    (r"^كودي$", "my_code"),
    (r"^تغيير اسم دولتي\s+(.+)$", "rename_country"),
    (r"^علم دولتي$", "set_flag"),
    (r"^دولتي$|^دولي$", "my_country"),
    (r"^دولته$", "his_country"),
    (r"^قائمة الدول$", "countries_list"),
    (r"^إحصائيات اللعبة$", "game_stats"),
    (r"^إحصائياتي$", "my_stats"),
    (r"^جيران$", "neighbors"),
    (r"^رتبتي$", "my_rank"),
    (r"^سجل حروبي$", "war_log"),

    # الاقتصاد
    (r"^جمع الضرائب$", "collect_tax"),
    (r"^بناء مزرعة$|^بناء مزرعة\s+(.+)$", "build_farm"),
    (r"^بناء منشاة\s*(.*)$", "build_facility"),
    (r"^بناء بنية تحتية$", "build_infrastructure"),
    (r"^العاصمة\s+(.+)$", "set_capital"),
    (r"^تحويل\s+(\d+)\s+(\S+)$", "transfer"),
    (r"^البنك الدولي$", "world_bank"),
    (r"^ديوني$", "my_debts"),
    (r"^مهرجان شعبي$", "festival"),
    (r"^خزنتي$", "my_treasury"),

    # الجيش والحرب
    (r"^تجنيد\s+(\d+)$", "recruit"),
    (r"^اعلن حرب علي\s+(.+)$", "declare_war"),
    (r"^هجوم علي\s+(.+)$", "attack"),
    (r"^غزو\s+(.+)$", "invasion"),
    (r"^دمج\s+(.+)$", "merge_city"),

    # المشروع النووي والبيولوجي
    (r"^مشروعي النووي$", "my_nuclear"),
    (r"^تخصيب قنبلة_ذرية$", "enrich_atomic"),
    (r"^تخصيب قنبلة_هيدروجينية$", "enrich_hydrogen"),
    (r"^إلغاء تخصيب$", "cancel_enrich"),
    (r"^اضرب قنبلة_ذرية\s+(.+)$", "drop_atomic"),
    (r"^اضرب قنبلة_هيدروجينية\s+(.+)$", "drop_hydrogen"),
    (r"^مشروعي البيولوجي$", "my_bio"),
    (r"^تطوير سلاح_بيولوجي$", "develop_bio"),
    (r"^تطوير سم_قاتل$", "develop_toxin"),
    (r"^استخدم سلاح_بيولوجي\s+(.+)$", "use_bio"),
    (r"^استخدم سم_قاتل\s+(.+)$", "use_toxin"),

    # المتجر والمحاصيل
    (r"^شراء\s+(\S+)\s+(\d+)$", "buy_weapon"),
    (r"^مزرعتي$", "my_farm"),
    (r"^حصاد محصول\s+(.+)$", "harvest_crop"),
    (r"^حصاد الكل$", "harvest_all"),

    # الغزو والاستعمار القديم
    (r"^استعمر\s+(.+)$", "colonize"),
    (r"^احصد دولي$", "harvest_empire"),
    (r"^ثورة$", "revolt"),
    (r"^استقلال$", "independence"),
    (r"^اهدي مستعمرة\s+(.+)$", "gift_colony"),

    # الدبلوماسية
    (r"^معاهدة سلام مع\s+(.+)$", "peace_treaty"),
    (r"^احمي\s+(.+)$", "protect"),
    (r"^قبول الحماية$", "accept_protection"),
    (r"^رفض الحماية$", "reject_protection"),
    (r"^الغاء الحماية$", "remove_protection"),

    # المخابرات
    (r"^مخابراتي$", "intelligence"),
    (r"^تجسس علي\s+(.+)$", "spy"),
    (r"^تخريب\s+(.+)$", "sabotage"),
    (r"^اغتيال\s+(.+)$", "assassinate"),
    (r"^زرع عميل\s+(.+)$", "infiltrate"),
    (r"^مضادة تجسس$", "counter_intel"),
    (r"^معلومات مزيفة$", "fake_info"),
    (r"^جواسيس مكشوفون$", "exposed_spies"),
    (r"^تحصين$", "fortify"),

    # البنية التحتية
    (r"^بنية تحتية$", "infrastructure"),

    # البورصة
    (r"^بورصة$", "stock_market"),
    (r"^شراء أسهم\s+(\S+)\s+(\d+)$", "buy_stock"),
    (r"^بيع أسهم\s+(\S+)\s+(\d+)$", "sell_stock"),
    (r"^محفظتي$", "my_portfolio"),

    # الأحلاف
    (r"^انشاء حلف\s+(.+)$", "create_alliance"),
    (r"^دعوه\s+(\S+)\s+(\S+)$", "invite_alliance"),
    (r"^حلفي$", "my_alliance"),
    (r"^جيش الحلف\s+(.+)$", "alliance_army"),
    (r"^قائمة الاحلاف$|^الاحلاف$", "alliances_list"),
    (r"^هجوم جماعي\s+(\S+)\s+علي\s+(.+)$", "alliance_attack"),
    (r"^مغادره حلف\s+(.+)$", "leave_alliance"),
    (r"^اطرد\s+(\S+)\s+من\s+(\S+)$", "kick_from_alliance"),
    (r"^حل حلف\s+(.+)$", "dissolve_alliance"),

    # المضائق
    (r"^اغلق مضيق\s+(.+)$", "close_strait"),
    (r"^افتح مضيق\s+(.+)$", "open_strait"),

    # أوامر الأدمن
    (r"^اللاعبين$", "admin_list_players"),
    (r"^منح مثاقيل\s+(.+)$", "admin_grant_money"),
    (r"^منح جيش\s+(.+)$", "admin_grant_army"),
    (r"^منح xp\s+(.+)$", "admin_grant_xp"),
    (r"^منح هيبة\s+(.+)$", "admin_grant_prestige"),
    (r"^تجميد\s+(.+)$", "admin_freeze"),
    (r"^فك احتلال\s+(.+)$", "admin_free_occupation"),
    (r"^حذف دولة (.+)$", "admin_delete_country"),
    (r"^منح ملكية\s+(.+)$", "admin_transfer"),
    (r"^بان\s+(.+)$", "admin_ban"),
    (r"^رفع بان\s+(.+)$", "admin_unban"),
    (r"^وصمة\s+(.+)$", "admin_stigma"),
    (r"^رفع وصمة\s+(.+)$", "admin_remove_stigma"),
    (r"^سجل\s+(.+)$", "admin_country_log"),
    (r"^احصائيات الان$", "admin_stats_now"),
    (r"^اعلان\s+(.+)$", "admin_broadcast"),
    (r"^نشر\s+(.+)$", "admin_announce"),
    (r"^توبيك الاعلانات\s+(.+)$", "admin_set_topic"),
    (r"^تفعيل SoN$", "admin_activate_son"),
    (r"^إلغاء تفعيل\s+(.+)$", "admin_deactivate_group"),
    (r"^الجروبات$", "admin_list_groups"),
    (r"^تسريع الكوارث\s*(.*)$", "admin_force_event"),
    (r"^وقف اللعبة$", "admin_pause_game"),
    (r"^شغل اللعبة$", "admin_resume_game"),
    (r"^اقفل الحروب$", "admin_pause_wars"),
    (r"^افتح الحروب$", "admin_resume_wars"),
    (r"^حفظ اللعبة$", "admin_backup_game"),
    (r"^استعادة اللعبة$", "admin_restore_game"),
    (r"^حفظ الاعلام$", "admin_backup_flags"),
    (r"^استعادة الاعلام$", "admin_restore_flags"),
    (r"^اعادة اللعبة$", "admin_reset_game"),
    (r"^confirm_reset$", "admin_confirm_reset"),

    # المساعدة
    (r"^مساعدة$|^مساعده$|^help$|^الاوامر$", "help"),
]

# ================================ دوال مساعدة ================================
async def not_implemented_yet(update: Update, context: ContextTypes.DEFAULT_TYPE, feature_name: str):
    await update.message.reply_text(f"⚠️ *ميزة `{feature_name}` قيد التطوير حاليًا وستتوفر قريبًا.*", parse_mode="Markdown")

from bot_filters import admin_reply_only

# ================================ معالج تفعيل SoN (بلا فلتر — يعمل دائماً) ================================
async def activate_son_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعالج 'تفعيل SoN' مباشرةً بغض النظر عن أي فلتر — حتى في المجموعات غير المفعّلة."""
    from handlers.admin import is_admin, cmd_activate_son, cmd_deactivate_group
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    text = (update.message.text or "").strip()
    if text == "تفعيل SoN":
        await cmd_activate_son(update, context)
    elif text.startswith("إلغاء تفعيل"):
        parts = text.split()
        context.args = parts[2:] if len(parts) > 2 else []
        await cmd_deactivate_group(update, context)

# ================================ معالج الرسائل الذكي ================================
@admin_reply_only
async def smart_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    # حالات خاصة
    if context.user_data.get("awaiting_flag"):
        await process_flag(update, context)
        return
    if context.user_data.get("awaiting_alliance_name"):
        await create_alliance_handler(update, context)
        return
    from handlers.admin import is_admin
    if context.user_data.get("admin_action") and is_admin(user_id):
        await admin_action_handler(update, context)
        return
    # كمية مخصصة للمتجر
    if await handle_custom_qty_message(update, context):
        return

    matched = False
    for pattern, command in ARABIC_PATTERNS:
        m = re.match(pattern, text, re.IGNORECASE)
        if m:
            matched = True
            groups = [g for g in m.groups() if g is not None]

            # تنفيذ الأوامر
            if command == "join":
                await start_cmd(update, context)
            elif command == "my_code":
                user = await get_user(user_id)
                await update.message.reply_text(f"🔑 *كودك:* `{user['user_id']}`" if user else "ليس لديك دولة بعد.", parse_mode="Markdown")
            elif command == "set_flag":
                await update.message.reply_text("🏳️ *أرسل صورة علمك*", parse_mode="Markdown")
                context.user_data["awaiting_flag"] = True
            elif command == "my_country":
                user = await get_user(user_id)
                if user:
                    await update.message.reply_text(f"🌍 *دولتك:* {user['country']}\n🏛️ *العاصمة:* {user['capital']}", parse_mode="Markdown")
                else:
                    await update.message.reply_text("لا يوجد دولة مسجلة لك.")
            elif command == "map":
                await map_handler(update, context)
            elif command == "leaderboard":
                await leaderboard_handler(update, context)
            elif command == "straits":
                await straits_handler(update, context)
            elif command == "my_stats":
                await status_handler(update, context)
            elif command == "war_log":
                await war_history_callback(update, context)
            elif command == "collect_tax":
                await update.message.reply_text("💰 *تم جمع الضرائب!* سيتم إضافتها تلقائياً.", parse_mode="Markdown")
            elif command in ("build_farm", "build_facility"):
                await build_handler(update, context)
            elif command == "build_infrastructure":
                await build_infrastructure_command(update, context)
            elif command == "transfer":
                await send_aid_handler(update, context)
            elif command == "my_treasury":
                user = await get_user(user_id)
                if user:
                    await update.message.reply_text(f"💰 *خزينتك:* `{user['gold']:,.0f} ¥`", parse_mode="Markdown")
            elif command == "recruit":
                context.args = [groups[0]]
                await recruit_handler(update, context)
            elif command == "declare_war" or command == "attack":
                context.args = [groups[0]]
                await attack_handler(update, context)
            elif command == "invasion":
                context.args = [groups[0]]
                await invasion_handler(update, context)
            elif command == "merge_city":
                context.args = [groups[0]]
                await merge_city_handler(update, context)
            elif command == "my_nuclear":
                await nuclear_status_handler(update, context)
            elif command == "enrich_atomic":
                await enrich_atomic_handler(update, context)
            elif command == "enrich_hydrogen":
                await enrich_hydrogen_handler(update, context)
            elif command == "cancel_enrich":
                await cancel_enrich_handler(update, context)
            elif command == "drop_atomic":
                context.args = [groups[0]]
                await drop_atomic_handler(update, context)
            elif command == "drop_hydrogen":
                context.args = [groups[0]]
                await drop_hydrogen_handler(update, context)
            elif command == "my_bio":
                await bio_status_handler(update, context)
            elif command == "develop_bio":
                await develop_bio_handler(update, context)
            elif command == "develop_toxin":
                await develop_toxin_handler(update, context)
            elif command == "use_bio":
                context.args = [groups[0]]
                await use_bio_handler(update, context)
            elif command == "use_toxin":
                context.args = [groups[0]]
                await use_toxin_handler(update, context)
            elif command == "shop":
                await shop_handler(update, context)
            elif command == "market":
                await market_handler(update, context)
            elif command == "my_farm":
                await update.message.reply_text("🌾 *لعرض محاصيلك، استخدم الزر 📊 مخزني داخل المتجر.*", parse_mode="Markdown")
            elif command == "harvest_crop":
                context.args = [groups[0]]
                await harvest_crop_handler(update, context)
            elif command == "harvest_all":
                user = await get_user(user_id)
                if user:
                    await harvest_all_crops(update, user)
            elif command == "colonize":
                context.args = [groups[0]]
                await colonize_handler(update, context)
            elif command == "harvest_empire":
                await harvest_empire_handler(update, context)
            elif command == "revolt":
                await revolt_handler(update, context)
            elif command == "independence":
                await independence_handler(update, context)
            elif command == "gift_colony":
                context.args = text.split()[2:]
                await gift_colony_handler(update, context)
            elif command == "intelligence":
                await intelligence_handler(update, context)
            elif command == "spy":
                context.args = [groups[0]]
                await spy_operation(update, context, "تجسس على")
            elif command == "sabotage":
                context.args = [groups[0]]
                await spy_operation(update, context, "تخريب")
            elif command == "assassinate":
                context.args = [groups[0]]
                await spy_operation(update, context, "اغتيال")
            elif command == "counter_intel":
                await counter_intelligence(update, context)
            elif command == "fake_info":
                await fake_info(update, context)
            elif command == "exposed_spies":
                await exposed_spies(update, context)
            elif command == "fortify":
                await fortify(update, context)
            elif command == "infrastructure":
                await infrastructure_handler(update, context)
            elif command == "stock_market":
                await stock_market_handler(update, context)
            elif command == "buy_stock":
                context.args = [groups[0], groups[1]]
                await buy_stock_handler(update, context)
            elif command == "sell_stock":
                context.args = [groups[0], groups[1]]
                await sell_stock_handler(update, context)
            elif command == "my_portfolio":
                await my_portfolio_handler(update, context)
            elif command == "create_alliance":
                context.args = [text.split()[2]] if len(text.split()) > 2 else []
                await create_alliance_handler(update, context)
            elif command == "invite_alliance":
                context.args = [groups[0], groups[1]]
                await invite_alliance_handler(update, context)
            elif command == "my_alliance":
                await my_alliance_handler(update, context)
            elif command == "alliance_army":
                context.args = [groups[0]]
                await alliance_army_handler(update, context)
            elif command == "alliances_list":
                await list_alliances_handler(update, context)
            elif command == "alliance_attack":
                context.args = [groups[0], groups[1]]
                await alliance_attack_handler(update, context)
            elif command == "leave_alliance":
                context.args = [groups[0]]
                await leave_alliance_handler(update, context)
            elif command == "kick_from_alliance":
                await not_implemented_yet(update, context, "طرد من حلف")
            elif command == "dissolve_alliance":
                context.args = [groups[0]]
                await dissolve_alliance_handler(update, context)
            elif command == "close_strait":
                context.args = [groups[0]]
                await close_strait_command(update, context)
            elif command == "open_strait":
                context.args = [groups[0]]
                await open_strait_command(update, context)
            elif command == "admin_list_players":
                await cmd_list_players(update, context)
            elif command == "admin_grant_money":
                context.args = text.split()[2:] if len(text.split()) > 2 else []
                await cmd_grant_money(update, context)
            elif command == "admin_grant_army":
                context.args = text.split()[2:] if len(text.split()) > 2 else []
                await cmd_grant_army(update, context)
            elif command == "admin_grant_xp":
                context.args = text.split()[2:] if len(text.split()) > 2 else []
                await cmd_grant_xp(update, context)
            elif command == "admin_grant_prestige":
                context.args = text.split()[2:] if len(text.split()) > 2 else []
                await cmd_grant_prestige(update, context)
            elif command == "admin_freeze":
                context.args = text.split()[1:]
                await cmd_toggle_freeze(update, context)
            elif command == "admin_free_occupation":
                context.args = text.split()[2:] if len(text.split()) > 2 else []
                await cmd_free_occupation(update, context)
            elif command == "admin_delete_country":
                country_part = text[9:].strip()
                context.args = [country_part]
                await cmd_delete_country(update, context)
            elif command == "admin_transfer":
                context.args = text.split()[2:] if len(text.split()) > 2 else []
                await cmd_transfer_ownership(update, context)
            elif command == "admin_ban":
                context.args = text.split()[1:]
                await cmd_ban(update, context)
            elif command == "admin_unban":
                context.args = text.split()[1:]
                await cmd_unban(update, context)
            elif command == "admin_stigma":
                context.args = text.split()[1:]
                await cmd_stigma(update, context)
            elif command == "admin_remove_stigma":
                context.args = text.split()[1:]
                await cmd_remove_stigma(update, context)
            elif command == "admin_country_log":
                context.args = text.split()[1:]
                await cmd_country_log(update, context)
            elif command == "admin_stats_now":
                await cmd_game_stats(update, context)
            elif command == "admin_broadcast":
                context.args = text.split()[1:]
                await cmd_broadcast(update, context)
            elif command == "admin_announce":
                context.args = text.split()[1:]
                await cmd_announce(update, context)
            elif command == "admin_set_topic":
                context.args = text.split()[1:]
                await cmd_set_announcements_topic(update, context)
            elif command == "admin_activate_son":
                await cmd_activate_son(update, context)
            elif command == "admin_deactivate_group":
                context.args = text.split()[1:]
                await cmd_deactivate_group(update, context)
            elif command == "admin_list_groups":
                await cmd_list_groups(update, context)
            elif command == "admin_force_event":
                if groups and groups[0]:
                    context.args = [groups[0]]
                    await targeted_disaster_handler(update, context)
                else:
                    await cmd_force_event(update, context)
            elif command == "admin_pause_game":
                await cmd_pause_game(update, context)
            elif command == "admin_resume_game":
                await cmd_resume_game(update, context)
            elif command == "admin_pause_wars":
                await cmd_pause_wars(update, context)
            elif command == "admin_resume_wars":
                await cmd_resume_wars(update, context)
            elif command == "admin_backup_game":
                await cmd_backup_game(update, context)
            elif command == "admin_restore_game":
                await cmd_restore_game(update, context)
            elif command == "admin_backup_flags":
                await cmd_backup_flags(update, context)
            elif command == "admin_restore_flags":
                await cmd_restore_flags(update, context)
            elif command == "admin_reset_game":
                await cmd_reset_game(update, context)
            elif command == "admin_confirm_reset":
                await cmd_confirm_reset(update, context)
            elif command == "help":
                await help_handler(update, context)
            else:
                await not_implemented_yet(update, context, command)
            break

    if not matched:
        user = await get_user(user_id)
        if user and text not in ("", "/"):
            await update.message.reply_text(
                f"❓ *لم أفهم الأمر:* `{text}`\n💡 اكتب `مساعدة` لعرض الأوامر المتاحة",
                parse_mode="Markdown"
            )

# ================================ معالج الصور ================================
@admin_reply_only
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_flag"):
        await process_flag(update, context)
    else:
        await update.message.reply_text("📸 *لم أتوقع صورة.* إذا كنت تريد رفع علمك، ابدأ التسجيل بـ `/start`", parse_mode="Markdown")

# ================================ دالة المساعدة ================================
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 *أوامر عصر الأمم*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎮 *البداية:*\n  `انضم` – بدء التسجيل\n  `كودي` – عرض كودك\n  `علم دولتي` – رفع صورة العلم\n\n"
        "📊 *المعلومات:*\n  `دولتي`، `خريطة`، `المتصدرين`، `المضائق`، `إحصائياتي`، `سجل حروبي`\n\n"
        "💰 *الاقتصاد:*\n  `جمع الضرائب`، `بناء مزرعة`، `بناء منشاة`، `بناء بنية تحتية`، `تحويل [مبلغ] [كود]`، `خزنتي`\n\n"
        "⚔️ *الجيش والحرب:*\n  `تجنيد [عدد]`، `اعلن حرب علي [دولة]`، `هجوم علي [دولة]`، `غزو [دولة]`، `دمج [مدينة]`\n\n"
        "☢️ *المشروع النووي:*\n  `مشروعي النووي`، `تخصيب قنبلة_ذرية`، `اضرب قنبلة_ذرية [دولة]`\n\n"
        "🧬 *المشروع البيولوجي:*\n  `مشروعي البيولوجي`، `تطوير سلاح_بيولوجي`، `استخدم سلاح_بيولوجي [دولة]`\n\n"
        "🏪 *المتجر:*\n  `متجر` – متجر الأسلحة والمحاصيل والمباني والحصون\n  `مزرعتي` – لمتابعة المحاصيل\n  `حصاد محصول [الاسم]`\n\n"
        "🏴 *الغزو والاستعمار:*\n  `استعمر [دولة]`، `احصد دولي`، `ثورة`، `استقلال`\n\n"
        "🤝 *الدبلوماسية والأحلاف:*\n  `انشاء حلف [اسم]`، `حلفي`، `دعوه [حلف] [دولة]`، `هجوم جماعي [حلف] علي [دولة]`\n\n"
        "🕵️ *المخابرات:*\n  `مخابراتي`، `تجسس علي [دولة]`، `تخريب [دولة]`، `اغتيال [دولة]`، `تحصين`\n\n"
        "📈 *البورصة:*\n  `بورصة`، `شراء أسهم [مورد] [عدد]`، `بيع أسهم [مورد] [عدد]`، `محفظتي`\n\n"
        "🏗️ *البنية التحتية:*\n  `بنية تحتية` – عرض وترقية السعات\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ *الأدمن:* `/admin` – لوحة التحكم\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *بعض الأوامر قيد التطوير، للمزيد استخدم المساعدة داخل اللعبة.*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ================================ معالج الكول باك ================================
async def all_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    # أزرار الرجوع
    if data in ("economy_back", "diplomacy_back", "military_back", "back_to_infra", "back_to_main_shop", "admin_back", "market_back"):
        if data == "economy_back":
            await economy_handler(update, context)
        elif data == "diplomacy_back":
            await diplomacy_handler(update, context)
        elif data == "military_back":
            await military_handler(update, context)
        elif data == "back_to_infra":
            await infrastructure_handler(update, context)
        elif data in ("back_to_main_shop", "market_back"):
            await market_handler(update, context)
        elif data == "admin_back":
            await admin_handler(update, context)
        return

    # أزرار الغزو
    if data.startswith("invade_city_"):
        await attack_city_handler(update, context)
        return

    # ── أزرار المتجر الإمبراطوري الجديد ──
    if data.startswith("s_"):
        await shop_callback(update, context)
        return

    # أزرار المتجر المتقدم (legacy)
    if data.startswith("market_") or data.startswith("buy_") or data.startswith("confirm_") or data.startswith("custom_") or data in ("my_inventory", "harvest_all"):
        await advanced_shop_callback(update, context)
        return

    # أزرار البورصة
    if data in ("refresh_stocks", "my_portfolio"):
        await stock_callback(update, context)
        return

    # أزرار الأحلاف
    if data.startswith("accept_invite_") or data == "decline_invite":
        await alliances_callback(update, context)
        return

    # أزرار البنية التحتية
    if data == "upgrade_infra":
        await upgrade_infra_callback(update, context)
    elif data == "infra_stats":
        await infra_stats_callback(update, context)

    # أزرار الخريطة والاقتصاد والحروب
    elif data in ("refresh_map", "full_map", "my_status"):
        await map_callback(update, context)
    elif data in ("build_menu", "upgrade_menu", "harvest", "bank_menu", "economy_back"):
        await build_menu_callback(update, context)
    elif data.startswith("build_"):
        await build_action_callback(update, context)
    elif data.startswith("confirm_build_"):
        await confirm_build(update, context)
    elif data in ("war_menu", "defensive_mode", "truce_menu", "war_history", "military_back"):
        if data == "war_menu":
            await declare_war_callback(update, context)
        elif data == "war_history":
            await war_history_callback(update, context)
        else:
            await query.edit_message_text("⚙️ *هذه الخاصية قيد التطوير*", parse_mode="Markdown")
    elif data.startswith("declare_war_"):
        country = data.replace("declare_war_", "")
        context.args = [country]
        await attack_handler(update, context)
    elif data.startswith("confirm_attack_"):
        await confirm_attack(update, context)

    # أزرار الدبلوماسية والمضائق والأدمن
    elif data.startswith(("create_alliance", "alliance_members", "peace_menu", "peace_",
                           "diplomatic_status", "alliance_council", "diplomacy_back")):
        await diplomacy_callback(update, context)
    elif data.startswith(("block_strait_", "open_strait_")):
        await straits_callback(update, context)
    elif data.startswith(("confirm_country_", "restart_country")):
        await confirm_country_callback(update, context)
    elif data.startswith("admin_"):
        if data == "admin_logs":
            await admin_logs_callback(update, context)
        else:
            await admin_callback(update, context)
    else:
        await query.edit_message_text("⚠️ *هذا الزر غير مفعل حالياً.*", parse_mode="Markdown")

# ================================ التشغيل الرئيسي ================================
async def run():
    await init_db()
    logger.info("✅ Database initialized")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(get_conversation_handler())
    app.add_handler(CommandHandler("start", admin_reply_only(start_cmd)))
    app.add_handler(CommandHandler("map", admin_reply_only(map_handler)))
    app.add_handler(CommandHandler("status", admin_reply_only(status_handler)))
    app.add_handler(CommandHandler("economy", admin_reply_only(economy_handler)))
    app.add_handler(CommandHandler("military", admin_reply_only(military_handler)))
    app.add_handler(CommandHandler("shop", admin_reply_only(shop_handler)))
    app.add_handler(CommandHandler("diplomacy", admin_reply_only(diplomacy_handler)))
    app.add_handler(CommandHandler("straits", admin_reply_only(straits_handler)))
    app.add_handler(CommandHandler("leaderboard", admin_reply_only(leaderboard_handler)))
    app.add_handler(CommandHandler("admin", admin_reply_only(admin_handler)))
    app.add_handler(CommandHandler("help", admin_reply_only(help_handler)))
    app.add_handler(CallbackQueryHandler(all_callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    # معالج تفعيل SoN — بلا فلتر، يُسجَّل قبل smart_message_handler حتى يعمل دائماً
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"^(تفعيل SoN|إلغاء تفعيل.*)$"),
        activate_son_direct
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, smart_message_handler))

    setup_jobs(app)
    logger.info("🚀 *عصر الأمم* – البوت يعمل الآن!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    finally:
        loop.close()
