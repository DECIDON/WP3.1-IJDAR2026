"""M-POPP (Constum et al. 2024, Zenodo 10980636) : actes de mariage manuscrits / dactylographiés.

Source : labels-<kind>-encoding-4.json (balises ouvrantes/fermantes, conteneurs fusionnés), seul
encodage où les niveaux 1-3 sont de vrais empans englobants. 23 paires de balises = 23 classes :
niv.1 Administrative/Husband/Wife/Witness, niv.2 Father/Mother/Ex-husband, niv.3 Birth/Residence,
niv.4 14 champs atomiques. Une span par balise (tous niveaux gardés, cf. CONTRAT).
Mise en page : ⓟ…Ⓟ page, ⓜ…Ⓜ zone d'acte, ⓝ…Ⓝ note marginale, ⓑ…Ⓑ corps → doc = zone ⓜ.
"""
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ["IJDAR_RAW"], "mpopp", "m-popp_datasets")
OUT = os.environ["IJDAR_NORMALIZED"]

PAIRS = {  # ouvrante -> (fermante, label)
    "📖": ("📕", "Administrative"), "👨": ("👦", "Husband"), "👰": ("👧", "Wife"), "🥸": ("🧐", "Witness"),
    "👴": ("🎩", "Father"), "👵": ("👒", "Mother"), "💔": ("😡", "Ex-husband"),
    "🏥": ("👶", "Birth"), "🏠": ("🏡", "Residence"),
    "💬": ("🗯", "First name"), "🗨": ("💭", "Family name"), "⌛": ("⏳", "Age"), "🔧": ("🪛", "Occupation"),
    "🔟": ("🔢", "Street number"), "🛣": ("🛤", "Street type"), "🔠": ("🔡", "Street name"),
    "🌇": ("🌉", "City"), "🗺": ("📌", "Department/Country"), "🌞": ("🌝", "Day"), "📅": ("📆", "Month"),
    "🗓": ("🎉", "Year"), "⏰": ("⌚", "Hour"), "🕑": ("🕘", "Minute"),
}
CLOSE = {c: o for o, (c, _) in PAIRS.items()}
LAYOUT = set("ⓟⓅⓜⓂⓝⓃⓑⒷ")

SUBSETS = {
    "mpopp-manuscrits": dict(kind="handwritten", sous_corpus="actes manuscrits",
                             sheets=["Datasets NER français#12", "Datasets Structured Output#3"],
                             published={"tokens": None, "mentions": None, "docs": 344}),
    "mpopp-dactylo": dict(kind="printed", sous_corpus="actes dactylographiés",
                          sheets=["Datasets NER français#12", "Datasets Structured Output#4"],
                          published={"tokens": None, "mentions": None, "docs": 363}),
}


def parse(seg, warn):
    """Retire les balises de `seg` → (texte, spans). Pile : une fermante ferme l'ouvrante la plus récente
    de même type (tolère un léger désordre)."""
    text, spans, stack = [], [], []
    pos = 0
    for ch in seg:
        if ch in PAIRS:
            stack.append((ch, pos))
        elif ch in CLOSE:
            o = CLOSE[ch]
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == o:
                    _, s = stack.pop(i)
                    if i != len(stack):
                        warn["mal_imbrique"] += 1
                    spans.append([s, pos, PAIRS[o][1]])
                    break
            else:
                warn["fermante_orpheline"] += 1
        elif ch in "ⒷⓃ":  # fin de bloc : les entités non fermées (coupées par la page) y sont closes
            for o, s in stack:
                spans.append([s, pos, PAIRS[o][1]])
            warn["close_en_fin_de_bloc"] += len(stack)
            stack = []
        elif ch in LAYOUT or (ord(ch) > 0x2000 and not ch.isalnum() and ch not in "–—’‘“”…•°"
                              and not 0x2000 <= ord(ch) < 0x2070):
            warn[f"symbole_ignore_{ch}"] += 1
        else:
            text.append(ch)
            pos += 1
    warn["ouvrante_orpheline"] += len(stack)
    text = "".join(text)
    out = []
    for s, e, lab in spans:  # trim des espaces de bord
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            out.append([s, e, lab])
        else:
            warn["span_vide"] += 1
    return text, out


for key, cfg in SUBSETS.items():
    path = f"{RAW}/{cfg['kind']}/labels/labels-{cfg['kind']}-encoding-4.json"
    gt = json.load(open(path))["ground_truth"]
    warn, n_docs, n_pages = Counter(), 0, 0
    with open(f"{OUT}/{key}.jsonl", "w") as fh:
        for split, pages in gt.items():
            for page, v in sorted(pages.items()):
                n_pages += 1
                t = v["text"]
                rest = re.sub(r"ⓜ.*?Ⓜ", "", t, flags=re.S)
                if re.sub(r"[ⓟⓅ\s]", "", rest):
                    warn["texte_hors_zone_acte"] += 1
                for j, seg in enumerate(re.findall(r"ⓜ(.*?)Ⓜ", t, re.S)):
                    seg = seg.replace("Ⓝ", "Ⓝ\n").replace("ⓑ", "\nⓑ")  # note marginale / corps séparés
                    text, spans = parse(seg, warn)
                    lead = len(text) - len(text.lstrip("\n"))
                    text = text.strip("\n")
                    spans = [[a - lead, b - lead, lab] for a, b, lab in spans]
                    n_docs += 1
                    fh.write(json.dumps({"doc_id": f"{page}#{j}", "page_id": page,
                                         "split": {"valid": "dev"}.get(split, split),
                                         "text": text, "spans": spans}, ensure_ascii=False) + "\n")
    print(key, n_pages, "pages", n_docs, "zones", dict(warn))
    meta = {
        "key": key, "dataset": "M-POPP", "sous_corpus": cfg["sous_corpus"], "sheets": cfg["sheets"],
        "unite_doc": "zone d'acte (ⓜ…Ⓜ) d'une page ; un acte coupé par un saut de page = 2 zones",
        "source": "https://zenodo.org/records/10980636 (m-popp_datasets.zip, labels-*-encoding-4.json seuls)",
        "version": "Zenodo 10980636 (2024-04-30)", "annotation": "gold",
        "remarques": (
            "Balises retirées du texte ; encodage 4 (ouvrantes+fermantes, conteneurs fusionnés). "
            "23 classes = 23 balises sur 4 niveaux, une span par balise (niv.1 Administrative/Husband/Wife/"
            "Witness ; niv.2 Father/Mother/Ex-husband ; niv.3 Birth/Residence ; niv.4 First name, Family name, "
            "Age, Occupation, Street number/type/name, City, Department/Country, Day, Month, Year, Hour, Minute) "
            "→ les mentions incluent les conteneurs. Les 118 chemins combinés (ex. Wife>Father>First name) ne "
            "sont pas des labels. Doc = zone d'acte ⓜ d'une page (page_id = image -left/-right) : les actes "
            "à cheval sur deux pages ne sont pas recollés (pas de marqueur fiable de début d'acte, surtout en "
            "dactylographié), d'où plus de docs que d'actes publiés. Note marginale ⓝ et corps ⓑ séparés "
            "par un saut de ligne. Split valid → dev. "
            "Entités non fermées en fin de bloc (coupées par la page) closes à la fin du bloc ; quelques balises "
            "mal imbriquées (47 manuscrit, 21 dactylo) fermées sur l'ouvrante de même type la plus récente. "
            "Dactylographié : 145 pages dans le dépôt (118/14/13) contre 143 (116/14/13) notées dans la fiche."),
        "published": cfg["published"],
    }
    json.dump(meta, open(f"{OUT}/{key}.meta.json", "w"), ensure_ascii=False, indent=1)
