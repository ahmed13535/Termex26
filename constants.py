"""
constants.py – ثوابت اللعبة لبوت عصر الأمم
جميع القيم الثابتة في مكان واحد لسهولة التعديل.
"""

# ==============================
# ⏱️ فترات الانتظار (بالثواني)
# ==============================
ATTACK_COOLDOWN = 300          # 5 دقائق بين كل هجوم
WAR_COOLDOWN = 3600            # ساعة قبل إعلان حرب جديدة
STRAIT_BLOCK_COOLDOWN = 7200   # ساعتان لإغلاق المضيق
TAX_INTERVAL = 600             # جمع الضرائب كل 10 دقائق
GAME_LOOP_INTERVAL = 60        # دورة اللعبة كل دقيقة
STOCK_UPDATE_INTERVAL = 3600   # تحديث البورصة كل ساعة
DISASTER_INTERVAL = 1800       # كارثة عشوائية كل 30 دقيقة
PROJECT_ADVANCE_INTERVAL = 60  # تقدم المشاريع كل دقيقة

# ==============================
# 💰 الاقتصاد
# ==============================
BASE_INCOME = 1_000_000          # الدخل الأساسي للدورة
TAX_RATE = 0.15                  # نسبة الضريبة
SOLDIER_UPKEEP = 0.1             # تكلفة صيانة كل جندي
TANK_UPKEEP = 500                # تكلفة صيانة كل دبابة
AIRCRAFT_UPKEEP = 2_000          # تكلفة صيانة كل طائرة
STARTING_GOLD = 50_000_000       # الذهب الابتدائي
STARTING_FOOD = 10_000
STARTING_ENERGY = 5_000
STARTING_SOLDIERS = 10_000

# ==============================
# ⚔️ المعارك
# ==============================
MAX_RECRUIT_PER_CMD = 100_000    # أقصى عدد تجنيد بأمر واحد
SOLDIER_COST = 1_000             # تكلفة الجندي الواحد
OCCUPATION_XP_REWARD = 200       # XP عند الاحتلال
OCCUPATION_PRESTIGE = 500        # هيبة عند الاحتلال
LOOT_PERCENTAGE = 0.10           # نسبة النهب عند الاحتلال

# ==============================
# 🏗️ المباني
# ==============================
BUILDINGS = {
    "مزرعة":      {"cost": 500_000,    "food": 500,          "emoji": "🌾"},
    "مصنع":       {"cost": 2_000_000,  "production": 200,    "emoji": "🏭"},
    "بنك":        {"cost": 3_000_000,  "gold_bonus": 0.05,   "emoji": "🏦"},
    "حقل_نفط":   {"cost": 5_000_000,  "energy": 300,        "emoji": "🛢️"},
    "ثكنة":       {"cost": 1_000_000,  "recruit_bonus": 500, "emoji": "🏗️"},
    "مطار":       {"cost": 8_000_000,  "air_bonus": 2,       "emoji": "✈️"},
    "ميناء":      {"cost": 4_000_000,  "naval_bonus": 2,     "emoji": "⚓"},
    "مفاعل":      {"cost": 20_000_000, "energy": 2000,       "emoji": "☢️"},
    "مختبر":      {"cost": 15_000_000, "research": 100,      "emoji": "🧪"},
    "برج_دفاع":  {"cost": 3_000_000,  "defense_bonus": 0.15, "emoji": "🗼"},
}

# ==============================
# 🔫 الأسلحة (مصنفة)
# ==============================

# الأسلحة البرية
LAND_WEAPONS = {
    "جندي":          {"cost": 1_000,    "soldiers": 1,   "damage": 0.01,   "emoji": "👤",  "category": "land"},
    "دبابة":         {"cost": 80_000,   "soldiers": 25,  "damage": 0.30,   "emoji": "🚛",  "category": "land"},
    "مدفعية":        {"cost": 150_000,  "soldiers": 10,  "damage": 0.50,   "emoji": "💥",  "category": "land"},
    "قناص":          {"cost": 50_000,   "soldiers": 2,   "damage": 0.15,   "emoji": "🎯",  "category": "land"},
    "صاروخ_أرض_أرض": {"cost": 200_000,  "soldiers": 5,   "damage": 1.00,   "emoji": "🚀",  "category": "land"},
}

# الأسلحة الجوية
AIR_WEAPONS = {
    "طائرة_حربية":  {"cost": 500_000,   "soldiers": 5,   "damage": 1.20,   "emoji": "✈️",  "category": "air"},
    "طائرة_شبح":    {"cost": 900_000,   "soldiers": 3,   "damage": 1.80,   "emoji": "🛩️",  "category": "air"},
    "مسيّرة":        {"cost": 120_000,   "soldiers": 0,   "damage": 0.40,   "emoji": "🛸",  "category": "air"},
    "قاذفة":        {"cost": 700_000,   "soldiers": 8,   "damage": 2.00,   "emoji": "🛦",  "category": "air"},
    "دفاع_جوي":     {"cost": 400_000,   "soldiers": 20,  "defense": 0.80,  "emoji": "🛡️", "category": "air"},
}

# الأسلحة البحرية
NAVAL_WEAPONS = {
    "حاملة":         {"cost": 5_000_000,  "soldiers": 200, "damage": 3.00,  "emoji": "🚢", "category": "naval"},
    "غواصة":         {"cost": 2_000_000,  "soldiers": 50,  "damage": 2.50,  "emoji": "🌊", "category": "naval"},
    "مدمرة":         {"cost": 1_500_000,  "soldiers": 80,  "damage": 2.00,  "emoji": "⛵", "category": "naval"},
    "زورق_صواريخ":  {"cost": 600_000,    "soldiers": 20,  "damage": 1.00,  "emoji": "🛥️", "category": "naval"},
}

# الصواريخ الاستراتيجية
MISSILE_WEAPONS = {
    "صاروخ_باليستي":  {"cost": 800_000,   "soldiers": 0,  "damage": 3.00,  "emoji": "🚀", "category": "missile"},
    "صاروخ_فرط_صوتي": {"cost": 1_200_000, "soldiers": 0,  "damage": 4.50,  "emoji": "⚡", "category": "missile"},
    "صاروخ_كروز":     {"cost": 500_000,   "soldiers": 0,  "damage": 2.20,  "emoji": "💫", "category": "missile"},
    "دفاع_صاروخي":   {"cost": 2_000_000, "soldiers": 30, "defense": 1.50, "emoji": "🛡️", "category": "missile"},
}

# أسلحة الدمار الشامل
WMD_WEAPONS = {
    "رأس_نووي":       {"cost": 50_000_000, "soldiers": 0, "damage": 50.0, "emoji": "☢️", "category": "wmd",
                       "requires": {"مفاعل": 1, "مختبر": 1}},
    "سلاح_بيولوجي":  {"cost": 10_000_000, "soldiers": 0, "damage": 8.0,  "emoji": "☣️", "category": "wmd",
                       "requires": {"مختبر": 1}},
    "قنبلة_هيدروجينية": {"cost": 80_000_000, "soldiers": 0, "damage": 100.0, "emoji": "💣", "category": "wmd",
                           "requires": {"مفاعل": 2, "مختبر": 2}},
}

# دمج كل الأسلحة في قاموس واحد
WEAPONS = {**LAND_WEAPONS, **AIR_WEAPONS, **NAVAL_WEAPONS, **MISSILE_WEAPONS, **WMD_WEAPONS}

# Legacy mapping للتوافق مع الكود القديم
WEAPONS_LEGACY = {
    "جندي": WEAPONS["جندي"],
    "دبابة": WEAPONS["دبابة"],
    "مدفعية": WEAPONS["مدفعية"],
    "طائرة": WEAPONS["طائرة_حربية"],
    "صاروخ": WEAPONS["صاروخ_باليستي"],
    "دفاع_جوي": WEAPONS["دفاع_جوي"],
    "حاملة": WEAPONS["حاملة"],
    "غواصة": WEAPONS["غواصة"],
    "سلاح_بيولوجي": WEAPONS["سلاح_بيولوجي"],
    "رأس_نووي": WEAPONS["رأس_نووي"],
}

# ==============================
# 🌾 المحاصيل الزراعية
# ==============================
CROPS = {
    "قمح":    {"base_price": 500,   "growth_hours": 2, "emoji": "🌾"},
    "أرز":    {"base_price": 600,   "growth_hours": 3, "emoji": "🍚"},
    "بطاطا":  {"base_price": 400,   "growth_hours": 2, "emoji": "🥔"},
    "قهوة":   {"base_price": 1200,  "growth_hours": 6, "emoji": "☕"},
    "شاي":    {"base_price": 800,   "growth_hours": 4, "emoji": "🍃"},
    "طماطم":  {"base_price": 300,   "growth_hours": 1, "emoji": "🍅"},
    "ذرة":    {"base_price": 450,   "growth_hours": 2, "emoji": "🌽"},
    "زيتون":  {"base_price": 700,   "growth_hours": 5, "emoji": "🫒"},
}

# ==============================
# 📊 تصنيفات المتجر
# ==============================
SHOP_CATEGORIES = {
    "land":    {"name": "أسلحة برية",              "emoji": "🪖"},
    "air":     {"name": "أسلحة جوية",              "emoji": "✈️"},
    "naval":   {"name": "أسلحة بحرية",             "emoji": "⚓"},
    "missile": {"name": "صواريخ استراتيجية",       "emoji": "🚀"},
    "wmd":     {"name": "أسلحة دمار شامل",         "emoji": "☢️"},
    "crops":   {"name": "موارد زراعية ومحاصيل",    "emoji": "🌾"},
    "infra":   {"name": "بنية تحتية ومباني",       "emoji": "🏗️"},
}

# ==============================
# 🔔 أنواع الإشعارات
# ==============================
NOTIFICATION_TYPES = {
    "war_declared":       "إعلان حرب",
    "attacked":           "تعرض لهجوم",
    "disaster":           "كارثة طبيعية",
    "alliance_invite":    "دعوة حلف",
    "peace_offer":        "عرض سلام",
    "protection_offer":   "عرض حماية",
    "unfreeze":           "انتهاء تجميد",
    "project_complete":   "اكتمال مشروع",
    "stock_alert":        "تنبيه بورصة",
    "strait_blocked":     "مضيق مغلق",
    "truce_ending":       "انتهاء هدنة",
    "colony_revolt":      "ثورة مستعمرة",
}

# ==============================
# 🗺️ الخريطة
# ==============================
MAP_WIDTH = 1280
MAP_HEIGHT = 1280
FLAG_CACHE_SIZE = (20, 20)       # حجم الأعلام المخزنة مؤقتاً

# ==============================
# 🧠 المخابرات
# ==============================
SPY_BASE_COST = 500_000
SPY_SUCCESS_BASE = 0.60          # احتمالية النجاح الأساسية
SPY_DETECT_BASE = 0.25           # احتمالية الكشف الأساسية
SPY_OPERATIONS = {
    "تجسس على":   {"cost": 500_000,   "success": 0.70, "detect": 0.20, "emoji": "🔍"},
    "تخريب":      {"cost": 1_000_000, "success": 0.55, "detect": 0.35, "emoji": "💣"},
    "اغتيال":     {"cost": 2_000_000, "success": 0.40, "detect": 0.45, "emoji": "🗡️"},
    "زرع_عميل":   {"cost": 800_000,   "success": 0.50, "detect": 0.30, "emoji": "🕵️"},
}

# ==============================
# ☢️ المشاريع النووية والبيولوجية
# ==============================
ATOMIC_CYCLES_REQUIRED = 30      # عدد الدورات لإتمام القنبلة الذرية
HYDROGEN_CYCLES_REQUIRED = 60    # عدد الدورات للقنبلة الهيدروجينية
BIO_CYCLES_REQUIRED = 20         # دورات السلاح البيولوجي
TOXIN_CYCLES_REQUIRED = 15       # دورات السم القاتل

ATOMIC_COST_PER_CYCLE = 5_000_000
HYDROGEN_COST_PER_CYCLE = 10_000_000
BIO_COST_PER_CYCLE = 3_000_000
TOXIN_COST_PER_CYCLE = 2_000_000

# ==============================
# 📈 البورصة
# ==============================
STOCK_RESOURCES = ["قمح", "ذهب", "نفط", "حديد", "خشب", "قهوة", "شاي"]
STOCK_MIN_PRICE = 10.0
STOCK_MAX_PRICE = 1_000.0
STOCK_VOLATILITY = 0.15          # نسبة التذبذب القصوى

# ==============================
# 🌪️ الكوارث
# ==============================
DISASTERS = {
    "زلزال":        {"food_loss": 0.20, "gold_loss": 0.05, "soldier_loss": 0.05, "emoji": "🌋"},
    "فيضان":        {"food_loss": 0.35, "gold_loss": 0.10, "soldier_loss": 0.00, "emoji": "🌊"},
    "جفاف":         {"food_loss": 0.45, "gold_loss": 0.05, "soldier_loss": 0.00, "emoji": "🌵"},
    "وباء":         {"food_loss": 0.10, "gold_loss": 0.15, "soldier_loss": 0.15, "emoji": "🦠"},
    "عاصفة_رعدية": {"food_loss": 0.10, "gold_loss": 0.08, "soldier_loss": 0.02, "emoji": "⛈️"},
    "حريق_غابات":  {"food_loss": 0.25, "gold_loss": 0.07, "soldier_loss": 0.03, "emoji": "🔥"},
}

# ==============================
# 🔐 حد الطلبات (Rate Limiting)
# ==============================
RATE_LIMIT_ATTACKS_PER_MINUTE = 3    # أقصى هجمات في الدقيقة
RATE_LIMIT_BUYS_PER_MINUTE = 10      # أقصى عمليات شراء في الدقيقة
RATE_LIMIT_WINDOW = 60               # نافذة الحد (بالثواني)

# ==============================
# 🗺️ إحداثيات المدن (PROVINCES)
# ==============================
PROVINCES = {
    "ألمانيا": {
        "برلين":      {"px": 642, "py": 674},
        "ميونخ":      {"px": 790, "py": 605},
        "هامبورغ":    {"px": 571, "py": 735},
        "فرانكفورت":  {"px": 610, "py": 835},
        "كولونيا":    {"px": 698, "py": 752},
    },
    "فرنسا": {
        "باريس":      {"px": 406, "py": 806},
        "ليون":       {"px": 322, "py": 961},
        "مارسيليا":   {"px": 441, "py": 875},
        "بوردو":      {"px": 536, "py": 1052},
        "تولوز":      {"px": 303, "py": 831},
    },
    "النرويج": {
        "أوسلو":          {"px": 634, "py": 412},
        "بيرغن":          {"px": 804, "py": 345},
        "تروندهايم":      {"px": 812, "py": 237},
        "كريستيانساند":  {"px": 672, "py": 285},
    },
    "السويد": {
        "ستوكهولم":   {"px": 511, "py": 439},
        "غوتنبرغ":    {"px": 578, "py": 371},
        "مالمو":      {"px": 544, "py": 318},
        "أوبسالا":    {"px": 618, "py": 217},
    },
    "إسبانيا": {
        "مدريد":      {"px": 154, "py": 1127},
        "برشلونة":    {"px": 306, "py": 1050},
        "فالنسيا":    {"px": 155, "py": 1010},
        "إشبيلية":    {"px": 363, "py": 1138},
    },
    "إيطاليا": {
        "روما":       {"px": 629, "py": 1034},
        "ميلانو":     {"px": 536, "py": 1122},
        "نابولي":     {"px": 731, "py": 1107},
        "فينيسيا":    {"px": 538, "py": 937},
    },
    "المملكة المتحدة": {
        "لندن":       {"px": 306, "py": 670},
        "مانشستر":    {"px": 301, "py": 554},
        "إدنبرة":     {"px": 178, "py": 611},
    },
    "بولندا": {
        "وارسو":      {"px": 786, "py": 689},
        "كراكوف":     {"px": 939, "py": 582},
    },
    "المجر": {
        "بودابست":    {"px": 885, "py": 850},
        "كلوج":       {"px": 783, "py": 846},
    },
    "تركيا": {
        "اسطنبول":    {"px": 1033, "py": 1023},
        "أنقرة":      {"px": 1233, "py": 1052},
    },
    "اليونان": {
        "أثينا":      {"px": 1104, "py": 1027},
    },
    "البرتغال": {
        "لشبونة":     {"px": 70,  "py": 1058},
    },
    "فنلندا": {
        "هلسنكي":     {"px": 552, "py": 553},
    },
}
