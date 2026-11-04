"""
Générateur de CV — version « sans fenêtre »
===========================================

Lit le fichier « mon_cv.yaml » et crée directement le PDF dans « sortie ».
(L'application avec fenêtre se lance avec lancer.py ou GenerateurCV.exe.)

Utilisation :
    .venv\\Scripts\\python.exe generer_cv.py                -> utilise mon_cv.yaml
    .venv\\Scripts\\python.exe generer_cv.py autre_cv.yaml  -> utilise un autre fichier

Le plus simple : double-cliquer sur « Generer_mon_CV.bat ».
"""

import os
import sys
from pathlib import Path

from cvapp import moteur
from cvapp.moteur import ErreurCV

DOSSIER = Path(__file__).resolve().parent


def main(arguments) -> int:
    chemin_cv = (Path(arguments[0]) if arguments else DOSSIER / "mon_cv.yaml").resolve()
    print(f"Lecture de {chemin_cv.name}…")
    brut = moteur.lire_fichier(chemin_cv)
    cv = moteur.normaliser(brut)
    moteur.verifier_pour_pdf(cv)
    if brut.get("modele") and str(brut["modele"]).strip().lower() not in moteur.MODELES:
        print(f"  ! Modèle « {brut['modele']} » inconnu (classique ou moderne) : j'utilise « classique ».")
    if cv.get("photo") and not moteur.chemin_photo(cv["photo"], chemin_cv.parent):
        print(f"  ! Photo introuvable ou format non pris en charge : {cv['photo']}\n"
              "    Le CV est créé sans photo.")

    html = moteur.creer_html(cv, chemin_cv.parent)
    sortie = DOSSIER / "sortie"
    sortie.mkdir(exist_ok=True)
    chemin_pdf = sortie / moteur.nom_du_fichier(cv["identite"])

    print(f"Création du PDF (modèle « {cv['modele']} »)…")
    from PySide6.QtWidgets import QApplication
    from cvapp.pdf import creer_pdf_sans_fenetre, depassement_mm

    _application = QApplication.instance() or QApplication(sys.argv[:1])
    try:
        hauteur = creer_pdf_sans_fenetre(html, chemin_pdf)
    except RuntimeError as erreur:
        raise ErreurCV(f"Le PDF n'a pas pu être créé ({erreur}).\n"
                       f"S'il est ouvert dans un lecteur PDF, fermez-le puis relancez.") from None

    pages = moteur.compter_pages(chemin_pdf)
    print(f"\nC'est prêt : {chemin_pdf}")
    if pages > 1:
        print(
            "\n" + "!" * 70 + "\n"
            f"  ATTENTION : votre CV fait {pages} pages au lieu d'une.\n"
            f"  Le contenu dépasse d'environ {depassement_mm(hauteur)} mm (sur 297 mm de hauteur).\n"
            "  Aucun texte n'a été coupé : la suite est sur la page 2.\n"
            "  Pour tenir sur une page : raccourcissez le profil, retirez quelques\n"
            "  missions, ou essayez l'autre modèle (classique / moderne).\n"
            + "!" * 70
        )
    if os.name == "nt" and not os.environ.get("CV_NE_PAS_OUVRIR"):
        os.startfile(chemin_pdf)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main(sys.argv[1:]))
    except ErreurCV as erreur:
        print(f"\nOups ! {erreur}")
        sys.exit(1)
