"""
Bijoy/SutonnyMJ -> Unicode Bengali conversion.
Ported from Mukti (https://github.com/GRU-953/Mukti) by Aninda S Howlader.
License: MIT
"""

import re


# ── Pre-conversion literal replacements ──────────────────────────────────────
PRE_MAP = [
    ("yy", "y"),
    ("vv", "v"),
    ("\xad\xad", "\xad"),
    ("y&", "y"),
    ("„&", "„"),
    ("‡u", "u‡"),
    ("wu", "uw"),
    (" ,", ","),
    (" \\|", "\\|"),
    ("\\\\ ", ""),
    (" \\\\", ""),
    ("\\\\", ""),
    ("\n\n\n\n\n", "\n\n"),
    ("\n\n\n\n", "\n\n"),
    ("\n\n\n", "\n\n"),
]

_PRE_REGEX = [
    (re.compile(r" +"), " "),
    (re.compile(r"\n +"), "\n"),
    (re.compile(r" +\n"), "\n"),
]

# ── Main Bijoy -> Unicode mapping ─────────────────────────────────────────────
# Ordered longest-key-first (done at compile time); entries mirror mappings.js.
_B2U_RAW = [
    # Bug-fix compound sequences (must come first)
    ("¯Í", "স্ত"),
    ("¯Î", "স্ত্র"),
    ("¯‘", "স্তু"),
    ("¯’", "স্থ"),
    ("šyÍ", "ন্তু"),
    ("«œ", "্রু"),
    ("¯c", "স্প"),
    ("ÿœ", "ক্ষ্ম"),
    ("šÍ", "ন্ত"),
    ("›U", "ন্ট"),

    # Multi-char specials
    ("„„", "ৃ"),
    ("Av", "আ"),
    ("\\|", "।"),
    ("\\&", "্‌"),
    ("\\^", "্ব"),

    # Conjuncts (jukto okkhor)
    ("°", "ক্ক"),
    ("±", "ক্ট"),
    ("²", "ক্ষ্ণ"),
    ("³", "ক্ত"),
    ("´", "ক্ম"),
    ("µ", "ক্র"),
    ("¶", "ক্ষ"),
    ("·", "ক্স"),
    ("¸", "গু"),
    ("¹", "জ্ঞ"),
    ("º", "গ্দ"),
    ("»", "গ্ধ"),
    ("¼", "ঙ্ক"),
    ("½", "ঙ্গ"),
    ("¾", "জ্জ"),
    ("¿", "্ত্র"),
    ("À", "জ্ঝ"),
    ("Á", "জ্ঞ"),
    ("Â", "ঞ্চ"),
    ("Ã", "ঞ্ছ"),
    ("Ä", "ঞ্জ"),
    ("Å", "ঞ্ঝ"),
    ("Æ", "ট্ট"),
    ("Ç", "ড্ড"),
    ("È", "ণ্ট"),
    ("É", "ণ্ঠ"),
    ("Ê", "ণ্ড"),
    ("Ë", "ত্ত"),
    ("Ì", "ত্থ"),
    ("Í", "ত্ম"),
    ("Î", "ত্র"),
    ("Ï", "দ্দ"),
    ("Ð", "-"),
    ("Ñ", "-"),
    ("Ò", "“"),
    ("Ó", "”"),
    ("Ô", "‘"),
    ("Õ", "’"),
    ("Ö", "্র"),
    ("×", "দ্ধ"),
    ("Ø", "দ্ব"),
    ("Ù", "দ্ম"),
    ("Ú", "ন্ঠ"),
    ("Û", "ন্ড"),
    ("Ü", "ন্ধ"),
    ("Ý", "ন্স"),
    ("Þ", "প্ট"),
    ("ß", "প্ত"),
    ("à", "প্প"),
    ("á", "প্স"),
    ("â", "ব্জ"),
    ("ã", "ব্দ"),
    ("ä", "ব্ধ"),
    ("å", "ভ্র"),
    ("æ", "ম্ন"),
    ("ç", "ম্ফ"),
    ("è", "্ন"),
    ("é", "ল্ক"),
    ("ê", "ল্গ"),
    ("ë", "ল্ট"),
    ("ì", "ল্ড"),
    ("í", "ল্প"),
    ("î", "ল্ফ"),
    ("ï", "শু"),
    ("ð", "শ্চ"),
    ("ñ", "শ্ছ"),
    ("ò", "ষ্ণ"),
    ("ó", "ষ্ট"),
    ("ô", "ষ্ঠ"),
    ("õ", "ষ্ফ"),
    ("ö", "স্খ"),
    ("÷", "স্ট"),
    ("ø", "স্ন"),
    ("ù", "স্ফ"),
    ("ú", "্প"),
    ("û", "হু"),
    ("ü", "হৃ"),
    ("ý", "হ্ন"),
    ("þ", "হ্ম"),
    ("ÿ", "ক্ষ"),

    # Kars and modifiers with special chars
    ("‘", "্তু"),
    ("’", "্থ"),
    ("‹", "্ক"),
    ("Œ", "্ক্র"),
    ("“", "চ্"),
    ("”", "চ্"),
    ("—", "্ত"),
    ("˜", "দ্"),
    ("™", "দ্"),
    ("š", "ন্"),
    ("›", "ন্"),
    ("œ", "্ন"),
    ("Ÿ", "্ব"),
    ("¡", "্ব"),
    ("¢", "্ভ"),
    ("£", "্ভ্র"),
    ("¤", "ম্"),
    ("¥", "্ম"),
    ("¦", "্ব"),
    ("§", "্ম"),
    ("¨", "্য"),
    ("©", "র্"),
    ("ª", "্র"),
    ("«", "্র"),
    ("¬", "্ল"),
    ("­", "্ল"),
    ("®", "ষ্"),
    ("¯", "স্"),
    ("•", "ঙ্"),

    # Vowel signs (kars)
    ("v", "া"),
    ("w", "ি"),
    ("x", "ী"),
    ("y", "ু"),
    ("z", "ু"),
    ("–", "ু"),
    ("~", "ূ"),
    ("ƒ", "ূ"),
    ("‚", "ূ"),
    ("„", "ৃ"),
    ("…", "ৃ"),
    ("†", "ে"),
    ("‡", "ে"),
    ("ˆ", "ৈ"),
    ("‰", "ৈ"),
    ("Š", "ৗ"),

    # Independent vowels
    ("A", "অ"),
    ("B", "ই"),
    ("C", "ঈ"),
    ("D", "উ"),
    ("E", "ঊ"),
    ("F", "ঋ"),
    ("G", "এ"),
    ("H", "ঐ"),
    ("I", "ও"),
    ("J", "ঔ"),

    # Consonants
    ("K", "ক"),
    ("L", "খ"),
    ("M", "গ"),
    ("N", "ঘ"),
    ("O", "ঙ"),
    ("P", "চ"),
    ("Q", "ছ"),
    ("R", "জ"),
    ("S", "ঝ"),
    ("T", "ঞ"),
    ("U", "ট"),
    ("V", "ঠ"),
    ("W", "ড"),
    ("X", "ঢ"),
    ("Y", "ণ"),
    ("Z", "ত"),
    ("_", "থ"),
    ("`", "দ"),
    ("a", "ধ"),
    ("b", "ন"),
    ("c", "প"),
    ("d", "ফ"),
    ("e", "ব"),
    ("^", "ব"),
    ("f", "ভ"),
    ("g", "ম"),
    ("h", "য"),
    ("i", "র"),
    ("j", "ল"),
    ("k", "শ"),
    ("l", "ষ"),
    ("m", "স"),
    ("n", "হ"),
    ("o", "ড়"),
    ("p", "ঢ়"),
    ("q", "য়"),
    ("r", "ৎ"),
    ("s", "ং"),
    ("t", "ঃ"),
    ("u", "ঁ"),

    # Bengali numerals
    ("0", "০"),
    ("1", "১"),
    ("2", "২"),
    ("3", "৩"),
    ("4", "৪"),
    ("5", "৫"),
    ("6", "৬"),
    ("7", "৭"),
    ("8", "৮"),
    ("9", "৯"),
]

# ── Post-conversion cleanup ───────────────────────────────────────────────────
POST_MAP = [
    ("০ঃ", "০:"),
    ("১ঃ", "১:"),
    ("২ঃ", "২:"),
    ("৩ঃ", "৩:"),
    ("৪ঃ", "৪:"),
    ("৫ঃ", "৫:"),
    ("৬ঃ", "৬:"),
    ("৭ঃ", "৭:"),
    ("৮ঃ", "৮:"),
    ("৯ঃ", "৯:"),
    (" ঃ", ":"),
    ("\nঃ", "\n:"),
    ("]ঃ", "]:"),
    ("[ঃ", "[:"),
    ("  ", " "),
    ("অা", "আ"),
    ("্‌্‌", "্‌"),
    ("স্ত্ম", "স্ত"),
    ("ন্ত্ম", "ন্ত"),
]

# ── Compile the main regex ────────────────────────────────────────────────────

def _build_regex():
    lookup = dict(_B2U_RAW)
    keys = sorted(lookup.keys(), key=len, reverse=True)
    pattern = "|".join(re.escape(k) for k in keys)
    return re.compile(pattern), lookup


_B2U_REGEX, _B2U_LOOKUP = _build_regex()


def _apply_literal(text, charmap):
    for old, new in charmap:
        if old:
            text = new.join(text.split(old))
    return text


# ── Bengali character classification ─────────────────────────────────────────

_CONSONANTS = set("কখগঘঙচছজঝঞ"
                  "টঠডঢণতথদধন"
                  "পফবভমযরলশষ"
                  "সহড়ঢ়য়ৎংঃঁ")
_PRE_KARS  = set("িৈে")        # ি ৈ ে
_POST_KARS = set("াোৌৗুূীৃ")  # া ো ৌ ৗ ু ূ ী ৃ
_ALL_KARS  = _PRE_KARS | _POST_KARS
_HALANT    = "্"
_NUKTA     = "ঁ"


def _ch(text, i):
    return text[i] if 0 <= i < len(text) else ""


def _is_cons(c):    return c in _CONSONANTS
def _is_prekar(c):  return c in _PRE_KARS
def _is_postkar(c): return c in _POST_KARS
def _is_kar(c):     return c in _ALL_KARS
def _is_halant(c):  return c == _HALANT
def _is_nukta(c):   return c == _NUKTA
def _is_space(c):   return c in " \t\n\r"


# ── Rearrangement (ported from rearrange.js) ─────────────────────────────────

def _rearrange(text):
    if not text:
        return text

    text = "্".join(text.split("্্"))

    # Pass 1 — reph and halant reordering
    i = 0
    while i < len(text):
        # Reph repositioning
        if (i > 0 and i < len(text) - 1 and
                _ch(text, i) == "র" and
                _is_halant(_ch(text, i + 1)) and
                not _is_halant(_ch(text, i - 1))):
            check = i - 1
            while check >= 0 and _is_kar(_ch(text, check)):
                check -= 1
            if check >= 0 and _is_cons(_ch(text, check)):
                cluster_start = check
                while True:
                    if cluster_start - 1 < 0:
                        break
                    if (_is_halant(_ch(text, cluster_start - 1)) and
                            cluster_start - 2 >= 0 and
                            _is_cons(_ch(text, cluster_start - 2))):
                        cluster_start -= 2
                    else:
                        break
                text = (text[:cluster_start] + "র" + _HALANT +
                        text[cluster_start:i] + text[i + 2:])
                i = cluster_start + 2
                continue

        # Vowel + HALANT + Consonant -> HALANT + Consonant + Vowel
        if (i > 0 and
                _is_halant(_ch(text, i)) and
                (_is_kar(_ch(text, i - 1)) or _is_nukta(_ch(text, i - 1))) and
                i < len(text) - 1):
            text = (text[:i - 1] + _ch(text, i) +
                    _ch(text, i + 1) + _ch(text, i - 1) + text[i + 2:])

        # RA + HALANT + Vowel -> Vowel + RA + HALANT
        if (i > 0 and i < len(text) - 1 and
                _is_halant(_ch(text, i)) and
                _ch(text, i - 1) == "র" and
                _ch(text, i - 2) != _HALANT and
                _is_kar(_ch(text, i + 1))):
            text = (text[:i - 1] + _ch(text, i + 1) +
                    _ch(text, i - 1) + _ch(text, i) + text[i + 2:])

        i += 1

    # Pass 2 — pre-kar repositioning and composite vowels
    i = 0
    while i < len(text):
        if (i < len(text) - 1 and
                _is_prekar(_ch(text, i)) and
                not _is_space(_ch(text, i + 1))):
            j = 1
            while i + j < len(text) - 1 and _is_cons(_ch(text, i + j)):
                if _is_halant(_ch(text, i + j + 1)):
                    j += 2
                else:
                    break
            base = text[:i] + text[i + 1:i + j + 1]
            l = 0
            c = _ch(text, i)
            nxt = _ch(text, i + j + 1)
            if c == "ে" and nxt == "া":
                base += "ো"; l = 1
            elif c == "ে" and nxt == "ৗ":
                base += "ৌ"; l = 1
            else:
                base += c
            text = base + text[i + j + l + 1:]
            i += j

        if (i < len(text) - 1 and
                _is_nukta(_ch(text, i)) and
                _is_postkar(_ch(text, i + 1))):
            text = text[:i] + _ch(text, i + 1) + _ch(text, i) + text[i + 2:]

        i += 1

    return text


# ── Public API ────────────────────────────────────────────────────────────────

def convert_bijoy_to_unicode(text: str) -> str:
    """Convert Bijoy/SutonnyMJ encoded text to Unicode Bengali."""
    if not text:
        return text
    text = _apply_literal(text, PRE_MAP)
    for pat, rep in _PRE_REGEX:
        text = pat.sub(rep, text)
    text = _B2U_REGEX.sub(lambda m: _B2U_LOOKUP.get(m.group(0), m.group(0)), text)
    text = _rearrange(text)
    text = _apply_literal(text, POST_MAP)
    return text


def detect_script(text: str) -> str:
    """Return 'bijoy', 'unicode_bn', 'latin', or 'other'."""
    if not text:
        return "other"
    bn = bj = la = 0
    for c in text:
        cp = ord(c)
        if 0x0980 <= cp <= 0x09FF:
            bn += 1
        elif ((0x00A0 <= cp <= 0x00FF) or
              (0x0152 <= cp <= 0x0178) or
              (0x2013 <= cp <= 0x2122) or
              cp in (0x0192, 0x02C6, 0x02DC, 0x0160, 0x0161)):
            bj += 1
        elif c.isalpha() and cp < 128:
            la += 1
    total = bn + bj + la
    if total == 0:
        return "other"
    if bj > 0:
        return "bijoy"
    if bn > 0:
        return "unicode_bn"
    return "latin"


def is_bijoy(text: str) -> bool:
    return detect_script(text) == "bijoy"
