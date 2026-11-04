"""Allège l'application fabriquée : ne garde que les traductions françaises et anglaises.

Les traductions de Qt (près de 55 Mo, dans toutes les langues) ne servent qu'aux
boîtes de dialogue standard. Lancé automatiquement par construire.bat.
"""

from pathlib import Path

DOSSIER = Path(__file__).resolve().parent.parent / "dist" / "GenerateurCV" / "_internal" / "PySide6" / "translations"
GARDER = ("fr", "en")


def garder(fichier: Path) -> bool:
    nom = fichier.stem.lower()
    if fichier.parent.name == "qtwebengine_locales":  # ex. : fr.pak, en-US.pak
        return nom.split("-")[0] in GARDER
    return nom.rsplit("_", 1)[-1] in GARDER  # ex. : qtbase_fr.qm


if __name__ == "__main__":
    gagne = 0
    if DOSSIER.is_dir():
        for fichier in DOSSIER.rglob("*"):
            if fichier.is_file() and fichier.suffix in (".qm", ".pak") and not garder(fichier):
                gagne += fichier.stat().st_size
                fichier.unlink()
    print(f"Traductions inutiles retirées : {gagne / 1024 / 1024:.0f} Mo gagnés")
