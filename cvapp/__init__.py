"""Générateur de CV : une application de bureau pour créer un beau CV en PDF.

Organisation du dossier :
    moteur.py       -> lecture / écriture du fichier .yaml, création de la page HTML
    pdf.py          -> transformation de la page HTML en PDF (moteur Chromium de Qt)
    style.py        -> couleurs noir et blanc de l'application, mode clair / sombre
    formulaire.py   -> les champs à remplir (identité, expériences, compétences…)
    fenetre.py      -> la fenêtre principale : formulaire à gauche, aperçu à droite
    ia.py           -> rédaction du profil par l'IA (Claude, d'Anthropic)
    dialogue_ia.py  -> la fenêtre « écrire avec l'ia »
    mise_a_jour.py  -> recherche et installation des nouvelles versions (GitHub)
    application.py  -> démarrage de l'application
"""

NOM_APPLICATION = "Générateur de CV"
NOM_EXE = "GenerateurCV"  # nom du programme .exe et du dossier qui le contient

# Numéro de version : à augmenter avant chaque publication (voir publier.bat)
VERSION = "1.2.0"

# Dépôt GitHub où sont publiées les nouvelles versions (« propriétaire/nom »)
DEPOT_GITHUB = "vdevdevde/generateur-cv"
