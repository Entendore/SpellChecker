#!/usr/bin/env python3
"""
Advanced NLP Text Corrector — PySide6 Edition
================================================================
Features:
  • All databases in a single ./database/ folder
  • Same schema & seed data as init_databases.py
  • Terminal-only logging (no log file)
  • Spell checking via BK-tree & Levenshtein distance
  • Grammar checking with language-specific rules
  • Multiple correction strategies (Interactive, Beam Search, MCTS)
  • User dictionary management with database persistence
  • Dark / Light themes
  • 20 languages
"""

import sys, re, os, heapq, random, string, logging, traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
import sqlite3

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QTabWidget, QComboBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QLineEdit, QCheckBox, QMessageBox,
    QSplitter, QStatusBar, QProgressBar,
    QAbstractItemView, QInputDialog, QListWidget,
)
from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import (
    QTextCharFormat, QColor, QFont, QTextCursor, QKeySequence, QAction
)

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Logging — Terminal Only
# ═══════════════════════════════════════════════════════════════════

def setup_logging():
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-18s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(ch)

logger = logging.getLogger("NLP_Corrector")

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Seed Dictionaries (Same as init_databases.py)
# ═══════════════════════════════════════════════════════════════════

SEED_MAP = {
    "en": "a able about above accept across act actually add afraid after "
          "afternoon again against age ago agree air all almost along already "
          "also always am among an and anger animal answer ant any anybody "
          "anymore anything anyplace anyway apart apartment appear apple are "
          "area arm army around arrive art as ask at attack attempt attend "
          "august aunt author autumn available away baby back bad bag ball ban "
          "band bank bar base basic basis bath be beach bean bear beat "
          "beautiful became because become bed been before began begin behind "
          "being believe bell belong below beside best better between beyond "
          "big bill bird birth bit bite black blame blank block blood blow "
          "blue board boat body bomb bond bone book border born both bother "
          "bottle bottom bound box boy brain branch brave bread break breath "
          "bridge brief bright bring broad broke brother brown brush build "
          "building burn bus business busy but buy by cabin cage cake call "
          "calm came camera camp can cap capital captain capture car card care "
          "careful carry case cash cast cat catch cause cell center central "
          "century certain chain chair chairman challenge champion chance "
          "change channel chapter character charge charm chart chase cheap "
          "check cheek cheese chest chicken chief child childhood chin chip "
          "choice choose church circle citizen city civil claim class clean "
          "clear click client climb clinical clock close cloth clothes cloud "
          "club clue cluster coach coal coast coat code coffee cold collar "
          "collect college colony color column combination come comfort "
          "command comment commit common communicate community company compare "
          "competition complete complex computer concern condition conduct "
          "confirm congress connect consider contact contain content contest "
          "continue control conversation cook cool cooperation copy core "
          "corner corporate correct cost could count counter country county "
          "couple courage course court cousin cover crack craft crash crazy "
          "cream create crime criminal crisis criteria critical crop cross "
          "crowd crucial cry cultural cup cure curious current curve custom "
          "customer cut cycle".split(),

    "es": "a al ahora algo algunos ante antes apellido aquél aquí así aunque "
          "año años cada casi caso casa cine ciudad como con conocer creo cual "
          "cuando de del desde donde dos él ella ellos en entre era es esa ese "
          "eso esta estado estos está estoy esto euro ejemplo el ella ellos "
          "embargo en entre era eres esa ese esto esto están estaban estar "
          "estas este estoy fin fue fuera gran ha habíamos haber hace hacer "
          "habían hasta hay hoy la las le les lo los me mi mismo mucho muy "
          "más mí mío nada ni no nos nosotras nosotros nuestra nuevo o otra "
          "otro otros para parte pasar pero poco por porque primero puede "
          "cuando que quien qué se sea señora señor si sí siempre sobre solo "
          "somos su sus suyo sí también tan tanto te tienen tengo ti tiene "
          "todo tu tú un una unas uno unos usted ustedes va van veces ver vez "
          "y ya yo él caminar camina caminé escuela compra manzana está mesa "
          "ayer".split(),

    "de": "aber alle als am an auch auf aus bei bin bis bist da dann das dem "
          "den der des die dieser du durch ein eine einem einer es für gegen "
          "hat habe haben hier ich ihm ihn ihm in ist ja je kann keine können "
          "man mehr mich mir mit nach nicht nichts nun nur oder ohne so soll "
          "seine seinem seiner sich sie sind so etwas um und uns unter vom "
          "von vor war was wenn wer wie wir wird wo zu zum zur gehen geht "
          "ging zur schule kauft ein apfel ist auf tisch und gestern sie".split(),

    "fr": "a au aux avec ce ces ci dans de des du elle en et eux il je la le "
          "leur lui ma mais me même mes moi mon ne nos notre nous on ou par "
          "pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une "
          "vos votre vous c ceci cela ces cet cette ici ils elles ont sont "
          "aime marche va vient achète pomme école maison table hier est allé "
          "avons font".split(),

    "it": "a ad ai al alla allo all hanno bene che chi ci come con cosa da "
          "dagl dagli dall dallo di dov dove e un una gli ha ho i il in la "
          "le lei li lo loro lui ma mi mio mia miei mie noi non o per più "
          "qui qua questo questa questi queste quelli quelle se sei si sono "
          "sta sto sul sulla sugli sugli tu tuo tua tuoi tue un uno va vi "
          "voi".split(),

    "hi": ["मैं", "और", "तुम", "वह", "यह", "क्या", "कौन", "कब", "कहाँ", "क्यों",
           "कैसे", "एक", "दो", "तीन", "चार", "पाँच", "घर", "स्कूल", "पानी", "खाना",
           "बाजार", "आम", "सेब", "दिन", "रात", "सुबह", "शाम", "आज", "कल", "पुराना",
           "नया", "अच्छा", "बुरा", "बड़ा", "छोटा", "जाना", "आना", "खाना", "पीना",
           "सोना", "पढ़ना", "लिखना", "बोलना", "सुनना", "देखना", "समझना", "काम",
           "दोस्त", "प्यार", "दुनिया", "देश", "शहर", "गाँव", "रास्ता", "दरवाज़ा",
           "खिड़की", "किताब", "कुर्सी", "मेज़", "लड़का", "लड़की", "आदमी", "औरत"],

    "ja": ["watashi", "anata", "kare", "kanojo", "kore", "sore", "are",
           "dare", "nani", "doko", "itsu", "naze", "dou", "ichi", "ni", "san",
           "shi", "go", "roku", "nana", "hachi", "kyu", "ju", "ie", "gakkou",
           "mizu", "tabemono", "kudamono", "asa", "hiru", "yoru", "ashita",
           "kinou", "kyou", "atarashii", "furui", "yoi", "warui", "ookii",
           "chiisai", "iku", "kuru", "taberu", "nomu", "neru", "miru", "kiku",
           "hanasu", "yomu", "kaku", "shigoto", "tomodachi", "ai", "sekai",
           "kuni", "machi", "michi", "doa", "mado", "hon", "isu", "tsukue",
           "otoko", "onna", "kodomo"],

    "zh": ["wo", "ni", "ta", "women", "nimen", "tamen", "zhe", "na", "shenme",
           "shui", "nali", "shenme", "shihou", "weishenme", "zenme", "yi", "er",
           "san", "si", "wu", "liu", "qi", "ba", "jiu", "shi", "jia", "xuexiao",
           "shui", "shiwu", "shuiguo", "zaoshang", "zhongwu", "wanshang",
           "mingtian", "zuotian", "jintian", "xin", "jiu", "hao", "huai", "da",
           "xiao", "qu", "lai", "chi", "he", "shui", "kan", "ting", "shuo",
           "du", "xie", "gongzuo", "pengyou", "ai", "shijie", "guojia",
           "chengshi", "lu", "men", "chuang", "shu", "yizi", "zhuozi",
           "nanren", "nüren", "haizi"],

    "ko": ["na", "neo", "geu", "uri", "neohui", "geudeul", "igeot", "geugeot",
           "mueot", "nugu", "eodi", "eonje", "wae", "eotteoke", "il", "i",
           "sam", "sa", "o", "yuk", "chil", "pal", "gu", "sip", "jip",
           "hakgyo", "mul", "eumsik", "gwail", "ajeossi", "nunkim", "achim",
           "jeongoh", "jeonyeok", "naeil", "eoje", "oneul", "saeroun",
           "oitheun", "joheun", "nappeun", "keun", "jageun", "gada", "oda",
           "meokda", "masida", "jada", "boda", "deudda", "malhada", "ilkda",
           "sseuda", "il", "chingu", "sarang", "segye", "gukga", "dosi",
           "gil", "mun", "chang", "chaek", "uija", "chaeksang", "namja",
           "yeoja", "ai"],

    "vi": ["tôi", "bạn", "anh", "chị", "em", "chúng", "họ", "này", "kia",
           "gì", "ai", "đâu", "khi nào", "tại sao", "như thế nào", "một",
           "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười",
           "nhà", "trường", "nước", "thức ăn", "trái cây", "sáng", "trưa",
           "tối", "ngày mai", "hôm qua", "hôm nay", "mới", "cũ", "tốt",
           "xấu", "lớn", "nhỏ", "đi", "đến", "ăn", "uống", "ngủ", "nhìn",
           "nghe", "nói", "đọc", "viết", "công việc", "bạn bè", "tình yêu",
           "thế giới", "đất nước", "thành phố", "đường", "cửa", "cửa sổ",
           "sách", "ghế", "bàn", "đàn ông", "phụ nữ", "trẻ em"],

    "sw": ["mimi", "wewe", "yeye", "sisi", "ninyi", "wao", "hili", "hilo",
           "nani", "nini", "wapi", "lini", "kwanini", "vipi", "moja", "mbili",
           "tatu", "nne", "tano", "sita", "saba", "nane", "tisa", "kumi",
           "nyumba", "shule", "maji", "chakula", "soko", "siku", "usiku",
           "asubuhi", "jioni", "leo", "jana", "kesho", "zuri", "mbaya",
           "kubwa", "ndogo", "kwenda", "kuja", "kula", "kunywa", "kulala",
           "kuona", "kusikia", "kusema", "kusoma", "kuandika", "kazi",
           "rafiki", "upendo", "dunia", "nchi", "jiji", "barabara", "mlango",
           "dirisha", "kitabu", "kiti", "meza", "mwanaume", "mwanamke",
           "mtoto"],

    "zu": ["mina", "wena", "yena", "thina", "nina", "bona", "lesi", "lelo",
           "ubani", "ini", "kuphi", "nini", "kungani", "kanjani", "kunye",
           "kubili", "kuthathu", "kune", "kuhlamu", "isithupha",
           "isikhombisa", "isishiyagalombili", "isishiyagalolunye", "ishumi",
           "indlu", "isikole", "amanzi", "ukudla", "isikhathi", "kusasa",
           "namuhla", "izolo", "kusasa", "kakhulu", "kancane", "kuhle",
           "kabi", "ukuya", "ukufika", "ukudla", "ukuphuza", "ukulala",
           "ukubona", "ukuzwa", "ukukhuluma", "ukufunda", "ukubhala",
           "umsebenzi", "umngane", "uthando", "omhlaba", "izwe", "idolobha",
           "umgwaqo", "umsindo", "iwindi", "incwadi", "isihlalo", "itafula",
           "indoda", "umfazi", "ingane"],

    "yo": ["emi", "iwo", "oun", "awa", "eyin", "awon", "eyi", "iyen", "kini",
           "tani", "nibo", "nigbawo", "kilode", "bawo", "okan", "eji", "eta",
           "erin", "arun", "efa", "eje", "ejo", "esan", "ewa", "ile",
           "ile-iwe", "omi", "ounje", "oja", "ojo", "oru", "aro", "ale",
           "loni", "ana", "ola", "titun", "ati", "daradara", "buruku", "nla",
           "kekere", "lo", "wa", "je", "mu", "sun", "ri", "gbo", "so", "ka",
           "ko", "ise", "ore", "ife", "aye", "orileede", "ilu", "ona",
           "ilekun", "ferese", "iwe", "aga", "tabili", "okunrin", "obinrin",
           "omode"],

    "am": ["ine", "ante", "ersu", "inja", "inante", "inesu", "yih", "yih",
           "min", "man", "yet", "meles", "lemin", "inidet", "and", "hulett",
           "sost", "arat", "amist", "sidist", "sebat", "siment", "zet",
           "asir", "bet", "timhirtbet", "waha", "megot", "gabaya", "ken",
           "lilit", "tewat", "meseret", "konjo", "meri", "tilik", "tinish",
           "mehed", "meta", "bela", "teta", "tesh", "ayehu", "semahu",
           "meslu", "new", "kedu", "sera", "gibie", "gwadegna", "fikir",
           "alem", "hager", "ketema", "ketema", "menor", "tanta", "tifir",
           "metsek", "seb", "yerfu", "sigab", "wend", "set", "lij"],

    "ha": ["ni", "ka", "shi", "mu", "ku", "su", "wannan", "wancan", "me",
           "wa", "ina", "yaushe", "domin", "yaya", "daya", "biyu", "uku",
           "hudu", "biyar", "shida", "bakwai", "takwas", "tara", "goma",
           "gida", "makaranta", "ruwa", "abinci", "kasuwa", "rana", "dare",
           "safe", "yamma", "yau", "jiya", "gobe", "sabon", "tsoho",
           "mai kyau", "mummunan", "babba", "karami", "tafiya", "zowa", "ci",
           "sha", "kwana", "gani", "ji", "fada", "karanta", "rubuta", "aiki",
           "aboki", "kauna", "duniya", "kasa", "birni", "hanya", "kofo",
           "taga", "littafi", "kujera", "tebur", "namiji", "mace", "yaro"],

    "nv": ["shí", "ni", "haííníísh", "hastiin", "asdzání", "diné", "tʼáá",
           "łáʼ", "naaki", "táá", "dį́į́ʼ", "ashdlaʼ", "hastą́ą́", "tsostsʼid",
           "tseebíí", "náhástʼéí", "tłaʼtsʼid", "neeznáá", "kin", "oltaʼ",
           "tó", "chʼiyáán", "naaldlooshii", "jó", "tʼééʼ", "abiní",
           "anaaʼ", "díí", "níná", "yiską́", "łitso", "łizhin", "dootłʼizh",
           "łichííʼ", "łibáá", "bee", "bílaʼashdlaʼii", "óóltaʼ", "bikeeʼ",
           "bíńákees", "bikeeʼ", "awééʼ", "altso", "ałtsé", "ákótʼéego",
           "tʼááłáʼí", "ałą́ą́", "hodina", "yáʼátʼéeh", "doo", "yóó",
           "hózhó", "chahałheeł", "ndaʼalką́ą́ʼ", "hataał", "ałchíní"],

    "qu": ["ñuqa", "qam", "pay", "ñuqanchik", "qamkuna", "paykuna", "kay",
           "chay", "ima", "pi", "maypi", "imaqtin", "imarayku", "imashina",
           "huk", "iskay", "kimsa", "tawa", "pichqa", "suqta", "qanchis",
           "pusaq", "isqun", "chunka", "wasi", "yachaywasi", "unu", "mikhuy",
           "hatun", "uchuy", "allin", "millay", "riy", "hamuy", "mikhuy",
           "upyay", "puñuy", "qhaway", "uyariy", "rimay", "ñawiy", "qillqay",
           "llankay", "masi", "khuyay", "pacha", "suyu", "llaqta", "ñan",
           "punku", "watana", "panqa", "tiyana", "mesa", "qhari", "warmi",
           "wawa"],

    "chr": ["agiya", "nihi", "ahi", "ani", "ihini", "anvi", "gini", "hawiya",
            "nvhwi", "gado", "hela", "utana", "sawini", "ohili", "sagwi",
            "taline", "joie", "nvhi", "hisgi", "ahlisgi", "osda", "uyoI",
            "utana", "usdi", "awali", "uli", "asdi", "amayi", "asgaya",
            "agehya", "ayvwi", "ulahiyi", "tsunilv", "gunahi", "dawhilv",
            "anitsv", "ganohili", "ganohalidoi", "dikanohi", "wadv", "gowhti",
            "anigilo", "aniwodi", "unalii", "adohi", "ulvelodi", "digohweli",
            "detsanv", "ugata", "asuya", "gohudi", "ohvi", "itsula", "alonv",
            "uwenv"],

    "oj": ["niin", "giin", "aapish", "wiin", "niindamin", "giinamin",
           "owinamin", "maaba", "naana", "moo", "anen", "wegonen", "aandi",
           "aaniish", "aaniin", "bezhik", "niizh", "nswi", "niiwin", "naanan",
           "ningodwaaswi", "niizhwaaswi", "nishwaaswi", "zhaangaso", "zhaang",
           "gikinoo'amaadi", "nibi", "babaama", "odaabaan", "anokii",
           "izhichige", "bimose", "nibaa", "waabama", "nendam", "gagwein",
           "gikendaan", "bizaan", "wenji", "maajaan", "bagwaji", "gitigaan",
           "dibishkaa", "gichi", "zhishi", "jaanii", "nookomis", "ookomisan",
           "mishoomis", "oogimaa", "anishinaabe", "ikwe", "inini",
           "abinoojiinh", "binesi", "makwa", "wajiw", "zaaga'igan"],

    "iu": ["uva", "ivvit", "uanga", "uvagut", "illisi", "uqalimak", "una",
           "taku", "kina", "sumi", "nakurmiik", "qanoq", "ataaseq", "marluk",
           "pingasut", "sisamat", "tallimat", "arfinillit", "marlunnillit",
           "pingasunnillit", "sisamannillit", "quliaq", "tuquraq", "inuk",
           "inukshuk", "nuna", "sila", "imiq", "qimmiq", "nanuq", "tuktu",
           "nalunaaquttaq", "ullaaq", "unnuaq", "tingmiat", "niriit",
           "qaqqaq", "saattuq", "kalaallit", "angut", "arnaq", "irnuk",
           "panik", "iniriq", "majjuti", "isumagijjutiqarniq",
           "qaujimajatuqangit", "piliriqatigiinniq", "avattimut", "naatsi",
           "kangiqtugaapik", "igluit", "nattivak"],
}

# ═══════════════════════════════════════════════════════════════════
# SECTION 3: Schema SQL (Identical to init_databases.py)
# ═══════════════════════════════════════════════════════════════════

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
"""

# ═══════════════════════════════════════════════════════════════════
# SECTION 4: Constants
# ═══════════════════════════════════════════════════════════════════

DB_FOLDER = "database"

LANGUAGES = [
    "en", "es", "de", "fr", "it",
    "hi", "ja", "zh", "ko", "vi",
    "sw", "zu", "yo", "am", "ha",
    "nv", "qu", "chr", "oj", "iu",
]

LANG_NAMES = {
    "en": "English", "es": "Spanish", "de": "German", "fr": "French",
    "it": "Italian", "hi": "Hindi", "ja": "Japanese (Romaji)",
    "zh": "Mandarin (Pinyin)", "ko": "Korean (Romanized)", "vi": "Vietnamese",
    "sw": "Swahili", "zu": "Zulu", "yo": "Yoruba", "am": "Amharic (Romanized)",
    "ha": "Hausa", "nv": "Navajo", "qu": "Quechua", "chr": "Cherokee (Romanized)",
    "oj": "Ojibwe", "iu": "Inuktitut (Romanized)",
}

# ═══════════════════════════════════════════════════════════════════
# SECTION 5: NLP Engine — Levenshtein & BK-Tree
# ═══════════════════════════════════════════════════════════════════

def levenshtein(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j - 1], dp[i][j - 1], dp[i - 1][j])
    return dp[n][m]


class BKNode:
    __slots__ = ("word", "children")

    def __init__(self, word: str):
        self.word = word
        self.children: Dict[int, "BKNode"] = {}


class BKTree:
    def __init__(self):
        self.root: Optional[BKNode] = None

    def add(self, word: str):
        if not self.root:
            self.root = BKNode(word)
            return
        node = self.root
        while True:
            dist = levenshtein(word, node.word)
            if dist in node.children:
                node = node.children[dist]
            else:
                node.children[dist] = BKNode(word)
                break

    def query(self, word: str, max_dist: int) -> List[Tuple[str, int]]:
        result = []

        def _dfs(node: BKNode):
            dist = levenshtein(word, node.word)
            if dist <= max_dist:
                result.append((node.word, dist))
            for d in range(max(0, dist - max_dist), dist + max_dist + 1):
                child = node.children.get(d)
                if child:
                    _dfs(child)

        if self.root:
            _dfs(self.root)
        return result

    def build_from_list(self, words: List[str]):
        self.root = None
        shuffled = list(words)
        random.shuffle(shuffled)
        for w in shuffled:
            self.add(w)


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: Database Manager
# ═══════════════════════════════════════════════════════════════════

class DatabaseManager:
    """Manages a dedicated SQLite database for a single language in ./database/."""

    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.db_dir = os.path.join(os.getcwd(), DB_FOLDER)
        self.db_path = os.path.join(self.db_dir, f"{lang_code}.db")
        self.conn = None
        self._init_db_structure()

    def _init_db_structure(self):
        logger.info(f"Initializing database for '{self.lang_code}' at: {self.db_path}")
        try:
            os.makedirs(self.db_dir, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.executescript(SCHEMA_SQL)
            self.conn.commit()

            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dictionary")
            if cursor.fetchone()[0] == 0:
                logger.info(f"Database empty for '{self.lang_code}'. Seeding …")
                self._seed_database()
            else:
                logger.debug(f"Database for '{self.lang_code}' already populated.")

        except sqlite3.Error as e:
            logger.critical(f"DB init failed for '{self.lang_code}': {e}\n{traceback.format_exc()}")
            raise RuntimeError(f"Database init error: {e}")
        except Exception as e:
            logger.critical(f"Unexpected DB init error for '{self.lang_code}': {e}\n{traceback.format_exc()}")
            raise

    def _seed_database(self):
        words = SEED_MAP.get(self.lang_code, [])
        if not words:
            return
        now = datetime.utcnow().isoformat()
        freq = Counter(words)
        try:
            with self.conn:
                self.conn.executemany(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at)
                       VALUES (?, ?, 0, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET freq = freq + ?, updated_at = ?""",
                    [(w, f, now, now, f, now) for w, f in freq.items()],
                )
                self._upsert_ngrams_internal(words)
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("last_seed_date", now),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("schema_version", "1.0"),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("lang_name", LANG_NAMES.get(self.lang_code, self.lang_code)),
                )
        except sqlite3.Error as e:
            logger.error(f"Seeding database failed: {e}")

    def _upsert_ngrams_internal(self, tokens: List[str]):
        bigram_freq = Counter(zip(tokens, tokens[1:]))
        trigram_freq = Counter(zip(tokens, tokens[1:], tokens[2:]))
        self.conn.executemany(
            """INSERT INTO bigrams (w1, w2, freq) VALUES (?, ?, ?)
               ON CONFLICT(w1, w2) DO UPDATE SET freq = freq + ?""",
            [(w1, w2, f, f) for (w1, w2), f in bigram_freq.items()],
        )
        self.conn.executemany(
            """INSERT INTO trigrams (w1, w2, w3, freq) VALUES (?, ?, ?, ?)
               ON CONFLICT(w1, w2, w3) DO UPDATE SET freq = freq + ?""",
            [(w1, w2, w3, f, f) for (w1, w2, w3), f in trigram_freq.items()],
        )

    def load_words(self) -> Dict[str, int]:
        try:
            cursor = self.conn.execute("SELECT word, freq FROM dictionary")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"Failed to load words for '{self.lang_code}': {e}")
            return {}

    def load_user_words(self) -> Set[str]:
        try:
            cursor = self.conn.execute("SELECT word FROM dictionary WHERE is_user=1")
            return {row[0] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"Failed to load user words for '{self.lang_code}': {e}")
            return set()

    def load_bigrams(self) -> Dict[str, Counter]:
        try:
            cursor = self.conn.execute("SELECT w1, w2, freq FROM bigrams")
            counts = defaultdict(Counter)
            for w1, w2, freq in cursor.fetchall():
                counts[w1][w2] = freq
            return counts
        except sqlite3.Error as e:
            logger.error(f"Failed to load bigrams for '{self.lang_code}': {e}")
            return defaultdict(Counter)

    def load_trigrams(self) -> Counter:
        try:
            cursor = self.conn.execute("SELECT w1, w2, w3, freq FROM trigrams")
            counts = Counter()
            for w1, w2, w3, freq in cursor.fetchall():
                counts[(w1, w2, w3)] = freq
            return counts
        except sqlite3.Error as e:
            logger.error(f"Failed to load trigrams for '{self.lang_code}': {e}")
            return Counter()

    def add_word(self, word: str):
        word = word.lower().strip()
        if not word:
            return
        now = datetime.utcnow().isoformat()
        try:
            with self.conn:
                self.conn.execute(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at)
                       VALUES (?, 1, 1, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET freq = freq + 1, is_user = 1, updated_at = ?""",
                    (word, now, now, now),
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to add word '{word}': {e}")

    def remove_user_word(self, word: str):
        word = word.lower().strip()
        try:
            with self.conn:
                self.conn.execute(
                    "DELETE FROM dictionary WHERE word=? AND is_user=1", (word,)
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to remove word '{word}': {e}")

    def import_corpus(self, text: str):
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            logger.warning("No tokens found in corpus to import.")
            return
        word_freq = Counter(tokens)
        now = datetime.utcnow().isoformat()
        logger.info(f"Importing corpus into '{self.lang_code}'. Tokens: {len(tokens)}")
        try:
            with self.conn:
                self.conn.executemany(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at)
                       VALUES (?, ?, 0, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET freq = freq + ?, updated_at = ?""",
                    [(w, f, now, now, f, now) for w, f in word_freq.items()],
                )
                self._upsert_ngrams_internal(tokens)
            logger.info(f"Corpus imported to '{self.lang_code}'.")
        except sqlite3.Error as e:
            logger.error(f"Corpus import failed for '{self.lang_code}': {e}\n{traceback.format_exc()}")
            raise RuntimeError(f"Database error during import: {e}")

    def get_db_size_mb(self) -> float:
        try:
            return os.path.getsize(self.db_path) / (1024 * 1024)
        except OSError:
            return 0.0

    def get_word_count(self) -> int:
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM dictionary")
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: Language Profile & Text Corrector
# ═══════════════════════════════════════════════════════════════════

class LanguageProfile:
    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.db = DatabaseManager(lang_code)
        self.words_freq: Dict[str, int] = {}
        self.words: Set[str] = set()
        self.user_words: Set[str] = set()
        self.bk = BKTree()
        self.bigram_counts: Dict[str, Counter] = defaultdict(Counter)
        self.trigram_counts: Counter = Counter()
        self.grammar_rules = self._init_grammar_rules()
        self.refresh_from_db()

    def refresh_from_db(self):
        logger.debug(f"Refreshing profile for '{self.lang_code}'")
        self.words_freq = self.db.load_words()
        self.words = set(self.words_freq.keys())
        self.user_words = self.db.load_user_words()
        self.bk = BKTree()
        self.bk.build_from_list(list(self.words))
        self.bigram_counts = self.db.load_bigrams()
        self.trigram_counts = self.db.load_trigrams()

    def _init_grammar_rules(self) -> List[Dict]:
        rules = []
        if self.lang_code == "en":
            rules.extend([
                {"pattern": re.compile(r"\b(your)\s+(going|coming|doing|being|making|having)\b", re.I),
                 "message": "Did you mean 'you're' (you are)?", "replacement": r"you're \2"},
                {"pattern": re.compile(r"\b(\w+)\s+\1\b", re.I),
                 "message": "Repeated word detected.", "replacement": r"\1"},
                {"pattern": re.compile(r"\b(a)\s+([aeiou]\w+)", re.I),
                 "message": "Use 'an' before vowel sounds.", "replacement": r"an \2"},
                {"pattern": re.compile(r"\b(its)\s+(a|the|been|not|very|so|too|really|quite)\b", re.I),
                 "message": "Did you mean 'it's' (it is)?", "replacement": r"it's \2"},
            ])
        else:
            rules.append({"pattern": re.compile(r"\b(\w+)\s+\1\b", re.I),
                          "message": "Repeated word detected.", "replacement": r"\1"})
        return rules


class TextCorrector:
    def __init__(self):
        self.profiles: Dict[str, LanguageProfile] = {}
        self.current_lang = "en"
        self._build_profiles()

    def _build_profiles(self):
        for code in LANGUAGES:
            try:
                self.profiles[code] = LanguageProfile(code)
            except Exception as e:
                logger.critical(f"Failed to build profile for {code}: {e}")

    def set_language(self, lang: str):
        self.current_lang = lang

    def add_word(self, word: str, lang: str = None) -> str:
        lang = lang or self.current_lang
        word = word.lower().strip()
        if not word:
            return "Empty word."
        try:
            self.profiles[lang].db.add_word(word)
            self.profiles[lang].refresh_from_db()
            logger.info(f"Added word '{word}' to {lang}")
            return f"✓ '{word}' added to {lang.upper()} dictionary."
        except Exception as e:
            logger.error(f"Error adding word: {e}")
            return f"Error adding word: {e}"

    def remove_word(self, word: str, lang: str = None) -> str:
        lang = lang or self.current_lang
        word = word.lower().strip()
        try:
            if word in self.profiles[lang].user_words:
                self.profiles[lang].db.remove_user_word(word)
                self.profiles[lang].refresh_from_db()
                logger.info(f"Removed word '{word}' from {lang}")
                return f"✓ '{word}' removed from {lang.upper()} user dict."
            return f"'{word}' not in user dict."
        except Exception as e:
            logger.error(f"Error removing word: {e}")
            return f"Error removing word: {e}"

    def import_corpus(self, file_path: str, lang: str = None):
        lang = lang or self.current_lang
        try:
            text = Path(file_path).read_text(encoding="utf-8")
            self.profiles[lang].db.import_corpus(text)
            self.profiles[lang].refresh_from_db()
            return True, f"Imported corpus to {lang.upper()}. DB updated."
        except IOError as e:
            logger.error(f"File read error: {e}")
            return False, f"Failed to read file: {e}"
        except Exception as e:
            logger.error(f"Import error: {e}")
            return False, f"Import failed: {e}"

    @staticmethod
    def tokenize(text: str) -> List[Dict]:
        tokens = []
        for m in re.finditer(r"\w+|[^\w\s]|\s+", text, re.UNICODE):
            tokens.append({"text": m.group(), "start": m.start(), "end": m.end(),
                           "is_word": bool(re.fullmatch(r"\w+", m.group()))})
        return tokens

    def generate_candidates(self, word: str, max_edit: int = 2, top_k: int = 8) -> List[str]:
        profile = self.profiles[self.current_lang]
        lw = word.lower()
        if lw in profile.words:
            return [lw]
        cand_set = set()
        if profile.bk.root:
            for term, d in profile.bk.query(lw, max_edit):
                if term in profile.words:
                    cand_set.add(term)
        letters = string.ascii_lowercase
        splits = [(lw[:i], lw[i:]) for i in range(len(lw) + 1)]
        edits1 = set(
            [L + R[1:] for L, R in splits if R]
            + [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
            + [L + c + R[1:] for L, R in splits if R for c in letters]
            + [L + c + R for L, R in splits for c in letters]
        )
        for w in edits1:
            if w in profile.words:
                cand_set.add(w)
        candidates = sorted(cand_set, key=lambda w: (-profile.words_freq.get(w, 0), levenshtein(lw, w)))
        return candidates[:top_k] if candidates else [lw]

    def _rank_candidates(self, misspelled: str, candidates: List[str], prev_word: Optional[str]) -> str:
        profile = self.profiles[self.current_lang]
        if not candidates:
            return misspelled
        if not prev_word:
            return max(candidates, key=lambda w: profile.words_freq.get(w, 1))
        best = max(candidates, key=lambda w: profile.bigram_counts.get(prev_word, {}).get(w, 0))
        if profile.bigram_counts.get(prev_word, {}).get(best, 0) == 0:
            return max(candidates, key=lambda w: profile.words_freq.get(w, 1))
        return best

    def correct_text_interactive(self, text: str) -> List[Dict]:
        profile = self.profiles[self.current_lang]
        tokens = self.tokenize(text)
        errors = []
        prev_word = None
        for tok in tokens:
            if not tok["is_word"]:
                continue
            word = tok["text"]
            lw = word.lower()
            if len(lw) <= 1 or lw.isdigit():
                prev_word = lw
                continue
            if lw in profile.words:
                prev_word = lw
                continue
            candidates = self.generate_candidates(word)
            best = self._rank_candidates(lw, candidates, prev_word)
            errors.append({"type": "spelling", "start": tok["start"], "end": tok["end"],
                           "original": word, "suggestion": best,
                           "message": f"Unknown word. Did you mean '{best}'?",
                           "all_candidates": candidates[:5]})
            prev_word = lw
        for rule in profile.grammar_rules:
            for m in rule["pattern"].finditer(text):
                suggestion = m.expand(rule["replacement"])
                errors.append({"type": "grammar", "start": m.start(), "end": m.end(),
                               "original": m.group(), "suggestion": suggestion,
                               "message": rule["message"], "all_candidates": [suggestion]})
        errors.sort(key=lambda e: e["start"])
        return errors

    def correct_beam_search(self, text: str, beam_width: int = 5) -> Tuple[str, float]:
        profile = self.profiles[self.current_lang]
        tokens = self.tokenize(text)
        word_tokens = [t for t in tokens if t["is_word"]]
        words = [t["text"].lower() for t in word_tokens]
        beams: List[Tuple[List[str], float]] = [([], 1.0)]
        total_tri = max(sum(profile.trigram_counts.values()), 1)
        for i, word in enumerate(words):
            new_beams = []
            cands = self.generate_candidates(word, top_k=beam_width)
            for seq, score in beams:
                for cand in cands:
                    if len(seq) >= 2:
                        reward = (profile.trigram_counts.get((seq[-2], seq[-1], cand), 0) + 1) / total_tri
                    elif len(seq) >= 1:
                        reward = (profile.bigram_counts.get(seq[-1], {}).get(cand, 0) + 1) / max(sum(profile.bigram_counts.get(seq[-1], {}).values()), 1)
                    else:
                        reward = profile.words_freq.get(cand, 1) / max(sum(profile.words_freq.values()), 1)
                    new_beams.append((seq + [cand], score * reward))
            beams = heapq.nlargest(beam_width, new_beams, key=lambda x: x[1])
        best_seq, best_score = max(beams, key=lambda x: x[1]) if beams else (words, 0.0)
        return self._reconstruct(tokens, word_tokens, best_seq), best_score

    def correct_mcts(self, text: str, iterations: int = 500) -> Tuple[str, float]:
        profile = self.profiles[self.current_lang]
        tokens = self.tokenize(text)
        word_tokens = [t for t in tokens if t["is_word"]]
        words = [t["text"] for t in word_tokens]
        best_tokens = words[:]
        best_score = self._score_sentence([w.lower() for w in best_tokens], profile)
        for _ in range(iterations):
            if not words:
                break
            i = random.randrange(len(words))
            candidates = self.generate_candidates(words[i])
            new_tokens = best_tokens[:]
            new_tokens[i] = random.choice(candidates)
            score = self._score_sentence([w.lower() for w in new_tokens], profile)
            if score > best_score:
                best_score = score
                best_tokens = new_tokens
        return self._reconstruct(tokens, word_tokens, [w.lower() for w in best_tokens]), best_score

    def _score_sentence(self, words: List[str], profile: LanguageProfile) -> float:
        freq_score = sum(profile.words_freq.get(w, 0) for w in words)
        grammar_penalty = sum(len(list(r["pattern"].finditer(" ".join(words)))) for r in profile.grammar_rules)
        return freq_score - 10 * grammar_penalty

    def _reconstruct(self, all_tokens, word_tokens, new_words) -> str:
        result, wi = [], 0
        for tok in all_tokens:
            if tok["is_word"] and wi < len(new_words):
                replacement = self._preserve_case(tok["text"], new_words[wi])
                result.append((tok["start"], tok["end"], replacement))
                wi += 1
        if not result:
            return "".join(t["text"] for t in all_tokens)
        parts, last_end = [], 0
        for start, end, repl in result:
            parts.append("".join(t["text"] for t in all_tokens if last_end <= t["start"] < start))
            parts.append(repl)
            last_end = end
        parts.append("".join(t["text"] for t in all_tokens if t["start"] >= last_end))
        return "".join(parts)

    @staticmethod
    def _preserve_case(original: str, replacement: str) -> str:
        if original.isupper():
            return replacement.upper()
        if original and original[0].isupper():
            return replacement.capitalize()
        return replacement

    @staticmethod
    def apply_corrections(text: str, errors: List[Dict], decisions: Dict) -> str:
        corrected = text
        for err in sorted(errors, key=lambda e: e["start"], reverse=True):
            decision = decisions.get(err["start"])
            if decision and decision != "ignore":
                corrected = corrected[:err["start"]] + decision + corrected[err["end"]:]
        return corrected

    def get_stats(self, text: str) -> Dict:
        tokens = self.tokenize(text)
        words = [t for t in tokens if t["is_word"]]
        profile = self.profiles.get(self.current_lang)
        unknown = 0
        if profile:
            unknown = sum(1 for w in words if w["text"].lower() not in profile.words and len(w["text"]) > 1)
        return {"chars": len(text), "words": len(words), "unknown_words": unknown}


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: Worker Thread
# ═══════════════════════════════════════════════════════════════════

class CorrectionWorker(QThread):
    finished = Signal(object)

    def __init__(self, corrector, text, mode, **kwargs):
        super().__init__()
        self.corrector = corrector
        self.text = text
        self.mode = mode
        self.kwargs = kwargs

    def run(self):
        try:
            if self.mode == "interactive":
                self.finished.emit({"errors": self.corrector.correct_text_interactive(self.text)})
            elif self.mode == "beam":
                c, s = self.corrector.correct_beam_search(self.text, self.kwargs.get("beam_width", 5))
                self.finished.emit({"corrected": c, "score": s})
            elif self.mode == "mcts":
                c, s = self.corrector.correct_mcts(self.text, self.kwargs.get("iterations", 500))
                self.finished.emit({"corrected": c, "score": s})
            elif self.mode == "import":
                ok, msg = self.corrector.import_corpus(self.kwargs["path"])
                self.finished.emit({"import_ok": ok, "import_msg": msg})
        except Exception as e:
            logger.error(f"Worker Thread Error: {e}\n{traceback.format_exc()}")
            self.finished.emit({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: Custom Widgets
# ═══════════════════════════════════════════════════════════════════

class HighlightTextEdit(QTextEdit):
    def __init__(self, parent=None, readonly=False):
        super().__init__(parent)
        self.setReadOnly(readonly)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

    def clear_highlights(self):
        self.setExtraSelections([])

    def highlight_errors(self, errors: List[Dict]):
        extra = []
        colors = {"spelling": QColor(255, 80, 80, 80), "grammar": QColor(80, 140, 255, 80),
                  "contraction": QColor(255, 180, 40, 80)}
        underlines = {"spelling": QColor(255, 0, 0), "grammar": QColor(0, 80, 255),
                      "contraction": QColor(200, 120, 0)}
        for err in errors:
            sel = QTextEdit.ExtraSelection()
            cursor = self.textCursor()
            cursor.setPosition(err["start"])
            cursor.setPosition(err["end"], QTextCursor.KeepAnchor)
            sel.cursor = cursor
            sel.format.setBackground(colors.get(err["type"], QColor(200, 200, 200, 80)))
            sel.format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            sel.format.setUnderlineColor(underlines.get(err["type"], QColor(128, 128, 128)))
            extra.append(sel)
        self.setExtraSelections(extra)


class ErrorTableWidget(QTableWidget):
    decision_changed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["#", "Type", "Original", "Suggestion", "Message", "Action"])
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self._errors: List[Dict] = []
        self._decisions: Dict[int, str] = {}

    def set_errors(self, errors: List[Dict]):
        self._errors = errors
        self._decisions = {}
        self.setRowCount(len(errors))
        icons = {"spelling": "✏️", "grammar": "📖", "contraction": "📝"}
        for i, err in enumerate(errors):
            self.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.setItem(i, 1, QTableWidgetItem(f"{icons.get(err['type'], '❓')} {err['type'].capitalize()}"))
            self.setItem(i, 2, QTableWidgetItem(err["original"]))
            combo = QComboBox()
            for c in err.get("all_candidates", [err["suggestion"]]):
                combo.addItem(c)
            combo.currentTextChanged.connect(lambda text, start=err["start"]: self._on_combo(start, text))
            self.setCellWidget(i, 3, combo)
            self.setItem(i, 4, QTableWidgetItem(err.get("message", "")))
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            for text, slot in [("✓", self._on_accept), ("✗", self._on_ignore), ("✎", self._on_custom)]:
                btn = QPushButton(text)
                btn.setFixedSize(28, 28)
                btn.clicked.connect(lambda _, start=err["start"], s=slot: s(start))
                action_layout.addWidget(btn)
            self.setCellWidget(i, 5, action_widget)

    def _on_accept(self, start: int):
        for err in self._errors:
            if err["start"] == start:
                self._decisions[start] = err["suggestion"]
                self.decision_changed.emit(start, err["suggestion"])
                break

    def _on_ignore(self, start: int):
        self._decisions[start] = "ignore"
        self.decision_changed.emit(start, "ignore")

    def _on_custom(self, start: int):
        text, ok = QInputDialog.getText(self, "Custom Correction", "Enter your correction:")
        if ok and text.strip():
            self._decisions[start] = text.strip()
            self.decision_changed.emit(start, text.strip())

    def _on_combo(self, start: int, text: str):
        if start in self._decisions and self._decisions[start] != "ignore":
            self._decisions[start] = text
            self.decision_changed.emit(start, text)

    def get_decisions(self) -> Dict:
        return dict(self._decisions)

    def accept_all(self):
        for err in self._errors:
            self._decisions[err["start"]] = err["suggestion"]

    def ignore_all(self):
        for err in self._errors:
            self._decisions[err["start"]] = "ignore"


# ═══════════════════════════════════════════════════════════════════
# SECTION 10: Styles
# ═══════════════════════════════════════════════════════════════════

DARK_STYLE = """
QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
QTextEdit { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; padding: 8px; }
QTextEdit[readOnly="true"] { background-color: #1e1e2e; }
QLineEdit { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; }
QPushButton { background-color: #45475a; color: #cdd6f4; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #585b70; }
QPushButton#primaryBtn { background-color: #89b4fa; color: #1e1e2e; }
QPushButton#primaryBtn:hover { background-color: #74c7ec; }
QPushButton#dangerBtn { background-color: #f38ba8; color: #1e1e2e; }
QPushButton#successBtn { background-color: #a6e3a1; color: #1e1e2e; }
QComboBox { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; }
QComboBox QAbstractItemView { background-color: #181825; color: #cdd6f4; selection-background-color: #45475a; }
QTabWidget::pane { border: 1px solid #45475a; border-radius: 4px; }
QTabBar::tab { background-color: #313244; color: #cdd6f4; padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background-color: #45475a; font-weight: bold; }
QTabBar::tab:hover { background-color: #585b70; }
QTableWidget { background-color: #181825; color: #cdd6f4; gridline-color: #45475a; border: 1px solid #45475a; border-radius: 4px; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background-color: #45475a; }
QHeaderView::section { background-color: #313244; color: #cdd6f4; padding: 6px; border: 1px solid #45475a; font-weight: bold; }
QGroupBox { border: 1px solid #45475a; border-radius: 6px; margin-top: 12px; padding-top: 16px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QLabel { color: #cdd6f4; }
QStatusBar { background-color: #181825; color: #a6adc8; border-top: 1px solid #45475a; }
QToolBar { background-color: #313244; border-bottom: 1px solid #45475a; spacing: 6px; }
QProgressBar { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; text-align: center; color: #cdd6f4; }
QProgressBar::chunk { background-color: #89b4fa; border-radius: 3px; }
QScrollBar:vertical { background-color: #181825; width: 10px; border: none; }
QScrollBar::handle:vertical { background-color: #45475a; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background-color: #45475a; }
QCheckBox { color: #cdd6f4; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #45475a; background-color: #181825; }
QCheckBox::indicator:checked { background-color: #89b4fa; }
QListWidget { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
QListWidget::item { padding: 4px; }
QListWidget::item:selected { background-color: #45475a; }
QMessageBox { background-color: #1e1e2e; color: #cdd6f4; }
"""

LIGHT_STYLE = """
QMainWindow, QWidget { background-color: #eff1f5; color: #4c4f69; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
QTextEdit { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; padding: 8px; }
QTextEdit[readOnly="true"] { background-color: #eff1f5; }
QLineEdit { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; padding: 4px 8px; }
QPushButton { background-color: #ccd0da; color: #4c4f69; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #bcc0cc; }
QPushButton#primaryBtn { background-color: #1e66f5; color: #ffffff; }
QPushButton#primaryBtn:hover { background-color: #2a7de1; }
QPushButton#dangerBtn { background-color: #d20f39; color: #ffffff; }
QPushButton#successBtn { background-color: #40a02b; color: #ffffff; }
QComboBox { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; padding: 4px 8px; }
QComboBox QAbstractItemView { background-color: #ffffff; color: #4c4f69; selection-background-color: #ccd0da; }
QTabWidget::pane { border: 1px solid #bcc0cc; border-radius: 4px; }
QTabBar::tab { background-color: #e6e9ef; color: #4c4f69; padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background-color: #ccd0da; font-weight: bold; }
QTabBar::tab:hover { background-color: #bcc0cc; }
QTableWidget { background-color: #ffffff; color: #4c4f69; gridline-color: #bcc0cc; border: 1px solid #bcc0cc; border-radius: 4px; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background-color: #ccd0da; }
QHeaderView::section { background-color: #e6e9ef; color: #4c4f69; padding: 6px; border: 1px solid #bcc0cc; font-weight: bold; }
QGroupBox { border: 1px solid #bcc0cc; border-radius: 6px; margin-top: 12px; padding-top: 16px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QLabel { color: #4c4f69; }
QStatusBar { background-color: #e6e9ef; color: #7c7f93; border-top: 1px solid #bcc0cc; }
QToolBar { background-color: #e6e9ef; border-bottom: 1px solid #bcc0cc; spacing: 6px; }
QProgressBar { background-color: #e6e9ef; border: 1px solid #bcc0cc; border-radius: 4px; text-align: center; color: #4c4f69; }
QProgressBar::chunk { background-color: #1e66f5; border-radius: 3px; }
QScrollBar:vertical { background-color: #e6e9ef; width: 10px; border: none; }
QScrollBar::handle:vertical { background-color: #bcc0cc; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background-color: #bcc0cc; }
QCheckBox { color: #4c4f69; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #bcc0cc; background-color: #ffffff; }
QCheckBox::indicator:checked { background-color: #1e66f5; }
QListWidget { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; }
QListWidget::item { padding: 4px; }
QListWidget::item:selected { background-color: #ccd0da; }
QMessageBox { background-color: #eff1f5; color: #4c4f69; }
"""


# ═══════════════════════════════════════════════════════════════════
# SECTION 11: Main Window
# ═══════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, corrector: TextCorrector):
        super().__init__()
        self.corrector = corrector
        self.worker = None
        self.current_errors = []
        self.settings = QSettings("NLP_Corrector", "App")
        self._setup_ui()
        self._setup_menu()
        self._restore_settings()
        self._update_db_stats()

    def _setup_ui(self):
        self.setWindowTitle("Advanced NLP Text Corrector")
        self.setMinimumSize(1100, 750)
        self.resize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # ── Top Bar ──
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        for code in LANGUAGES:
            self.lang_combo.addItem(f"{LANG_NAMES.get(code, code)} ({code})", code)
        self.lang_combo.setCurrentText("English (en)")
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        top_bar.addWidget(self.lang_combo)
        top_bar.addSpacing(20)
        self.theme_btn = QPushButton("🌙 Dark")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(True)
        self.theme_btn.setFixedWidth(100)
        self.theme_btn.toggled.connect(self._toggle_theme)
        top_bar.addWidget(self.theme_btn)
        top_bar.addStretch()
        self.stats_label = QLabel("Ready")
        self.stats_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        top_bar.addWidget(self.stats_label)
        main_layout.addLayout(top_bar)

        # ── Splitter ──
        splitter = QSplitter(Qt.Vertical)

        # Editor
        editor_group = QGroupBox("Input Text")
        editor_layout = QVBoxLayout(editor_group)
        self.input_edit = HighlightTextEdit()
        self.input_edit.setPlaceholderText("Type or paste text here, then click 'Check Spelling & Grammar' …")
        editor_layout.addWidget(self.input_edit)
        btn_row = QHBoxLayout()
        self.check_btn = QPushButton("🔍 Check Spelling & Grammar")
        self.check_btn.setObjectName("primaryBtn")
        self.check_btn.clicked.connect(self._on_check)
        btn_row.addWidget(self.check_btn)
        self.beam_btn = QPushButton("🔮 Beam Search")
        self.beam_btn.clicked.connect(self._on_beam)
        btn_row.addWidget(self.beam_btn)
        self.mcts_btn = QPushButton("🎲 MCTS")
        self.mcts_btn.clicked.connect(self._on_mcts)
        btn_row.addWidget(self.mcts_btn)
        self.clear_btn = QPushButton("🗑 Clear")
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        editor_layout.addLayout(btn_row)
        splitter.addWidget(editor_group)

        # Results tabs
        self.result_tabs = QTabWidget()

        # Tab: Interactive
        interactive_widget = QWidget()
        interactive_layout = QVBoxLayout(interactive_widget)
        self.error_table = ErrorTableWidget()
        self.error_table.decision_changed.connect(self._on_decision_changed)
        interactive_layout.addWidget(self.error_table)
        action_row = QHBoxLayout()
        self.accept_all_btn = QPushButton("✓ Accept All")
        self.accept_all_btn.setObjectName("successBtn")
        self.accept_all_btn.clicked.connect(self._on_accept_all)
        action_row.addWidget(self.accept_all_btn)
        self.ignore_all_btn = QPushButton("✗ Ignore All")
        self.ignore_all_btn.setObjectName("dangerBtn")
        self.ignore_all_btn.clicked.connect(self._on_ignore_all)
        action_row.addWidget(self.ignore_all_btn)
        self.apply_btn = QPushButton("✨ Apply Corrections")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.clicked.connect(self._on_apply)
        action_row.addWidget(self.apply_btn)
        action_row.addStretch()
        interactive_layout.addLayout(action_row)
        self.result_tabs.addTab(interactive_widget, "✏️ Interactive")

        # Tab: Auto-Corrected
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        self.output_edit = HighlightTextEdit(readonly=True)
        self.output_edit.setPlaceholderText("Auto-corrected text will appear here …")
        output_layout.addWidget(self.output_edit)
        self.score_label = QLabel("Score: —")
        output_layout.addWidget(self.score_label)
        self.result_tabs.addTab(output_widget, "📄 Auto-Corrected")

        # Tab: Database
        db_widget = QWidget()
        db_layout = QVBoxLayout(db_widget)
        import_row = QHBoxLayout()
        self.import_btn = QPushButton("📂 Import Corpus (.txt)")
        self.import_btn.clicked.connect(self._on_import_corpus)
        import_row.addWidget(self.import_btn)
        import_row.addStretch()
        db_layout.addLayout(import_row)
        dict_group = QGroupBox("User Dictionary")
        dict_layout = QHBoxLayout(dict_group)
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Enter word to add/remove …")
        dict_layout.addWidget(self.word_input)
        self.add_word_btn = QPushButton("➕ Add")
        self.add_word_btn.setObjectName("successBtn")
        self.add_word_btn.clicked.connect(self._on_add_word)
        dict_layout.addWidget(self.add_word_btn)
        self.remove_word_btn = QPushButton("➖ Remove")
        self.remove_word_btn.setObjectName("dangerBtn")
        self.remove_word_btn.clicked.connect(self._on_remove_word)
        dict_layout.addWidget(self.remove_word_btn)
        db_layout.addWidget(dict_group)
        self.word_list = QListWidget()
        self.word_list.setAlternatingRowColors(True)
        db_layout.addWidget(self.word_list)
        self.db_info_label = QLabel("")
        db_layout.addWidget(self.db_info_label)
        self.result_tabs.addTab(db_widget, "🗄 Database")

        splitter.addWidget(self.result_tabs)
        splitter.setSizes([400, 350])
        main_layout.addWidget(splitter)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — Select a language and start typing")

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Import Corpus …", self._on_import_corpus, QKeySequence("Ctrl+O"))
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close, QKeySequence("Ctrl+Q"))
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Clear All", self._on_clear, QKeySequence("Ctrl+Shift+X"))
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About", self._on_about)

    def _restore_settings(self):
        lang = self.settings.value("language", "en")
        idx = self.lang_combo.findData(lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        dark = self.settings.value("dark_mode", True, type=bool)
        self.theme_btn.setChecked(dark)
        self._apply_theme(dark)

    def _save_settings(self):
        self.settings.setValue("language", self.corrector.current_lang)
        self.settings.setValue("dark_mode", self.theme_btn.isChecked())

    def _toggle_theme(self, checked: bool):
        self._apply_theme(checked)
        self.theme_btn.setText("🌙 Dark" if checked else "☀ Light")

    def _apply_theme(self, dark: bool):
        QApplication.instance().setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)

    def _on_lang_changed(self, index: int):
        lang = self.lang_combo.itemData(index)
        if lang:
            self.corrector.set_language(lang)
            self._update_db_stats()
            self._update_word_list()
            self.status.showMessage(f"Switched to {LANG_NAMES.get(lang, lang)}")

    def _update_db_stats(self):
        profile = self.corrector.profiles.get(self.corrector.current_lang)
        if not profile:
            return
        db = profile.db
        wc = db.get_word_count()
        sz = db.get_db_size_mb()
        uw = len(profile.user_words)
        self.db_info_label.setText(f"📂 {db.db_path}  |  {wc} words  |  {uw} user words  |  {sz:.2f} MB")
        self.stats_label.setText(
            f"Lang: {self.corrector.current_lang.upper()}  |  Words: {wc}  |  User: {uw}  |  DB: {sz:.2f} MB")

    def _update_word_list(self):
        self.word_list.clear()
        profile = self.corrector.profiles.get(self.corrector.current_lang)
        if not profile:
            return
        for word in sorted(profile.user_words):
            self.word_list.addItem(word)

    # ── Correction Actions ──

    def _on_check(self):
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.status.showMessage("No text to check.")
            return
        self._start_worker(text, "interactive")

    def _on_beam(self):
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.status.showMessage("No text to correct.")
            return
        self._start_worker(text, "beam", beam_width=5)

    def _on_mcts(self):
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.status.showMessage("No text to correct.")
            return
        self._start_worker(text, "mcts", iterations=500)

    def _start_worker(self, text, mode, **kwargs):
        if self.worker and self.worker.isRunning():
            self.status.showMessage("A correction is already in progress …")
            return
        self.check_btn.setEnabled(False)
        self.beam_btn.setEnabled(False)
        self.mcts_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status.showMessage(f"Running {mode} correction …")
        self.worker = CorrectionWorker(self.corrector, text, mode, **kwargs)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self, result: Dict):
        self.check_btn.setEnabled(True)
        self.beam_btn.setEnabled(True)
        self.mcts_btn.setEnabled(True)
        self.progress.setVisible(False)

        if "error" in result:
            self.status.showMessage(f"Error: {result['error']}")
            QMessageBox.critical(self, "Error", result["error"])
            return

        if "errors" in result:
            self.current_errors = result["errors"]
            self.error_table.set_errors(self.current_errors)
            self.input_edit.highlight_errors(self.current_errors)
            self.result_tabs.setCurrentIndex(0)
            self.status.showMessage(f"Found {len(self.current_errors)} issues.")

        elif "corrected" in result:
            self.output_edit.setPlainText(result["corrected"])
            self.score_label.setText(f"Score: {result['score']:.6f}")
            self.result_tabs.setCurrentIndex(1)
            self.status.showMessage("Auto-correction complete.")

        elif "import_ok" in result:
            ok, msg = result["import_ok"], result["import_msg"]
            if ok:
                self._update_db_stats()
                self._update_word_list()
                self.status.showMessage(msg)
            else:
                self.status.showMessage(msg)
                QMessageBox.warning(self, "Import Error", msg)

    # ── Interactive Actions ──

    def _on_decision_changed(self, start: int, decision: str):
        self.status.showMessage(f"Decision for position {start}: {decision}")

    def _on_accept_all(self):
        self.error_table.accept_all()
        self.status.showMessage("All suggestions accepted.")

    def _on_ignore_all(self):
        self.error_table.ignore_all()
        self.status.showMessage("All suggestions ignored.")

    def _on_apply(self):
        text = self.input_edit.toPlainText()
        decisions = self.error_table.get_decisions()
        if not decisions:
            self.status.showMessage("No corrections to apply.")
            return
        corrected = TextCorrector.apply_corrections(text, self.current_errors, decisions)
        self.input_edit.setPlainText(corrected)
        self.input_edit.clear_highlights()
        self.current_errors = []
        self.error_table.set_errors([])
        self.status.showMessage("Corrections applied!")

    # ── Dictionary Actions ──

    def _on_add_word(self):
        word = self.word_input.text().strip()
        if not word:
            return
        msg = self.corrector.add_word(word)
        self._update_db_stats()
        self._update_word_list()
        self.word_input.clear()
        self.status.showMessage(msg)

    def _on_remove_word(self):
        word = self.word_input.text().strip()
        if not word:
            return
        msg = self.corrector.remove_word(word)
        self._update_db_stats()
        self._update_word_list()
        self.word_input.clear()
        self.status.showMessage(msg)

    def _on_import_corpus(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Corpus", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        self._start_worker("", "import", path=path)

    # ── Misc ──

    def _on_clear(self):
        self.input_edit.clear()
        self.output_edit.clear()
        self.input_edit.clear_highlights()
        self.current_errors = []
        self.error_table.set_errors([])
        self.status.showMessage("Cleared.")

    def _on_about(self):
        QMessageBox.about(self, "About",
                          "Advanced NLP Text Corrector\n\n"
                          "• 20 languages with isolated databases\n"
                          "• BK-tree + Levenshtein spell checking\n"
                          "• Grammar rules with regex patterns\n"
                          "• Interactive, Beam Search & MCTS correction\n"
                          "• User dictionary management\n"
                          "• Dark / Light themes\n\n"
                          "All databases stored in ./database/")

    def closeEvent(self, event):
        self._save_settings()
        for profile in self.corrector.profiles.values():
            profile.db.close()
        super().closeEvent(event)


# ═══════════════════════════════════════════════════════════════════
# SECTION 12: Entry Point
# ═══════════════════════════════════════════════════════════════════

def main():
    setup_logging()
    logger.info("Starting NLP Text Corrector …")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    corrector = TextCorrector()
    window = MainWindow(corrector)
    window.show()

    logger.info("Application ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()