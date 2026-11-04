"""La fenêtre principale du Générateur de CV.

    ┌──────────────────────────────────────────────────────────────┐
    │ generateur_cv_                                        v1.0.0 │
    │ [nouveau] [ouvrir…] [enregistrer sous…]  [classique][moderne] [créer le pdf] │
    ├───────────────────────────┬──────────────────────────────────┤
    │ formulaire (défilant)     │ aperçu du CV, mis à jour en direct│
    ├───────────────────────────┴──────────────────────────────────┤
    │ > messages                         (bandeau de mise à jour)  │
    └──────────────────────────────────────────────────────────────┘

Tout est enregistré automatiquement dans le fichier .yaml du CV
(par défaut : Documents\\Générateur de CV\\mon_cv.yaml).
"""

import json
import logging
import os
import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QPixmap, QShortcut
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from . import DEPOT_GITHUB, NOM_APPLICATION, NOM_EXE, VERSION, moteur, mise_a_jour
from .formulaire import Formulaire, bouton, etiquette
from .moteur import ErreurCV
from .style import appliquer_theme, associer_icone, couleurs_actuelles, definir_preference, mode_sombre_actif
from .pdf import JS_HAUTEUR, charger_html, depassement_mm, mise_en_page_a4

journal = logging.getLogger(__name__)
MARGE = 24
LARGEUR_PAGE_PX = 210 / 25.4 * 96  # largeur d'une page A4 en pixels CSS


def dossier_documents() -> Path:
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(documents or Path.home()) / NOM_APPLICATION


class EnTete(QWidget):
    """Le petit logo, le nom de l'application et sa version."""

    def __init__(self, parent=None):
        super().__init__(parent)
        ligne = QHBoxLayout(self)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(9)
        logo = QLabel()
        image = QPixmap(str(moteur.DOSSIER_BASE / "ressources" / "icone.png"))
        if not image.isNull():
            image.setDevicePixelRatio(2)
            logo.setPixmap(image.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
        ligne.addWidget(logo)
        ligne.addWidget(etiquette(NOM_APPLICATION, "logo"))
        version = etiquette(f"v{VERSION}", "version")
        ligne.addWidget(version, 0, Qt.AlignmentFlag.AlignBottom)


class RelaisMiseAJour(QObject):
    """Fait passer les nouvelles de la mise à jour (fil d'arrière-plan) vers la fenêtre."""

    trouvee = Signal(object)
    progression = Signal(int, str)
    prete = Signal(object)
    echec = Signal(str)


class FenetrePrincipale(QMainWindow):
    def __init__(self, fichier_demande: str | None = None):
        super().__init__()
        self.setWindowTitle(NOM_APPLICATION)
        self.resize(1280, 820)
        self.setMinimumSize(900, 560)

        self.reglages = QSettings(NOM_EXE, NOM_EXE)
        self.fichier: Path | None = None
        self.modele = "classique"
        self.pdf_demande: Path | None = None   # PDF à créer dès que l'aperçu est prêt
        self.hauteur_px = 0.0
        self._chargement_en_cours = False
        self._page_prete = False

        # --- Barre d'outils ---
        b_nouveau = bouton("Nouveau", aide="Commencer un nouveau CV vide (Ctrl+N)", icone="nouveau")
        b_ouvrir = bouton("Ouvrir…", aide="Ouvrir un fichier de CV .yaml (Ctrl+O)", icone="ouvrir")
        b_copie = bouton("Enregistrer sous…", aide="Enregistrer une copie de ce CV sous un autre nom",
                         icone="enregistrer")
        self.b_theme = bouton("", aide="Changer de thème : clair ou sombre")
        self.b_theme.clicked.connect(self._basculer_theme)
        self._etiqueter_bouton_theme()
        b_nouveau.clicked.connect(self.nouveau)
        b_ouvrir.clicked.connect(self.ouvrir)
        b_copie.clicked.connect(self.enregistrer_sous)

        self.choix_modele = QButtonGroup(self)
        self.boutons_modele = {}
        for cle, libelle in moteur.MODELES.items():
            b = bouton(libelle, "choix", aide=f"Modèle « {libelle.lower()} »")
            b.setCheckable(True)
            self.choix_modele.addButton(b)
            self.boutons_modele[cle] = b
            b.clicked.connect(lambda _=False, c=cle: self._changer_modele(c))
        self.boutons_modele["classique"].setToolTip("Une seule colonne")
        self.boutons_modele["moderne"].setToolTip("Colonne grise à gauche, contenu à droite")

        self.b_pdf = bouton("Créer le PDF", "primaire", "Créer le CV en PDF et l'ouvrir (Ctrl+P)", "pdf")
        self.b_pdf.clicked.connect(self.creer_pdf)

        barre = QFrame()
        barre.setObjectName("barre")
        outils = QHBoxLayout(barre)
        outils.setContentsMargins(MARGE, 12, MARGE, 12)
        outils.setSpacing(8)
        outils.addWidget(EnTete())
        outils.addSpacing(18)
        for b in (b_nouveau, b_ouvrir, b_copie, self.b_theme):
            outils.addWidget(b)
        outils.addStretch(1)
        outils.addWidget(etiquette("Modèle", "discret"))
        outils.addWidget(self.boutons_modele["classique"])
        outils.addWidget(self.boutons_modele["moderne"])
        outils.addSpacing(14)
        outils.addWidget(self.b_pdf)

        # --- Formulaire (à gauche) ---
        self.formulaire = Formulaire()
        self.formulaire.modifie.connect(self._sur_modification)
        self.formulaire.demande_ia.connect(self.rediger_profil_ia)
        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setWidget(self.formulaire)
        defilement.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        defilement.setMinimumWidth(460)

        # --- Aperçu (à droite) ---
        self.apercu = QWebEngineView()
        self.apercu.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        reglages_web = self.apercu.settings()
        reglages_web.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        reglages_web.setAttribute(QWebEngineSettings.WebAttribute.PrintElementBackgrounds, True)
        self.apercu.loadFinished.connect(self._apercu_charge)
        self.apercu.page().pdfPrintingFinished.connect(self._pdf_termine)
        self.etat_page = etiquette("", "discret")
        cote_apercu = QWidget()
        d_apercu = QVBoxLayout(cote_apercu)
        d_apercu.setContentsMargins(0, 0, 0, 0)
        d_apercu.setSpacing(0)
        d_apercu.addWidget(self.apercu, 1)
        ligne_etat = QHBoxLayout()
        ligne_etat.setContentsMargins(14, 6, 14, 6)
        ligne_etat.addWidget(self.etat_page)
        d_apercu.addLayout(ligne_etat)

        separateur = QSplitter(Qt.Orientation.Horizontal)
        separateur.addWidget(defilement)
        separateur.addWidget(cote_apercu)
        separateur.setStretchFactor(0, 5)
        separateur.setStretchFactor(1, 6)
        separateur.setHandleWidth(1)
        separateur.setChildrenCollapsible(False)
        self.separateur = separateur

        # --- Bas : messages + bandeau de mise à jour ---
        self.message = etiquette("", "pied")
        self.lien_dossier = bouton("Ouvrir le dossier", "lien", icone="dossier")
        self.lien_dossier.clicked.connect(self._ouvrir_dossier_pdf)
        self.lien_dossier.hide()
        bas = QFrame()
        bas.setObjectName("bandeau")
        ligne_bas = QHBoxLayout(bas)
        ligne_bas.setContentsMargins(MARGE, 8, MARGE, 8)
        ligne_bas.addWidget(self.message, 1)
        ligne_bas.addWidget(self.lien_dossier)
        self.bandeau_maj = self._construire_bandeau_maj()

        # --- Assemblage ---
        centre = QWidget()
        disposition = QVBoxLayout(centre)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(0)
        disposition.addWidget(barre)
        disposition.addWidget(separateur, 1)
        disposition.addWidget(bas)
        disposition.addWidget(self.bandeau_maj)
        self.setCentralWidget(centre)

        # --- Minuteurs : on attend une courte pause dans la frappe ---
        self._minuteur_apercu = QTimer(self, singleShot=True, interval=250)
        self._minuteur_apercu.timeout.connect(self._rafraichir_apercu)
        self._minuteur_sauvegarde = QTimer(self, singleShot=True, interval=700)
        self._minuteur_sauvegarde.timeout.connect(self.enregistrer)
        self._minuteur_message = QTimer(self, singleShot=True, interval=8000)
        self._minuteur_message.timeout.connect(self._message_par_defaut)

        QShortcut(QKeySequence("Ctrl+P"), self, self.creer_pdf)
        QShortcut(QKeySequence("Ctrl+S"), self, lambda: self.enregistrer(True))
        QShortcut(QKeySequence("Ctrl+O"), self, self.ouvrir)
        QShortcut(QKeySequence("Ctrl+N"), self, self.nouveau)

        self._ouvrir_au_demarrage(fichier_demande)

        if not DEPOT_GITHUB.startswith("PROPRIETAIRE"):
            QTimer.singleShot(1500, self._verifier_mise_a_jour)

    # ------------------------------------------------------------------
    # Fichiers
    # ------------------------------------------------------------------

    def _ouvrir_au_demarrage(self, fichier_demande):
        candidats = [fichier_demande, self.reglages.value("dernier_fichier", "")]
        for candidat in candidats:
            if candidat and Path(candidat).is_file() and self._charger(Path(candidat), silencieux=True):
                return
        # Première utilisation : on part de l'exemple, rangé dans les Documents
        dossier = dossier_documents()
        fichier = dossier / "mon_cv.yaml"
        if not fichier.exists():
            try:
                dossier.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(moteur.FICHIER_EXEMPLE, fichier)
            except OSError as erreur:
                journal.error("Copie de l'exemple impossible : %s", erreur)
        if not self._charger(fichier):
            self.fichier = fichier
            self.formulaire.definir(moteur.normaliser({}), dossier)
            self._rafraichir_apercu()
        if self.fichier == fichier:
            self._afficher_message(
                f"Bienvenue ! Remplacez l'exemple par vos informations : tout est enregistré "
                f"automatiquement dans {self._chemin_court(fichier)}", duree=20000)

    def _charger(self, chemin: Path, silencieux=False) -> bool:
        try:
            cv = moteur.normaliser(moteur.lire_fichier(chemin))
        except ErreurCV as erreur:
            if not silencieux:
                QMessageBox.warning(self, NOM_APPLICATION, str(erreur))
            return False
        self._minuteur_sauvegarde.stop()
        self.fichier = chemin.resolve()
        self.reglages.setValue("dernier_fichier", str(self.fichier))
        self.modele = cv["modele"]
        self.boutons_modele[self.modele].setChecked(True)
        self.formulaire.definir(cv, self.fichier.parent)
        self.setWindowTitle(f"{self.fichier.name} — {NOM_APPLICATION}")
        self._rafraichir_apercu()
        self._message_par_defaut()
        return True

    def donnees(self) -> dict:
        return {"modele": self.modele, **self.formulaire.donnees()}

    def enregistrer(self, manuel=False):
        self._minuteur_sauvegarde.stop()
        if not self.fichier:
            return
        try:
            moteur.enregistrer_fichier(self.donnees(), self.fichier)
        except OSError as erreur:
            self._afficher_message(f"Impossible d'enregistrer : {erreur}")
            return
        if manuel:
            self._afficher_message(f"Enregistré dans {self._chemin_court(self.fichier)}")

    def _choisir_fichier(self, titre: str, nom_propose: str) -> Path | None:
        dossier = self.fichier.parent if self.fichier else dossier_documents()
        chemin, _ = QFileDialog.getSaveFileName(
            self, titre, str(dossier / nom_propose), "CV (*.yaml *.yml)")
        if not chemin:
            return None
        chemin = Path(chemin)
        return chemin if chemin.suffix.lower() in (".yaml", ".yml") else chemin.with_suffix(".yaml")

    def nouveau(self):
        self.enregistrer()
        chemin = self._choisir_fichier("Où enregistrer le nouveau CV ?", "nouveau_cv.yaml")
        if not chemin:
            return
        try:
            moteur.enregistrer_fichier({"modele": self.modele}, chemin)
        except OSError as erreur:
            QMessageBox.warning(self, NOM_APPLICATION, f"Impossible de créer le fichier : {erreur}")
            return
        self._charger(chemin)

    def ouvrir(self):
        self.enregistrer()
        dossier = self.fichier.parent if self.fichier else dossier_documents()
        chemin, _ = QFileDialog.getOpenFileName(self, "Ouvrir un CV", str(dossier), "CV (*.yaml *.yml)")
        if chemin:
            self._charger(Path(chemin))

    def enregistrer_sous(self):
        nom = self.fichier.stem + "_copie.yaml" if self.fichier else "mon_cv.yaml"
        chemin = self._choisir_fichier("Enregistrer une copie du CV", nom)
        if not chemin:
            return
        ancien_dossier = self.fichier.parent if self.fichier else chemin.parent
        donnees = self.donnees()
        # La photo est notée par rapport au dossier du CV : on garde un chemin valable
        if donnees.get("photo"):
            photo = moteur.chemin_photo(donnees["photo"], ancien_dossier)
            donnees["photo"] = str(photo) if photo else donnees["photo"]
        try:
            moteur.enregistrer_fichier(donnees, chemin)
        except OSError as erreur:
            QMessageBox.warning(self, NOM_APPLICATION, f"Impossible d'enregistrer : {erreur}")
            return
        self._charger(chemin)
        self._afficher_message(f"Copie enregistrée : {self._chemin_court(chemin)}")

    # ------------------------------------------------------------------
    # Modifications et aperçu
    # ------------------------------------------------------------------

    def _changer_modele(self, modele: str):
        if modele != self.modele:
            self.modele = modele
            self._sur_modification()

    def _sur_modification(self):
        self._minuteur_apercu.start()
        self._minuteur_sauvegarde.start()

    def _cv_actuel(self) -> dict:
        return moteur.normaliser(self.donnees())

    def _rafraichir_apercu(self):
        self._minuteur_apercu.stop()
        dossier = self.fichier.parent if self.fichier else dossier_documents()
        try:
            html = moteur.creer_html(self._cv_actuel(), dossier, apercu=True,
                                     fond_apercu=couleurs_actuelles()["apercu"])
        except Exception as erreur:  # modèle HTML abîmé : on le dit sans planter
            journal.exception("Création de l'aperçu")
            self.etat_page.setText(f"Aperçu impossible : {erreur}")
            return
        page = self.apercu.page()
        if self._page_prete and not self._chargement_en_cours:
            # La page est déjà affichée : on remplace seulement son contenu.
            # Pas de rechargement, donc pas de clignotement, et on reste au même endroit.
            debut, fin = html.find(">", html.find("<html")) + 1, html.rfind("</html>")
            script = f"document.documentElement.innerHTML = {json.dumps(html[debut:fin])}; {JS_HAUTEUR}"
            page.runJavaScript(script, 0, self._hauteur_mesuree)
            return
        self._chargement_en_cours = True
        charger_html(page, html)

    def _apercu_charge(self, reussi: bool):
        self._chargement_en_cours = False
        if not reussi:
            return
        self._page_prete = True
        self._ajuster_zoom()
        self.apercu.page().runJavaScript(JS_HAUTEUR, 0, self._hauteur_mesuree)

    def _hauteur_mesuree(self, hauteur):
        self.hauteur_px = float(hauteur or 0)
        depasse = depassement_mm(self.hauteur_px)
        js = "document.documentElement.classList.toggle('depasse', %s)" % ("true" if depasse else "false")
        self.apercu.page().runJavaScript(js)
        if depasse:
            self.etat_page.setText(f"⚠ Le contenu dépasse d'environ {depasse} mm : le CV fera 2 pages")
        else:
            self.etat_page.setText("✓ Le CV tient sur une page A4")
        if self.pdf_demande:
            self._imprimer()

    def _ajuster_zoom(self):
        """L'aperçu montre toujours toute la largeur de la page."""
        largeur = max(self.apercu.width() - 18, 200)  # 18 : la barre de défilement
        self.apercu.setZoomFactor(max(0.25, min(1.6, largeur / (LARGEUR_PAGE_PX + 40))))

    def showEvent(self, evenement):
        super().showEvent(evenement)
        if not getattr(self, "_partage_fait", False):
            # Au premier affichage : formulaire et aperçu se partagent la largeur
            self._partage_fait = True
            largeur = self.separateur.width()
            self.separateur.setSizes([int(largeur * 0.46), largeur - int(largeur * 0.46)])

    def resizeEvent(self, evenement):
        super().resizeEvent(evenement)
        QTimer.singleShot(0, self._ajuster_zoom)

    # ------------------------------------------------------------------
    # Profil rédigé par l'IA
    # ------------------------------------------------------------------

    def rediger_profil_ia(self):
        from .dialogue_ia import DialogueIA

        dialogue = DialogueIA(self._cv_actuel(), self.formulaire.profil.toPlainText(), self)
        if dialogue.exec() and dialogue.texte_choisi:
            self.formulaire.profil.setPlainText(dialogue.texte_choisi)  # enregistré et affiché tout seul
            self._afficher_message("Profil rédigé par l'IA : relisez-le dans l'aperçu.")

    # ------------------------------------------------------------------
    # Création du PDF
    # ------------------------------------------------------------------

    def creer_pdf(self):
        cv = self._cv_actuel()
        try:
            moteur.verifier_pour_pdf(cv)
        except ErreurCV as erreur:
            QMessageBox.information(self, NOM_APPLICATION, str(erreur))
            return
        self.enregistrer()
        sortie = (self.fichier.parent if self.fichier else dossier_documents()) / "sortie"
        try:
            sortie.mkdir(parents=True, exist_ok=True)
        except OSError as erreur:
            QMessageBox.warning(self, NOM_APPLICATION, f"Impossible de créer le dossier « sortie » : {erreur}")
            return
        self.pdf_demande = sortie / moteur.nom_du_fichier(cv["identite"])
        self.b_pdf.setEnabled(False)
        self._afficher_message("Création du PDF…", duree=0)
        # L'aperçu doit d'abord être à jour : on imprime une fois qu'il est prêt
        if self._minuteur_apercu.isActive() or self._chargement_en_cours or not self._page_prete:
            self._rafraichir_apercu()
        else:
            self._imprimer()

    def _imprimer(self):
        chemin = self.pdf_demande
        if not chemin:
            return
        # On prépare le message à l'avance : la mesure de l'aperçu est la bonne
        self._depassement_pdf = depassement_mm(self.hauteur_px)
        self.apercu.page().printToPdf(str(chemin), mise_en_page_a4())

    def _pdf_termine(self, chemin: str, reussi: bool):
        self.pdf_demande = None
        self.b_pdf.setEnabled(True)
        chemin = Path(chemin)
        if not reussi:
            self._afficher_message("Le PDF n'a pas pu être créé.")
            QMessageBox.warning(
                self, NOM_APPLICATION,
                f"Impossible d'enregistrer « {chemin.name} ».\n\n"
                "Il est peut-être ouvert dans un lecteur PDF : fermez-le, puis réessayez.")
            return
        self.dernier_pdf = chemin
        self._afficher_message(f"PDF créé : {chemin.name}", duree=0)
        self.lien_dossier.show()
        try:
            os.startfile(chemin)  # ouvre le PDF avec le lecteur habituel
        except OSError:
            pass
        pages = moteur.compter_pages(chemin)
        if pages > 1:
            QMessageBox.warning(
                self, NOM_APPLICATION,
                f"Votre CV fait {pages} pages au lieu d'une.\n\n"
                f"Le contenu dépasse d'environ {self._depassement_pdf} mm (sur 297 mm). "
                "Aucun texte n'a été coupé : la suite est sur la page 2.\n\n"
                "Pour tenir sur une page, vous pouvez :\n"
                "  •  raccourcir le profil ou retirer quelques missions ;\n"
                "  •  garder seulement les expériences les plus utiles ;\n"
                "  •  essayer l'autre modèle (classique / moderne).\n\n"
                "Dans l'aperçu, un trait pointillé montre où s'arrête la page 1.")

    def _ouvrir_dossier_pdf(self):
        chemin = getattr(self, "dernier_pdf", None)
        if chemin and chemin.exists():
            os.system(f'explorer /select,"{chemin}"')

    # ------------------------------------------------------------------
    # Messages en bas de la fenêtre
    # ------------------------------------------------------------------

    @staticmethod
    def _chemin_court(chemin: Path) -> str:
        try:
            return "~\\" + str(Path(chemin).resolve().relative_to(Path.home()))
        except ValueError:
            return str(chemin)

    def _afficher_message(self, texte: str, duree: int = 8000):
        self.message.setText(texte)
        self._minuteur_message.stop()
        if duree:
            self._minuteur_message.start(duree)

    def _message_par_defaut(self):
        self.lien_dossier.hide()
        if self.fichier:
            self.message.setText(f"Enregistrement automatique dans {self._chemin_court(self.fichier)}")

    # ------------------------------------------------------------------
    # Mise à jour (bandeau discret en bas de la fenêtre)
    # ------------------------------------------------------------------

    def _construire_bandeau_maj(self):
        bandeau = QFrame()
        bandeau.setObjectName("bandeau")
        ligne = QHBoxLayout(bandeau)
        ligne.setContentsMargins(MARGE, 10, MARGE, 10)
        ligne.setSpacing(14)
        self.texte_maj = etiquette("")
        self.bouton_maj = bouton("Mettre à jour", "primaire", icone="maj")
        self.bouton_maj.clicked.connect(self._installer_mise_a_jour)
        self.bouton_plus_tard = bouton("Plus tard", "lien")
        self.bouton_plus_tard.clicked.connect(lambda: self.bandeau_maj.hide())
        ligne.addWidget(self.texte_maj, 1)
        ligne.addWidget(self.bouton_plus_tard)
        ligne.addWidget(self.bouton_maj)
        bandeau.hide()

        self.infos_maj = None
        self.relais_maj = RelaisMiseAJour(self)
        self.relais_maj.trouvee.connect(self._mise_a_jour_trouvee)
        self.relais_maj.progression.connect(
            lambda p, t: self.texte_maj.setText(f"{t} {p} %" if p >= 0 else t))
        self.relais_maj.prete.connect(self._mise_a_jour_prete)
        self.relais_maj.echec.connect(self._mise_a_jour_echouee)
        return bandeau

    def _verifier_mise_a_jour(self):
        """Interroge GitHub en arrière-plan (la fenêtre reste utilisable)."""
        def travail():
            infos = mise_a_jour.verifier()
            if infos:
                self.relais_maj.trouvee.emit(infos)
        threading.Thread(target=travail, daemon=True).start()

    def _mise_a_jour_trouvee(self, infos: dict):
        self.infos_maj = infos
        notes = f" — {infos['notes'].splitlines()[0]}" if infos.get("notes") else ""
        self.texte_maj.setText(f"Nouvelle version disponible : v{infos['version']}{notes}")
        self.bouton_maj.setText("Mettre à jour")
        self.bouton_maj.setEnabled(True)
        self.bouton_plus_tard.show()
        self.bandeau_maj.show()

    def _installer_mise_a_jour(self):
        infos = self.infos_maj
        if not infos:
            return
        # Depuis le code Python (ou sans .zip joint) : on ouvre simplement la page GitHub
        if not mise_a_jour.est_installee() or not infos.get("zip"):
            QDesktopServices.openUrl(QUrl(mise_a_jour.PAGE_VERSIONS))
            return
        self.enregistrer()
        self.bouton_maj.setEnabled(False)
        self.bouton_plus_tard.hide()
        self.texte_maj.setText("Téléchargement…")

        def travail():
            try:
                preparation = mise_a_jour.telecharger_et_preparer(
                    infos["zip"], self.relais_maj.progression.emit, lambda: False)
            except mise_a_jour.ErreurConversion as erreur:
                self.relais_maj.echec.emit(str(erreur))
            except Exception as erreur:
                self.relais_maj.echec.emit(f"La mise à jour a échoué : {erreur}")
            else:
                self.relais_maj.prete.emit(preparation)
        threading.Thread(target=travail, daemon=True).start()

    def _mise_a_jour_prete(self, preparation: dict):
        """La nouvelle version est prête : on lance le remplacement et on ferme."""
        try:
            mise_a_jour.lancer_remplacement(preparation)
        except Exception as erreur:
            self._mise_a_jour_echouee(str(erreur))
            return
        self.texte_maj.setText("Redémarrage…")
        QTimer.singleShot(300, QApplication.instance().quit)

    def _mise_a_jour_echouee(self, message: str):
        QMessageBox.warning(self, NOM_APPLICATION, message)
        self.texte_maj.setText("La mise à jour n'a pas pu être installée.")
        self.bouton_maj.setText("Réessayer")
        self.bouton_maj.setEnabled(True)
        self.bouton_plus_tard.show()

    # ------------------------------------------------------------------

    def theme_change(self):
        """Le thème a changé (bouton ou réglage de Windows) : on redessine l'aperçu."""
        self._etiqueter_bouton_theme()
        self._rafraichir_apercu()

    def _etiqueter_bouton_theme(self):
        # Le bouton propose l'autre thème : « Clair » quand on est en sombre, et inversement
        if mode_sombre_actif():
            self.b_theme.setText("Clair")
            associer_icone(self.b_theme, "soleil", "texte", 15)
        else:
            self.b_theme.setText("Sombre")
            associer_icone(self.b_theme, "lune", "texte", 15)

    def _basculer_theme(self):
        nouveau = "clair" if mode_sombre_actif() else "sombre"
        definir_preference(nouveau)
        self.reglages.setValue("theme", nouveau)  # retenu pour les prochains démarrages
        appliquer_theme(QApplication.instance())
        self.theme_change()

    def closeEvent(self, evenement):
        self.enregistrer()
        evenement.accept()
