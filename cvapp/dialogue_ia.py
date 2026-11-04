"""La fenêtre « rédiger mon profil avec l'IA ».

1. La personne se décrit en quelques mots (facultatif) et choisit un ton.
2. L'IA écrit un paragraphe à partir de ces mots et du reste du CV.
3. La personne peut retoucher le texte, réessayer, ou l'utiliser dans son CV.
"""

import threading

from PySide6.QtCore import QObject, QSettings, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QButtonGroup, QDialog, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from . import NOM_EXE, ia
from .formulaire import bouton, etiquette, texte_multiligne


class _Relais(QObject):
    """Ramène la réponse de l'IA (fil d'arrière-plan) vers la fenêtre."""

    reussite = Signal(str)
    echec = Signal(str)


class DialogueIA(QDialog):
    def __init__(self, cv: dict, profil_actuel: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rédiger mon profil avec l'IA")
        self.setMinimumWidth(620)
        self.texte_choisi = ""
        self._cv = cv
        self._profil_actuel = profil_actuel
        self._reglages = QSettings(NOM_EXE, NOM_EXE)
        self._relais = _Relais(self)
        self._relais.reussite.connect(self._reponse_recue)
        self._relais.echec.connect(self._erreur)

        d = QVBoxLayout(self)
        d.setContentsMargins(26, 22, 26, 22)
        d.setSpacing(8)

        d.addWidget(etiquette("> rédiger mon profil avec l'ia", "section"))
        d.addWidget(etiquette(
            "Pas d'idée ? Décrivez-vous en quelques mots, comme à un ami : l'IA s'appuie sur ces mots "
            "et sur le reste de votre CV (expériences, formations, compétences) pour écrire un "
            "paragraphe que vous pourrez retoucher.", "discret", retour_ligne=True))
        d.addSpacing(6)

        d.addWidget(etiquette("Quelques mots sur vous (facultatif)", "champ"))
        self.description = texte_multiligne(
            96, "Ex. : j'aime résoudre des problèmes, je suis patiente et organisée, "
                "je cherche un premier poste de développeuse dans une petite équipe à Lyon.")
        d.addWidget(self.description)

        # --- Ton ---
        ligne_ton = QHBoxLayout()
        ligne_ton.addWidget(etiquette("ton :", "discret"))
        self.groupe_ton = QButtonGroup(self)
        for i, ton in enumerate(ia.TONS):
            b = bouton(ton, "choix")
            b.setCheckable(True)
            b.setChecked(i == 0)
            b.setProperty("ton", ton)
            self.groupe_ton.addButton(b)
            ligne_ton.addWidget(b)
        ligne_ton.addStretch(1)
        d.addLayout(ligne_ton)

        # --- Clé API (seulement si elle manque, ou pour la changer) ---
        self.bloc_cle = QWidget()
        zone = QVBoxLayout(self.bloc_cle)
        zone.setContentsMargins(0, 8, 0, 0)
        zone.setSpacing(4)
        zone.addWidget(etiquette("Votre clé API Anthropic", "champ"))
        ligne_cle = QHBoxLayout()
        self.saisie_cle = QLineEdit()
        self.saisie_cle.setEchoMode(QLineEdit.EchoMode.Password)
        self.saisie_cle.setPlaceholderText("sk-ant-…")
        obtenir = bouton("[obtenir une clé]", "lien")
        obtenir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ia.ADRESSE_CLES)))
        ligne_cle.addWidget(self.saisie_cle, 1)
        ligne_cle.addWidget(obtenir)
        zone.addLayout(ligne_cle)
        zone.addWidget(etiquette(
            "Elle est enregistrée uniquement sur cet ordinateur. Chaque rédaction coûte "
            "environ 1 à 3 centimes sur votre compte Anthropic.", "discret", retour_ligne=True))
        d.addWidget(self.bloc_cle)

        self._cle = ia.cle_par_defaut(self._reglages.value("cle_api", ""))
        self.changer_cle = bouton("[changer de clé]", "lien")
        self.changer_cle.clicked.connect(lambda: self._afficher_cle(True))
        self._afficher_cle(not self._cle)

        # --- Résultat ---
        d.addSpacing(8)
        self.titre_resultat = etiquette("Proposition (vous pouvez la modifier)", "champ")
        self.resultat = texte_multiligne(110)
        self.titre_resultat.hide()
        self.resultat.hide()
        d.addWidget(self.titre_resultat)
        d.addWidget(self.resultat)

        self.etat = etiquette(
            "Vos informations sont envoyées à Claude (Anthropic) pour écrire le texte. "
            "Vos coordonnées (email, téléphone…) ne sont pas envoyées.", "discret", retour_ligne=True)
        d.addWidget(self.etat)

        # --- Boutons ---
        d.addSpacing(6)
        bas = QHBoxLayout()
        bas.addWidget(self.changer_cle)
        bas.addStretch(1)
        annuler = bouton("annuler")
        annuler.clicked.connect(self.reject)
        self.b_rediger = bouton("✦ rédiger", "primaire")
        self.b_rediger.clicked.connect(self._rediger)
        self.b_utiliser = bouton("utiliser ce texte", "primaire")
        self.b_utiliser.clicked.connect(self._utiliser)
        self.b_utiliser.hide()
        bas.addWidget(annuler)
        bas.addWidget(self.b_rediger)
        bas.addWidget(self.b_utiliser)
        d.addLayout(bas)

        self.description.setFocus()

    def _afficher_cle(self, visible: bool):
        self.bloc_cle.setVisible(visible)
        self.changer_cle.setVisible(not visible)
        if visible:
            self.saisie_cle.setFocus()

    # ------------------------------------------------------------------

    def _rediger(self):
        nouvelle = self.saisie_cle.text().strip()
        if self.bloc_cle.isVisible() and nouvelle:
            self._cle = nouvelle
        if not self._cle:
            self.etat.setText("⚠ Collez d'abord votre clé API Anthropic ([obtenir une clé]).")
            self._afficher_cle(True)
            return

        ton = self.groupe_ton.checkedButton().property("ton")
        description = self.description.toPlainText()
        profil = self.resultat.toPlainText() if self.resultat.isVisible() else self._profil_actuel
        cle, cv = self._cle, self._cv

        self.b_rediger.setEnabled(False)
        self.b_utiliser.setEnabled(False)
        self.etat.setText("> l'ia rédige votre profil… (quelques secondes)")

        def travail():
            try:
                texte = ia.rediger_profil(cv, description, ton, cle, profil)
            except ia.ErreurIA as erreur:
                self._relais.echec.emit(str(erreur))
            except Exception as erreur:  # filet de sécurité
                self._relais.echec.emit(f"Une erreur inattendue est survenue : {erreur}")
            else:
                self._relais.reussite.emit(texte)
        threading.Thread(target=travail, daemon=True).start()

    def _reponse_recue(self, texte: str):
        # La clé a fonctionné : on la garde pour la prochaine fois
        self._reglages.setValue("cle_api", self._cle)
        self._afficher_cle(False)
        self.titre_resultat.show()
        self.resultat.show()
        self.resultat.setPlainText(texte)
        self.etat.setText("✓ Relisez et retouchez si besoin. « réessayer » propose une autre version.")
        self.b_rediger.setText("↻ réessayer")
        self.b_rediger.setObjectName("")
        self.b_rediger.style().unpolish(self.b_rediger)
        self.b_rediger.style().polish(self.b_rediger)
        self.b_rediger.setEnabled(True)
        self.b_utiliser.setEnabled(True)
        self.b_utiliser.show()

    def _erreur(self, message: str):
        self.etat.setText(f"⚠ {message}")
        self.b_rediger.setEnabled(True)
        self.b_utiliser.setEnabled(True)
        if "clé" in message:
            self._afficher_cle(True)

    def _utiliser(self):
        self.texte_choisi = " ".join(self.resultat.toPlainText().split())
        if self.texte_choisi:
            self.accept()
