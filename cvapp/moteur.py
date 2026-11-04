"""Le cœur du générateur, sans interface :

- lire et enregistrer le fichier d'informations (.yaml) ;
- nettoyer les données (une section vide n'apparaît pas dans le CV) ;
- remplir le modèle HTML + CSS (dossier « modeles »).
"""

import re
import sys
from pathlib import Path
from urllib.parse import quote

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Dossier des fichiers livrés avec l'application (modèles, exemple, icône).
# Depuis le .exe, PyInstaller les range dans sys._MEIPASS.
DOSSIER_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DOSSIER_MODELES = DOSSIER_BASE / "modeles"
FICHIER_EXEMPLE = DOSSIER_BASE / "mon_cv.yaml"

MODELES = {"classique": "Classique", "moderne": "Moderne"}

# Une page A4 : 210 × 297 mm. En pixels CSS (96 par pouce) :
HAUTEUR_A4_PX = 297 / 25.4 * 96


class ErreurCV(Exception):
    """Erreur expliquée en français, affichée telle quelle à l'utilisateur."""


# ---------------------------------------------------------------------------
# Lecture et écriture du fichier
# ---------------------------------------------------------------------------

def lire_fichier(chemin: Path) -> dict:
    chemin = Path(chemin)
    if not chemin.exists():
        raise ErreurCV(f"Le fichier « {chemin.name} » est introuvable.")
    try:
        texte = chemin.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        texte = chemin.read_text(encoding="cp1252")  # ancien Bloc-notes (« ANSI »)

    try:
        donnees = yaml.safe_load(texte)
    except yaml.YAMLError as erreur:
        marque = getattr(erreur, "problem_mark", None)
        ligne = f" vers la ligne {marque.line + 1}" if marque is not None else ""
        raise ErreurCV(
            f"Le fichier « {chemin.name} » contient une erreur de mise en forme{ligne}.\n"
            "Vérifiez à cet endroit :\n"
            "  - que le décalage (les espaces en début de ligne) est le même que dans l'exemple ;\n"
            "  - que vous n'avez pas utilisé la touche Tabulation (seulement des espaces) ;\n"
            "  - qu'un texte contenant « : » est bien \"entre guillemets\"."
        ) from None

    if donnees is None:
        return {}
    if not isinstance(donnees, dict):
        raise ErreurCV(f"Le fichier « {chemin.name} » n'a pas la forme d'un CV.")
    return donnees


ENTETE_FICHIER = """\
# ============================================================================
#  Mon CV — fichier créé par l'application « Générateur de CV ».
#  Vous pouvez le modifier dans l'application, ou à la main dans le Bloc-notes
#  (gardez le décalage en début de ligne, avec des espaces uniquement).
# ============================================================================

"""


def enregistrer_fichier(donnees: dict, chemin: Path):
    """Enregistre les informations du CV dans un fichier .yaml lisible."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    texte = yaml.safe_dump(donnees, allow_unicode=True, sort_keys=False, width=1000)
    # Une ligne vide entre les grandes sections, pour la lisibilité
    texte = re.sub(r"\n(?=[a-z_]+:)", "\n\n", texte)
    temporaire = chemin.with_suffix(".tmp")
    temporaire.write_text(ENTETE_FICHIER + texte, encoding="utf-8")
    temporaire.replace(chemin)  # remplacement en une fois : jamais de fichier à moitié écrit


# ---------------------------------------------------------------------------
# Nettoyage des données
# ---------------------------------------------------------------------------

def nettoyer(valeur, cle=""):
    """Retire les champs vides et convertit tout en texte.

    Une section vide ou absente devient None : elle n'est pas affichée.
    """
    if valeur is None:
        return None
    if isinstance(valeur, bool):  # en YAML, « oui » / « non » deviennent des booléens
        return "Oui" if valeur else "Non"
    if isinstance(valeur, (int, float)):
        if cle == "niveau" and float(valeur).is_integer() and 1 <= valeur <= 5:
            return int(valeur)  # un niveau de 1 à 5 s'affiche avec des points
        return str(valeur)
    if isinstance(valeur, dict):
        propre = {str(k): nettoyer(v, str(k)) for k, v in valeur.items()}
        propre = {k: v for k, v in propre.items() if v is not None}
        return propre or None
    if isinstance(valeur, list):
        propre = [nettoyer(v, cle) for v in valeur]
        propre = [v for v in propre if v is not None]
        return propre or None
    texte = " ".join(str(valeur).split())  # espaces et retours à la ligne en trop
    if cle == "niveau" and texte in {"1", "2", "3", "4", "5"}:
        return int(texte)
    return texte or None


def _en_liste(valeur):
    if valeur is None:
        return None
    return valeur if isinstance(valeur, list) else [valeur]


def normaliser(brut: dict) -> dict:
    """Donne toujours la même forme aux données, même si le fichier est approximatif."""
    cv = nettoyer(brut) or {}
    if not isinstance(cv.get("identite"), dict):
        cv["identite"] = {}

    def liste_de_fiches(section, cle_principale):
        elements = _en_liste(cv.get(section)) or []
        resultat = []
        for e in elements:
            if isinstance(e, str):  # « - Python » au lieu de « - nom: Python »
                e = {cle_principale: e}
            if isinstance(e, dict) and e.get(cle_principale):
                resultat.append(e)
        cv[section] = resultat or None

    liste_de_fiches("experiences", "poste")
    liste_de_fiches("formations", "diplome")
    liste_de_fiches("competences", "nom")
    liste_de_fiches("langues", "langue")

    for e in cv.get("experiences") or []:
        missions = _en_liste(e.get("missions"))
        e["missions"] = [m for m in missions if isinstance(m, str)] if missions else None

    interets = _en_liste(cv.get("centres_interet"))
    cv["centres_interet"] = [c for c in interets if isinstance(c, str)] if interets else None

    if not isinstance(cv.get("profil"), str):
        cv["profil"] = None
    if not isinstance(cv.get("photo"), str):
        cv["photo"] = None

    modele = str(cv.get("modele") or "").strip().lower()
    cv["modele"] = modele if modele in MODELES else "classique"
    return cv


def verifier_pour_pdf(cv: dict):
    if not (cv["identite"].get("prenom") or cv["identite"].get("nom")):
        raise ErreurCV("Indiquez au moins votre prénom et votre nom avant de créer le PDF.")


def liste_contacts(identite: dict) -> list:
    champs = [
        ("ville", "Ville"),
        ("email", "Email"),
        ("telephone", "Téléphone"),
        ("site_web", "Site web"),
        ("linkedin", "LinkedIn"),
    ]
    return [{"etiquette": e, "valeur": identite[c]} for c, e in champs if identite.get(c)]


def nom_du_fichier(identite: dict) -> str:
    """« CV_Prenom_Nom.pdf », sans caractère interdit par Windows."""
    texte = "_".join(m for m in (identite.get("prenom", ""), identite.get("nom", "")) if m)
    texte = re.sub(r'[\\/:*?"<>|]', "", texte)
    texte = re.sub(r"\s+", "_", texte).strip("_.")
    return f"CV_{texte}.pdf" if texte else "CV.pdf"


# ---------------------------------------------------------------------------
# Photo et police
# ---------------------------------------------------------------------------

EXTENSIONS_PHOTO = (".jpg", ".jpeg", ".png", ".webp")


def chemin_photo(valeur, dossier_cv: Path) -> Path | None:
    """Le chemin complet de la photo, ou None si elle est absente ou introuvable."""
    if not valeur:
        return None
    chemin = Path(str(valeur).strip().strip('"'))
    if not chemin.is_absolute():
        chemin = Path(dossier_cv) / chemin
    if chemin.is_file() and chemin.suffix.lower() in EXTENSIONS_PHOTO:
        return chemin
    return None


def adresse_fichier(chemin: Path) -> str:
    """Adresse « file:///… » d'un fichier, lisible par le moteur de rendu."""
    return "file:///" + quote(str(Path(chemin).resolve()).replace("\\", "/"), safe="/:")


def police_inter(dossiers) -> str | None:
    """Si un fichier de police Inter se trouve dans un dossier « polices », on l'utilise."""
    for dossier in dossiers:
        dossier = Path(dossier) / "polices"
        if not dossier.is_dir():
            continue
        candidats = [
            p for p in dossier.iterdir()
            if p.suffix.lower() in (".ttf", ".woff2") and p.name.lower().startswith("inter")
            and "italic" not in p.name.lower()
        ]
        candidats.sort(key=lambda p: "variable" not in p.name.lower())
        if candidats:
            return adresse_fichier(candidats[0])
    return None


# ---------------------------------------------------------------------------
# Création de la page HTML
# ---------------------------------------------------------------------------

_environnement = None


def _gabarits() -> Environment:
    global _environnement
    if _environnement is None:
        _environnement = Environment(
            loader=FileSystemLoader(DOSSIER_MODELES, encoding="utf-8"),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _environnement


def creer_html(cv: dict, dossier_cv: Path, apercu: bool = False) -> str:
    """Remplit le modèle choisi avec les informations du CV.

    apercu=True ajoute l'habillage de l'aperçu à l'écran (fond gris, ombre,
    trait « fin de la page 1 »). Il disparaît à l'impression en PDF.
    """
    photo = chemin_photo(cv.get("photo"), dossier_cv)
    return _gabarits().get_template(f"{cv['modele']}.html").render(
        cv=cv,
        photo=adresse_fichier(photo) if photo else None,
        contacts=liste_contacts(cv["identite"]),
        police_inter=police_inter([dossier_cv, DOSSIER_BASE]),
        apercu=apercu,
    )


def compter_pages(chemin_pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", Path(chemin_pdf).read_bytes()))
