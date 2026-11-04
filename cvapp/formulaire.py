"""Le formulaire à remplir : identité, photo, profil, expériences, formations,
compétences, langues et centres d'intérêt.

Chaque modification émet le signal « modifie » : la fenêtre enregistre alors
le fichier et met à jour l'aperçu.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from .moteur import EXTENSIONS_PHOTO


# ---------------------------------------------------------------------------
# Petites fonctions pratiques
# ---------------------------------------------------------------------------

def bouton(texte: str, nom: str | None = None, aide: str = "") -> QPushButton:
    b = QPushButton(texte)
    if nom:
        b.setObjectName(nom)
    if aide:
        b.setToolTip(aide)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def etiquette(texte: str = "", nom: str | None = None, retour_ligne: bool = False) -> QLabel:
    e = QLabel(texte)
    if nom:
        e.setObjectName(nom)
    e.setWordWrap(retour_ligne)
    return e


def texte_multiligne(hauteur: int, exemple: str = "") -> QPlainTextEdit:
    zone = QPlainTextEdit()
    zone.setPlaceholderText(exemple)
    zone.setFixedHeight(hauteur)
    zone.setTabChangesFocus(True)  # la touche Tab passe au champ suivant
    return zone


def lignes(zone: QPlainTextEdit) -> list[str]:
    """Le texte d'une zone, une valeur par ligne (lignes vides ignorées)."""
    return [l.strip().lstrip("-•").strip() for l in zone.toPlainText().splitlines() if l.strip()]


SUGGESTIONS_COMPETENCE = ["", "1", "2", "3", "4", "5", "Notions", "Intermédiaire", "Avancé", "Expert"]
SUGGESTIONS_LANGUE = [
    "", "Langue maternelle", "Bilingue", "Courant (C1)", "Courant (B2)",
    "Intermédiaire (B1)", "Notions (A2)", "Débutant (A1)",
]


def liste_niveaux(suggestions: list[str], aide: str) -> QComboBox:
    """Liste déroulante de niveaux, dans laquelle on peut aussi écrire."""
    choix = QComboBox()
    choix.setEditable(True)
    choix.addItems(suggestions)
    choix.setToolTip(aide)
    choix.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    choix.lineEdit().setPlaceholderText("niveau")
    return choix


# ---------------------------------------------------------------------------
# Une « fiche » : une expérience, une formation, une compétence…
# ---------------------------------------------------------------------------

class Fiche(QFrame):
    """Un élément d'une liste, avec ses champs et les boutons ↑ ↓ ×.

    champs : liste de (clé, libellé, genre, exemple), genre parmi
             "ligne", "lignes" (une valeur par ligne), "competence", "langue".
    compacte=True : tout sur une seule ligne (compétences, langues).
    """

    modifiee = Signal()
    monter = Signal(object)
    descendre = Signal(object)
    supprimer = Signal(object)

    def __init__(self, champs, compacte: bool, parent=None):
        super().__init__(parent)
        self._champs = champs
        self._saisies = {}

        b_haut = bouton("↑", "petit", "Monter")
        b_bas = bouton("↓", "petit", "Descendre")
        b_suppr = bouton("×", "petit", "Supprimer")
        b_haut.clicked.connect(lambda: self.monter.emit(self))
        b_bas.clicked.connect(lambda: self.descendre.emit(self))
        b_suppr.clicked.connect(lambda: self.supprimer.emit(self))
        boutons = QHBoxLayout()
        boutons.setSpacing(4)
        for b in (b_haut, b_bas, b_suppr):
            boutons.addWidget(b)

        if compacte:
            ligne = QHBoxLayout(self)
            ligne.setContentsMargins(0, 0, 0, 0)
            ligne.setSpacing(6)
            for cle, libelle, genre, exemple in champs:
                saisie = self._creer_saisie(genre, exemple or libelle)
                ligne.addWidget(saisie, 3 if genre == "ligne" else 2)
                self._saisies[cle] = (genre, saisie)
            ligne.addLayout(boutons)
            return

        self.setObjectName("fiche")
        grille = QGridLayout(self)
        grille.setContentsMargins(12, 10, 12, 12)
        grille.setHorizontalSpacing(10)
        grille.setVerticalSpacing(3)
        rang, colonne = 0, 0
        for cle, libelle, genre, exemple in champs:
            saisie = self._creer_saisie(genre, exemple)
            self._saisies[cle] = (genre, saisie)
            pleine_largeur = genre == "lignes"
            if pleine_largeur and colonne == 1:
                rang, colonne = rang + 2, 0
            grille.addWidget(etiquette(libelle, "champ"), rang, colonne, 1, 2 if pleine_largeur else 1)
            grille.addWidget(saisie, rang + 1, colonne, 1, 2 if pleine_largeur else 1)
            if pleine_largeur or colonne == 1:
                rang, colonne = rang + 2, 0
            else:
                colonne = 1
        rang = rang + 2 if colonne == 1 else rang
        boutons.insertStretch(0, 1)
        grille.addLayout(boutons, rang, 0, 1, 2)

    def _creer_saisie(self, genre: str, exemple: str):
        if genre == "lignes":
            saisie = texte_multiligne(78, exemple)
            saisie.textChanged.connect(self.modifiee)
        elif genre in ("competence", "langue"):
            if genre == "competence":
                saisie = liste_niveaux(SUGGESTIONS_COMPETENCE,
                                       "Un chiffre de 1 à 5 s'affiche avec des points (●●●○○).\n"
                                       "Un mot s'affiche tel quel. Vide : pas de niveau.")
            else:
                saisie = liste_niveaux(SUGGESTIONS_LANGUE, "Choisissez ou écrivez un niveau.")
            saisie.setMinimumWidth(110)
            saisie.currentTextChanged.connect(self.modifiee)
        else:
            saisie = QLineEdit()
            saisie.setPlaceholderText(exemple)
            saisie.textChanged.connect(self.modifiee)
        return saisie

    def valeurs(self) -> dict:
        resultat = {}
        for cle, (genre, saisie) in self._saisies.items():
            if genre == "lignes":
                valeur = lignes(saisie)
            elif isinstance(saisie, QComboBox):
                valeur = saisie.currentText().strip()
                if valeur in {"1", "2", "3", "4", "5"}:
                    valeur = int(valeur)
            else:
                valeur = saisie.text().strip()
            if valeur:
                resultat[cle] = valeur
        return resultat

    def definir(self, donnees: dict):
        for cle, (genre, saisie) in self._saisies.items():
            valeur = donnees.get(cle)
            if genre == "lignes":
                saisie.setPlainText("\n".join(valeur or []))
            elif isinstance(saisie, QComboBox):
                saisie.setCurrentText("" if valeur is None else str(valeur))
            else:
                saisie.setText("" if valeur is None else str(valeur))
                saisie.setCursorPosition(0)

    def premier_champ(self):
        return next(iter(self._saisies.values()))[1]


class SectionListe(QWidget):
    """Une section faite d'une liste de fiches, avec « + ajouter »."""

    modifiee = Signal()

    def __init__(self, champs, texte_ajout: str, compacte: bool = False, parent=None):
        super().__init__(parent)
        self._champs = champs
        self._compacte = compacte
        self._fiches: list[Fiche] = []

        self._liste = QVBoxLayout()
        self._liste.setContentsMargins(0, 0, 0, 0)
        self._liste.setSpacing(6 if compacte else 10)
        ajout = bouton(f"+ {texte_ajout}", "lien")
        ajout.clicked.connect(self._ajouter_vide)

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(6)
        disposition.addLayout(self._liste)
        disposition.addWidget(ajout, 0, Qt.AlignmentFlag.AlignLeft)

    def _nouvelle_fiche(self) -> Fiche:
        fiche = Fiche(self._champs, self._compacte)
        fiche.modifiee.connect(self.modifiee)
        fiche.monter.connect(lambda f: self._deplacer(f, -1))
        fiche.descendre.connect(lambda f: self._deplacer(f, +1))
        fiche.supprimer.connect(self._supprimer)
        self._fiches.append(fiche)
        self._liste.addWidget(fiche)
        return fiche

    def _ajouter_vide(self):
        fiche = self._nouvelle_fiche()
        fiche.premier_champ().setFocus()
        self.modifiee.emit()

    def _deplacer(self, fiche: Fiche, sens: int):
        i = self._fiches.index(fiche)
        j = i + sens
        if not 0 <= j < len(self._fiches):
            return
        self._fiches[i], self._fiches[j] = self._fiches[j], self._fiches[i]
        self._liste.removeWidget(fiche)
        self._liste.insertWidget(j, fiche)
        self.modifiee.emit()

    def _supprimer(self, fiche: Fiche):
        self._fiches.remove(fiche)
        self._liste.removeWidget(fiche)
        fiche.deleteLater()
        self.modifiee.emit()

    def valeurs(self) -> list[dict]:
        return [v for v in (f.valeurs() for f in self._fiches) if v]

    def definir(self, elements):
        for fiche in self._fiches:
            self._liste.removeWidget(fiche)
            fiche.deleteLater()
        self._fiches = []
        for element in elements or []:
            self._nouvelle_fiche().definir(element)


# ---------------------------------------------------------------------------
# Le formulaire complet
# ---------------------------------------------------------------------------

CHAMPS_IDENTITE = [
    ("prenom", "Prénom", "Camille"),
    ("nom", "Nom", "Durand"),
    ("titre", "Titre", "Développeuse junior"),
    ("ville", "Ville", "Lyon"),
    ("email", "Email", "camille@exemple.fr"),
    ("telephone", "Téléphone", "06 12 34 56 78"),
    ("site_web", "Site web (facultatif)", "monsite.fr"),
    ("linkedin", "LinkedIn (facultatif)", "linkedin.com/in/…"),
]

CHAMPS_EXPERIENCE = [
    ("poste", "Poste", "ligne", "Développeuse web (stage)"),
    ("entreprise", "Entreprise", "ligne", "Atelier Numérique"),
    ("ville", "Ville", "ligne", "Lyon"),
    ("dates", "Dates", "ligne", "Mars 2025 – Août 2025"),
    ("missions", "Missions (une par ligne)", "lignes", "Création d'un site de réservation…"),
]
CHAMPS_FORMATION = [
    ("diplome", "Diplôme", "ligne", "Licence Économie et gestion"),
    ("dates", "Dates", "ligne", "2018 – 2021"),
    ("ecole", "École", "ligne", "Université Lyon 2"),
]
CHAMPS_COMPETENCE = [("nom", "Compétence", "ligne", "Compétence (ex. : Python)"),
                     ("niveau", "Niveau", "competence", "")]
CHAMPS_LANGUE = [("langue", "Langue", "ligne", "Langue (ex. : Anglais)"),
                 ("niveau", "Niveau", "langue", "")]


class Formulaire(QWidget):
    modifie = Signal()
    demande_ia = Signal()  # clic sur « écrire avec l'ia »

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chargement = False
        self._photo: str | None = None
        self.dossier_cv = Path.home()

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 18, 22, 28)
        disposition.setSpacing(6)

        def titre(texte, aide=""):
            if disposition.count():
                disposition.addSpacing(18)
            disposition.addWidget(etiquette(texte, "section"))
            if aide:
                disposition.addWidget(etiquette(aide, "discret", retour_ligne=True))
            disposition.addSpacing(4)

        # --- Identité ---
        titre("> identité")
        grille = QGridLayout()
        grille.setHorizontalSpacing(10)
        grille.setVerticalSpacing(3)
        self.identite: dict[str, QLineEdit] = {}
        for i, (cle, libelle, exemple) in enumerate(CHAMPS_IDENTITE):
            saisie = QLineEdit()
            saisie.setPlaceholderText(exemple)
            saisie.textChanged.connect(self._signaler)
            self.identite[cle] = saisie
            rang, colonne = divmod(i, 2)
            grille.addWidget(etiquette(libelle, "champ"), rang * 2, colonne)
            grille.addWidget(saisie, rang * 2 + 1, colonne)
        disposition.addLayout(grille)

        # --- Photo ---
        titre("> photo", "Facultative. Elle est découpée en rond et passée en noir et blanc.")
        ligne_photo = QHBoxLayout()
        self.texte_photo = etiquette("aucune photo", "discret")
        choisir = bouton("choisir…")
        choisir.clicked.connect(self._choisir_photo)
        self.retirer_photo = bouton("[retirer]", "lien")
        self.retirer_photo.clicked.connect(lambda: self._definir_photo(None, signaler=True))
        ligne_photo.addWidget(self.texte_photo, 1)
        ligne_photo.addWidget(self.retirer_photo)
        ligne_photo.addWidget(choisir)
        disposition.addLayout(ligne_photo)

        # --- Profil ---
        titre("> profil")
        ligne_profil = QHBoxLayout()
        ligne_profil.addWidget(etiquette("Un court paragraphe (3 à 4 lignes) qui vous présente.",
                                         "discret", retour_ligne=True), 1)
        bouton_ia = bouton("✦ écrire avec l'ia", aide="Vous ne savez pas quoi mettre ? "
                           "Décrivez-vous en quelques mots et l'IA rédige le paragraphe.")
        bouton_ia.clicked.connect(self.demande_ia)
        ligne_profil.addWidget(bouton_ia, 0, Qt.AlignmentFlag.AlignBottom)
        disposition.addLayout(ligne_profil)
        disposition.addSpacing(4)
        self.profil = texte_multiligne(92, "Développeuse junior passionnée par…")
        self.profil.textChanged.connect(self._signaler)
        disposition.addWidget(self.profil)

        # --- Listes ---
        titre("> expériences", "La plus récente en premier.")
        self.experiences = SectionListe(CHAMPS_EXPERIENCE, "ajouter une expérience")
        disposition.addWidget(self.experiences)

        titre("> formations")
        self.formations = SectionListe(CHAMPS_FORMATION, "ajouter une formation")
        disposition.addWidget(self.formations)

        titre("> compétences", "Niveau facultatif : 1 à 5 (points) ou un mot.")
        self.competences = SectionListe(CHAMPS_COMPETENCE, "ajouter une compétence", compacte=True)
        disposition.addWidget(self.competences)

        titre("> langues")
        self.langues = SectionListe(CHAMPS_LANGUE, "ajouter une langue", compacte=True)
        disposition.addWidget(self.langues)

        titre("> centres d'intérêt", "Un par ligne.")
        self.interets = texte_multiligne(80, "Randonnée\nPhotographie")
        self.interets.textChanged.connect(self._signaler)
        disposition.addWidget(self.interets)

        disposition.addStretch(1)

        for section in (self.experiences, self.formations, self.competences, self.langues):
            section.modifiee.connect(self._signaler)

    # --- Photo -----------------------------------------------------------

    def _choisir_photo(self):
        filtres = "Images (" + " ".join(f"*{e}" for e in EXTENSIONS_PHOTO) + ")"
        chemin, _ = QFileDialog.getOpenFileName(self, "Choisir une photo", str(Path.home() / "Pictures"), filtres)
        if chemin:
            self._definir_photo(chemin, signaler=True)

    def _definir_photo(self, valeur, signaler=False):
        self._photo = valeur or None
        if self._photo:
            chemin = Path(self._photo)
            if not chemin.is_absolute():
                chemin = self.dossier_cv / chemin
            nom = chemin.name
            self.texte_photo.setText(nom if chemin.is_file() else f"{nom} (introuvable)")
            self.retirer_photo.show()
        else:
            self.texte_photo.setText("aucune photo")
            self.retirer_photo.hide()
        if signaler:
            self._signaler()

    # --- Lecture / écriture des valeurs -------------------------------------

    def _signaler(self, *_):
        if not self._chargement:
            self.modifie.emit()

    def donnees(self) -> dict:
        """Les informations saisies, prêtes à être enregistrées (champs vides retirés)."""
        identite = {c: s.text().strip() for c, s in self.identite.items() if s.text().strip()}
        photo = self._photo
        if photo:
            # Photo rangée à côté du fichier du CV : on garde juste son nom
            try:
                photo = str(Path(photo).resolve().relative_to(self.dossier_cv.resolve()))
            except ValueError:
                pass
        brut = {
            "identite": identite,
            "photo": photo,
            "profil": " ".join(self.profil.toPlainText().split()),
            "experiences": self.experiences.valeurs(),
            "formations": self.formations.valeurs(),
            "competences": self.competences.valeurs(),
            "langues": self.langues.valeurs(),
            "centres_interet": lignes(self.interets),
        }
        return {k: v for k, v in brut.items() if v}

    def definir(self, cv: dict, dossier_cv: Path):
        """Remplit le formulaire avec un CV (déjà normalisé par moteur.normaliser)."""
        self._chargement = True
        try:
            self.dossier_cv = Path(dossier_cv)
            for cle, saisie in self.identite.items():
                saisie.setText(cv["identite"].get(cle, ""))
                saisie.setCursorPosition(0)
            self._definir_photo(cv.get("photo"))
            self.profil.setPlainText(cv.get("profil") or "")
            self.experiences.definir(cv.get("experiences"))
            self.formations.definir(cv.get("formations"))
            self.competences.definir(cv.get("competences"))
            self.langues.definir(cv.get("langues"))
            self.interets.setPlainText("\n".join(cv.get("centres_interet") or []))
        finally:
            self._chargement = False
