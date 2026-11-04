"""Transformation de la page HTML du CV en PDF.

On utilise le moteur Chromium intégré à Qt (QtWebEngine) : le même que pour
l'aperçu dans l'application. Ce qu'on voit à l'écran est donc exactement ce
qu'on obtient dans le PDF, et rien n'est à installer en plus.
"""

import tempfile
from pathlib import Path

from PySide6.QtCore import QEventLoop, QMarginsF, QTimer, QUrl
from PySide6.QtGui import QPageLayout, QPageSize

from .moteur import HAUTEUR_A4_PX

# Dossier temporaire où l'on écrit les pages HTML avant de les afficher
# (une page chargée depuis un fichier peut afficher la photo, elle aussi sur le disque).
_DOSSIER_TEMPORAIRE = Path(tempfile.mkdtemp(prefix="generateur_cv_"))

# JavaScript : hauteur du contenu du CV, en pixels CSS
JS_HAUTEUR = "document.querySelector('main') ? document.querySelector('main').getBoundingClientRect().height : 0"


def mise_en_page_a4() -> QPageLayout:
    """Une page A4 en portrait, sans marge : les marges sont dans le modèle CSS."""
    return QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Portrait,
        QMarginsF(0, 0, 0, 0),
        QPageLayout.Unit.Millimeter,
    )


def charger_html(page, html: str, nom: str = "apercu.html"):
    """Affiche une page HTML dans un QWebEnginePage (via un fichier temporaire).

    setHtml() est limité à 2 Mo : avec un fichier, pas de limite.
    """
    fichier = _DOSSIER_TEMPORAIRE / nom
    fichier.write_text(html, encoding="utf-8")
    page.load(QUrl.fromLocalFile(str(fichier)))


def depassement_mm(hauteur_px: float) -> int:
    """De combien de millimètres le contenu dépasse la page A4 (0 si ça tient)."""
    return max(0, round((float(hauteur_px or 0) - HAUTEUR_A4_PX) / 96 * 25.4))


def creer_pdf_sans_fenetre(html: str, chemin_pdf: Path, delai_max_s: int = 60) -> float:
    """Version « ligne de commande » : charge la page, attend, imprime en PDF.

    Il faut qu'une QApplication existe déjà. Renvoie la hauteur du contenu (px).
    """
    from PySide6.QtWebEngineCore import QWebEnginePage

    page = QWebEnginePage()
    boucle = QEventLoop()
    resultat = {"ok": False, "hauteur": 0.0, "erreur": "délai dépassé"}

    def charge(reussi):
        if not reussi:
            resultat["erreur"] = "la page n'a pas pu être préparée"
            boucle.quit()
            return
        # Un court délai : le temps que la photo et la police soient affichées
        QTimer.singleShot(300, lambda: page.runJavaScript(JS_HAUTEUR, 0, mesure))

    def mesure(hauteur):
        resultat["hauteur"] = float(hauteur or 0)
        page.printToPdf(str(chemin_pdf), mise_en_page_a4())

    def imprime(_chemin, reussi):
        resultat["ok"] = reussi
        resultat["erreur"] = "" if reussi else "impossible d'écrire le fichier PDF"
        boucle.quit()

    page.loadFinished.connect(charge)
    page.pdfPrintingFinished.connect(imprime)
    QTimer.singleShot(delai_max_s * 1000, boucle.quit)
    charger_html(page, html, "ligne_de_commande.html")
    boucle.exec()
    page.deleteLater()
    if not resultat["ok"]:
        raise RuntimeError(resultat["erreur"])
    return resultat["hauteur"]
