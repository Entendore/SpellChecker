#!/usr/bin/env python3
"""
Database Initialization Script for Advanced NLP Text Corrector
================================================================
Creates isolated SQLite databases for 20 languages within their own
folders in the Current Working Directory (CWD).

Categories Included:
  - Core: English, Spanish, German, French, Italian
  - Asian: Hindi, Japanese (Romaji), Mandarin (Pinyin), Korean (Romanized), Vietnamese
  - African: Swahili, Zulu, Yoruba, Amharic (Romanized), Hausa
  - Native American: Navajo, Quechua, Cherokee (Romanized), Ojibwe, Inuktitut (Romanized)

Folder Structure Generated:
  ./en/en.db, ./es/es.db, ./de/de.db, ... , ./iu/iu.db
"""

import os
import logging
import sqlite3
from datetime import datetime
from collections import Counter

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Logging Configuration
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("DB_Init")

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Seed Dictionaries (Curated Lists)
# ═══════════════════════════════════════════════════════════════════
# Note: Words are stored as Lists to perfectly preserve diacritics, 
# glottal stops (') , and avoid tokenization errors during DB seeding.

SEED_MAP = {
    # --- Core Languages ---
    "en": "a able about above accept across act actually add afraid after afternoon again against age ago agree air all almost along already also always am among an and anger animal answer ant any anybody anymore anything anyplace anyway apart apartment appear apple are area arm army around arrive art as ask at attack attempt attend august aunt author autumn available away baby back bad bag ball ban band bank bar base basic basis bath be beach bean bear beat beautiful became because become bed been before began begin behind being believe bell belong below beside best better between beyond big bill bird birth bit bite black blame blank block blood blow blue board boat body bomb bond bone book border born both bother bottle bottom bound box boy brain branch brave bread break breath bridge brief bright bring broad broke brother brown brush build building burn bus business busy but buy by cabin cage cake call calm came camera camp can cap capital captain capture car card care careful carry case cash cast cat catch cause cell center central century certain chain chair chairman challenge champion chance change channel chapter character charge charm chart chase cheap check cheek cheese chest chicken chief child childhood chin chip choice choose church circle citizen city civil claim class clean clear click client climb clinical clock close cloth clothes cloud club clue cluster coach coal coast coat code coffee cold collar collect college colony color column combination come comfort command comment commit common communicate community company compare competition complete complex computer concern condition conduct confirm congress connect consider contact contain content contest continue control conversation cook cool cooperation copy core corner corporate correct cost could count counter country county couple courage course court cousin cover crack craft crash crazy cream create crime criminal crisis criteria critical crop cross crowd crucial cry cultural cup cure curious current curve custom customer cut cycle".split(),
    
    "es": "a al ahora algo algunos ante antes apellido aquél aquí así aunque año años cada casi caso casa cine ciudad como con conocer creo cual cuando de del desde donde dos él ella ellos en entre era es esa ese eso esta estado estos está estoy esto euro ejemplo el ella ellos embargo en entre era eres esa ese esto esto están estaban estar estas este estoy fin fue fuera gran ha habíamos haber hace hacer habían hasta hay hoy la las le les lo los me mi mismo mucho muy más mí mío nada ni no nos nosotras nosotros nuestra nuevo o otra otro otros para parte pasar pero poco por porque primero puede cuando que quien qué se sea señora señor si sí siempre sobre solo somos su sus suyo sí también tan tanto te tienen tengo ti tiene todo tu tú un una unas uno unos usted ustedes va van veces ver vez y ya yo él caminar camina caminé escuela compra manzana está mesa ayer".split(),
    
    "de": "aber alle als am an auch auf aus bei bin bis bist da dann das dem den der des die dieser du durch ein eine einem einer es für gegen hat habe haben hier ich ihm ihn ihm in ist ja je kann keine können man mehr mich mir mit nach nicht nichts nun nur oder ohne so soll seine seinem seiner sich sie sind so etwas um und uns unter vom von vor war was wenn wer wie wir wird wo zu zum zur gehen geht ging zur schule kauft ein apfel ist auf tisch und gestern sie".split(),
    
    "fr": "a au aux avec ce ces ci dans de des du elle en et eux il je la le leur lui ma mais me même mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous c ceci cela ces cet cette ici ils elles ont sont aime marche va vient achète pomme école maison table hier est allé avons font".split(),
    
    "it": "a ad ai al alla allo all hanno bene che chi ci come con cosa da dagl dagli dall dallo di dov dove e un una gli ha ho i il in la le lei li lo loro lui ma mi mio mia miei mie noi non o per più qui qua questo questa questi queste quelli quelle se sei si sono sta sto sul sulla sugli sugli tu tuo tua tuoi tue un uno va vi voi".split(),

    # --- Asian Languages ---
    "hi": ["मैं", "और", "तुम", "वह", "यह", "क्या", "कौन", "कब", "कहाँ", "क्यों", "कैसे", "एक", "दो", "तीन", "चार", "पाँच", "घर", "स्कूल", "पानी", "खाना", "बाजार", "आम", "सेब", "दिन", "रात", "सुबह", "शाम", "आज", "कल", "पुराना", "नया", "अच्छा", "बुरा", "बड़ा", "छोटा", "जाना", "आना", "खाना", "पीना", "सोना", "पढ़ना", "लिखना", "बोलना", "सुनना", "देखना", "समझना", "काम", "दोस्त", "प्यार", "दुनिया", "देश", "शहर", "गाँव", "रास्ता", "दरवाज़ा", "खिड़की", "किताब", "कुर्सी", "मेज़", "लड़का", "लड़की", "आदमी", "औरत"],
    
    "ja": ["watashi", "anata", "kare", "kanojo", "kore", "sore", "are", "dare", "nani", "doko", "itsu", "naze", "dou", "ichi", "ni", "san", "shi", "go", "roku", "nana", "hachi", "kyu", "ju", "ie", "gakkou", "mizu", "tabemono", "kudamono", "asa", "hiru", "yoru", "ashita", "kinou", "kyou", "atarashii", "furui", "yoi", "warui", "ookii", "chiisai", "iku", "kuru", "taberu", "nomu", "neru", "miru", "kiku", "hanasu", "yomu", "kaku", "shigoto", "tomodachi", "ai", "sekai", "kuni", "machi", "michi", "doa", "mado", "hon", "isu", "tsukue", "otoko", "onna", "kodomo"],
    
    "zh": ["wo", "ni", "ta", "women", "nimen", "tamen", "zhe", "na", "shenme", "shui", "nali", "shenme", "shihou", "weishenme", "zenme", "yi", "er", "san", "si", "wu", "liu", "qi", "ba", "jiu", "shi", "jia", "xuexiao", "shui", "shiwu", "shuiguo", "zaoshang", "zhongwu", "wanshang", "mingtian", "zuotian", "jintian", "xin", "jiu", "hao", "huai", "da", "xiao", "qu", "lai", "chi", "he", "shui", "kan", "ting", "shuo", "du", "xie", "gongzuo", "pengyou", "ai", "shijie", "guojia", "chengshi", "lu", "men", "chuang", "shu", "yizi", "zhuozi", "nanren", "nüren", "haizi"],
    
    "ko": ["na", "neo", "geu", "uri", "neohui", "geudeul", "igeot", "geugeot", "mueot", "nugu", "eodi", "eonje", "wae", "eotteoke", "il", "i", "sam", "sa", "o", "yuk", "chil", "pal", "gu", "sip", "jip", "hakgyo", "mul", "eumsik", "gwail", "ajeossi", "nunkim", "achim", "jeongoh", "jeonyeok", "naeil", "eoje", "oneul", "saeroun", "oitheun", "joheun", "nappeun", "keun", "jageun", "gada", "oda", "meokda", "masida", "jada", "boda", "deudda", "malhada", "ilkda", "sseuda", "il", "chingu", "sarang", "segye", "gukga", "dosi", "gil", "mun", "chang", "chaek", "uija", "chaeksang", "namja", "yeoja", "ai"],
    
    "vi": ["tôi", "bạn", "anh", "chị", "em", "chúng", "họ", "này", "kia", "gì", "ai", "đâu", "khi nào", "tại sao", "như thế nào", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười", "nhà", "trường", "nước", "thức ăn", "trái cây", "sáng", "trưa", "tối", "ngày mai", "hôm qua", "hôm nay", "mới", "cũ", "tốt", "xấu", "lớn", "nhỏ", "đi", "đến", "ăn", "uống", "ngủ", "nhìn", "nghe", "nói", "đọc", "viết", "công việc", "bạn bè", "tình yêu", "thế giới", "đất nước", "thành phố", "đường", "cửa", "cửa sổ", "sách", "ghế", "bàn", "đàn ông", "phụ nữ", "trẻ em"],

    # --- African Languages ---
    "sw": ["mimi", "wewe", "yeye", "sisi", "ninyi", "wao", "hili", "hilo", "nani", "nini", "wapi", "lini", "kwanini", "vipi", "moja", "mbili", "tatu", "nne", "tano", "sita", "saba", "nane", "tisa", "kumi", "nyumba", "shule", "maji", "chakula", "soko", "siku", "usiku", "asubuhi", "jioni", "leo", "jana", "kesho", "zuri", "mbaya", "kubwa", "ndogo", "kwenda", "kuja", "kula", "kunywa", "kulala", "kuona", "kusikia", "kusema", "kusoma", "kuandika", "kazi", "rafiki", "upendo", "dunia", "nchi", "jiji", "barabara", "mlango", "dirisha", "kitabu", "kiti", "meza", "mwanaume", "mwanamke", "mtoto"],
    
    "zu": ["mina", "wena", "yena", "thina", "nina", "bona", "lesi", "lelo", "ubani", "ini", "kuphi", "nini", "kungani", "kanjani", "kunye", "kubili", "kuthathu", "kune", "kuhlamu", "isithupha", "isikhombisa", "isishiyagalombili", "isishiyagalolunye", "ishumi", "indlu", "isikole", "amanzi", "ukudla", "isikhathi", "kusasa", "namuhla", "izolo", "kusasa", "kakhulu", "kancane", "kuhle", "kabi", "ukuya", "ukufika", "ukudla", "ukuphuza", "ukulala", "ukubona", "ukuzwa", "ukukhuluma", "ukufunda", "ukubhala", "umsebenzi", "umngane", "uthando", "omhlaba", "izwe", "idolobha", "umgwaqo", "umsindo", "iwindi", "incwadi", "isihlalo", "itafula", "indoda", "umfazi", "ingane"],
    
    "yo": ["emi", "iwo", "oun", "awa", "eyin", "awon", "eyi", "iyen", "kini", "tani", "nibo", "nigbawo", "kilode", "bawo", "okan", "eji", "eta", "erin", "arun", "efa", "eje", "ejo", "esan", "ewa", "ile", "ile-iwe", "omi", "ounje", "oja", "ojo", "oru", "aro", "ale", "loni", "ana", "ola", "titun", "ati", "daradara", "buruku", "nla", "kekere", "lo", "wa", "je", "mu", "sun", "ri", "gbo", "so", "ka", "ko", "ise", "ore", "ife", "aye", "orileede", "ilu", "ona", "ilekun", "ferese", "iwe", "aga", "tabili", "okunrin", "obinrin", "omode"],
    
    "am": ["ine", "ante", "ersu", "inja", "inante", "inesu", "yih", "yih", "min", "man", "yet", "meles", "lemin", "inidet", "and", "hulett", "sost", "arat", "amist", "sidist", "sebat", "siment", "zet", "asir", "bet", "timhirtbet", "waha", "megot", "gabaya", "ken", "lilit", "tewat", "meseret", "konjo", "meri", "tilik", "tinish", "mehed", "meta", "bela", "teta", "tesh", "ayehu", "semahu", "meslu", "new", "kedu", "sera", "gibie", "gwadegna", "fikir", "alem", "hager", "ketema", "ketema", "menor", "tanta", "tifir", "metsek", "seb", "yerfu", "sigab", "wend", "set", "lij"],
    
    "ha": ["ni", "ka", "shi", "mu", "ku", "su", "wannan", "wancan", "me", "wa", "ina", "yaushe", "domin", "yaya", "daya", "biyu", "uku", "hudu", "biyar", "shida", "bakwai", "takwas", "tara", "goma", "gida", "makaranta", "ruwa", "abinci", "kasuwa", "rana", "dare", "safe", "yamma", "yau", "jiya", "gobe", "sabon", "tsoho", "mai kyau", "mummunan", "babba", "karami", "tafiya", "zowa", "ci", "sha", "kwana", "gani", "ji", "fada", "karanta", "rubuta", "aiki", "aboki", "kauna", "duniya", "kasa", "birni", "hanya", "kofo", "taga", "littafi", "kujera", "tebur", "namiji", "mace", "yaro"],

    # --- Native American Languages ---
    "nv": ["shí", "ni", "haííníísh", "hastiin", "asdzání", "diné", "tʼáá", "łáʼ", "naaki", "táá", "dį́į́ʼ", "ashdlaʼ", "hastą́ą́", "tsostsʼid", "tseebíí", "náhástʼéí", "tłaʼtsʼid", "neeznáá", "kin", "oltaʼ", "tó", "chʼiyáán", "naaldlooshii", "jó", "tʼééʼ", "abiní", "anaaʼ", "díí", "níná", "yiską́", "łitso", "łizhin", "dootłʼizh", "łichííʼ", "łibáá", "bee", "bílaʼashdlaʼii", "óóltaʼ", "bikeeʼ", "bíńákees", "bikeeʼ", "awééʼ", "altso", "ałtsé", "ákótʼéego", "tʼááłáʼí", "ałą́ą́", "hodina", "yáʼátʼéeh", "doo", "yóó", "hózhó", "chahałheeł", "ndaʼalką́ą́ʼ", "hataał", "ałchíní"],
    
    "qu": ["ñuqa", "qam", "pay", "ñuqanchik", "qamkuna", "paykuna", "kay", "chay", "ima", "pi", "maypi", "imaqtin", "imarayku", "imashina", "huk", "iskay", "kimsa", "tawa", "pichqa", "suqta", "qanchis", "pusaq", "isqun", "chunka", "wasi", "yachaywasi", "unu", "mikhuy", "hatun", "uchuy", "allin", "millay", "riy", "hamuy", "mikhuy", "upyay", "puñuy", "qhaway", "uyariy", "rimay", "ñawiy", "qillqay", "llankay", "masi", "khuyay", "pacha", "suyu", "llaqta", "ñan", "punku", "watana", "panqa", "tiyana", "mesa", "qhari", "warmi", "wawa"],
    
    "chr": ["agiya", "nihi", "ahi", "ani", "ihini", "anvi", "gini", "hawiya", "nvhwi", "gado", "hela", "utana", "sawini", "ohili", "sagwi", "taline", "joie", "nvhi", "hisgi", "ahlisgi", "osda", "uyoI", "utana", "usdi", "awali", "uli", "asdi", "amayi", "asgaya", "agehya", "ayvwi", "ulahiyi", "tsunilv", "gunahi", "dawhilv", "anitsv", "ganohili", "ganohalidoi", "dikanohi", "wadv", "gowhti", "anigilo", "aniwodi", "unalii", "adohi", "ulvelodi", "digohweli", "detsanv", "ugata", "asuya", "gohudi", "ohvi", "itsula", "alonv", "uwenv"],
    
    "oj": ["niin", "giin", "aapish", "wiin", "niindamin", "giinamin", "owinamin", "maaba", "naana", "moo", "anen", "wegonen", "aandi", "aaniish", "aaniin", "bezhik", "niizh", "nswi", "niiwin", "naanan", "ningodwaaswi", "niizhwaaswi", "nishwaaswi", "zhaangaso", "zhaang", "gikinoo'amaadi", "nibi", "babaama", "odaabaan", "anokii", "izhichige", "bimose", "nibaa", "waabama", "nendam", "gagwein", "gikendaan", "bizaan", "wenji", "maajaan", "bagwaji", "gitigaan", "dibishkaa", "gichi", "zhishi", "jaanii", "nookomis", "ookomisan", "mishoomis", "oogimaa", "anishinaabe", "ikwe", "inini", "abinoojiinh", "binesi", "makwa", "wajiw", "zaaga'igan"],
    
    "iu": ["uva", "ivvit", "uanga", "uvagut", "illisi", "uqalimak", "una", "taku", "kina", "sumi", "nakurmiik", "qanoq", "ataaseq", "marluk", "pingasut", "sisamat", "tallimat", "arfinillit", "marlunnillit", "pingasunnillit", "sisamannillit", "quliaq", "tuquraq", "inuk", "inukshuk", "nuna", "sila", "imiq", "qimmiq", "nanuq", "tuktu", "nalunaaquttaq", "ullaaq", "unnuaq", "tingmiat", "niriit", "qaqqaq", "saattuq", "kalaallit", "angut", "arnaq", "irnuk", "panik", "iniriq", "majjuti", "isumagijjutiqarniq", "qaujimajatuqangit", "piliriqatigiinniq", "avattimut", "naatsi", "kangiqtugaapik", "igluit", "nattivak"]
}

# ═══════════════════════════════════════════════════════════════════
# SECTION 3: Database Manager Class
# ═══════════════════════════════════════════════════════════════════

class DatabaseInitializer:
    """Handles the creation and seeding of a language-specific SQLite database."""

    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.db_dir = os.path.join(os.getcwd(), lang_code)
        self.db_path = os.path.join(self.db_dir, f"{lang_code}.db")
        self.conn = None

    def init_database(self):
        logger.info(f"--- Processing Language: {self.lang_code.upper()} ---")
        self._create_directory()
        self._connect()
        self._enforce_schema()
        self._seed_data()
        self._disconnect()
        logger.info(f"--- Completed {self.lang_code.upper()} ---\n")

    def _create_directory(self):
        try:
            os.makedirs(self.db_dir, exist_ok=True)
            logger.info(f"Directory ensured: {self.db_dir}")
        except OSError as e:
            logger.error(f"Failed to create directory {self.db_dir}: {e}")
            raise

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _disconnect(self):
        if self.conn:
            self.conn.close()
            logger.info("Connection closed.")

    def _enforce_schema(self):
        """Creates the strict relational schema with constraints and indexes."""
        cursor = self.conn.cursor()
        try:
            # Metadata Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS metadata (
                                key TEXT PRIMARY KEY, 
                                value TEXT NOT NULL)""")

            # Dictionary Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS dictionary (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                word TEXT NOT NULL UNIQUE,
                                freq INTEGER NOT NULL DEFAULT 1,
                                is_user INTEGER NOT NULL DEFAULT 0,
                                created_at TEXT NOT NULL,
                                updated_at TEXT NOT NULL)""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dict_user ON dictionary(is_user)")

            # Bigrams Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS bigrams (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                w1 TEXT NOT NULL,
                                w2 TEXT NOT NULL,
                                freq INTEGER NOT NULL DEFAULT 1,
                                UNIQUE(w1, w2))""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bigrams_w1 ON bigrams(w1)")

            # Trigrams Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS trigrams (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                w1 TEXT NOT NULL,
                                w2 TEXT NOT NULL,
                                w3 TEXT NOT NULL,
                                freq INTEGER NOT NULL DEFAULT 1,
                                UNIQUE(w1, w2, w3))""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trigrams_w1w2 ON trigrams(w1, w2)")

            self.conn.commit()
            logger.info("Database schema enforced successfully.")
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Schema creation failed: {e}")
            raise

    def _seed_data(self):
        """Seeds the database with the base vocabulary and n-grams if empty."""
        words = SEED_MAP.get(self.lang_code, [])
        if not words:
            logger.warning(f"No seed data found for {self.lang_code}. Skipping seeding.")
            return

        # Check if already seeded
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dictionary")
        count = cursor.fetchone()[0]

        if count > 0:
            logger.info(f"Database already contains {count} words. Seeding skipped.")
            return

        logger.info(f"Seeding database with {len(words)} tokens...")
        now = datetime.utcnow().isoformat()
        freq = Counter(words)

        try:
            with self.conn:
                # 1. Insert Words
                self.conn.executemany(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at) 
                       VALUES (?, ?, 0, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET freq = freq + ?, updated_at = ?""",
                    [(w, f, now, now, f, now) for w, f in freq.items()]
                )

                # 2. Insert Bigrams
                bigram_freq = Counter(zip(words, words[1:]))
                self.conn.executemany(
                    """INSERT INTO bigrams (w1, w2, freq) VALUES (?, ?, ?)
                       ON CONFLICT(w1, w2) DO UPDATE SET freq = freq + ?""",
                    [(w1, w2, f, f) for (w1, w2), f in bigram_freq.items()]
                )

                # 3. Insert Trigrams
                trigram_freq = Counter(zip(words, words[1:], words[2:]))
                self.conn.executemany(
                    """INSERT INTO trigrams (w1, w2, w3, freq) VALUES (?, ?, ?, ?)
                       ON CONFLICT(w1, w2, w3) DO UPDATE SET freq = freq + ?""",
                    [(w1, w2, w3, f, f) for (w1, w2, w3), f in trigram_freq.items()]
                )

                # 4. Set metadata
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("last_seed_date", now)
                )

            logger.info(f"Successfully seeded {len(freq)} unique words, {len(bigram_freq)} bigrams, and {len(trigram_freq)} trigrams.")
        except sqlite3.Error as e:
            logger.error(f"Seeding failed: {e}")
            raise

# ═══════════════════════════════════════════════════════════════════
# SECTION 4: Main Execution
# ═══════════════════════════════════════════════════════════════════

def main():
    # All 20 languages mapped to ISO 639 codes
    languages = [
        "en", "es", "de", "fr", "it",         # Core
        "hi", "ja", "zh", "ko", "vi",         # Asian
        "sw", "zu", "yo", "am", "ha",         # African
        "nv", "qu", "chr", "oj", "iu"         # Native American
    ]
    
    logger.info(f"Starting database initialization for {len(languages)} languages.")
    logger.info(f"Target base directory: {os.getcwd()}\n")

    for lang in languages:
        try:
            initializer = DatabaseInitializer(lang)
            initializer.init_database()
        except Exception as e:
            logger.error(f"Halting processing for {lang} due to critical error.")

    logger.info("✅ All language database initialization tasks complete!")

if __name__ == "__main__":
    main()