#!/usr/bin/env python3
"""
Database Initialization Script for Advanced NLP Text Corrector
================================================================
Creates isolated SQLite databases for 20 languages inside ./database/

Schema Version: 2.0  (adds grammar_rules + confusion_pairs tables)
Run download_dictionaries.py AFTER this to populate with real data.
"""

import os
import logging
import sqlite3
from datetime import datetime
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("DB_Init")

DB_FOLDER = "database"

SEED_MAP = {
    "en": "a able about above accept across act actually add afraid after afternoon again against age ago agree air all almost along already also always am among an and anger animal answer ant any anybody anymore anything anyplace anyway apart apartment appear apple are area arm army around arrive art as ask at attack attempt attend august aunt author autumn available away baby back bad bag ball ban band bank bar base basic basis bath be beach bean bear beat beautiful became because become bed been before began begin behind being believe bell belong below beside best better between beyond big bill bird birth bit bite black blame blank block blood blow blue board boat body bomb bond bone book border born both bother bottle bottom bound box boy brain branch brave bread break breath bridge brief bright bring broad broke brother brown brush build building burn bus business busy but buy by cabin cage cake call calm came camera camp can cap capital captain capture car card care careful carry case cash cast cat catch cause cell center central century certain chain chair chairman challenge champion chance change channel chapter character charge charm chart chase cheap check cheek cheese chest chicken chief child childhood chin chip choice choose church circle citizen city civil claim class clean clear click client climb clinical clock close cloth clothes cloud club clue cluster coach coal coast coat code coffee cold collar collect college colony color column combination come comfort command comment commit common communicate community company compare competition complete complex computer concern condition conduct confirm congress connect consider contact contain content contest continue control conversation cook cool cooperation copy core corner corporate correct cost could count counter country county couple courage course court cousin cover crack craft crash crazy cream create crime criminal crisis criteria critical crop cross crowd crucial cry cultural cup cure curious current curve custom customer cut cycle".split(),
    "es": "a al ahora algo algunos ante antes apellido aquél aquí así aunque año años cada casi caso casa cine ciudad como con conocer creo cual cuando de del desde donde dos él ella ellos en entre era es esa ese eso esta estado estos está estoy esto euro ejemplo el ella ellos embargo en entre era eres esa ese esto esto están estaban estar estas este estoy fin fue fuera gran ha habíamos haber hace hacer habían hasta hay hoy la las le les lo los me mi mismo mucho muy más mí mío nada ni no nos nosotras nosotros nuestra nuevo o otra otro otros para parte pasar pero poco por porque primero puede cuando que quien qué se sea señora señor si sí siempre sobre solo somos su sus suyo sí también tan tanto te tienen tengo ti tiene todo tu tú un una unas uno unos usted ustedes va van veces ver vez y ya yo él caminar camina caminé escuela compra manzana está mesa ayer".split(),
    "de": "aber alle als am an auch auf aus bei bin bis bist da dann das dem den der des die dieser du durch ein eine einem einer es für gegen hat habe haben hier ich ihm ihn ihm in ist ja je kann keine können man mehr mich mir mit nach nicht nichts nun nur oder ohne so soll seine seinem seiner sich sie sind so etwas um und uns unter vom von vor war was wenn wer wie wir wird wo zu zum zur gehen geht ging zur schule kauft ein apfel ist auf tisch und gestern sie".split(),
    "fr": "a au aux avec ce ces ci dans de des du elle en et eux il je la le leur lui ma mais me même mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous c ceci cela ces cet cette ici ils elles ont sont aime marche va vient achète pomme école maison table hier est allé avons font".split(),
    "it": "a ad ai al alla allo all hanno bene che chi ci come con cosa da dagl dagli dall dallo di dov dove e un una gli ha ho i il in la le lei li lo loro lui ma mi mio mia miei mie noi non o per più qui qua questo questa questi queste quelli quelle se sei si sono sta sto sul sulla sugli sugli tu tuo tua tuoi tue un uno va vi voi".split(),
    "hi": ["मैं", "और", "तुम", "वह", "यह", "क्या", "कौन", "कब", "कहाँ", "क्यों", "कैसे", "एक", "दो", "तीन", "चार", "पाँच", "घर", "स्कूल", "पानी", "खाना", "बाजार", "आम", "सेब", "दिन", "रात", "सुबह", "शाम", "आज", "कल", "पुराना", "नया", "अच्छा", "बुरा", "बड़ा", "छोटा", "जाना", "आना", "खाना", "पीना", "सोना", "पढ़ना", "लिखना", "बोलना", "सुनना", "देखना", "समझना", "काम", "दोस्त", "प्यार", "दुनिया", "देश", "शहर", "गाँव", "रास्ता", "दरवाज़ा", "खिड़की", "किताब", "कुर्सी", "मेज़", "लड़का", "लड़की", "आदमी", "औरत"],
    "ja": ["watashi", "anata", "kare", "kanojo", "kore", "sore", "are", "dare", "nani", "doko", "itsu", "naze", "dou", "ichi", "ni", "san", "shi", "go", "roku", "nana", "hachi", "kyu", "ju", "ie", "gakkou", "mizu", "tabemono", "kudamono", "asa", "hiru", "yoru", "ashita", "kinou", "kyou", "atarashii", "furui", "yoi", "warui", "ookii", "chiisai", "iku", "kuru", "taberu", "nomu", "neru", "miru", "kiku", "hanasu", "yomu", "kaku", "shigoto", "tomodachi", "ai", "sekai", "kuni", "machi", "michi", "doa", "mado", "hon", "isu", "tsukue", "otoko", "onna", "kodomo"],
    "zh": ["wo", "ni", "ta", "women", "nimen", "tamen", "zhe", "na", "shenme", "shui", "nali", "shenme", "shihou", "weishenme", "zenme", "yi", "er", "san", "si", "wu", "liu", "qi", "ba", "jiu", "shi", "jia", "xuexiao", "shui", "shiwu", "shuiguo", "zaoshang", "zhongwu", "wanshang", "mingtian", "zuotian", "jintian", "xin", "jiu", "hao", "huai", "da", "xiao", "qu", "lai", "chi", "he", "shui", "kan", "ting", "shuo", "du", "xie", "gongzuo", "pengyou", "ai", "shijie", "guojia", "chengshi", "lu", "men", "chuang", "shu", "yizi", "zhuozi", "nanren", "nüren", "haizi"],
    "ko": ["na", "neo", "geu", "uri", "neohui", "geudeul", "igeot", "geugeot", "mueot", "nugu", "eodi", "eonje", "wae", "eotteoke", "il", "i", "sam", "sa", "o", "yuk", "chil", "pal", "gu", "sip", "jip", "hakgyo", "mul", "eumsik", "gwail", "ajeossi", "nunkim", "achim", "jeongoh", "jeonyeok", "naeil", "eoje", "oneul", "saeroun", "oitheun", "joheun", "nappeun", "keun", "jageun", "gada", "oda", "meokda", "masida", "jada", "boda", "deudda", "malhada", "ilkda", "sseuda", "il", "chingu", "sarang", "segye", "gukga", "dosi", "gil", "mun", "chang", "chaek", "uija", "chaeksang", "namja", "yeoja", "ai"],
    "vi": ["tôi", "bạn", "anh", "chị", "em", "chúng", "họ", "này", "kia", "gì", "ai", "đâu", "khi nào", "tại sao", "như thế nào", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười", "nhà", "trường", "nước", "thức ăn", "trái cây", "sáng", "trưa", "tối", "ngày mai", "hôm qua", "hôm nay", "mới", "cũ", "tốt", "xấu", "lớn", "nhỏ", "đi", "đến", "ăn", "uống", "ngủ", "nhìn", "nghe", "nói", "đọc", "viết", "công việc", "bạn bè", "tình yêu", "thế giới", "đất nước", "thành phố", "đường", "cửa", "cửa sổ", "sách", "ghế", "bàn", "đàn ông", "phụ nữ", "trẻ em"],
    "sw": ["mimi", "wewe", "yeye", "sisi", "ninyi", "wao", "hili", "hilo", "nani", "nini", "wapi", "lini", "kwanini", "vipi", "moja", "mbili", "tatu", "nne", "tano", "sita", "saba", "nane", "tisa", "kumi", "nyumba", "shule", "maji", "chakula", "soko", "siku", "usiku", "asubuhi", "jioni", "leo", "jana", "kesho", "zuri", "mbaya", "kubwa", "ndogo", "kwenda", "kuja", "kula", "kunywa", "kulala", "kuona", "kusikia", "kusema", "kusoma", "kuandika", "kazi", "rafiki", "upendo", "dunia", "nchi", "jiji", "barabara", "mlango", "dirisha", "kitabu", "kiti", "meza", "mwanaume", "mwanamke", "mtoto"],
    "zu": ["mina", "wena", "yena", "thina", "nina", "bona", "lesi", "lelo", "ubani", "ini", "kuphi", "nini", "kungani", "kanjani", "kunye", "kubili", "kuthathu", "kune", "kuhlamu", "isithupha", "isikhombisa", "isishiyagalombili", "isishiyagalolunye", "ishumi", "indlu", "isikole", "amanzi", "ukudla", "isikhathi", "kusasa", "namuhla", "izolo", "kusasa", "kakhulu", "kancane", "kuhle", "kabi", "ukuya", "ukufika", "ukudla", "ukuphuza", "ukulala", "ukubona", "ukuzwa", "ukukhuluma", "ukufunda", "ukubhala", "umsebenzi", "umngane", "uthando", "omhlaba", "izwe", "idolobha", "umgwaqo", "umsindo", "iwindi", "incwadi", "isihlalo", "itafula", "indoda", "umfazi", "ingane"],
    "yo": ["emi", "iwo", "oun", "awa", "eyin", "awon", "eyi", "iyen", "kini", "tani", "nibo", "nigbawo", "kilode", "bawo", "okan", "eji", "eta", "erin", "arun", "efa", "eje", "ejo", "esan", "ewa", "ile", "ile-iwe", "omi", "ounje", "oja", "ojo", "oru", "aro", "ale", "loni", "ana", "ola", "titun", "ati", "daradara", "buruku", "nla", "kekere", "lo", "wa", "je", "mu", "sun", "ri", "gbo", "so", "ka", "ko", "ise", "ore", "ife", "aye", "orileede", "ilu", "ona", "ilekun", "ferese", "iwe", "aga", "tabili", "okunrin", "obinrin", "omode"],
    "am": ["ine", "ante", "ersu", "inja", "inante", "inesu", "yih", "yih", "min", "man", "yet", "meles", "lemin", "inidet", "and", "hulett", "sost", "arat", "amist", "sidist", "sebat", "siment", "zet", "asir", "bet", "timhirtbet", "waha", "megot", "gabaya", "ken", "lilit", "tewat", "meseret", "konjo", "meri", "tilik", "tinish", "mehed", "meta", "bela", "teta", "tesh", "ayehu", "semahu", "meslu", "new", "kedu", "sera", "gibie", "gwadegna", "fikir", "alem", "hager", "ketema", "ketema", "menor", "tanta", "tifir", "metsek", "seb", "yerfu", "sigab", "wend", "set", "lij"],
    "ha": ["ni", "ka", "shi", "mu", "ku", "su", "wannan", "wancan", "me", "wa", "ina", "yaushe", "domin", "yaya", "daya", "biyu", "uku", "hudu", "biyar", "shida", "bakwai", "takwas", "tara", "goma", "gida", "makaranta", "ruwa", "abinci", "kasuwa", "rana", "dare", "safe", "yamma", "yau", "jiya", "gobe", "sabon", "tsoho", "mai kyau", "mummunan", "babba", "karami", "tafiya", "zowa", "ci", "sha", "kwana", "gani", "ji", "fada", "karanta", "rubuta", "aiki", "aboki", "kauna", "duniya", "kasa", "birni", "hanya", "kofo", "taga", "littafi", "kujera", "tebur", "namiji", "mace", "yaro"],
    "nv": ["shí", "ni", "haííníísh", "hastiin", "asdzání", "diné", "tʼáá", "łáʼ", "naaki", "táá", "dį́į́ʼ", "ashdlaʼ", "hastą́ą́", "tsostsʼid", "tseebíí", "náhástʼéí", "tłaʼtsʼid", "neeznáá", "kin", "oltaʼ", "tó", "chʼiyáán", "naaldlooshii", "jó", "tʼééʼ", "abiní", "anaaʼ", "díí", "níná", "yiską́", "łitso", "łizhin", "dootłʼizh", "łichííʼ", "łibáá", "bee", "bílaʼashdlaʼii", "óóltaʼ", "bikeeʼ", "bíńákees", "bikeeʼ", "awééʼ", "altso", "ałtsé", "ákótʼéego", "tʼááłáʼí", "ałą́ą́", "hodina", "yáʼátʼéeh", "doo", "yóó", "hózhó", "chahałheeł", "ndaʼalką́ą́ʼ", "hataał", "ałchíní"],
    "qu": ["ñuqa", "qam", "pay", "ñuqanchik", "qamkuna", "paykuna", "kay", "chay", "ima", "pi", "maypi", "imaqtin", "imarayku", "imashina", "huk", "iskay", "kimsa", "tawa", "pichqa", "suqta", "qanchis", "pusaq", "isqun", "chunka", "wasi", "yachaywasi", "unu", "mikhuy", "hatun", "uchuy", "allin", "millay", "riy", "hamuy", "mikhuy", "upyay", "puñuy", "qhaway", "uyariy", "rimay", "ñawiy", "qillqay", "llankay", "masi", "khuyay", "pacha", "suyu", "llaqta", "ñan", "punku", "watana", "panqa", "tiyana", "mesa", "qhari", "warmi", "wawa"],
    "chr": ["agiya", "nihi", "ahi", "ani", "ihini", "anvi", "gini", "hawiya", "nvhwi", "gado", "hela", "utana", "sawini", "ohili", "sagwi", "taline", "joie", "nvhi", "hisgi", "ahlisgi", "osda", "uyoI", "utana", "usdi", "awali", "uli", "asdi", "amayi", "asgaya", "agehya", "ayvwi", "ulahiyi", "tsunilv", "gunahi", "dawhilv", "anitsv", "ganohili", "ganohalidoi", "dikanohi", "wadv", "gowhti", "anigilo", "aniwodi", "unalii", "adohi", "ulvelodi", "digohweli", "detsanv", "ugata", "asuya", "gohudi", "ohvi", "itsula", "alonv", "uwenv"],
    "oj": ["niin", "giin", "aapish", "wiin", "niindamin", "giinamin", "owinamin", "maaba", "naana", "moo", "anen", "wegonen", "aandi", "aaniish", "aaniin", "bezhik", "niizh", "nswi", "niiwin", "naanan", "ningodwaaswi", "niizhwaaswi", "nishwaaswi", "zhaangaso", "zhaang", "gikinoo'amaadi", "nibi", "babaama", "odaabaan", "anokii", "izhichige", "bimose", "nibaa", "waabama", "nendam", "gagwein", "gikendaan", "bizaan", "wenji", "maajaan", "bagwaji", "gitigaan", "dibishkaa", "gichi", "zhishi", "jaanii", "nookomis", "ookomisan", "mishoomis", "oogimaa", "anishinaabe", "ikwe", "inini", "abinoojiinh", "binesi", "makwa", "wajiw", "zaaga'igan"],
    "iu": ["uva", "ivvit", "uanga", "uvagut", "illisi", "uqalimak", "una", "taku", "kina", "sumi", "nakurmiik", "qanoq", "ataaseq", "marluk", "pingasut", "sisamat", "tallimat", "arfinillit", "marlunnillit", "pingasunnillit", "sisamannillit", "quliaq", "tuquraq", "inuk", "inukshuk", "nuna", "sila", "imiq", "qimmiq", "nanuq", "tuktu", "nalunaaquttaq", "ullaaq", "unnuaq", "tingmiat", "niriit", "qaqqaq", "saattuq", "kalaallit", "angut", "arnaq", "irnuk", "panik", "iniriq", "majjuti", "isumagijjutiqarniq", "qaujimajatuqangit", "piliriqatigiinniq", "avattimut", "naatsi", "kangiqtugaapik", "igluit", "nattivak"],
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dictionary (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    word       TEXT    NOT NULL UNIQUE,
    freq       INTEGER NOT NULL DEFAULT 1,
    is_user    INTEGER NOT NULL DEFAULT 0 CHECK(is_user IN (0, 1)),
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word);
CREATE INDEX IF NOT EXISTS idx_dict_user ON dictionary(is_user);

CREATE TABLE IF NOT EXISTS bigrams (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    w1   TEXT    NOT NULL,
    w2   TEXT    NOT NULL,
    freq INTEGER NOT NULL DEFAULT 1,
    UNIQUE(w1, w2)
);
CREATE INDEX IF NOT EXISTS idx_bigrams_w1 ON bigrams(w1);

CREATE TABLE IF NOT EXISTS trigrams (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    w1   TEXT    NOT NULL,
    w2   TEXT    NOT NULL,
    w3   TEXT    NOT NULL,
    freq INTEGER NOT NULL DEFAULT 1,
    UNIQUE(w1, w2, w3)
);
CREATE INDEX IF NOT EXISTS idx_trigrams_w1w2 ON trigrams(w1, w2);

CREATE TABLE IF NOT EXISTS grammar_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type   TEXT    NOT NULL,
    pattern     TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    replacement TEXT    NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 0,
    enabled     INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_grammar_type ON grammar_rules(rule_type);

CREATE TABLE IF NOT EXISTS confusion_pairs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    wrong         TEXT    NOT NULL,
    correct       TEXT    NOT NULL,
    context_hint  TEXT,
    message       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_confusion_wrong ON confusion_pairs(wrong);
"""

LANGUAGES = [
    "en", "es", "de", "fr", "it",
    "hi", "ja", "zh", "ko", "vi",
    "sw", "zu", "yo", "am", "ha",
    "nv", "qu", "chr", "oj", "iu",
]


class DatabaseInitializer:
    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.db_dir = os.path.join(os.getcwd(), DB_FOLDER)
        self.db_path = os.path.join(self.db_dir, f"{lang_code}.db")
        self.conn = None

    def init_database(self):
        logger.info(f"--- {self.lang_code.upper()} ---")
        os.makedirs(self.db_dir, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dictionary")
        if cursor.fetchone()[0] == 0:
            self._seed()

        self.conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '2.0')")
        self.conn.commit()
        self.conn.close()
        logger.info(f"--- {self.lang_code.upper()} done ---")

    def _seed(self):
        words = SEED_MAP.get(self.lang_code, [])
        if not words:
            return
        now = datetime.utcnow().isoformat()
        freq = Counter(words)
        with self.conn:
            self.conn.executemany(
                "INSERT INTO dictionary (word, freq, is_user, created_at, updated_at) VALUES (?, ?, 0, ?, ?) ON CONFLICT(word) DO UPDATE SET freq = freq + ?, updated_at = ?",
                [(w, f, now, now, f, now) for w, f in freq.items()],
            )
            bf = Counter(zip(words, words[1:]))
            self.conn.executemany(
                "INSERT INTO bigrams (w1, w2, freq) VALUES (?, ?, ?) ON CONFLICT(w1, w2) DO UPDATE SET freq = freq + ?",
                [(w1, w2, f, f) for (w1, w2), f in bf.items()],
            )
            tf = Counter(zip(words, words[1:], words[2:]))
            self.conn.executemany(
                "INSERT INTO trigrams (w1, w2, w3, freq) VALUES (?, ?, ?, ?) ON CONFLICT(w1, w2, w3) DO UPDATE SET freq = freq + ?",
                [(w1, w2, w3, f, f) for (w1, w2, w3), f in tf.items()],
            )
        logger.info(f"  Seeded {len(freq)} words.")


def main():
    logger.info(f"Initializing {len(LANGUAGES)} language databases in ./{DB_FOLDER}/")
    for lang in LANGUAGES:
        try:
            DatabaseInitializer(lang).init_database()
        except Exception as e:
            logger.error(f"Failed for {lang}: {e}")
    logger.info("✅ All databases initialized. Run download_dictionaries.py next for real word lists.")


if __name__ == "__main__":
    main()