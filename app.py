#!/usr/bin/env python3
"""
Advanced NLP Text Corrector — Self-Contained Single File
==========================================================
A PySide6 desktop application for multi-language spelling and grammar checking.

Features:
  - 20 languages with isolated SQLite databases
  - BK-tree + Levenshtein spell checking
  - Grammar rules & confusion pairs (embedded, no external files needed)
  - Interactive, Beam Search & MCTS correction modes
  - User dictionary management
  - Dark / Light themes
  - Optional: download 50k word-frequency lists from GitHub (one-click in UI)

Usage:
  python app.py
"""

import sys, re, os, heapq, random, string, logging, traceback, urllib.request, urllib.error
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
from difflib import SequenceMatcher
import sqlite3

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QTabWidget, QComboBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QLineEdit, QMessageBox, QSplitter, QStatusBar,
    QProgressBar, QAbstractItemView, QInputDialog, QListWidget,
    QMenu, QToolBar, QCheckBox, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, QSettings, QTimer, QSize
from PySide6.QtGui import (
    QTextCharFormat, QColor, QFont, QTextCursor, QKeySequence, QAction,
    QIcon, QPalette,
)

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Logging
# ═══════════════════════════════════════════════════════════════════

def setup_logging():
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-18s | %(message)s", "%H:%M:%S"
    ))
    logging.getLogger().addHandler(ch)
    logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger("NLP_Corrector")

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Constants, Schema & Data
# ═══════════════════════════════════════════════════════════════════

DB_FOLDER = "database"

LANGUAGES = [
    "en", "es", "de", "fr", "it", "hi", "ja", "zh", "ko", "vi",
    "sw", "zu", "yo", "am", "ha", "nv", "qu", "chr", "oj", "iu",
]
LANG_NAMES = {
    "en": "English", "es": "Spanish", "de": "German", "fr": "French",
    "it": "Italian", "hi": "Hindi", "ja": "Japanese (Romaji)",
    "zh": "Mandarin (Pinyin)", "ko": "Korean (Romanized)", "vi": "Vietnamese",
    "sw": "Swahili", "zu": "Zulu", "yo": "Yoruba", "am": "Amharic (Romanized)",
    "ha": "Hausa", "nv": "Navajo", "qu": "Quechua", "chr": "Cherokee (Romanized)",
    "oj": "Ojibwe", "iu": "Inuktitut (Romanized)",
}

FREQ_BASE_URL = (
    "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
    "master/content/2018/{lang}/{lang}_50k.txt"
)
DOWNLOAD_LANGS = {"en", "es", "de", "fr", "it", "hi", "ja", "zh", "ko",
                  "vi", "sw", "zu", "yo", "am", "ha"}

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
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dictionary (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT NOT NULL UNIQUE, freq INTEGER NOT NULL DEFAULT 1, is_user INTEGER NOT NULL DEFAULT 0 CHECK(is_user IN (0,1)), created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word);
CREATE INDEX IF NOT EXISTS idx_dict_user ON dictionary(is_user);
CREATE TABLE IF NOT EXISTS bigrams (id INTEGER PRIMARY KEY AUTOINCREMENT, w1 TEXT NOT NULL, w2 TEXT NOT NULL, freq INTEGER NOT NULL DEFAULT 1, UNIQUE(w1,w2));
CREATE INDEX IF NOT EXISTS idx_bigrams_w1 ON bigrams(w1);
CREATE TABLE IF NOT EXISTS trigrams (id INTEGER PRIMARY KEY AUTOINCREMENT, w1 TEXT NOT NULL, w2 TEXT NOT NULL, w3 TEXT NOT NULL, freq INTEGER NOT NULL DEFAULT 1, UNIQUE(w1,w2,w3));
CREATE INDEX IF NOT EXISTS idx_trigrams_w1w2 ON trigrams(w1,w2);
CREATE TABLE IF NOT EXISTS grammar_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, rule_type TEXT NOT NULL, pattern TEXT NOT NULL, message TEXT NOT NULL, replacement TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS idx_grammar_type ON grammar_rules(rule_type);
CREATE TABLE IF NOT EXISTS confusion_pairs (id INTEGER PRIMARY KEY AUTOINCREMENT, wrong TEXT NOT NULL, correct TEXT NOT NULL, context_hint TEXT, message TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_confusion_wrong ON confusion_pairs(wrong);
"""

# ── Grammar Rules (embedded from download_dictionaries.py) ──────────

GRAMMAR_RULES = {
    "en": [
        {"rule_type": "regex", "pattern": r"\b(your)\s+(going|coming|doing|being|making|having|running|talking|walking|looking|trying|working|playing|saying|taking|getting|feeling|moving|living|giving|reading|writing|thinking|sitting|standing|sleeping|eating|drinking|watching|listening|waiting|leaving|putting|bringing|keeping|letting|setting|hitting|cutting|shutting|hurting|costing)\b",
         "message": "Did you mean 'you're' (you are)?", "replacement": r"you're \2", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(its)\s+(a|an|the|been|not|very|so|too|really|quite|just|also|still|already|always|never|often|probably|likely|certainly|definitely|clearly|obviously|apparently|supposed|going|been)\b",
         "message": "Did you mean 'it's' (it is)?", "replacement": r"it's \2", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(there)\s+(going|coming|doing|being|making|having|running|looking|trying|working|playing|taking|getting|sitting|standing|sleeping|eating|watching|waiting|leaving|coming|supposed)\b",
         "message": "Did you mean 'they're' (they are)?", "replacement": r"they're \2", "priority": 8},
        {"rule_type": "regex", "pattern": r"\b(a)\s+([aeiou]\w+)", "message": "Use 'an' before vowel sounds.", "replacement": r"an \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(an)\s+([bcdfghjklmnpqrstvwxyz]\w+)", "message": "Use 'a' before consonant sounds.", "replacement": r"a \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(could|would|should|must)\s+of\b", "message": "Use 'have' instead of 'of' after modal verbs.", "replacement": r"\1 have", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(alot)\b", "message": "'alot' is not a word. Did you mean 'a lot'?", "replacement": r"a lot", "priority": 9},
        {"rule_type": "regex", "pattern": r"\b(i)\s+\w+", "message": "Capitalize 'I' as a pronoun.", "replacement": r"I", "priority": 2},
        {"rule_type": "regex", "pattern": r"\b(cannot)\s+(help|but|stand|bear|afford)\b", "message": "Correct usage: 'cannot' + verb.", "replacement": r"cannot \2", "priority": 1},
        {"rule_type": "regex", "pattern": r"\b(im)\s+(not|sure|going|sorry|happy|glad|afraid|tired|hungry|thirsty|busy|ready|interested|concerned|aware|excited|worried|curious|impressed|confident|certain)\b",
         "message": "Did you mean 'I'm' (I am)?", "replacement": r"I'm \2", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(didnt|doesnt|dont|cant|wont|wouldnt|couldnt|shouldnt|wasnt|werent|isnt|arent|hasnt|havent|hadnt)\b",
         "message": "Missing apostrophe in contraction.", "replacement": r"\1", "priority": 8},
        {"rule_type": "regex", "pattern": r"\b(he|she|it)\s+(don't)\b", "message": "Use 'doesn't' with 3rd person singular.", "replacement": r"\1 doesn't", "priority": 7},
    ],
    "es": [
        {"rule_type": "regex", "pattern": r"\b(hay)\s+(un|una|el|la|los|las|mucho|mucha|muchos|muchas|poco|poca|pocos|pocas|más|menos)\b",
         "message": "Verifique: 'hay' (verbo haber) vs 'ay' (interjección).", "replacement": r"hay \2", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(mas)\s+(que|de|el|la|los|las|un|una)\b",
         "message": "¿Quiso decir 'más' (con acento)?", "replacement": r"más \2", "priority": 6},
        {"rule_type": "regex", "pattern": r"\b(aun)\s+(cuando|que|si)\b",
         "message": "¿Quiso decir 'aún' (todavía)?", "replacement": r"aún \2", "priority": 6},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Palabra repetida.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(tu)\s+(casa|familia|madre|padre|vida|trabajo|nombre|país)\b",
         "message": "Verifique: 'tu' (posesivo) vs 'tú' (pronombre).", "replacement": r"tu \2", "priority": 2},
        {"rule_type": "regex", "pattern": r"\b(el)\s+(es|era|está|estaba|será|sería|ha|había|puede|podía|tiene|tenía|quiere|quería|sabe|sabía|va|iba|viene|venía)\b",
         "message": "¿Quiso decir 'él' (pronombre)?", "replacement": r"él \2", "priority": 4},
    ],
    "de": [
        {"rule_type": "regex", "pattern": r"\b(das)\s+(wir|ich|du|er|sie|es|ihr|Sie)\s+(machen|wollen|können|müssen|sollen|dürfen|werden|haben|sein|lassen|bringen|geben|finden|wissen|denken|glauben|sehen|kommen|gehen|brauchen|versuchen)\b",
         "message": "Meinten Sie 'dass' (Konjunktion)?", "replacement": r"dass \2 \3", "priority": 9},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Wiederholtes Wort erkannt.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(seid)\s+(ihr|Ihr)\b",
         "message": "Verwechselung von 'seit' (Zeit) und 'seid' (Verb).", "replacement": r"seit ihr", "priority": 7},
        {"rule_type": "regex", "pattern": r"\b(wider)\s+(erwartung|Willen|spiegeln|richten)\b",
         "message": "Meinten Sie 'wider' oder 'wieder'?", "replacement": r"wider \2", "priority": 5},
    ],
    "fr": [
        {"rule_type": "regex", "pattern": r"\b(a)\s+(fait|été|vu|pris|mis|donné|dit|voulu|pu|dû|su|cru|dû|eu|venu|allé|resté|devenu|paru|semblé|né|mort)\b",
         "message": "Vérifiez: 'a' (verbe avoir) vs 'à' (préposition).", "replacement": r"a \2", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(ou)\s+(est|sont|était|sera|serait|a|ont|avait|aura|aurait|peut|doit|va|vient|faut|semble|paraît|reste)\b",
         "message": "Vouliez-vous dire 'où' (lieu/question)?", "replacement": r"où \2", "priority": 7},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Mot répété détecté.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(la)\s+(ou|et|mais|donc|car|ni|que|qui|quand|si|comme|puisque)\b",
         "message": "Vouliez-vous dire 'là' (lieu)?", "replacement": r"là \2", "priority": 6},
    ],
    "it": [
        {"rule_type": "regex", "pattern": r"\b(e)\s+(stato|stata|stati|state|andato|andata|andati|andate|venuto|venuta|venuti|venute|detto|fatto|visto|potuto|voluto|dovuto|saputo|avuto|dato|messo|preso|scritto|letto|conosciuto)\b",
         "message": "Verificare: 'è' (verbo essere) vs 'e' (congiunzione).", "replacement": r"è \2", "priority": 8},
        {"rule_type": "regex", "pattern": r"\b(li)\s+(ho|hai|ha|abbiamo|avete|hanno|vedo|vedi|vede|vediamo|vedete|vedono|conosco|conosci|conosce|conosciamo|conoscete|conoscono)\b",
         "message": "Verificare: 'li' (pronome) vs 'lì' (avverbio di luogo).", "replacement": r"li \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Parola ripetuta rilevata.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(ne)\s+(ho|hai|ha|abbiamo|avete|hanno|sono|sei|è|siamo|siete)\b",
         "message": "Verificare: 'né' (congiunzione negativa) vs 'ne' (pronome/partitivo).", "replacement": r"ne \2", "priority": 5},
    ],
}
# Add repeated-word rule for languages that don't have specific rules
for _lang in LANGUAGES:
    if _lang not in GRAMMAR_RULES:
        GRAMMAR_RULES[_lang] = [
            {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
        ]

# ── Confusion Pairs (embedded from download_dictionaries.py) ────────

CONFUSION_PAIRS = {
    "en": [
        ("their", "there", "location", "Did you mean 'there' (location)?"),
        ("their", "they're", "contraction", "Did you mean 'they're' (they are)?"),
        ("there", "their", "possession", "Did you mean 'their' (possessive)?"),
        ("there", "they're", "contraction", "Did you mean 'they're' (they are)?"),
        ("your", "you're", "contraction", "Did you mean 'you're' (you are)?"),
        ("youre", "you're", "contraction", "Did you mean 'you're' (you are)?"),
        ("its", "it's", "contraction", "Did you mean 'it's' (it is)?"),
        ("its'", "it's", "contraction", "Did you mean 'it's' (it is)?"),
        ("affect", "effect", "verb/noun", "Did you mean 'effect' (noun)? If verb, 'affect' is correct."),
        ("effect", "affect", "noun/verb", "Did you mean 'affect' (verb)? If noun, 'effect' is correct."),
        ("then", "than", "comparison", "Did you mean 'than' (comparison)?"),
        ("than", "then", "time/sequence", "Did you mean 'then' (time/sequence)?"),
        ("lose", "loose", "not-tight", "Did you mean 'loose' (not tight)? If 'lose' (fail to win), this is correct."),
        ("loose", "lose", "misplace/fail", "Did you mean 'lose' (misplace/fail)?"),
        ("accept", "except", "exclusion", "Did you mean 'except' (exclusion)?"),
        ("except", "accept", "receive", "Did you mean 'accept' (receive)?"),
        ("weather", "whether", "if/whether", "Did you mean 'whether' (if)?"),
        ("whether", "weather", "climate", "Did you mean 'weather' (climate)?"),
        ("piece", "peace", "no-war", "Did you mean 'peace' (no war)?"),
        ("peace", "piece", "part", "Did you mean 'piece' (part)?"),
        ("principal", "principle", "rule/belief", "Did you mean 'principle' (rule/belief)?"),
        ("principle", "principal", "head/main", "Did you mean 'principal' (head/main)?"),
        ("stationary", "stationery", "writing-supplies", "Did you mean 'stationery' (writing supplies)?"),
        ("stationery", "stationary", "not-moving", "Did you mean 'stationary' (not moving)?"),
        ("complement", "compliment", "praise", "Did you mean 'compliment' (praise)?"),
        ("compliment", "complement", "complete", "Did you mean 'complement' (complete)?"),
        ("desert", "dessert", "sweet-food", "Did you mean 'dessert' (sweet food)?"),
        ("dessert", "desert", "dry-land/abandon", "Did you mean 'desert' (dry land/abandon)?"),
        ("advise", "advice", "noun", "Did you mean 'advice' (noun)? 'Advise' is a verb."),
        ("advice", "advise", "verb", "Did you mean 'advise' (verb)? 'Advice' is a noun."),
        ("breath", "breathe", "verb", "Did you mean 'breathe' (verb)? 'Breath' is a noun."),
        ("breathe", "breath", "noun", "Did you mean 'breath' (noun)? 'Breathe' is a verb."),
        ("choose", "chose", "past-tense", "Did you mean 'chose' (past tense)? 'Choose' is present."),
        ("chose", "choose", "present", "Did you mean 'choose' (present)? 'Chose' is past."),
        ("quite", "quiet", "silent", "Did you mean 'quiet' (silent)?"),
        ("quiet", "quite", "very/fairly", "Did you mean 'quite' (very/fairly)?"),
        ("through", "threw", "past-throw", "Did you mean 'threw' (past of throw)?"),
        ("threw", "through", "via", "Did you mean 'through' (via)?"),
        ("weak", "week", "7-days", "Did you mean 'week' (7 days)?"),
        ("week", "weak", "not-strong", "Did you mean 'weak' (not strong)?"),
        ("aloud", "allowed", "permitted", "Did you mean 'allowed' (permitted)?"),
        ("allowed", "aloud", "out-loud", "Did you mean 'aloud' (out loud)?"),
        ("bare", "bear", "animal/carry", "Did you mean 'bear' (animal/carry)?"),
        ("bear", "bare", "naked", "Did you mean 'bare' (naked)?"),
        ("brake", "break", "smash", "Did you mean 'break' (smash)?"),
        ("break", "brake", "stop", "Did you mean 'brake' (stop)?"),
        ("coarse", "course", "class/path", "Did you mean 'course' (class/path)?"),
        ("course", "coarse", "rough", "Did you mean 'coarse' (rough)?"),
        ("hear", "here", "location", "Did you mean 'here' (location)?"),
        ("here", "hear", "listen", "Did you mean 'hear' (listen)?"),
        ("hole", "whole", "entire", "Did you mean 'whole' (entire)?"),
        ("whole", "hole", "opening", "Did you mean 'hole' (opening)?"),
        ("know", "no", "negative", "Did you mean 'no' (negative)?"),
        ("no", "know", "understand", "Did you mean 'know' (understand)?"),
        ("meet", "meat", "food", "Did you mean 'meat' (food)?"),
        ("meat", "meet", "encounter", "Did you mean 'meet' (encounter)?"),
        ("plain", "plane", "aircraft", "Did you mean 'plane' (aircraft)?"),
        ("plane", "plain", "simple", "Did you mean 'plain' (simple)?"),
        ("right", "write", "verb", "Did you mean 'write' (verb)?"),
        ("write", "right", "correct/direction", "Did you mean 'right' (correct/direction)?"),
        ("sail", "sale", "selling", "Did you mean 'sale' (selling)?"),
        ("sale", "sail", "boat", "Did you mean 'sail' (boat)?"),
        ("scene", "seen", "viewed", "Did you mean 'seen' (viewed)?"),
        ("seen", "scene", "view", "Did you mean 'scene' (view)?"),
        ("site", "sight", "vision", "Did you mean 'sight' (vision)?"),
        ("sight", "site", "location", "Did you mean 'site' (location)?"),
        ("wait", "weight", "heaviness", "Did you mean 'weight' (heaviness)?"),
        ("weight", "wait", "delay", "Did you mean 'wait' (delay)?"),
        ("ware", "wear", "clothing", "Did you mean 'wear' (clothing)?"),
        ("wear", "ware", "goods", "Did you mean 'ware' (goods)?"),
        ("were", "where", "location", "Did you mean 'where' (location)?"),
        ("where", "were", "past-be", "Did you mean 'were' (past of be)?"),
    ],
    "es": [
        ("hay", "ay", "interjección", "¿Quiso decir 'ay' (interjección)?"),
        ("ay", "hay", "verbo-haber", "¿Quiso decir 'hay' (verbo haber)?"),
        ("mas", "más", "cantidad", "¿Quiso decir 'más' (con acento, cantidad)?"),
        ("más", "mas", "pero", "¿Quiso decir 'mas' (pero)?"),
        ("aun", "aún", "todavía", "¿Quiso decir 'aún' (todavía)?"),
        ("aún", "aun", "incluso", "¿Quiso decir 'aun' (incluso)?"),
        ("como", "cómo", "interrogativo", "¿Quiso decir 'cómo' (interrogativo)?"),
        ("cómo", "como", "comparativo", "¿Quiso decir 'como' (comparativo)?"),
        ("que", "qué", "interrogativo", "¿Quiso decir 'qué' (interrogativo)?"),
        ("qué", "que", "relativo", "¿Quiso decir 'que' (relativo)?"),
        ("mi", "mí", "pronombre", "¿Quiso decir 'mí' (pronombre)?"),
        ("mí", "mi", "posesivo", "¿Quiso decir 'mi' (posesivo)?"),
        ("tu", "tú", "pronombre", "¿Quiso decir 'tú' (pronombre)?"),
        ("tú", "tu", "posesivo", "¿Quiso decir 'tu' (posesivo)?"),
        ("el", "él", "pronombre", "¿Quiso decir 'él' (pronombre)?"),
        ("él", "el", "artículo", "¿Quiso decir 'el' (artículo)?"),
        ("se", "sé", "verbo-saber", "¿Quiso decir 'sé' (verbo saber)?"),
        ("sé", "se", "pronombre", "¿Quiso decir 'se' (pronombre)?"),
        ("te", "té", "bebida", "¿Quiso decir 'té' (bebida)?"),
        ("té", "te", "pronombre", "¿Quiso decir 'te' (pronombre)?"),
        ("si", "sí", "afirmación", "¿Quiso decir 'sí' (afirmación)?"),
        ("sí", "si", "condicional", "¿Quiso decir 'si' (condicional)?"),
        ("solo", "sólo", "solamente", "¿Quiso decir 'sólo' (solamente)?"),
        ("sólo", "solo", "adjetivo", "¿Quiso decir 'solo' (adjetivo)?"),
        ("ha", "a", "preposición", "¿Quiso decir 'a' (preposición) en vez de 'ha' (verbo)?"),
        ("a", "ha", "verbo", "¿Quiso decir 'ha' (verbo haber)?"),
        ("echo", "hecho", "participio", "¿Quiso decir 'hecho' (participio de hacer)?"),
        ("hecho", "echo", "verbo-echar", "¿Quiso decir 'echo' (verbo echar)?"),
        ("valla", "vaya", "interjección", "¿Quiso decir 'vaya' (interjección)?"),
        ("vaya", "valla", "cerca", "¿Quiso decir 'valla' (cerca)?"),
        ("baya", "vaya", "interjección", "¿Quiso decir 'vaya' (interjección)?"),
        ("haya", "aya", "niñera", "¿Quiso decir 'aya' (niñera)?"),
        ("aya", "haya", "verbo-haber", "¿Quiso decir 'haya' (verbo haber)?"),
        ("halla", "haya", "verbo-haber", "¿Quiso decir 'haya' (verbo haber)?"),
        ("haya", "halla", "verbo-hallar", "¿Quiso decir 'halla' (verbo hallar)?"),
    ],
    "de": [
        ("das", "dass", "Konjunktion", "Meinten Sie 'dass' (Konjunktion)?"),
        ("dass", "das", "Artikel", "Meinten Sie 'das' (Artikel)?"),
        ("seit", "seid", "Verb-sein", "Meinten Sie 'seid' (Verb sein, 2. Person Plural)?"),
        ("seid", "seit", "Zeitangabe", "Meinten Sie 'seit' (Zeitangabe)?"),
        ("wider", "wieder", "nochmals", "Meinten Sie 'wieder' (nochmals)?"),
        ("wieder", "wider", "gegen", "Meinten Sie 'wider' (gegen)?"),
        ("muß", "muss", "neue-Rechtschreibung", "Verwenden Sie 'muss' (neue Rechtschreibung)."),
    ],
    "fr": [
        ("a", "à", "préposition", "Vouliez-vous dire 'à' (préposition)?"),
        ("à", "a", "verbe-avoir", "Vouliez-vous dire 'a' (verbe avoir, présent)?"),
        ("ou", "où", "lieu", "Vouliez-vous dire 'où' (lieu/question)?"),
        ("où", "ou", "conjonction", "Vouliez-vous dire 'ou' (conjonction)?"),
        ("ce", "se", "réfléchi", "Vouliez-vous dire 'se' (pronom réfléchi)?"),
        ("se", "ce", "démonstratif", "Vouliez-vous dire 'ce' (déterminant)?"),
        ("la", "là", "lieu", "Vouliez-vous dire 'là' (lieu)?"),
        ("là", "la", "article", "Vouliez-vous dire 'la' (article)?"),
        ("du", "dû", "participe", "Vouliez-vous dire 'dû' (participe passé de devoir)?"),
        ("dû", "du", "article", "Vouliez-vous dire 'du' (article)?"),
        ("sur", "sûr", "certain", "Vouliez-vous dire 'sûr' (certain)?"),
        ("sûr", "sur", "préposition", "Vouliez-vous dire 'sur' (préposition)?"),
        ("et", "est", "verbe", "Vouliez-vous dire 'est' (verbe être)?"),
        ("est", "et", "conjonction", "Vouliez-vous dire 'et' (conjonction)?"),
        ("son", "sont", "verbe", "Vouliez-vous dire 'sont' (verbe être)?"),
        ("sont", "son", "possessif", "Vouliez-vous dire 'son' (possessif)?"),
        ("peu", "peut", "verbe", "Vouliez-vous dire 'peut' (verbe pouvoir)?"),
        ("peut", "peu", "quantité", "Vouliez-vous dire 'peu' (quantité)?"),
        ("tout", "tous", "pluriel", "Vouliez-vous dire 'tous' (pluriel)?"),
        ("tous", "tout", "singulier", "Vouliez-vous dire 'tout' (singulier)?"),
    ],
    "it": [
        ("e", "è", "verbo-essere", "Volevate dire 'è' (verbo essere)?"),
        ("è", "e", "congiunzione", "Volevate dire 'e' (congiunzione)?"),
        ("li", "lì", "avverbio-luogo", "Volevate dire 'lì' (avverbio di luogo)?"),
        ("lì", "li", "pronome", "Volevate dire 'li' (pronome)?"),
        ("la", "là", "avverbio-luogo", "Volevate dire 'là' (avverbio di luogo)?"),
        ("là", "la", "articolo", "Volevate dire 'la' (articolo)?"),
        ("se", "sé", "pronome-riflessivo", "Volevate dire 'sé' (pronome riflessivo)?"),
        ("sé", "se", "congiunzione", "Volevate dire 'se' (congiunzione)?"),
        ("ne", "né", "negazione", "Volevate dire 'né' (congiunzione negativa)?"),
        ("né", "ne", "pronome", "Volevate dire 'ne' (pronome/partitivo)?"),
        ("da", "dà", "verbo-dare", "Volevate dire 'dà' (verbo dare)?"),
        ("dà", "da", "preposizione", "Volevate dire 'da' (preposizione)?"),
        ("si", "sì", "affermazione", "Volevate dire 'sì' (affermazione)?"),
        ("sì", "si", "pronome", "Volevate dire 'si' (pronome)?"),
        ("te", "té", "bevanda", "Volevate dire 'té' (bevanda)?"),
        ("té", "te", "pronome", "Volevate dire 'te' (pronome)?"),
    ],
}


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: NLP Engine
# ═══════════════════════════════════════════════════════════════════

def levenshtein(a: str, b: str) -> int:
    if not a: return len(b)
    if not b: return len(a)
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1): dp[i][0] = i
    for j in range(m+1): dp[0][j] = j
    for i in range(1, n+1):
        for j in range(1, m+1):
            if a[i-1] == b[j-1]: dp[i][j] = dp[i-1][j-1]
            else: dp[i][j] = 1 + min(dp[i-1][j-1], dp[i][j-1], dp[i-1][j])
    return dp[n][m]


class BKNode:
    __slots__ = ("word", "children")
    def __init__(self, word): self.word = word; self.children = {}


class BKTree:
    def __init__(self): self.root = None
    def add(self, word):
        if not self.root: self.root = BKNode(word); return
        node = self.root
        while True:
            d = levenshtein(word, node.word)
            if d in node.children: node = node.children[d]
            else: node.children[d] = BKNode(word); break
    def query(self, word, max_dist):
        result = []
        def _dfs(n):
            d = levenshtein(word, n.word)
            if d <= max_dist: result.append((n.word, d))
            for k in range(max(0, d-max_dist), d+max_dist+1):
                c = n.children.get(k)
                if c: _dfs(c)
        if self.root: _dfs(self.root)
        return result
    def build_from_list(self, words):
        self.root = None
        w = list(words); random.shuffle(w)
        for x in w: self.add(x)


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: Database Manager (self-contained)
# ═══════════════════════════════════════════════════════════════════

class DatabaseManager:
    def __init__(self, lang_code):
        self.lang_code = lang_code
        self.db_dir = os.path.join(os.getcwd(), DB_FOLDER)
        self.db_path = os.path.join(self.db_dir, f"{lang_code}.db")
        self.conn = None
        self._init()

    def _init(self):
        os.makedirs(self.db_dir, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dictionary")
        if cur.fetchone()[0] == 0:
            self._seed()
        self._ensure_grammar_data()

    def _seed(self):
        words = SEED_MAP.get(self.lang_code, [])
        if not words: return
        now = datetime.utcnow().isoformat()
        freq = Counter(words)
        with self.conn:
            self.conn.executemany(
                "INSERT INTO dictionary (word,freq,is_user,created_at,updated_at) VALUES (?, ?,0,?,?) "
                "ON CONFLICT(word) DO UPDATE SET freq=freq+?,updated_at=?",
                [(w,f,now,now,f,now) for w,f in freq.items()],
            )
            bf = Counter(zip(words, words[1:]))
            self.conn.executemany(
                "INSERT INTO bigrams (w1,w2,freq) VALUES (?,?,?) "
                "ON CONFLICT(w1,w2) DO UPDATE SET freq=freq+?",
                [(a,b,f,f) for (a,b),f in bf.items()],
            )
            tf = Counter(zip(words, words[1:], words[2:]))
            self.conn.executemany(
                "INSERT INTO trigrams (w1,w2,w3,freq) VALUES (?,?,?,?) "
                "ON CONFLICT(w1,w2,w3) DO UPDATE SET freq=freq+?",
                [(a,b,c,f,f) for (a,b,c),f in tf.items()],
            )

    def _ensure_grammar_data(self):
        """Insert embedded grammar rules and confusion pairs on first run."""
        # Only insert if no rules exist yet
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM grammar_rules")
        if cur.fetchone()[0] == 0:
            rules = GRAMMAR_RULES.get(self.lang_code, [])
            if rules:
                with self.conn:
                    self.conn.executemany(
                        "INSERT INTO grammar_rules (rule_type,pattern,message,replacement,priority,enabled) VALUES (?,?,?, ?,?,1)",
                        [(r["rule_type"], r["pattern"], r["message"], r["replacement"], r.get("priority", 0))
                         for r in rules],
                    )
                logger.info(f"  Inserted {len(rules)} grammar rules for {self.lang_code}")

        cur.execute("SELECT COUNT(*) FROM confusion_pairs")
        if cur.fetchone()[0] == 0:
            pairs = CONFUSION_PAIRS.get(self.lang_code, [])
            if pairs:
                with self.conn:
                    self.conn.executemany(
                        "INSERT INTO confusion_pairs (wrong,correct,context_hint,message) VALUES (?,?,?,?)",
                        [(p[0], p[1], p[2], p[3]) for p in pairs],
                    )
                logger.info(f"  Inserted {len(pairs)} confusion pairs for {self.lang_code}")

        now = datetime.utcnow().isoformat()
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '2.0')")
            self.conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_init', ?)", (now,))

    def load_words(self) -> Dict[str,int]:
        try: return {r[0]:r[1] for r in self.conn.execute("SELECT word,freq FROM dictionary").fetchall()}
        except: return {}

    def load_user_words(self) -> Set[str]:
        try: return {r[0] for r in self.conn.execute("SELECT word FROM dictionary WHERE is_user=1").fetchall()}
        except: return set()

    def load_bigrams(self) -> Dict[str,Counter]:
        try:
            c = defaultdict(Counter)
            for w1,w2,f in self.conn.execute("SELECT w1,w2,freq FROM bigrams").fetchall(): c[w1][w2]=f
            return c
        except: return defaultdict(Counter)

    def load_trigrams(self) -> Counter:
        try: return Counter({(r[0],r[1],r[2]):r[3] for r in self.conn.execute("SELECT w1,w2,w3,freq FROM trigrams").fetchall()})
        except: return Counter()

    def load_grammar_rules(self) -> List[Dict]:
        try:
            return [{"rule_type":r[0],"pattern":re.compile(r[1]),"message":r[2],"replacement":r[3],"priority":r[4]}
                    for r in self.conn.execute("SELECT rule_type,pattern,message,replacement,priority FROM grammar_rules WHERE enabled=1 ORDER BY priority DESC").fetchall()
                    if r[1]]
        except: return []

    def load_confusion_pairs(self) -> Dict[str, List[Dict]]:
        try:
            d = defaultdict(list)
            for wrong, correct, hint, msg in self.conn.execute("SELECT wrong,correct,context_hint,message FROM confusion_pairs").fetchall():
                d[wrong.lower()].append({"correct":correct,"hint":hint,"message":msg})
            return d
        except: return defaultdict(list)

    def add_word(self, word):
        word = word.lower().strip()
        if not word: return
        now = datetime.utcnow().isoformat()
        with self.conn:
            self.conn.execute(
                "INSERT INTO dictionary (word,freq,is_user,created_at,updated_at) VALUES (?,1,1,?,?) "
                "ON CONFLICT(word) DO UPDATE SET freq=freq+1,is_user=1,updated_at=?",
                (word,now,now,now),
            )

    def remove_user_word(self, word):
        with self.conn:
            self.conn.execute("DELETE FROM dictionary WHERE word=? AND is_user=1", (word.lower().strip(),))

    def import_corpus(self, text):
        tokens = re.findall(r'\w+', text.lower())
        if not tokens: return
        freq = Counter(tokens); now = datetime.utcnow().isoformat()
        with self.conn:
            self.conn.executemany(
                "INSERT INTO dictionary (word,freq,is_user,created_at,updated_at) VALUES (?, ?,0,?,?) "
                "ON CONFLICT(word) DO UPDATE SET freq=freq+?,updated_at=?",
                [(w,f,now,now,f,now) for w,f in freq.items()],
            )
            bf = Counter(zip(tokens, tokens[1:]))
            self.conn.executemany(
                "INSERT INTO bigrams (w1,w2,freq) VALUES (?,?,?) ON CONFLICT(w1,w2) DO UPDATE SET freq=freq+?",
                [(a,b,f,f) for (a,b),f in bf.items()],
            )
            tf = Counter(zip(tokens, tokens[1:], tokens[2:]))
            self.conn.executemany(
                "INSERT INTO trigrams (w1,w2,w3,freq) VALUES (?,?,?,?) ON CONFLICT(w1,w2,w3) DO UPDATE SET freq=freq+?",
                [(a,b,c,f,f) for (a,b,c),f in tf.items()],
            )

    def download_dictionary(self):
        """Download 50k word list from FrequencyWords GitHub repo."""
        if self.lang_code not in DOWNLOAD_LANGS:
            return False, f"No remote dictionary available for '{self.lang_code}'."
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dictionary")
        existing = cur.fetchone()[0]
        if existing >= 10000:
            return True, f"Already {existing:,} words. Skipping download."

        url = FREQ_BASE_URL.format(lang=self.lang_code)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NLP-Corrector/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return False, f"HTTP {e.code} for '{self.lang_code}'."
        except urllib.error.URLError as e:
            return False, f"Network error: {e.reason}"
        except Exception as e:
            return False, f"Download failed: {e}"

        lines = raw.strip().split("\n")
        now = datetime.utcnow().isoformat()
        word_data = []
        all_words = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                word, freq_str = parts[0], parts[1]
                try: freq = int(freq_str)
                except ValueError: continue
                word_data.append((word, freq, now))
                repeat = min(max(1, int(freq ** 0.15)), 50)
                all_words.extend([word] * repeat)
            elif len(parts) == 1 and parts[0]:
                word_data.append((parts[0], 1, now))
                all_words.append(parts[0])

        if not word_data:
            return False, "No valid words parsed."

        with self.conn:
            self.conn.executemany(
                """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at)
                   VALUES (?, ?, 0, ?, ?)
                   ON CONFLICT(word) DO UPDATE SET freq = freq + excluded.freq, updated_at = excluded.updated_at""",
                [(w, f, now, now) for w, f, now in word_data],
            )
            bigram_freq = Counter(zip(all_words, all_words[1:]))
            self.conn.executemany(
                "INSERT INTO bigrams (w1,w2,freq) VALUES (?,?,?) ON CONFLICT(w1,w2) DO UPDATE SET freq=freq+?",
                [(w1, w2, f, f) for (w1, w2), f in bigram_freq.items()],
            )
            trigram_freq = Counter(zip(all_words, all_words[1:], all_words[2:]))
            self.conn.executemany(
                "INSERT INTO trigrams (w1,w2,w3,freq) VALUES (?,?,?,?) ON CONFLICT(w1,w2,w3) DO UPDATE SET freq=freq+?",
                [(w1, w2, w3, f, f) for (w1, w2, w3), f in trigram_freq.items()],
            )

        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dictionary")
        total = cur.fetchone()[0]
        return True, f"Downloaded {len(word_data):,} words. DB now has {total:,} words."

    def get_db_size_mb(self) -> float:
        try: return os.path.getsize(self.db_path)/(1024*1024)
        except: return 0.0

    def get_word_count(self) -> int:
        try: return self.conn.execute("SELECT COUNT(*) FROM dictionary").fetchone()[0]
        except: return 0

    def close(self):
        if self.conn: self.conn.close(); self.conn = None


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: Language Profile & Text Corrector
# ═══════════════════════════════════════════════════════════════════

class LanguageProfile:
    def __init__(self, lang_code):
        self.lang_code = lang_code
        self.db = DatabaseManager(lang_code)
        self.words_freq = {}; self.words = set(); self.user_words = set()
        self.bk = BKTree(); self.bigram_counts = defaultdict(Counter); self.trigram_counts = Counter()
        self.grammar_rules = []; self.confusion_pairs = {}
        self.refresh_from_db()

    def refresh_from_db(self):
        self.words_freq = self.db.load_words()
        self.words = set(self.words_freq.keys())
        self.user_words = self.db.load_user_words()
        self.bk = BKTree(); self.bk.build_from_list(list(self.words))
        self.bigram_counts = self.db.load_bigrams()
        self.trigram_counts = self.db.load_trigrams()
        self.grammar_rules = self.db.load_grammar_rules()
        self.confusion_pairs = self.db.load_confusion_pairs()
        logger.info(f"Profile '{self.lang_code}': {len(self.words)} words, "
                     f"{len(self.grammar_rules)} rules, {len(self.confusion_pairs)} confusion pairs")


class TextCorrector:
    def __init__(self):
        self.profiles = {}; self.current_lang = "en"
        for code in LANGUAGES:
            try: self.profiles[code] = LanguageProfile(code)
            except Exception as e: logger.critical(f"Failed to build profile for {code}: {e}")

    def set_language(self, lang): self.current_lang = lang

    def add_word(self, word, lang=None):
        lang = lang or self.current_lang; word = word.lower().strip()
        if not word: return "Empty word."
        try: self.profiles[lang].db.add_word(word); self.profiles[lang].refresh_from_db(); return f"'{word}' added to {lang.upper()}."
        except Exception as e: return f"Error: {e}"

    def remove_word(self, word, lang=None):
        lang = lang or self.current_lang; word = word.lower().strip()
        try:
            if word in self.profiles[lang].user_words:
                self.profiles[lang].db.remove_user_word(word); self.profiles[lang].refresh_from_db(); return f"'{word}' removed."
            return f"'{word}' not in user dict."
        except Exception as e: return f"Error: {e}"

    def import_corpus(self, path, lang=None):
        lang = lang or self.current_lang
        try:
            text = Path(path).read_text(encoding='utf-8')
            self.profiles[lang].db.import_corpus(text); self.profiles[lang].refresh_from_db()
            return True, f"Imported to {lang.upper()}."
        except Exception as e: return False, str(e)

    def download_dictionary(self, lang=None):
        lang = lang or self.current_lang
        try:
            ok, msg = self.profiles[lang].db.download_dictionary()
            if ok:
                self.profiles[lang].refresh_from_db()
            return ok, msg
        except Exception as e: return False, str(e)

    @staticmethod
    def tokenize(text):
        return [{"text":m.group(),"start":m.start(),"end":m.end(),"is_word":bool(re.fullmatch(r"\w+",m.group()))}
                for m in re.finditer(r"\w+|[^\w\s]|\s+", text, re.UNICODE)]

    def generate_candidates(self, word, max_edit=2, top_k=8):
        p = self.profiles[self.current_lang]; lw = word.lower()
        if lw in p.words: return [lw]
        cs = set()
        if p.bk.root:
            for t, d in p.bk.query(lw, max_edit):
                if t in p.words: cs.add(t)
        letters = string.ascii_lowercase
        splits = [(lw[:i], lw[i:]) for i in range(len(lw)+1)]
        e1 = set(
            [L+R[1:] for L,R in splits if R]
            +[L+R[1]+R[0]+R[2:] for L,R in splits if len(R)>1]
            +[L+c+R[1:] for L,R in splits if R for c in letters]
            +[L+c+R for L,R in splits for c in letters],
        )
        for w in e1:
            if w in p.words: cs.add(w)
        return sorted(cs, key=lambda w: (-p.words_freq.get(w,0), levenshtein(lw,w)))[:top_k] or [lw]

    def _rank(self, misspelled, candidates, prev_word):
        p = self.profiles[self.current_lang]
        if not candidates: return misspelled
        if not prev_word: return max(candidates, key=lambda w: p.words_freq.get(w,1))
        best = max(candidates, key=lambda w: p.bigram_counts.get(prev_word,{}).get(w,0))
        if p.bigram_counts.get(prev_word,{}).get(best,0) == 0:
            return max(candidates, key=lambda w: p.words_freq.get(w,1))
        return best

    def correct_text_interactive(self, text):
        p = self.profiles[self.current_lang]; tokens = self.tokenize(text); errors = []; prev_word = None
        for tok in tokens:
            if not tok["is_word"]: continue
            w = tok["text"]; lw = w.lower()
            if len(lw) <= 1 or lw.isdigit(): prev_word = lw; continue
            if lw in p.words:
                if lw in p.confusion_pairs:
                    for pair in p.confusion_pairs[lw]:
                        errors.append({"type":"confusion","start":tok["start"],"end":tok["end"],
                                       "original":w,"suggestion":pair["correct"],"message":pair["message"],
                                       "all_candidates":[pair["correct"]]})
                prev_word = lw; continue
            candidates = self.generate_candidates(w)
            best = self._rank(lw, candidates, prev_word)
            errors.append({"type":"spelling","start":tok["start"],"end":tok["end"],
                           "original":w,"suggestion":best,
                           "message":f"Unknown word. Did you mean '{best}'?",
                           "all_candidates":candidates[:5]})
            prev_word = lw
        for rule in p.grammar_rules:
            try:
                for m in rule["pattern"].finditer(text):
                    suggestion = m.expand(rule["replacement"])
                    errors.append({"type":"grammar","start":m.start(),"end":m.end(),
                                   "original":m.group(),"suggestion":suggestion,
                                   "message":rule["message"],"all_candidates":[suggestion]})
            except re.error: pass
        errors.sort(key=lambda e: e["start"]); return errors

    def correct_beam_search(self, text, beam_width=5):
        p = self.profiles[self.current_lang]; tokens = self.tokenize(text)
        wt = [t for t in tokens if t["is_word"]]; words = [t["text"].lower() for t in wt]
        beams = [([], 1.0)]; tt = max(sum(p.trigram_counts.values()), 1)
        for i, word in enumerate(words):
            nb = []; cands = self.generate_candidates(word, top_k=beam_width)
            for seq, sc in beams:
                for c in cands:
                    if len(seq) >= 2: r = (p.trigram_counts.get((seq[-2],seq[-1],c),0)+1)/tt
                    elif len(seq) >= 1: r = (p.bigram_counts.get(seq[-1],{}).get(c,0)+1)/max(sum(p.bigram_counts.get(seq[-1],{}).values()),1)
                    else: r = p.words_freq.get(c,1)/max(sum(p.words_freq.values()),1)
                    nb.append((seq+[c], sc*r))
            beams = heapq.nlargest(beam_width, nb, key=lambda x: x[1])
        bs, bsc = max(beams, key=lambda x: x[1]) if beams else (words, 0.0)
        return self._reconstruct(tokens, wt, bs), bsc

    def correct_mcts(self, text, iterations=500):
        p = self.profiles[self.current_lang]; tokens = self.tokenize(text)
        wt = [t for t in tokens if t["is_word"]]; words = [t["text"] for t in wt]
        bt = words[:]; bs = self._score([w.lower() for w in bt], p)
        for _ in range(iterations):
            if not words: break
            i = random.randrange(len(words))
            cands = self.generate_candidates(words[i])
            nt = bt[:]; nt[i] = random.choice(cands)
            s = self._score([w.lower() for w in nt], p)
            if s > bs: bs = s; bt = nt
        return self._reconstruct(tokens, wt, [w.lower() for w in bt]), bs

    def _score(self, words, p):
        return sum(p.words_freq.get(w,0) for w in words) - 10*sum(
            len(list(r["pattern"].finditer(" ".join(words)))) for r in p.grammar_rules
        )

    def _reconstruct(self, all_tokens, word_tokens, new_words):
        result, wi = [], 0
        for tok in all_tokens:
            if tok["is_word"] and wi < len(new_words):
                o = tok["text"]; r = new_words[wi]
                rep = r.upper() if o.isupper() else (r.capitalize() if o and o[0].isupper() else r)
                result.append((tok["start"], tok["end"], rep)); wi += 1
        if not result: return "".join(t["text"] for t in all_tokens)
        parts, le = [], 0
        for s, e, r in result:
            parts.append("".join(t["text"] for t in all_tokens if le <= t["start"] < s))
            parts.append(r); le = e
        parts.append("".join(t["text"] for t in all_tokens if t["start"] >= le))
        return "".join(parts)

    @staticmethod
    def apply_corrections(text, errors, decisions):
        c = text
        for e in sorted(errors, key=lambda x: x["start"], reverse=True):
            d = decisions.get(e["start"])
            if d and d != "ignore": c = c[:e["start"]]+d+c[e["end"]:]
        return c

    def get_stats(self, text):
        tokens = self.tokenize(text); words = [t for t in tokens if t["is_word"]]
        p = self.profiles.get(self.current_lang)
        unk = sum(1 for w in words if w["text"].lower() not in p.words and len(w["text"])>1) if p else 0
        return {"chars":len(text),"words":len(words),"unknown_words":unk}


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: Worker Threads
# ═══════════════════════════════════════════════════════════════════

class CorrectionWorker(QThread):
    finished = Signal(object)
    progress = Signal(str)

    def __init__(self, corrector, text, mode, **kw):
        super().__init__()
        self.corrector = corrector; self.text = text; self.mode = mode; self.kw = kw

    def run(self):
        try:
            if self.mode == "interactive":
                self.progress.emit("Analyzing text ...")
                result = self.corrector.correct_text_interactive(self.text)
                self.finished.emit({"errors": result})
            elif self.mode == "beam":
                self.progress.emit("Running beam search ...")
                c, s = self.corrector.correct_beam_search(self.text, self.kw.get("beam_width", 5))
                self.finished.emit({"corrected": c, "score": s})
            elif self.mode == "mcts":
                self.progress.emit("Running MCTS optimisation ...")
                c, s = self.corrector.correct_mcts(self.text, self.kw.get("iterations", 500))
                self.finished.emit({"corrected": c, "score": s})
            elif self.mode == "import":
                self.progress.emit("Importing corpus ...")
                ok, msg = self.corrector.import_corpus(self.kw["path"])
                self.finished.emit({"import_ok": ok, "import_msg": msg})
        except Exception as e:
            self.finished.emit({"error": str(e)})


class DownloadWorker(QThread):
    finished = Signal(object)
    progress = Signal(str)

    def __init__(self, corrector, lang):
        super().__init__()
        self.corrector = corrector; self.lang = lang

    def run(self):
        try:
            self.progress.emit(f"Downloading dictionary for {self.lang.upper()} ...")
            ok, msg = self.corrector.download_dictionary(self.lang)
            self.finished.emit({"download_ok": ok, "download_msg": msg})
        except Exception as e:
            self.finished.emit({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: Custom Widgets
# ═══════════════════════════════════════════════════════════════════

class HighlightTextEdit(QTextEdit):
    """Editor with error highlighting + right-click context menu."""

    suggestion_requested = Signal(int, int, str)

    def __init__(self, parent=None, readonly=False):
        super().__init__(parent)
        self.setReadOnly(readonly)
        self.setAcceptRichText(False)
        f = QFont("Consolas", 11); f.setStyleHint(QFont.Monospace); self.setFont(f)
        self._errors: list = []

    def clear_highlights(self):
        self.setExtraSelections([])

    def highlight_errors(self, errors):
        self._errors = errors
        extra = []
        colors = {"spelling": QColor(255,80,80,70), "grammar": QColor(80,140,255,70), "confusion": QColor(255,180,40,70)}
        underlines = {"spelling": QColor(255,0,0), "grammar": QColor(0,80,255), "confusion": QColor(200,120,0)}
        for e in errors:
            sel = QTextEdit.ExtraSelection()
            cur = self.textCursor(); cur.setPosition(e["start"]); cur.setPosition(e["end"], QTextCursor.KeepAnchor)
            sel.cursor = cur
            sel.format.setBackground(colors.get(e["type"], QColor(200,200,200,80)))
            sel.format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            sel.format.setUnderlineColor(underlines.get(e["type"], QColor(128,128,128)))
            extra.append(sel)
        self.setExtraSelections(extra)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        for e in self._errors:
            if e["start"] <= pos <= e["end"]:
                menu.addSeparator()
                sug_label = menu.addAction(f"Suggestions for '{e['original']}':")
                sug_label.setEnabled(False)
                for cand in e.get("all_candidates", [e["suggestion"]])[:5]:
                    action = menu.addAction(f"  -> {cand}")
                    action.triggered.connect(
                        self._make_suggestion_handler(e["start"], e["end"], cand)
                    )
                break
        menu.exec(event.globalPos())

    def _make_suggestion_handler(self, start, end, replacement):
        def handler():
            self.suggestion_requested.emit(start, end, replacement)
        return handler

    def select_range(self, start, end):
        cur = self.textCursor()
        cur.setPosition(start)
        cur.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cur)
        self.ensureCursorVisible()


class ErrorTableWidget(QTableWidget):
    """Error list with per-row decision state colours & Add-to-dict button."""

    decision_changed = Signal(int, str)
    add_to_dict = Signal(str)

    _STATE_COLORS = {
        "accepted":  QColor(40, 160, 60, 35),
        "ignored":   QColor(160, 40, 40, 25),
        "custom":    QColor(40, 100, 200, 35),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["#", "Type", "Original", "Suggestion", "Message", "Decision", "Action"])
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._errors = []
        self._decisions: Dict[int, str] = {}

    def set_errors(self, errors):
        self._errors = errors
        self._decisions = {}
        self.setRowCount(len(errors))
        icons = {"spelling": "SPELL", "grammar": "GRAM", "confusion": "CONF"}

        for i, e in enumerate(errors):
            self.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            type_item = QTableWidgetItem(f"{icons.get(e['type'], '?')} {e['type'].capitalize()}")
            self.setItem(i, 1, type_item)
            self.setItem(i, 2, QTableWidgetItem(e["original"]))

            combo = QComboBox()
            for c in e.get("all_candidates", [e["suggestion"]]):
                combo.addItem(c)
            combo.currentTextChanged.connect(
                lambda t, s=e["start"]: self._on_combo(s, t)
            )
            self.setCellWidget(i, 3, combo)

            self.setItem(i, 4, QTableWidgetItem(e.get("message", "")))

            decision_label = QLabel("Pending")
            decision_label.setAlignment(Qt.AlignCenter)
            decision_label.setObjectName("decisionLabel")
            self.setCellWidget(i, 5, decision_label)

            aw = QWidget()
            al = QHBoxLayout(aw)
            al.setContentsMargins(2, 2, 2, 2)
            al.setSpacing(3)

            btn_accept = QPushButton("OK")
            btn_accept.setFixedSize(30, 28)
            btn_accept.setToolTip("Accept suggestion")
            btn_accept.setObjectName("successBtn")
            btn_accept.clicked.connect(lambda _, s=e["start"]: self._on_accept(s))
            al.addWidget(btn_accept)

            btn_ignore = QPushButton("X")
            btn_ignore.setFixedSize(30, 28)
            btn_ignore.setToolTip("Ignore this error")
            btn_ignore.setObjectName("dangerBtn")
            btn_ignore.clicked.connect(lambda _, s=e["start"]: self._on_ignore(s))
            al.addWidget(btn_ignore)

            btn_custom = QPushButton("E")
            btn_custom.setFixedSize(30, 28)
            btn_custom.setToolTip("Enter custom replacement")
            btn_custom.clicked.connect(lambda _, s=e["start"]: self._on_custom(s))
            al.addWidget(btn_custom)

            btn_dict = QPushButton("+D")
            btn_dict.setFixedSize(34, 28)
            btn_dict.setToolTip("Add original word to user dictionary")
            btn_dict.clicked.connect(lambda _, w=e["original"]: self.add_to_dict.emit(w))
            al.addWidget(btn_dict)

            self.setCellWidget(i, 6, aw)

    def _update_row_state(self, start, state_key):
        for i, e in enumerate(self._errors):
            if e["start"] == start:
                color = self._STATE_COLORS.get(state_key, QColor(0,0,0,0))
                label_text = state_key.capitalize()
                if state_key == "custom":
                    label_text = f"Custom: {self._decisions[start]}"
                decision_label = self.cellWidget(i, 5)
                if decision_label:
                    decision_label.setText(label_text)
                for col in range(self.columnCount()):
                    item = self.item(i, col)
                    if item:
                        item.setBackground(color)
                break

    def _on_accept(self, s):
        for e in self._errors:
            if e["start"] == s:
                self._decisions[s] = e["suggestion"]
                self.decision_changed.emit(s, e["suggestion"])
                self._update_row_state(s, "accepted")
                break

    def _on_ignore(self, s):
        self._decisions[s] = "ignore"
        self.decision_changed.emit(s, "ignore")
        self._update_row_state(s, "ignored")

    def _on_custom(self, s):
        t, ok = QInputDialog.getText(self, "Custom Correction", "Enter replacement:")
        if ok and t.strip():
            self._decisions[s] = t.strip()
            self.decision_changed.emit(s, t.strip())
            self._update_row_state(s, "custom")

    def _on_combo(self, s, t):
        if s in self._decisions and self._decisions[s] not in ("ignore",):
            self._decisions[s] = t
            self.decision_changed.emit(s, t)

    def get_decisions(self):
        return dict(self._decisions)

    def accept_all(self):
        for e in self._errors:
            self._decisions[e["start"]] = e["suggestion"]
            self._update_row_state(e["start"], "accepted")

    def ignore_all(self):
        for e in self._errors:
            self._decisions[e["start"]] = "ignore"
            self._update_row_state(e["start"], "ignored")

    def get_error_at_row(self, row):
        if 0 <= row < len(self._errors):
            return self._errors[row]
        return None


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: Stylesheets
# ═══════════════════════════════════════════════════════════════════

DARK_STYLE = """
QMainWindow, QWidget { background: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; font-size: 10pt }
QTextEdit { background: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; padding: 8px; selection-background-color: #45475a }
QTextEdit[readOnly="true"] { background: #1e1e2e }
QLineEdit { background: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; selection-background-color: #45475a }
QPushButton { background: #45475a; color: #cdd6f4; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold }
QPushButton:hover { background: #585b70 }
QPushButton:pressed { background: #6c7086 }
QPushButton:disabled { background: #313244; color: #585b70 }
QPushButton#primaryBtn { background: #89b4fa; color: #1e1e2e } QPushButton#primaryBtn:hover { background: #74c7ec }
QPushButton#dangerBtn { background: #f38ba8; color: #1e1e2e } QPushButton#dangerBtn:hover { background: #eba0ac }
QPushButton#successBtn { background: #a6e3a1; color: #1e1e2e } QPushButton#successBtn:hover { background: #94e2d5 }
QPushButton#accentBtn { background: #cba6f7; color: #1e1e2e } QPushButton#accentBtn:hover { background: #b4befe }
QComboBox { background: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; min-width: 60px }
QComboBox::drop-down { border: none; width: 20px }
QComboBox QAbstractItemView { background: #181825; color: #cdd6f4; selection-background-color: #45475a; border: 1px solid #45475a }
QTabWidget::pane { border: 1px solid #45475a; border-radius: 4px; top: -1px }
QTabBar::tab { background: #313244; color: #bac2de; padding: 8px 18px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px }
QTabBar::tab:selected { background: #45475a; color: #cdd6f4; font-weight: bold }
QTabBar::tab:hover { background: #585b70 }
QTableWidget { background: #181825; color: #cdd6f4; gridline-color: #45475a; border: 1px solid #45475a; border-radius: 4px }
QTableWidget::item { padding: 4px } QTableWidget::item:selected { background: #45475a }
QHeaderView::section { background: #313244; color: #cdd6f4; padding: 6px; border: 1px solid #45475a; font-weight: bold }
QGroupBox { border: 1px solid #45475a; border-radius: 6px; margin-top: 12px; padding-top: 18px; font-weight: bold }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px }
QLabel { color: #cdd6f4 }
QLabel#statsLabel { color: #a6adc8; font-size: 9pt; background: transparent }
QLabel#decisionLabel { font-size: 9pt; }
QStatusBar { background: #181825; color: #a6adc8; border-top: 1px solid #45475a; font-size: 9pt }
QProgressBar { background: #313244; border: 1px solid #45475a; border-radius: 4px; text-align: center; color: #cdd6f4; max-height: 6px }
QProgressBar::chunk { background: #89b4fa; border-radius: 3px }
QScrollBar:vertical { background: #181825; width: 10px; border: none }
QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; min-height: 30px }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0 }
QScrollBar:horizontal { background: #181825; height: 10px; border: none }
QScrollBar::handle:horizontal { background: #45475a; border-radius: 4px; min-width: 30px }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0 }
QSplitter::handle { background: #45475a; height: 3px }
QListWidget { background: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px }
QListWidget::item { padding: 4px } QListWidget::item:selected { background: #45475a }
QMessageBox { background: #1e1e2e; color: #cdd6f4 }
QMenu { background: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 4px }
QMenu::item:selected { background: #45475a }
QMenu::separator { height: 1px; background: #45475a; margin: 4px 8px }
QToolBar { background: #181825; border: none; spacing: 6px; padding: 4px }
QCheckBox { color: #cdd6f4; spacing: 6px }
QCheckBox::indicator { width: 16px; height: 16px }
QFrame#separatorLine { background: #45475a; max-height: 1px }
"""

LIGHT_STYLE = """
QMainWindow, QWidget { background: #eff1f5; color: #4c4f69; font-family: 'Segoe UI', sans-serif; font-size: 10pt }
QTextEdit { background: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; padding: 8px; selection-background-color: #ccd0da }
QTextEdit[readOnly="true"] { background: #eff1f5 }
QLineEdit { background: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; padding: 4px 8px; selection-background-color: #ccd0da }
QPushButton { background: #ccd0da; color: #4c4f69; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold }
QPushButton:hover { background: #bcc0cc }
QPushButton:pressed { background: #acb0be }
QPushButton:disabled { background: #e6e9ef; color: #9ca0b0 }
QPushButton#primaryBtn { background: #1e66f5; color: #ffffff } QPushButton#primaryBtn:hover { background: #2a7de1 }
QPushButton#dangerBtn { background: #d20f39; color: #ffffff } QPushButton#dangerBtn:hover { background: #e63e5c }
QPushButton#successBtn { background: #40a02b; color: #ffffff } QPushButton#successBtn:hover { background: #56b640 }
QPushButton#accentBtn { background: #8839ef; color: #ffffff } QPushButton#accentBtn:hover { background: #9b6fef }
QComboBox { background: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; padding: 4px 8px; min-width: 60px }
QComboBox::drop-down { border: none; width: 20px }
QComboBox QAbstractItemView { background: #ffffff; color: #4c4f69; selection-background-color: #ccd0da; border: 1px solid #bcc0cc }
QTabWidget::pane { border: 1px solid #bcc0cc; border-radius: 4px; top: -1px }
QTabBar::tab { background: #e6e9ef; color: #5c5f77; padding: 8px 18px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px }
QTabBar::tab:selected { background: #ccd0da; color: #4c4f69; font-weight: bold }
QTabBar::tab:hover { background: #bcc0cc }
QTableWidget { background: #ffffff; color: #4c4f69; gridline-color: #bcc0cc; border: 1px solid #bcc0cc; border-radius: 4px }
QTableWidget::item { padding: 4px } QTableWidget::item:selected { background: #ccd0da }
QHeaderView::section { background: #e6e9ef; color: #4c4f69; padding: 6px; border: 1px solid #bcc0cc; font-weight: bold }
QGroupBox { border: 1px solid #bcc0cc; border-radius: 6px; margin-top: 12px; padding-top: 18px; font-weight: bold }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px }
QLabel { color: #4c4f69 }
QLabel#statsLabel { color: #7c7f93; font-size: 9pt; background: transparent }
QLabel#decisionLabel { font-size: 9pt; }
QStatusBar { background: #e6e9ef; color: #7c7f93; border-top: 1px solid #bcc0cc; font-size: 9pt }
QProgressBar { background: #e6e9ef; border: 1px solid #bcc0cc; border-radius: 4px; text-align: center; color: #4c4f69; max-height: 6px }
QProgressBar::chunk { background: #1e66f5; border-radius: 3px }
QScrollBar:vertical { background: #e6e9ef; width: 10px; border: none }
QScrollBar::handle:vertical { background: #bcc0cc; border-radius: 4px; min-height: 30px }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0 }
QScrollBar:horizontal { background: #e6e9ef; height: 10px; border: none }
QScrollBar::handle:horizontal { background: #bcc0cc; border-radius: 4px; min-width: 30px }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0 }
QSplitter::handle { background: #bcc0cc; height: 3px }
QListWidget { background: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px }
QListWidget::item { padding: 4px } QListWidget::item:selected { background: #ccd0da }
QMessageBox { background: #eff1f5; color: #4c4f69 }
QMenu { background: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; padding: 4px }
QMenu::item:selected { background: #ccd0da }
QMenu::separator { height: 1px; background: #bcc0cc; margin: 4px 8px }
QToolBar { background: #e6e9ef; border: none; spacing: 6px; padding: 4px }
QCheckBox { color: #4c4f69; spacing: 6px }
QCheckBox::indicator { width: 16px; height: 16px }
QFrame#separatorLine { background: #bcc0cc; max-height: 1px }
"""


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: Diff Helper
# ═══════════════════════════════════════════════════════════════════

def build_diff_html(original: str, corrected: str) -> str:
    orig_words = original.split()
    corr_words = corrected.split()
    sm = SequenceMatcher(None, orig_words, corr_words)
    parts: list = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            parts.append(" ".join(orig_words[i1:i2]))
        elif op == "replace":
            removed = " ".join(orig_words[i1:i2])
            added   = " ".join(corr_words[j1:j2])
            parts.append(f'<span style="background:#f38ba855;text-decoration:line-through">{removed}</span> '
                         f'<span style="background:#a6e3a155;font-weight:bold">{added}</span>')
        elif op == "delete":
            removed = " ".join(orig_words[i1:i2])
            parts.append(f'<span style="background:#f38ba855;text-decoration:line-through">{removed}</span>')
        elif op == "insert":
            added = " ".join(corr_words[j1:j2])
            parts.append(f'<span style="background:#a6e3a155;font-weight:bold">{added}</span>')
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════
# SECTION 10: Main Window
# ═══════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, corrector: TextCorrector):
        super().__init__()
        self.corrector = corrector
        self.worker = None
        self.download_worker = None
        self.current_errors = []
        self._last_check_text = ""
        self.settings = QSettings("NLP_Corrector", "App")

        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._restore_settings()
        self._update_db_stats()
        self._update_word_list()
        self._update_live_stats()

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(400)
        self._stats_timer.setSingleShot(True)
        self.input_edit.textChanged.connect(self._stats_timer.start)
        self._stats_timer.timeout.connect(self._update_live_stats)

    # ────────────────────────────────────────────────────
    # UI Setup
    # ────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("Advanced NLP Text Corrector")
        self.setMinimumSize(1100, 750)
        self.resize(1440, 920)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        lang_label = QLabel("Language:")
        lang_label.setStyleSheet("font-weight: bold")
        top_bar.addWidget(lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(210)
        for code in LANGUAGES:
            self.lang_combo.addItem(f"{LANG_NAMES.get(code, code)}  ({code})", code)
        self.lang_combo.setCurrentText("English  (en)")
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        top_bar.addWidget(self.lang_combo)

        top_bar.addSpacing(16)

        self.theme_btn = QPushButton("Dark")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(True)
        self.theme_btn.setFixedWidth(100)
        self.theme_btn.setToolTip("Toggle dark / light theme")
        self.theme_btn.toggled.connect(self._toggle_theme)
        top_bar.addWidget(self.theme_btn)

        top_bar.addStretch()

        self.stats_label = QLabel("Ready")
        self.stats_label.setObjectName("statsLabel")
        top_bar.addWidget(self.stats_label)

        main_layout.addLayout(top_bar)

        # Splitter
        splitter = QSplitter(Qt.Vertical)

        # Editor Group
        editor_group = QGroupBox("Input Text")
        editor_layout = QVBoxLayout(editor_group)
        editor_layout.setSpacing(6)

        self.input_edit = HighlightTextEdit()
        self.input_edit.setPlaceholderText(
            "Type or paste text here, then press F7 or click 'Check Spelling & Grammar' ..."
        )
        self.input_edit.suggestion_requested.connect(self._on_context_suggestion)
        editor_layout.addWidget(self.input_edit)

        self.live_stats_label = QLabel("0 chars  |  0 words  |  0 unknown")
        self.live_stats_label.setObjectName("statsLabel")
        editor_layout.addWidget(self.live_stats_label)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.check_btn = QPushButton("Check Spelling & Grammar")
        self.check_btn.setObjectName("primaryBtn")
        self.check_btn.setToolTip("Run interactive spell & grammar check (F7)")
        self.check_btn.clicked.connect(self._on_check)
        btn_row.addWidget(self.check_btn)

        self.beam_btn = QPushButton("Beam Search")
        self.beam_btn.setToolTip("Auto-correct using beam-search decoding")
        self.beam_btn.clicked.connect(self._on_beam)
        btn_row.addWidget(self.beam_btn)

        self.mcts_btn = QPushButton("MCTS")
        self.mcts_btn.setToolTip("Auto-correct using Monte-Carlo tree search")
        self.mcts_btn.clicked.connect(self._on_mcts)
        btn_row.addWidget(self.mcts_btn)

        btn_row.addSpacing(16)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.setToolTip("Clear all text and results (Ctrl+Shift+X)")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.clear_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("successBtn")
        self.save_btn.setToolTip("Save current input text to a file (Ctrl+S)")
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        btn_row.addStretch()
        editor_layout.addLayout(btn_row)
        splitter.addWidget(editor_group)

        # Result Tabs
        self.result_tabs = QTabWidget()

        # Tab: Interactive
        interactive_widget = QWidget()
        interactive_layout = QVBoxLayout(interactive_widget)
        interactive_layout.setSpacing(6)

        nav_row = QHBoxLayout()
        self.prev_err_btn = QPushButton("Previous Error")
        self.prev_err_btn.setToolTip("Jump to previous error in text")
        self.prev_err_btn.clicked.connect(self._on_prev_error)
        nav_row.addWidget(self.prev_err_btn)

        self.next_err_btn = QPushButton("Next Error")
        self.next_err_btn.setToolTip("Jump to next error in text")
        self.next_err_btn.clicked.connect(self._on_next_error)
        nav_row.addWidget(self.next_err_btn)

        self.err_count_label = QLabel("No errors")
        self.err_count_label.setObjectName("statsLabel")
        nav_row.addWidget(self.err_count_label)
        nav_row.addStretch()
        interactive_layout.addLayout(nav_row)

        self.error_table = ErrorTableWidget()
        self.error_table.decision_changed.connect(self._on_decision_changed)
        self.error_table.add_to_dict.connect(self._on_add_word_from_error)
        self.error_table.cellDoubleClicked.connect(self._on_error_double_clicked)
        interactive_layout.addWidget(self.error_table)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.accept_all_btn = QPushButton("Accept All")
        self.accept_all_btn.setObjectName("successBtn")
        self.accept_all_btn.setToolTip("Accept all suggestions at once")
        self.accept_all_btn.clicked.connect(self._on_accept_all)
        action_row.addWidget(self.accept_all_btn)

        self.ignore_all_btn = QPushButton("Ignore All")
        self.ignore_all_btn.setObjectName("dangerBtn")
        self.ignore_all_btn.setToolTip("Ignore all errors at once")
        self.ignore_all_btn.clicked.connect(self._on_ignore_all)
        action_row.addWidget(self.ignore_all_btn)

        action_row.addSpacing(20)

        self.apply_btn = QPushButton("Apply Corrections")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.setToolTip("Apply accepted corrections to the text (Ctrl+Enter)")
        self.apply_btn.clicked.connect(self._on_apply)
        action_row.addWidget(self.apply_btn)

        self.recheck_btn = QPushButton("Re-check")
        self.recheck_btn.setObjectName("accentBtn")
        self.recheck_btn.setToolTip("Re-run the check on the updated text")
        self.recheck_btn.clicked.connect(self._on_check)
        self.recheck_btn.setVisible(False)
        action_row.addWidget(self.recheck_btn)

        action_row.addStretch()
        interactive_layout.addLayout(action_row)

        self._interactive_tab_idx = self.result_tabs.addTab(interactive_widget, "Interactive")

        # Tab: Auto-Corrected
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setSpacing(6)

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setFont(QFont("Consolas", 11))
        self.output_edit.setPlaceholderText("Auto-corrected text will appear here ...")
        output_layout.addWidget(self.output_edit)

        out_btn_row = QHBoxLayout()
        self.score_label = QLabel("Score: --")
        self.score_label.setObjectName("statsLabel")
        out_btn_row.addWidget(self.score_label)
        out_btn_row.addStretch()

        self.copy_corrected_btn = QPushButton("Copy to Clipboard")
        self.copy_corrected_btn.setToolTip("Copy the corrected text to the clipboard")
        self.copy_corrected_btn.clicked.connect(self._on_copy_corrected)
        out_btn_row.addWidget(self.copy_corrected_btn)

        self.use_as_input_btn = QPushButton("Use as Input")
        self.use_as_input_btn.setToolTip("Copy the corrected text into the input editor for further editing")
        self.use_as_input_btn.clicked.connect(self._on_use_corrected_as_input)
        out_btn_row.addWidget(self.use_as_input_btn)

        output_layout.addLayout(out_btn_row)
        self._autocorrect_tab_idx = self.result_tabs.addTab(output_widget, "Auto-Corrected")

        # Tab: Database
        db_widget = QWidget()
        db_layout = QVBoxLayout(db_widget)
        db_layout.setSpacing(8)

        # Download + Import row
        dl_import_row = QHBoxLayout()
        self.download_btn = QPushButton("Download 50k Dictionary")
        self.download_btn.setObjectName("accentBtn")
        self.download_btn.setToolTip("Download 50k word-frequency list from GitHub for the current language")
        self.download_btn.clicked.connect(self._on_download_dictionary)
        dl_import_row.addWidget(self.download_btn)

        self.import_btn = QPushButton("Import Corpus (.txt)")
        self.import_btn.setObjectName("accentBtn")
        self.import_btn.setToolTip("Import a text file to train the language model (Ctrl+O)")
        self.import_btn.clicked.connect(self._on_import_corpus)
        dl_import_row.addWidget(self.import_btn)

        dl_import_row.addStretch()
        db_layout.addLayout(dl_import_row)

        # Add/Remove word
        dict_group = QGroupBox("User Dictionary")
        dict_layout = QHBoxLayout(dict_group)
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Enter word to add / remove ...")
        self.word_input.returnPressed.connect(self._on_add_word)
        dict_layout.addWidget(self.word_input)

        self.add_word_btn = QPushButton("Add")
        self.add_word_btn.setObjectName("successBtn")
        self.add_word_btn.setToolTip("Add word to the user dictionary (Enter)")
        self.add_word_btn.clicked.connect(self._on_add_word)
        dict_layout.addWidget(self.add_word_btn)

        self.remove_word_btn = QPushButton("Remove")
        self.remove_word_btn.setObjectName("dangerBtn")
        self.remove_word_btn.setToolTip("Remove word from the user dictionary")
        self.remove_word_btn.clicked.connect(self._on_remove_word)
        dict_layout.addWidget(self.remove_word_btn)
        db_layout.addWidget(dict_group)

        # Search filter + list
        filter_row = QHBoxLayout()
        self.dict_filter_input = QLineEdit()
        self.dict_filter_input.setPlaceholderText("Filter words ...")
        self.dict_filter_input.textChanged.connect(self._on_filter_words)
        filter_row.addWidget(self.dict_filter_input)
        db_layout.addLayout(filter_row)

        self.word_list = QListWidget()
        self.word_list.setAlternatingRowColors(True)
        db_layout.addWidget(self.word_list)

        self.db_info_label = QLabel("")
        self.db_info_label.setObjectName("statsLabel")
        db_layout.addWidget(self.db_info_label)

        self._db_tab_idx = self.result_tabs.addTab(db_widget, "Database")

        splitter.addWidget(self.result_tabs)
        splitter.setSizes([420, 380])
        main_layout.addWidget(splitter)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        main_layout.addWidget(self.progress)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready -- Select a language and start typing  |  F7 = Check  |  Ctrl+Enter = Apply")

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Import Corpus ...", self._on_import_corpus, QKeySequence("Ctrl+O"))
        file_menu.addAction("Save Text ...", self._on_save, QKeySequence("Ctrl+S"))
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close, QKeySequence("Ctrl+Q"))

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Check Spelling & Grammar", self._on_check, QKeySequence("F7"))
        edit_menu.addAction("Apply Corrections", self._on_apply, QKeySequence("Ctrl+Return"))
        edit_menu.addSeparator()
        edit_menu.addAction("Clear All", self._on_clear, QKeySequence("Ctrl+Shift+X"))

        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction("Download Dictionary for Current Language", self._on_download_dictionary)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About", self._on_about)
        help_menu.addAction("Keyboard Shortcuts", self._on_shortcuts)

    def _setup_shortcuts(self):
        pass

    # ────────────────────────────────────────────────────
    # Settings & Theme
    # ────────────────────────────────────────────────────

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
        self.theme_btn.setText("Dark" if checked else "Light")

    def _apply_theme(self, dark: bool):
        QApplication.instance().setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)

    # ────────────────────────────────────────────────────
    # Language & DB Info
    # ────────────────────────────────────────────────────

    def _on_lang_changed(self, index: int):
        lang = self.lang_combo.itemData(index)
        if lang:
            self.corrector.set_language(lang)
            self._update_db_stats()
            self._update_word_list()
            self._update_live_stats()
            self.status.showMessage(f"Switched to {LANG_NAMES.get(lang, lang)}")

    def _update_db_stats(self):
        profile = self.corrector.profiles.get(self.corrector.current_lang)
        if not profile: return
        db = profile.db
        wc = db.get_word_count()
        sz = db.get_db_size_mb()
        uw = len(profile.user_words)
        gr = len(profile.grammar_rules)
        cp = len(profile.confusion_pairs)
        self.db_info_label.setText(
            f"DB: {db.db_path}  |  {wc:,} words  |  {uw} user  |  {gr} rules  |  {cp} pairs  |  {sz:.2f} MB"
        )
        self.stats_label.setText(
            f"Lang: {self.corrector.current_lang.upper()}  |  Words: {wc:,}  |  Rules: {gr}  |  Pairs: {cp}  |  DB: {sz:.2f} MB"
        )

    def _update_word_list(self, filter_text=""):
        self.word_list.clear()
        profile = self.corrector.profiles.get(self.corrector.current_lang)
        if not profile: return
        ft = filter_text.lower()
        for word in sorted(profile.user_words):
            if not ft or ft in word.lower():
                self.word_list.addItem(word)

    def _on_filter_words(self, text):
        self._update_word_list(text)

    def _update_live_stats(self):
        text = self.input_edit.toPlainText()
        stats = self.corrector.get_stats(text)
        self.live_stats_label.setText(
            f"{stats['chars']} chars  |  {stats['words']} words  |  {stats['unknown_words']} unknown"
        )

    def _set_interactive_tab_badge(self, count: int):
        if count > 0:
            self.result_tabs.setTabText(self._interactive_tab_idx, f"Interactive ({count})")
        else:
            self.result_tabs.setTabText(self._interactive_tab_idx, "Interactive")

    # ────────────────────────────────────────────────────
    # Correction Actions
    # ────────────────────────────────────────────────────

    def _on_check(self):
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.status.showMessage("No text to check.")
            return
        self._last_check_text = text
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
            self.status.showMessage("A correction is already in progress ...")
            return
        self._set_buttons_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status.showMessage(f"Running {mode} correction ...")
        self.worker = CorrectionWorker(self.corrector, text, mode, **kwargs)
        self.worker.progress.connect(lambda msg: self.status.showMessage(msg))
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _set_buttons_enabled(self, enabled: bool):
        for btn in (self.check_btn, self.beam_btn, self.mcts_btn, self.apply_btn,
                    self.accept_all_btn, self.ignore_all_btn, self.download_btn, self.import_btn):
            btn.setEnabled(enabled)

    def _on_worker_finished(self, result: Dict):
        self._set_buttons_enabled(True)
        self.progress.setVisible(False)

        if "error" in result:
            self.status.showMessage(f"Error: {result['error']}")
            QMessageBox.critical(self, "Error", result["error"])
            return

        if "errors" in result:
            self.current_errors = result["errors"]
            self.error_table.set_errors(self.current_errors)
            self.input_edit.highlight_errors(self.current_errors)
            self._set_interactive_tab_badge(len(self.current_errors))
            self.err_count_label.setText(f"{len(self.current_errors)} error(s) found")
            self.result_tabs.setCurrentIndex(self._interactive_tab_idx)
            self.recheck_btn.setVisible(True)
            if self.current_errors:
                e = self.current_errors[0]
                self.input_edit.select_range(e["start"], e["end"])
                self.error_table.selectRow(0)
            self.status.showMessage(
                f"Found {len(self.current_errors)} issue(s).  Review -> Apply (Ctrl+Enter)"
            )

        elif "corrected" in result:
            original = self.input_edit.toPlainText()
            corrected = result["corrected"]
            diff_html = build_diff_html(original, corrected)
            self.output_edit.setHtml(
                f"<pre style='font-family:Consolas,monospace;font-size:11pt;"
                f"white-space:pre-wrap;word-wrap:break-word'>{diff_html}</pre>"
            )
            self._last_corrected_plain = corrected
            self.score_label.setText(f"Score: {result['score']:.6f}")
            self.result_tabs.setCurrentIndex(self._autocorrect_tab_idx)
            self.status.showMessage("Auto-correction complete. Use 'Copy' or 'Use as Input' below.")

        elif "import_ok" in result:
            ok, msg = result["import_ok"], result["import_msg"]
            if ok:
                self._update_db_stats()
                self._update_word_list()
                self._update_live_stats()
                self.status.showMessage(f"{msg}")
            else:
                self.status.showMessage(f"{msg}")
                QMessageBox.warning(self, "Import Error", msg)

    # ────────────────────────────────────────────────────
    # Interactive / Error Table
    # ────────────────────────────────────────────────────

    def _on_decision_changed(self, start: int, decision: str):
        n_decided = len(self.error_table.get_decisions())
        n_total = len(self.current_errors)
        self.status.showMessage(
            f"Decision for position {start}: {decision}  ({n_decided}/{n_total} decided)"
        )

    def _on_accept_all(self):
        self.error_table.accept_all()
        self.status.showMessage("All suggestions accepted. Press 'Apply Corrections' to commit.")

    def _on_ignore_all(self):
        self.error_table.ignore_all()
        self.status.showMessage("All suggestions ignored.")

    def _on_apply(self):
        text = self.input_edit.toPlainText()
        decisions = self.error_table.get_decisions()
        if not decisions:
            self.status.showMessage("No corrections to apply -- accept or ignore some errors first.")
            return
        corrected = TextCorrector.apply_corrections(text, self.current_errors, decisions)
        self.input_edit.setPlainText(corrected)
        self.input_edit.clear_highlights()
        self.current_errors = []
        self.error_table.set_errors([])
        self._set_interactive_tab_badge(0)
        self.err_count_label.setText("No errors")
        self._update_live_stats()
        self.status.showMessage("Corrections applied! Click 'Re-check' to verify.")

    def _on_error_double_clicked(self, row: int):
        error = self.error_table.get_error_at_row(row)
        if error:
            self.input_edit.select_range(error["start"], error["end"])
            self.input_edit.setFocus()

    def _on_prev_error(self):
        self._navigate_error(-1)

    def _on_next_error(self):
        self._navigate_error(1)

    def _navigate_error(self, direction: int):
        if not self.current_errors:
            return
        cursor_pos = self.input_edit.textCursor().position()
        if direction > 0:
            for e in self.current_errors:
                if e["start"] > cursor_pos:
                    self.input_edit.select_range(e["start"], e["end"])
                    row = self.current_errors.index(e)
                    self.error_table.selectRow(row)
                    return
            self.input_edit.select_range(self.current_errors[0]["start"], self.current_errors[0]["end"])
            self.error_table.selectRow(0)
        else:
            for e in reversed(self.current_errors):
                if e["end"] < cursor_pos:
                    self.input_edit.select_range(e["start"], e["end"])
                    row = self.current_errors.index(e)
                    self.error_table.selectRow(row)
                    return
            last = self.current_errors[-1]
            self.input_edit.select_range(last["start"], last["end"])
            self.error_table.selectRow(len(self.current_errors) - 1)

    def _on_context_suggestion(self, start: int, end: int, replacement: str):
        cursor = self.input_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        cursor.insertText(replacement)
        self.input_edit.clear_highlights()
        self._on_check()

    def _on_add_word_from_error(self, word: str):
        msg = self.corrector.add_word(word)
        self._update_db_stats()
        self._update_word_list()
        self._update_live_stats()
        self.status.showMessage(msg)

    # ────────────────────────────────────────────────────
    # Auto-Correct Tab Actions
    # ────────────────────────────────────────────────────

    def _on_copy_corrected(self):
        text = getattr(self, "_last_corrected_plain", self.output_edit.toPlainText())
        QApplication.clipboard().setText(text)
        self.status.showMessage("Corrected text copied to clipboard.")

    def _on_use_corrected_as_input(self):
        text = getattr(self, "_last_corrected_plain", self.output_edit.toPlainText())
        self.input_edit.setPlainText(text)
        self._update_live_stats()
        self.status.showMessage("Corrected text moved to input editor. You can re-check it now.")

    # ────────────────────────────────────────────────────
    # Download Dictionary
    # ────────────────────────────────────────────────────

    def _on_download_dictionary(self):
        lang = self.corrector.current_lang
        if self.download_worker and self.download_worker.isRunning():
            self.status.showMessage("Download already in progress ...")
            return
        self._set_buttons_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.download_worker = DownloadWorker(self.corrector, lang)
        self.download_worker.progress.connect(lambda msg: self.status.showMessage(msg))
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_finished(self, result: Dict):
        self._set_buttons_enabled(True)
        self.progress.setVisible(False)
        if "error" in result:
            self.status.showMessage(f"Download error: {result['error']}")
            QMessageBox.critical(self, "Download Error", result["error"])
            return
        ok = result.get("download_ok", False)
        msg = result.get("download_msg", "")
        if ok:
            self._update_db_stats()
            self._update_word_list()
            self._update_live_stats()
            self.status.showMessage(f"Done: {msg}")
        else:
            self.status.showMessage(f"Skipped: {msg}")

    # ────────────────────────────────────────────────────
    # Dictionary Actions
    # ────────────────────────────────────────────────────

    def _on_add_word(self):
        word = self.word_input.text().strip()
        if not word: return
        msg = self.corrector.add_word(word)
        self._update_db_stats()
        self._update_word_list(self.dict_filter_input.text())
        self._update_live_stats()
        self.word_input.clear()
        self.status.showMessage(msg)

    def _on_remove_word(self):
        word = self.word_input.text().strip()
        if not word:
            item = self.word_list.currentItem()
            if item:
                word = item.text()
        if not word: return
        msg = self.corrector.remove_word(word)
        self._update_db_stats()
        self._update_word_list(self.dict_filter_input.text())
        self._update_live_stats()
        self.word_input.clear()
        self.status.showMessage(msg)

    def _on_import_corpus(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Corpus", "",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)",
        )
        if not path: return
        self._start_worker("", "import", path=path)

    # ────────────────────────────────────────────────────
    # File Actions
    # ────────────────────────────────────────────────────

    def _on_save(self):
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.status.showMessage("Nothing to save.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Text", "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not path: return
        try:
            Path(path).write_text(text, encoding="utf-8")
            self.status.showMessage(f"Saved to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", str(e))

    def _on_clear(self):
        has_text = self.input_edit.toPlainText().strip()
        has_errors = bool(self.current_errors)
        if has_text or has_errors:
            reply = QMessageBox.question(
                self, "Confirm Clear",
                "Clear all text and results?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.input_edit.clear()
        self.output_edit.clear()
        self.input_edit.clear_highlights()
        self.current_errors = []
        self.error_table.set_errors([])
        self._set_interactive_tab_badge(0)
        self.err_count_label.setText("No errors")
        self.recheck_btn.setVisible(False)
        self._last_check_text = ""
        self._update_live_stats()
        self.status.showMessage("Cleared.")

    # ────────────────────────────────────────────────────
    # Help
    # ────────────────────────────────────────────────────

    def _on_about(self):
        QMessageBox.about(
            self, "About",
            "<h2>Advanced NLP Text Corrector</h2>"
            "<p>Self-contained single-file application.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>20 languages with isolated SQLite databases</li>"
            "<li>BK-tree + Levenshtein spell checking</li>"
            "<li>Grammar rules &amp; confusion pairs (embedded)</li>"
            "<li>Interactive, Beam Search &amp; MCTS correction</li>"
            "<li>User dictionary management</li>"
            "<li>Download 50k word lists from GitHub</li>"
            "<li>Dark / Light themes</li>"
            "</ul>"
            "<p>Databases stored in <code>./database/</code></p>",
        )

    def _on_shortcuts(self):
        QMessageBox.information(
            self, "Keyboard Shortcuts",
            "<table cellpadding='4'>"
            "<tr><td><b>F7</b></td><td>Check spelling &amp; grammar</td></tr>"
            "<tr><td><b>Ctrl+Enter</b></td><td>Apply corrections</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save text to file</td></tr>"
            "<tr><td><b>Ctrl+O</b></td><td>Import corpus</td></tr>"
            "<tr><td><b>Ctrl+Shift+X</b></td><td>Clear all</td></tr>"
            "<tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>"
            "<tr><td><b>Right-click</b></td><td>Suggestions for word under cursor</td></tr>"
            "<tr><td><b>Double-click row</b></td><td>Jump to error in text</td></tr>"
            "</table>",
        )

    # ────────────────────────────────────────────────────
    # Cleanup
    # ────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._save_settings()
        for profile in self.corrector.profiles.values():
            profile.db.close()
        super().closeEvent(event)


# ═══════════════════════════════════════════════════════════════════
# SECTION 11: Entry Point
# ═══════════════════════════════════════════════════════════════════

def main():
    setup_logging()
    logger.info("Starting NLP Text Corrector (self-contained) ...")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    corrector = TextCorrector()
    window = MainWindow(corrector)
    window.show()

    logger.info("Application ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()