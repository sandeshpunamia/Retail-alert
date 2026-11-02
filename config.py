"""Settings for the Reliance regulatory monitor. Edit freely - no code knowledge needed."""

# ---------- Stream 1: news on government action ----------
# Groups are checked in this order; an item goes to the FIRST group it matches.
# mode: "instant" = emailed every hour as it appears; "digest" = queued for the 4 daily digests.
ACTION_WORDS = ("raid OR raided OR seized OR sealed OR notice OR penalty OR fined OR \"show cause\" "
                "OR \"licence suspended\" OR \"license suspended\" OR crackdown OR inspection OR FSSAI "
                "OR \"Legal Metrology\" OR CCI OR CCPA OR \"consumer court\"")

def _q(brands):
    return "(" + " OR ".join(f'"{b}"' if " " in b else b for b in brands) + f") ({ACTION_WORDS})"

GROUPS = [
    {"key": "reliance", "label": "Reliance group", "mode": "instant", "email": "reliance",
     "brands": ["reliance retail", "jiomart", "reliance fresh", "reliance smart", "smart bazaar",
                "reliance trends", "reliance digital", "rcpl", "reliance consumer products",
                "reliance industries", "reliance jio mart", "freshpik", "ajio", "netmeds", "campa",
                "tira", "reliance market", "hamleys", "milkbasket", "urban ladder", "reliance brands"],
     "queries": [
        "Reliance Retail FSSAI raid", "Reliance Retail notice government",
        "JioMart FSSAI notice", "JioMart raid OR seized OR sealed",
        "Reliance Fresh FSSAI raid OR sealed OR notice", "Smart Bazaar FSSAI OR raid OR notice",
        "Reliance Smart Point FSSAI OR raid OR notice", "Reliance Retail Legal Metrology penalty",
        "Reliance Retail show cause notice", "Reliance Retail ED OR CCI OR GST notice",
        "RCPL Campa FSSAI OR notice OR penalty", "Reliance store licence suspended",
        "Reliance Retail consumer court order", "Reliance Digital OR Trends OR Ajio notice raid",
        "Tira Beauty notice OR raid OR CDSCO", "Hamleys OR Milkbasket OR Netmeds notice OR raid OR FSSAI"]},
    {"key": "quick", "label": "Quick commerce", "mode": "instant", "email": "competitor",
     "brands": ["zepto", "blinkit", "swiggy instamart", "instamart", "bigbasket", "big basket",
                "flipkart minutes", "amazon now", "dark store", "dark stores", "quick commerce"],
     "queries": [_q(["Zepto", "Blinkit"]), _q(["Instamart", "BigBasket"]),
                 "dark store FSSAI OR raid OR notice OR sealed", "quick commerce FSSAI OR CCI OR notice OR licence"]},
    {"key": "physical", "label": "Physical retail", "mode": "instant", "email": "competitor",
     "brands": ["dmart", "d-mart", "avenue supermarts", "more retail", "more supermarket", "more megastore",
                "spencer's", "spencers", "vishal mega mart", "star bazaar", "star market", "trent",
                "lulu hypermarket", "nature's basket", "easyday", "shoppers stop", "croma",
                "lifestyle stores", "pantaloons", "v-mart", "baskin"],
     "queries": [_q(["DMart", "Avenue Supermarts"]), _q(["More Retail", "Spencer's Retail"]),
                 _q(["Vishal Mega Mart", "Star Bazaar", "Lulu Hypermarket"]),
                 _q(["Shoppers Stop", "Croma", "Pantaloons", "Lifestyle stores"]),
                 "supermarket FSSAI raid OR sealed OR licence suspended", "hypermarket Legal Metrology penalty"]},
    {"key": "sector", "label": "Sector-wide action", "mode": "instant", "email": "competitor",
     "brands": ["e-commerce", "ecommerce", "retailers", "supermarkets", "food business operators",
                "online platforms", "food delivery", "retail chains"],
     "queries": ["FSSAI drive on e-commerce OR retailers OR supermarkets", "Legal Metrology e-commerce crackdown",
                 "CCPA notice e-commerce platforms", "CCI probe retail OR e-commerce OR quick commerce"]},
    {"key": "ecom", "label": "E-commerce", "mode": "digest", "email": "digest",
     "brands": ["amazon", "flipkart", "myntra", "meesho", "nykaa", "tata neu", "snapdeal", "jiomart"],
     "queries": [_q(["Amazon India", "Flipkart"]), _q(["Myntra", "Meesho"]), _q(["Tata Neu", "Snapdeal"])]},
    {"key": "beauty", "label": "Beauty (Tira competitors)", "mode": "digest", "email": "digest",
     "brands": ["nykaa", "purplle", "sephora", "health & glow", "mamaearth", "honasa", "sugar cosmetics",
                "lakme", "lakm\u00e9", "maybelline", "l'oreal", "loreal"],
     "generic": ["cosmetics", "cosmetic products", "cosmetic"],   # counted only if the story is Indian
     "queries": [_q(["Nykaa", "Purplle"]), _q(["Mamaearth", "Sugar Cosmetics", "Sephora India"]),
                 "cosmetics CDSCO OR raid OR seized OR spurious OR notice", "counterfeit cosmetics seized"]},
    {"key": "fmcg", "label": "FMCG (RCPL competitors)", "mode": "digest", "email": "digest",
     "brands": ["hul", "hindustan unilever", "nestle", "nestl\u00e9", "itc", "britannia", "p&g",
                "procter & gamble", "dabur", "marico", "tata consumer", "parle", "amul", "pepsico",
                "coca-cola", "coca cola", "mondelez", "patanjali", "godrej consumer", "awl agri",
                "adani wilmar", "haldiram", "mother dairy", "cadbury"],
     "queries": [_q(["Hindustan Unilever", "Nestle India"]), _q(["ITC", "Britannia", "Parle"]),
                 _q(["Dabur", "Marico", "Patanjali"]), _q(["Tata Consumer", "Amul", "Mother Dairy"]),
                 _q(["PepsiCo India", "Coca-Cola India", "Mondelez", "Haldiram"]),
                 "FMCG company FSSAI notice OR penalty OR recall OR ban"]},
]

ACTIONS = [
    "raid", "raided", "seized", "seizure", "sealed", "sealing", "notice", "show-cause",
    "show cause", "penalty", "fined", "fine", "licence suspended", "license suspended",
    "licence cancelled", "license cancelled", "inspection", "crackdown", "enforcement directorate",
    "gst", "cbi", "income tax", "cci", "ccpa", "banned", "prosecution", "adulterat",
    "unsafe", "misbranded", "legal metrology", "fssai", "fda", "cdsco",
    "consumer court", "summons", "probe", "investigation", "recall", "spurious", "counterfeit",
]
NEWS_MAX_AGE_HOURS = 48
FIRST_RUN_MAX_AGE_HOURS = 24   # first ever run: only last day, to avoid a flood
FIRST_RUN_CAP_PER_GROUP = 5
INDIA_TERMS = r"india|indian|cdsco|bis\b|fssai|delhi|mumbai|bengaluru|bangalore|chennai|kolkata|hyderabad|pune|gujarat|maharashtra|karnataka|tamil nadu|kerala|uttar pradesh|rajasthan|punjab|haryana|crore|lakh|\u20b9|rs\.?\s?\d"

# ---------- Stream 2: regulator notices and meeting minutes ----------
# direct = pages scraped for new links; gnews = Google News site: fallback query
REGULATORS = [
    {"name": "FSSAI",
     "direct": ["https://www.fssai.gov.in/advisories.php", "https://www.fssai.gov.in/notifications.php",
                "https://www.fssai.gov.in/orders.php", "https://www.fssai.gov.in/"],
     "gnews": ["site:fssai.gov.in notice OR order OR advisory OR meeting OR minutes"]},
    {"name": "FSSAI (CAG audit)",
     "direct": [],
     "gnews": ["CAG audit report FSSAI", "CAG FSSAI food safety audit observations"]},
    {"name": "Legal Metrology",
     "direct": ["https://consumeraffairs.nic.in/"],
     "gnews": ["Legal Metrology Department of Consumer Affairs notice OR amendment OR rules",
               "Legal Metrology Packaged Commodities Rules amendment"]},
    {"name": "CDSCO",
     "direct": ["https://cdsco.gov.in/opencms/opencms/en/Notifications/Public-Notices/",
                "https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Advisories_NO/"],
     "gnews": ["site:cdsco.gov.in notice OR circular OR minutes OR DTAB OR DCC",
               "CDSCO cosmetics notice OR rules OR labelling OR import registration"]},
    {"name": "DPIIT",
     "direct": ["https://www.dpiit.gov.in/"],
     "gnews": ["site:dpiit.gov.in press note OR notification OR consultation",
               "DPIIT retail trade notification OR consultation OR press note"]},
    {"name": "CPCB",
     "direct": ["https://cpcb.nic.in/"],
     "gnews": ["CPCB EPR plastic packaging notice OR direction OR guidelines",
               "site:cpcb.nic.in notice OR minutes OR direction"]},
]
NOTICE_WORDS = ["notice", "circular", "order", "advisory", "notification", "minutes", "meeting",
                "agenda", "press release", "press note", "guideline", "direction", "draft",
                "consultation", "amendment", "gazette", "regulation", "public notice", "dtab", "dcc"]
REG_MAX_AGE_DAYS = 14        # ignore anything older than this on first run
MAX_PDF_PAGES = 12

# Relevance scoring for Reliance Retail / FMCG
HIGH_WORDS = ["retail", "food business", "licence", "license", "label", "packaged", "labelling",
              "e-commerce", "epr", "plastic", "weighing", "legal metrology", "fmcg", "mrp",
              "expiry", "shelf life", "registration", "penalty", "prohibition", "ban", "import"]
MED_WORDS = ["manufactur", "standard", "testing", "sampling", "compliance", "deadline", "mandatory"]
