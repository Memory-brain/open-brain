"""
Relation type patterns for Open Brain Autolink.
Cascaded priority — first match wins.
Each entry: (relation_type, list_of_trigger_regexes)
Regexes match the ~80 chars BEFORE the [[wikilink]].
"""
import re

# Structural patterns (checked first, before cascade)
STRUCTURAL = [
    ("cross_domain",    re.compile(r"cross[- ]domain\b", re.IGNORECASE)),
    ("sintetiza_desde", re.compile(r"synthesized?\s+from\b|sintetizada?\s+desde\b", re.IGNORECASE)),
    ("sintetizada_en",  re.compile(r"sintetizada?\s+en\b|synthesized?\s+into\b", re.IGNORECASE)),
]

# Cascade: first pattern that matches wins
CASCADE = [
    ("refuta",          re.compile(r"\brefuta\b|\brefutes?\b|\bdisproves?\b|\bcontradicts?\b\s+directly", re.IGNORECASE)),
    ("contradice",      re.compile(r"\bcontradice\b|\bcontrasts?\s+with\b|\bcontradicts?\b|\btensión\s+con\b|\btension\s+with\b|\ben\s+tensión\b", re.IGNORECASE)),
    ("refina",          re.compile(r"\brefina\b|\brefinement\s+of\b|\bnarrows?\b|\bprecisa\b|\brefines?\b", re.IGNORECASE)),
    ("extiende",        re.compile(r"\bextiende\b|\bextends?\b|\bbuilds?\s+on\b|\bamplia\b|\bexpands?\b", re.IGNORECASE)),
    ("depende_de",      re.compile(r"\bdepende\s+de\b|\bdepends?\s+on\b|\brequires?\b|\bnecesita\b", re.IGNORECASE)),
    ("ejemplifica",     re.compile(r"\bejemplifica\b|\bexampl(?:e|ifies)\b|\bcase\s+of\b|\billustrates?\b|\bdemonstrates?\b", re.IGNORECASE)),
    ("validado_por",    re.compile(r"\bvalidado\s+por\b|\bvalidated\s+by\b|\bconfirmed\s+by\b|\bconfirma\b|\bconfirms?\b", re.IGNORECASE)),
    ("aplica_a",        re.compile(r"\baplicable\b|\baplica\s+a\b|\bapplies?\s+to\b|\bapplication\s+in\b|\busable\s+in\b", re.IGNORECASE)),
    ("alimenta",        re.compile(r"\balimenta\b|\bfeeds?\b|\binforms?\b|\bprovides?\s+input\b|\bnutre\b", re.IGNORECASE)),
    ("se_ancla_en",     re.compile(r"\bse\s+ancla\s+en\b|\banchored\s+in\b|\brooted\s+in\b|\bfounded\s+on\b", re.IGNORECASE)),
    ("refuerza",        re.compile(r"\brefuerza\b|\breinforces?\b|\bstrengthens?\b|\bsupports?\b|\bapoya\b", re.IGNORECASE)),
    ("operacionaliza",  re.compile(r"\boperacionaliza\b|\boperationalizes?\b|\bimplements?\b|\bconcretizes?\b|\bhace\s+concreto\b", re.IGNORECASE)),
    ("relacionada_con", re.compile(r"\brelacionad[ao]\s+con\b|\brelated\s+to\b|\bconnects?\s+to\b|\blinks?\s+to\b|\bconecta\s+con\b", re.IGNORECASE)),
    ("cita",            re.compile(r"\bcita\b|\bcites?\b|\bquotes?\b|\breferencia\b|\breferences?\b", re.IGNORECASE)),
]

# Default fallback
DEFAULT = "menciona"

WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]')

def classify_relation(context_before: str, link_title: str) -> str:
    """Given ~80 chars before [[link]], return the relation type."""
    ctx = context_before

    # Structural first
    for rel, pat in STRUCTURAL:
        if pat.search(ctx):
            return rel

    # Cascade
    for rel, pat in CASCADE:
        if pat.search(ctx):
            return rel

    return DEFAULT
