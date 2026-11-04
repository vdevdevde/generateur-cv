"""Point d'entrée du Générateur de CV.

Pour lancer l'application depuis le code :  .venv\\Scripts\\python.exe lancer.py
"""

import sys

from cvapp.application import demarrer

if __name__ == "__main__":
    sys.exit(demarrer())
