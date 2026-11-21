"""Reflex text heuristics: summarising, retoning, simplifying, scoring.

These run locally in well under a millisecond.  They power the offline
provider and give the Reason path (the model) a grounded first draft.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Tuple

STOP = set("""a an the and or but if then so of to in on at for with by from as is are was were be been being this that
these those it its i you he she we they them his her our your my me us do does did have has had not no yes can could
will would should may might must just very really also than too into over under about up down out off again more most
some any each few other such only own same don now there here what which who whom when where why how all both""".split())

_SENT = re.compile(r"(?<=[.!?…])\s+(?=[\"'(\[]?[A-Z0-9À-Ý])")


def sentences(text: str) -> List[str]:
    flat = re.sub(r"\s+", " ", (text or "").strip())
    return [p.strip() for p in _SENT.split(flat) if p.strip()]


def words(text: str) -> List[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", (text or "").lower(), re.UNICODE)


def keywords(text: str, n: int = 6) -> List[str]:
    freq: Dict[str, int] = {}
    for w in words(text):
        if len(w) > 2 and w not in STOP and not w.isdigit():
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-")
    return (cut or text[:limit]) + "…"


def sentence_case(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    lowered = " ".join(w if (w.isupper() and len(w) <= 4) else w.lower() for w in text.split(" "))
    return lowered[0].upper() + lowered[1:]


def title_case(text: str) -> str:
    small = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at"}
    parts = (text or "").strip().split()
    out = []
    for i, w in enumerate(parts):
        out.append(w.lower() if (i and w.lower() in small) else (w[0].upper() + w[1:] if w else w))
    return " ".join(out)


def _scores(text: str) -> List[Tuple[float, int, str]]:
    sents = sentences(text)
    freq: Dict[str, int] = {}
    for w in words(text):
        if w not in STOP and len(w) > 2:
            freq[w] = freq.get(w, 0) + 1
    scored = []
    for i, s in enumerate(sents):
        ws = [w for w in words(s) if w in freq]
        if not ws:
            scored.append((0.0, i, s))
            continue
        score = sum(freq[w] for w in ws) / math.sqrt(len(ws))
        score *= 1.25 if i == 0 else (1.1 if i == len(sents) - 1 else 1.0)
        if re.search(r"\d", s):
            score *= 1.1
        scored.append((score, i, s))
    return scored


def summarize(text: str, max_sentences: int = 2) -> str:
    scored = _scores(text)
    if len(scored) <= max_sentences:
        return " ".join(s for _, _, s in scored)
    top = sorted(scored, key=lambda t: (-t[0], t[1]))[:max(1, max_sentences)]
    return " ".join(s for _, _, s in sorted(top, key=lambda t: t[1]))


def key_points(text: str, n: int = 4, skip: str = "") -> List[str]:
    scored = sorted(_scores(text), key=lambda t: (-t[0], t[1]))
    out: List[str] = []
    for _, _, s in scored:
        if s in skip or len(out) >= n:
            continue
        out.append(clip(s.rstrip("."), 110))
    return out


_TRAILING = {"a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "by", "at", "from", "up", "that", "which", "is", "are", "be", "as", "than", "into", "before", "after", "until", "when", "while", "so", "but", "if"}


def title_of(text: str, max_words: int = 8) -> str:
    """A headline taken from the opening clause, never a bag of keywords."""
    sents = sentences(text)
    if not sents:
        return ""
    first = re.sub(r"[.!?…]+$", "", sents[0])
    tokens = first.split()
    if len(tokens) <= max_words:
        return first[:1].upper() + first[1:]
    clause = re.split(r"[,;:—–]\s", first)[0].split()
    tokens = clause if 3 <= len(clause) <= max_words else tokens[:max_words]
    while len(tokens) > 2 and tokens[-1].lower().strip(",") in _TRAILING:
        tokens.pop()
    out = " ".join(tokens).rstrip(",")
    return out[:1].upper() + out[1:]


_CONTRACT = [("can not", "can't"), ("cannot", "can't"), ("do not", "don't"), ("does not", "doesn't"), ("did not", "didn't"),
             ("will not", "won't"), ("is not", "isn't"), ("are not", "aren't"), ("was not", "wasn't"), ("have not", "haven't"),
             ("has not", "hasn't"), ("could not", "couldn't"), ("should not", "shouldn't"), ("we are", "we're"),
             ("you are", "you're"), ("it is", "it's"), ("that is", "that's"), ("we will", "we'll"), ("you will", "you'll"),
             ("i am", "I'm"), ("we have", "we've"), ("you have", "you've"), ("let us", "let's")]
_FILLER = [(r"\bin order to\b", "to"), (r"\bat this point in time\b", "now"), (r"\bdue to the fact that\b", "because"),
           (r"\bin the event that\b", "if"), (r"\bfor the purpose of\b", "to"), (r"\bwith regard to\b", "about"),
           (r"\bplease note that\b", ""), (r"\bit should be noted that\b", ""), (r"\bas a matter of fact\b", ""),
           (r"\b(just|really|very|actually|basically|simply|quite|literally)\s+", ""), (r"\s*\([^)]{0,80}\)", "")]
_HEDGE = [r"\bi think\b", r"\bi believe\b", r"\bmaybe\b", r"\bperhaps\b", r"\bsort of\b", r"\bkind of\b",
          r"\bit seems (that|like)\b", r"\bpossibly\b", r"\bi guess\b", r"\bjust\b"]
_SIMPLE = {"utilize": "use", "utilise": "use", "utilizing": "using", "utilising": "using", "utilization": "use", "utilisation": "use",
           "shall": "must", "any and all": "all", "arising out of or in connection with": "from", "in connection with": "about",
           "are required to": "need to", "is required to": "needs to", "indemnify": "compensate", "in the event that": "if",
           "aforementioned": "these", "commencing": "starting", "obtained": "got", "documentation": "documents", "stipulations": "terms", "acknowledge": "accept", "remuneration": "payment", "commence": "start", "terminate": "end", "approximately": "about",
           "assistance": "help", "purchase": "buy", "modify": "change", "additional": "more", "require": "need",
           "requires": "needs", "sufficient": "enough", "insufficient": "not enough", "demonstrate": "show",
           "facilitate": "help", "subsequently": "then", "prior to": "before", "numerous": "many", "obtain": "get",
           "regarding": "about", "endeavor": "try", "authenticate": "sign in", "configuration": "setup",
           "navigate": "go", "initiate": "start", "indicate": "show", "attempt": "try", "ensure": "make sure",
           "retain": "keep", "notify": "tell", "inquire": "ask", "permit": "let", "verify": "check",
           "currently": "now", "however": "but", "therefore": "so", "immediately": "right away", "select": "pick",
           "preferences": "settings", "discontinue": "stop", "erroneous": "wrong", "valid": "correct"}


def _apply_pairs(text: str, pairs: List[Tuple[str, str]], reverse: bool = False) -> str:
    for a, b in pairs:
        src, dst = (b, a) if reverse else (a, b)
        pattern = re.compile(r"\b" + re.escape(src) + r"\b", re.IGNORECASE)

        def repl(m: "re.Match[str]", dst: str = dst) -> str:
            return dst[0].upper() + dst[1:] if m.group(0)[0].isupper() else dst

        text = pattern.sub(repl, text)
    return text


def _tidy(text: str) -> str:
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\bBut,", "But", text)
    text = re.sub(r"([.!?]\s+)([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text[0].upper() + text[1:] if text else text


def retone(text: str, tone: str) -> str:
    """Rule-based tone shift: friendly, formal, concise, confident, empathetic, direct, neutral."""
    tone = (tone or "neutral").lower()
    out = (text or "").strip()
    if tone in ("friendly", "casual", "warm", "playful"):
        out = re.sub(r"\bplease be advised that\b\s*", "", out, flags=re.IGNORECASE)
        out = _apply_pairs(out, _CONTRACT)
        out = re.sub(r"\bYou must\b", "You'll need to", out)
        out = re.sub(r"\byou must\b", "you'll need to", out)
        out = re.sub(r"\b(Invalid|Incorrect)\b", "That doesn't look right:", out)
        out = re.sub(r"\bError\b:?", "Something went wrong.", out)
        out = re.sub(r"\bUnable to\b", "We couldn't", out)
    elif tone in ("formal", "professional"):
        out = _apply_pairs(out, _CONTRACT, reverse=True)
        out = re.sub(r"!+", ".", out)
        out = re.sub(r"\b(hi|hey)\b", "Hello", out, flags=re.IGNORECASE)
        out = re.sub(r"\bthanks\b", "thank you", out, flags=re.IGNORECASE)
        out = re.sub(r"\b(asap)\b", "as soon as possible", out, flags=re.IGNORECASE)
    elif tone in ("concise", "short", "shorter", "direct"):
        for pattern, repl in _FILLER:
            out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
        if tone != "direct" and len(sentences(out)) > 2:
            out = summarize(out, 2)
    elif tone in ("confident", "assertive"):
        for pattern in _HEDGE:
            out = re.sub(pattern + r",?\s*", "", out, flags=re.IGNORECASE)
        out = re.sub(r"\b(might|could) be able to\b", "can", out, flags=re.IGNORECASE)
        out = re.sub(r"\bshould be\b", "is", out, flags=re.IGNORECASE)
    elif tone in ("empathetic", "supportive", "calm"):
        out = _apply_pairs(out, _CONTRACT)
        out = re.sub(r"!+", ".", out)
        negative = re.search(r"\b(error|fail|failed|invalid|denied|unable|can't|couldn't|wrong|problem)\b", out, re.IGNORECASE)
        if negative and not out.lower().startswith("sorry"):
            out = "Sorry about that. " + out
    return _tidy(out)


def simplify(text: str, max_words: int = 20) -> str:
    out = (text or "").strip()
    for src, dst in sorted(_SIMPLE.items(), key=lambda kv: -len(kv[0])):
        out = _apply_pairs(out, [(src, dst)])
    for pattern, repl in _FILLER[:7]:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    pieces: List[str] = []
    for s in sentences(out) or [out]:
        if len(s.split()) > max_words:
            parts = re.split(r",\s+(?:and|but|which|so|because)\s+|;\s+", s)
            for p in parts:
                p = p.strip().rstrip(".")
                if p:
                    pieces.append(p[0].upper() + p[1:] + ".")
        else:
            pieces.append(s)
    return _tidy(" ".join(pieces))


def syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1 and not word.endswith(("le", "ee")):
        count -= 1
    return max(1, count)


def reading_grade(text: str) -> float:
    """Flesch–Kincaid grade level."""
    ws = words(text)
    sents = max(1, len(sentences(text)))
    if not ws:
        return 0.0
    grade = 0.39 * (len(ws) / sents) + 11.8 * (sum(syllables(w) for w in ws) / len(ws)) - 15.59
    return round(max(0.0, grade), 1)


_POS = set("""good great excellent love loved like happy thanks thank awesome amazing perfect fast easy helpful works
nice wonderful fantastic pleased delighted smooth reliable clear glad win improved better best success successful
appreciate brilliant solid stable resolved fixed saved recommend enjoy impressive""".split())
_NEG = set("""bad terrible awful hate hated slow broken bug bugs crash crashed crashes error errors fail failed failing
failure useless confusing confused annoying annoyed angry frustrated frustrating worst worse problem problems issue
issues wrong unacceptable disappointed disappointing refund cancel never stuck lost missing late delay delayed
ridiculous horrible waste poor unusable unhappy complaint stupid""".split())
_HOT = set("stupid idiot ridiculous incompetent useless pathetic unacceptable worst hate garbage trash nonsense".split())


def sentiment(text: str) -> Tuple[str, float]:
    """Lexicon polarity in [-1, 1] with simple negation handling."""
    ws = words(text)
    if not ws:
        return "neutral", 0.0
    score = 0.0
    for i, w in enumerate(ws):
        polarity = 1.0 if w in _POS else (-1.0 if w in _NEG else 0.0)
        if polarity and i and ws[i - 1] in ("not", "no", "never", "isn't", "don't", "doesn't", "can't", "won't", "didn't"):
            polarity = -polarity
        score += polarity
    norm = max(-1.0, min(1.0, score / math.sqrt(len(ws)) / 1.5))
    label = "positive" if norm > 0.15 else ("negative" if norm < -0.15 else "neutral")
    return label, round(norm, 2)


def heat(text: str) -> float:
    """0–1 estimate of how heated a message is (caps, exclamation, hostile words)."""
    raw = text or ""
    ws = words(raw)
    if not ws:
        return 0.0
    letters = [c for c in raw if c.isalpha()]
    caps = sum(1 for c in letters if c.isupper()) / max(1, len(letters))
    hostile = sum(1 for w in ws if w in _HOT) / len(ws)
    bangs = min(1.0, raw.count("!") / 4.0)
    _, polarity = sentiment(raw)
    value = 0.45 * min(1.0, hostile * 8) + 0.25 * (caps if len(letters) > 12 else 0) * 1.6 + 0.15 * bangs + 0.25 * max(0.0, -polarity)
    return round(min(1.0, value), 2)


_UI_WORDS: Dict[str, Dict[str, str]] = {
    "es": {"save": "Guardar", "cancel": "Cancelar", "delete": "Eliminar", "settings": "Configuración", "search": "Buscar",
           "welcome": "Bienvenido", "sign in": "Iniciar sesión", "sign out": "Cerrar sesión", "next": "Siguiente",
           "back": "Atrás", "yes": "Sí", "no": "No", "help": "Ayuda", "overview": "Resumen", "orders": "Pedidos",
           "customers": "Clientes", "reports": "Informes", "save changes": "Guardar cambios", "email": "Correo electrónico",
           "name": "Nombre", "total": "Total", "status": "Estado", "date": "Fecha", "invoices": "Facturas"},
    "fr": {"save": "Enregistrer", "cancel": "Annuler", "delete": "Supprimer", "settings": "Paramètres", "search": "Rechercher",
           "welcome": "Bienvenue", "sign in": "Se connecter", "sign out": "Se déconnecter", "next": "Suivant",
           "back": "Retour", "yes": "Oui", "no": "Non", "help": "Aide", "overview": "Aperçu", "orders": "Commandes",
           "customers": "Clients", "reports": "Rapports", "save changes": "Enregistrer les modifications",
           "email": "E-mail", "name": "Nom", "total": "Total", "status": "Statut", "date": "Date", "invoices": "Factures"},
    "de": {"save": "Speichern", "cancel": "Abbrechen", "delete": "Löschen", "settings": "Einstellungen", "search": "Suchen",
           "welcome": "Willkommen", "sign in": "Anmelden", "sign out": "Abmelden", "next": "Weiter", "back": "Zurück",
           "yes": "Ja", "no": "Nein", "help": "Hilfe", "overview": "Übersicht", "orders": "Bestellungen",
           "customers": "Kunden", "reports": "Berichte", "save changes": "Änderungen speichern", "email": "E-Mail",
           "name": "Name", "total": "Summe", "status": "Status", "date": "Datum", "invoices": "Rechnungen"},
    "pt": {"save": "Salvar", "cancel": "Cancelar", "delete": "Excluir", "settings": "Configurações", "search": "Pesquisar",
           "welcome": "Bem-vindo", "sign in": "Entrar", "sign out": "Sair", "next": "Próximo", "back": "Voltar",
           "yes": "Sim", "no": "Não", "help": "Ajuda", "overview": "Visão geral", "orders": "Pedidos",
           "customers": "Clientes", "reports": "Relatórios", "save changes": "Salvar alterações", "email": "E-mail",
           "name": "Nome", "total": "Total", "status": "Status", "date": "Data", "invoices": "Faturas"},
    "ja": {"save": "保存", "cancel": "キャンセル", "delete": "削除", "settings": "設定", "search": "検索", "welcome": "ようこそ",
           "sign in": "ログイン", "sign out": "ログアウト", "next": "次へ", "back": "戻る", "yes": "はい", "no": "いいえ",
           "help": "ヘルプ", "overview": "概要", "orders": "注文", "customers": "顧客", "reports": "レポート",
           "save changes": "変更を保存", "email": "メール", "name": "名前", "total": "合計", "status": "ステータス",
           "date": "日付", "invoices": "請求書"},
}
_ACCENT = str.maketrans("aeiouAEIOUcnyCNY", "áéíóúÁÉÍÓÚçñýÇÑÝ")


def localize(text: str, locale: str) -> Tuple[str, bool]:
    """Translate common interface vocabulary; fall back to pseudo-localisation.

    Returns ``(text, exact)``.  Pseudo-localised output keeps length and
    placeholders so layouts can be verified before real translation exists.
    """
    lang = (locale or "en").split("-")[0].lower()
    if lang == "en" or not text:
        return text, True
    table = _UI_WORDS.get(lang, {})
    hit = table.get(text.strip().lower())
    if hit:
        return hit, True
    parts = re.split(r"(\{[^}]*\}|%\w|\$\{[^}]*\})", text)
    pseudo = "".join(p if i % 2 else p.translate(_ACCENT) for i, p in enumerate(parts))
    return "[%s] %s" % (lang, pseudo), False


_ERROR_REWRITES = [
    (r"^\s*(?:error|failure|fatal|warning)\s*[:\-–]\s*", ""),
    (r"\boperation failed\b", "we couldn't finish that"),
    (r"\bdue to invalid input parameters\b", "because some of the details don't look right"),
    (r"\b(?:an )?unexpected error (?:has )?occurred\b", "something went wrong on our side"),
    (r"\bdue to\b", "because of"), (r"\bunable to\b", "couldn't"), (r"\bfailed to\b", "couldn't"),
    (r"\binvalid\b", "not valid"), (r"\bparameters?\b", "details"), (r"\bplease try again later\b", "try again in a few minutes"),
    (r"\bcontact (?:your )?(?:system )?administrator\b", "ask your workspace admin for help"),
]


def friendly_error(text: str, hint: str = "") -> str:
    """Rewrite a system-style error into a plain sentence that says what to do next."""
    out = (text or "").strip()
    for pattern, repl in _ERROR_REWRITES:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip().rstrip(".")
    out = out[:1].upper() + out[1:] + "." if out else ""
    if hint and not re.search(r"\b(try|check|ask)\b", out, re.IGNORECASE):
        out += " " + hint
    return out


_AUX = ("is", "are", "was", "were", "can", "could", "will", "would", "should", "must", "has", "have")
_VERBS = ("accept", "support", "include", "show", "run", "use", "send", "create", "let", "allow", "require", "need", "work", "handle", "detect",
          "import", "export", "save", "open", "add", "remove", "keep", "store", "check", "start", "stop", "take", "make", "give", "provide",
          "offer", "contain", "cover", "apply", "update", "sync", "return", "arrive", "appear", "expire", "renew", "cost", "ship")
_VERBS_S = {v + ("es" if v.endswith(("ch", "sh", "ss", "x")) else "s"): v for v in _VERBS}
_ADVERBS = ("now", "also", "always", "still", "just", "already", "only")


def question_from(sentence: str) -> str:
    """Turn a declarative sentence into the yes/no question it answers ("" when no safe rewrite exists)."""
    s = re.sub(r"[.!?…]+$", "", (sentence or "").strip())
    s = re.split(r",\s+(?:and|but|so|which)\s+|;\s+|\s+(?:and|so)\s+(?=(?:you|we|they|it|nothing|can|will|is|are|must|should|%s)\b)" % "|".join(_VERBS_S), s)[0]
    tokens = s.split()
    if len(tokens) < 3:
        return ""

    def subject(words: List[str]) -> str:
        words = [w for w in words if w.lower() not in _ADVERBS]
        if not words:
            return ""
        head = words[0]
        if not (head.isupper() and len(head) > 1):
            head = head[:1].lower() + head[1:]
        return " ".join([head] + words[1:])

    for i, tok in enumerate(tokens[1:7], start=1):
        low = tok.lower()
        if low in _AUX:
            rest = [t for t in tokens[i + 1:] if t.lower() not in ("not",) + _ADVERBS]
            who = subject(tokens[:i])
            return "%s %s %s?" % (low.capitalize(), who, " ".join(rest)) if who and rest else ""
        if low in _VERBS_S:
            who = subject(tokens[:i])
            return "Does %s %s %s?" % (who, _VERBS_S[low], " ".join(tokens[i + 1:])) if who and tokens[i + 1:] else ""
        if low in _VERBS and i == 1:
            return "Do %s %s?" % (subject(tokens[:1]), " ".join(tokens[1:]))
    return ""


_DECISION = re.compile(r"\b(decision\s*:|decided|agreed|approved|we(?:'ll| will) go with|going with|settled on|confirmed)", re.IGNORECASE)


def decisions(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pull explicit decisions, with owner and due date when stated, out of a discussion."""
    out: List[Dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        for sentence in sentences(str(m.get("content", ""))):
            if not _DECISION.search(sentence):
                continue
            text = re.sub(r"^\s*decision\s*:\s*", "", sentence.strip(), flags=re.IGNORECASE).rstrip(".")
            owner = re.search(r"\b([A-Z][a-zà-ÿ]+)\s+(?:owns|will own|takes|will take|is responsible for|to lead|leads)\b", text)
            due = re.search(r"\b(?:by|on|for|before)\s+((?:the\s+)?\d{1,2}(?:st|nd|rd|th)|monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|eod|end of (?:day|week|month))\b",
                            text, re.IGNORECASE)
            out.append({"decision": clip(text[:1].upper() + text[1:], 160), "owner": owner.group(1) if owner else m.get("author"),
                        "due": due.group(1) if due else None})
    return out
