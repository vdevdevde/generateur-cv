"""Dessine l'icône de l'application : un carré noir arrondi avec une page de CV blanche
(une pastille ronde pour la photo et quelques lignes de texte).

Produit ressources/icone.ico (pour Windows) et ressources/icone.png.
Lancement :  .venv\\Scripts\\python.exe outils\\creer_icone.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

DOSSIER = Path(__file__).resolve().parent.parent / "ressources"
TAILLE = 1024  # on dessine en grand, puis on réduit : les bords sont plus nets


def dessiner() -> Image.Image:
    s = TAILLE
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)

    # Fond : carré noir aux coins arrondis
    d.rounded_rectangle((0.04 * s, 0.04 * s, 0.96 * s, 0.96 * s), radius=0.2 * s, fill="black")

    # La page blanche
    g, h, dr, b = 0.27 * s, 0.17 * s, 0.73 * s, 0.83 * s
    d.rounded_rectangle((g, h, dr, b), radius=0.03 * s, fill="white")

    # Photo ronde + nom
    d.ellipse((0.33 * s, 0.24 * s, 0.45 * s, 0.36 * s), fill="#111111")
    d.rounded_rectangle((0.49 * s, 0.265 * s, 0.67 * s, 0.30 * s), radius=0.01 * s, fill="#111111")
    d.rounded_rectangle((0.49 * s, 0.315 * s, 0.61 * s, 0.335 * s), radius=0.01 * s, fill="#9A9A9A")

    # Lignes de texte grises
    y = 0.44 * s
    for longueur in (0.34, 0.30, 0.34, 0.22, None, 0.34, 0.28, 0.32):
        if longueur:
            d.rounded_rectangle((0.33 * s, y, (0.33 + longueur) * s, y + 0.022 * s),
                                radius=0.01 * s, fill="#A8A8A8")
        y += 0.045 * s
    return image


if __name__ == "__main__":
    DOSSIER.mkdir(exist_ok=True)
    icone = dessiner()
    icone.resize((256, 256), Image.Resampling.LANCZOS).save(DOSSIER / "icone.png")
    icone.save(DOSSIER / "icone.ico",
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Icône créée dans", DOSSIER)
