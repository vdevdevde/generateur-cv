"""Le style de l'application : des cartes arrondies, des icônes fines et une
police moderne, uniquement en noir, blanc et gris.

Deux jeux de couleurs : SOMBRE et CLAIR. L'application suit automatiquement
le réglage clair / sombre de Windows.

Les icônes viennent de la police d'icônes de Windows (« Segoe Fluent Icons »
sur Windows 11, « Segoe MDL2 Assets » sur Windows 10) : aucun fichier image.
"""

import weakref

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QIcon, QPainter, QPalette, QPixmap

POLICES_TEXTE = ["Segoe UI Variable Text", "Segoe UI", "Arial"]
POLICES_ICONES = ["Segoe Fluent Icons", "Segoe MDL2 Assets"]

SOMBRE = {
    "fond": "#0F0F10",          # fond de la fenêtre
    "carte": "#19191B",         # fond des cartes (sections)
    "champ": "#111113",         # fond des champs de saisie
    "texte": "#EDEDED",
    "doux": "#8C8C91",          # texte secondaire
    "trait": "#2A2A2E",         # bordures fines
    "trait_fort": "#3A3A3F",    # bordures des boutons
    "survol": "#232326",
    "appui": "#2D2D31",
    "pastille": "#2A2A2E",      # fond des boutons « + ajouter »
    "pastille_survol": "#35353A",
    "accent": "#F2F2F2",        # bouton principal
    "accent_survol": "#D2D2D2",
    "sur_accent": "#0F0F10",    # texte sur le bouton principal
    "apercu": "#0B0B0C",        # fond autour de la page dans l'aperçu
}

CLAIR = {
    "fond": "#F2F2F3",
    "carte": "#FFFFFF",
    "champ": "#F7F7F8",
    "texte": "#141414",
    "doux": "#6E6E73",
    "trait": "#E3E3E6",
    "trait_fort": "#D0D0D4",
    "survol": "#EEEEF0",
    "appui": "#E4E4E7",
    "pastille": "#EBEBED",
    "pastille_survol": "#E0E0E3",
    "accent": "#141414",
    "accent_survol": "#3A3A3D",
    "sur_accent": "#FFFFFF",
    "apercu": "#E4E4E6",
}

# Les icônes utilisées dans l'application (codes de la police d'icônes Windows)
GLYPHES = {
    "identite": "",      # silhouette
    "photo": "",         # appareil photo
    "profil": "",        # crayon
    "experiences": "",   # mallette
    "formations": "",    # toque de diplômé
    "competences": "",   # étoile
    "langues": "",       # globe
    "interets": "",      # cœur
    "nouveau": "",       # document
    "ouvrir": "",        # dossier ouvert
    "enregistrer": "",   # disquette
    "pdf": "",           # téléchargement
    "ajouter": "",       # +
    "monter": "",        # flèche haut
    "descendre": "",     # flèche bas
    "supprimer": "",     # corbeille
    "ia": "",            # ampoule
    "dossier": "",       # dossier
    "maj": "",           # flèches de mise à jour
}

_couleurs = CLAIR
_icones_suivies: list[tuple] = []   # (widget, nom, clé de couleur, taille) à redessiner au changement de thème


def couleurs_actuelles() -> dict:
    return _couleurs


def police_texte(taille: float = 9.5) -> QFont:
    disponibles = set(QFontDatabase.families())
    for nom in POLICES_TEXTE:
        if nom in disponibles:
            police = QFont(nom)
            police.setPointSizeF(taille)
            return police
    police = QFont()
    police.setPointSizeF(taille)
    return police


def _police_icones() -> str | None:
    disponibles = set(QFontDatabase.families())
    return next((n for n in POLICES_ICONES if n in disponibles), None)


def pixmap_icone(nom: str, couleur: str, taille: int = 16) -> QPixmap:
    """Dessine une icône (glyphe de la police d'icônes Windows) dans la couleur voulue."""
    echelle = 2  # dessinée en double taille : nette sur les écrans haute définition
    pixmap = QPixmap(taille * echelle, taille * echelle)
    pixmap.fill(Qt.GlobalColor.transparent)
    police = _police_icones()
    if police and nom in GLYPHES:
        peintre = QPainter(pixmap)
        peintre.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        f = QFont(police)
        f.setPixelSize(int(taille * echelle * 0.82))
        peintre.setFont(f)
        peintre.setPen(QColor(couleur))
        peintre.drawText(QRectF(0, 0, taille * echelle, taille * echelle),
                         Qt.AlignmentFlag.AlignCenter, GLYPHES[nom])
        peintre.end()
    pixmap.setDevicePixelRatio(echelle)
    return pixmap


def associer_icone(widget, nom: str, cle_couleur: str = "texte", taille: int = 16):
    """Met une icône sur un bouton ou un texte, et la recolore quand le thème change."""
    _poser_icone(widget, nom, cle_couleur, taille)
    _icones_suivies.append((weakref.ref(widget), nom, cle_couleur, taille))


def _poser_icone(widget, nom, cle_couleur, taille):
    pixmap = pixmap_icone(nom, _couleurs[cle_couleur], taille)
    if hasattr(widget, "setIcon"):
        widget.setIcon(QIcon(pixmap))
        widget.setIconSize(pixmap.size() / pixmap.devicePixelRatio())
    else:
        widget.setPixmap(pixmap)


def _rafraichir_icones():
    vivantes = []
    for ref, nom, cle, taille in _icones_suivies:
        widget = ref()
        if widget is None:
            continue
        try:
            _poser_icone(widget, nom, cle, taille)
        except RuntimeError:  # widget déjà détruit par Qt
            continue
        vivantes.append((ref, nom, cle, taille))
    _icones_suivies[:] = vivantes


def mode_sombre_actif() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def feuille_de_style(c: dict) -> str:
    """La feuille de style (comme du CSS) avec les couleurs données."""
    return f"""
    QWidget {{ background: {c['fond']}; color: {c['texte']}; }}
    QLabel {{ background: transparent; }}

    /* --- Barre du haut --- */
    QFrame#barre {{ background: {c['fond']}; border-bottom: 1px solid {c['trait']}; }}
    QLabel#logo {{ font-size: 11.5pt; font-weight: 700; }}
    QLabel#version {{ color: {c['doux']}; font-size: 8.5pt; }}

    /* --- Cartes (une par section du formulaire) --- */
    QFrame#carte {{
        background: {c['carte']};
        border: 1px solid {c['trait']};
        border-radius: 12px;
    }}
    QFrame#carte QWidget {{ background: transparent; }}
    QLabel#titreCarte {{ font-size: 10.5pt; font-weight: 650; }}
    QLabel#section {{ font-size: 12pt; font-weight: 700; }}
    QLabel#discret {{ color: {c['doux']}; }}
    QLabel#champ {{ color: {c['doux']}; font-size: 8.8pt; }}
    QLabel#pied {{ color: {c['doux']}; font-size: 8.8pt; }}

    /* Une expérience / une formation : petit cadre dans la carte */
    QFrame#fiche {{
        background: transparent;
        border: 1px solid {c['trait']};
        border-radius: 9px;
    }}
    QFrame#fiche QLabel {{ border: none; }}

    /* --- Champs de saisie --- */
    QLineEdit, QPlainTextEdit, QComboBox {{
        background: {c['champ']};
        border: 1px solid {c['trait']};
        border-radius: 7px;
        padding: 6px 9px;
        selection-background-color: {c['appui']};
        selection-color: {c['texte']};
    }}
    QFrame#carte QLineEdit, QFrame#carte QPlainTextEdit, QFrame#carte QComboBox {{ background: {c['champ']}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: {c['texte']}; }}
    QComboBox {{ min-width: 90px; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {c['carte']};
        border: 1px solid {c['trait_fort']};
        selection-background-color: {c['survol']};
        selection-color: {c['texte']};
        outline: none;
    }}

    /* --- Boutons --- */
    QPushButton {{
        background: {c['carte']};
        color: {c['texte']};
        border: 1px solid {c['trait_fort']};
        border-radius: 7px;
        padding: 6px 13px;
        font-weight: 600;
    }}
    QFrame#carte QPushButton {{ background: {c['carte']}; }}
    QPushButton:hover {{ background: {c['survol']}; }}
    QPushButton:pressed {{ background: {c['appui']}; }}
    QPushButton:disabled {{ color: {c['doux']}; }}

    QPushButton#primaire, QFrame#carte QPushButton#primaire {{
        background: {c['accent']};
        color: {c['sur_accent']};
        border: 1px solid {c['accent']};
    }}
    QPushButton#primaire:hover {{ background: {c['accent_survol']}; border-color: {c['accent_survol']}; }}
    QPushButton#primaire:disabled {{ background: {c['appui']}; border-color: {c['appui']}; color: {c['doux']}; }}

    /* « + Ajouter une expérience » : pastille pleine, sans bordure */
    QPushButton#ajout, QFrame#carte QPushButton#ajout {{
        background: {c['pastille']};
        border: none;
        padding: 7px 13px;
    }}
    QPushButton#ajout:hover {{ background: {c['pastille_survol']}; }}

    /* Petits boutons à icône (monter, descendre, supprimer) */
    QPushButton#petit, QFrame#carte QPushButton#petit {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px;
        min-width: 22px;
    }}
    QPushButton#petit:hover {{ background: {c['survol']}; border-color: {c['trait']}; }}

    /* Liens texte (retirer, plus tard, changer de clé…) */
    QPushButton#lien, QFrame#carte QPushButton#lien {{
        background: transparent;
        border: none;
        color: {c['doux']};
        padding: 4px 2px;
        font-weight: 500;
    }}
    QPushButton#lien:hover {{ color: {c['texte']}; }}

    /* Choix du modèle / du ton : boutons à bascule */
    QPushButton#choix {{ padding: 5px 13px; border-radius: 7px; font-weight: 500; }}
    QPushButton#choix:checked {{
        background: {c['accent']};
        color: {c['sur_accent']};
        border-color: {c['accent']};
        font-weight: 600;
    }}

    /* --- Divers --- */
    QFrame#ligne {{ background: {c['trait']}; border: none; max-height: 1px; min-height: 1px; }}
    QFrame#bandeau {{ background: {c['carte']}; border-top: 1px solid {c['trait']}; }}
    QFrame#bandeau QWidget {{ background: transparent; }}
    QFrame#bandeau QPushButton#primaire {{ padding: 5px 12px; }}
    QScrollArea {{ border: none; }}
    QSplitter::handle {{ background: {c['trait']}; }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['trait_fort']}; min-height: 30px; border-radius: 3px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QToolTip {{
        background: {c['texte']};
        color: {c['fond']};
        border: none;
        padding: 5px 8px;
    }}
    """


def appliquer_theme(application) -> dict:
    """Applique le thème clair ou sombre selon Windows. Renvoie les couleurs choisies."""
    global _couleurs
    c = _couleurs = SOMBRE if mode_sombre_actif() else CLAIR

    # La « palette » sert aux éléments que la feuille de style ne couvre pas (menus, dialogues…)
    palette = QPalette()
    for role, cle in (
        (QPalette.ColorRole.Window, "fond"),
        (QPalette.ColorRole.Base, "champ"),
        (QPalette.ColorRole.AlternateBase, "survol"),
        (QPalette.ColorRole.Button, "carte"),
        (QPalette.ColorRole.WindowText, "texte"),
        (QPalette.ColorRole.Text, "texte"),
        (QPalette.ColorRole.ButtonText, "texte"),
        (QPalette.ColorRole.ToolTipBase, "texte"),
        (QPalette.ColorRole.ToolTipText, "fond"),
        (QPalette.ColorRole.PlaceholderText, "doux"),
        (QPalette.ColorRole.Highlight, "appui"),
        (QPalette.ColorRole.HighlightedText, "texte"),
        (QPalette.ColorRole.Link, "texte"),
        (QPalette.ColorRole.Mid, "trait"),
    ):
        palette.setColor(role, QColor(c[cle]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(c["doux"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(c["doux"]))

    application.setPalette(palette)
    application.setStyleSheet(feuille_de_style(c))
    _rafraichir_icones()
    return c
