"""Démarrage de l'application : thème, gestion des erreurs, fenêtre."""

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QLocale, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import NOM_APPLICATION, NOM_EXE
from .moteur import DOSSIER_BASE
from .style import appliquer_theme, definir_preference, police_texte


def _preparer_journal():
    """Note les erreurs dans un petit fichier : %LOCALAPPDATA%\\GenerateurCV\\journal.txt"""
    dossier = Path(os.environ.get("LOCALAPPDATA", Path.home())) / NOM_EXE
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=dossier / "journal.txt",
            level=logging.WARNING,
            format="%(asctime)s %(levelname)s %(name)s : %(message)s",
            encoding="utf-8",
        )
    except OSError:
        pass


def _erreur_inattendue(type_erreur, valeur, trace):
    """Filet de sécurité : toute erreur imprévue affiche un message au lieu de planter."""
    logging.error("Erreur inattendue :\n%s", "".join(traceback.format_exception(type_erreur, valeur, trace)))
    QMessageBox.warning(
        None, NOM_APPLICATION,
        "Une erreur inattendue est survenue, mais l'application continue de fonctionner.\n\n"
        f"Détail technique : {valeur}",
    )


def demarrer() -> int:
    _preparer_journal()

    if sys.platform == "win32":  # pour que Windows affiche notre icône dans la barre des tâches
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{NOM_EXE}.App")
        except Exception:
            pass

    application = QApplication(sys.argv)
    application.setApplicationName(NOM_APPLICATION)
    application.setStyle("Fusion")
    application.setFont(police_texte(9.5))
    QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France))
    icone = DOSSIER_BASE / "ressources" / "icone.ico"
    if icone.exists():
        application.setWindowIcon(QIcon(str(icone)))

    sys.excepthook = _erreur_inattendue

    from .fenetre import FenetrePrincipale

    # Un fichier .yaml donné au lancement (ex. : glissé sur l'icône du .exe)
    fichier = next((a for a in sys.argv[1:] if a.lower().endswith((".yaml", ".yml")) and os.path.isfile(a)), None)
    definir_preference(QSettings(NOM_EXE, NOM_EXE).value("theme", "auto"))  # clair / sombre choisi
    appliquer_theme(application)  # avant la fenêtre : les icônes prennent les bonnes couleurs
    fenetre = FenetrePrincipale(fichier)

    def suivre_windows(*_):
        appliquer_theme(application)
        fenetre.theme_change()

    application.styleHints().colorSchemeChanged.connect(suivre_windows)
    fenetre.show()
    return application.exec()
