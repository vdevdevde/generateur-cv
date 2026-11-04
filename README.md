# Générateur de CV

Application Windows pour créer un beau CV en PDF, en noir et blanc, sans rien
connaître à la mise en page. On remplit un formulaire à gauche et on voit le CV
se mettre à jour en direct à droite.

- **2 modèles** : *classique* (une colonne) ou *moderne* (colonne grise à gauche).
- **Format A4 sur une page** : l'aperçu prévient si le contenu dépasse, avec un
  trait pointillé « fin de la page 1 ». Rien n'est jamais coupé.
- **Enregistrement automatique** dans `Documents\Générateur de CV\mon_cv.yaml`.
- **Le PDF** est créé dans `Documents\Générateur de CV\sortie\CV_Prenom_Nom.pdf`,
  puis s'ouvre tout seul.
- **Mises à jour automatiques** : quand une nouvelle version est publiée, un
  bandeau propose de l'installer en un clic.

## Installer

1. Sur la page GitHub du projet → **Releases** → téléchargez `GenerateurCV-x.y.z.zip`.
2. Faites un clic droit sur le fichier → *Extraire tout…*
3. Lancez `GenerateurCV\GenerateurCV.exe`.

Pour l'avoir sur le Bureau : clic droit sur `GenerateurCV.exe` → *Afficher d'autres
options* → *Envoyer vers* → *Bureau (créer un raccourci)*.

⚠️ Gardez le `.exe` dans son dossier `GenerateurCV` : il a besoin du dossier
`_internal` qui l'accompagne. Pour le déplacer, déplacez tout le dossier.

> Windows peut afficher « Windows a protégé votre ordinateur » au premier
> lancement, car l'application n'est pas signée. Cliquez sur *Informations
> complémentaires* → *Exécuter quand même*.

## Utiliser

| Bouton | Ce qu'il fait |
|---|---|
| **nouveau** | Commence un CV vide, enregistré dans un nouveau fichier |
| **ouvrir…** | Ouvre un autre CV (fichier `.yaml`) |
| **enregistrer sous…** | Fait une copie du CV (ex. : une version par candidature) |
| **classique / moderne** | Change le modèle |
| **créer le pdf** | Crée le PDF et l'ouvre (raccourci : Ctrl + P) |

Les niveaux de compétence : un chiffre de **1 à 5** s'affiche avec des points
(●●●○○), un mot (« Notions », « Avancé »…) s'affiche tel quel.

La police utilisée est **Segoe UI**, la police moderne de Windows. Pour utiliser
**Inter** à la place, installez-la depuis <https://rsms.me/inter/> : elle sera
choisie automatiquement.

---

## Pour les développeurs

### Organisation du code

| Fichier | Rôle |
|---|---|
| `cvapp\moteur.py` | Lecture / écriture du `.yaml`, nettoyage, page HTML |
| `cvapp\pdf.py` | Conversion HTML → PDF (moteur Chromium de Qt) |
| `cvapp\formulaire.py` | Les champs du formulaire |
| `cvapp\fenetre.py` | La fenêtre : barre d'outils, formulaire, aperçu |
| `cvapp\style.py` | Les couleurs de l'application (clair / sombre) |
| `cvapp\mise_a_jour.py` | Recherche et installation des nouvelles versions |
| `modeles\` | Les modèles du CV en HTML + CSS (`commun.css` : couleurs, tailles) |
| `mon_cv.yaml` | L'exemple chargé au premier lancement |

### Lancer depuis le code

```
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe lancer.py
```

Il existe aussi une version **sans fenêtre** : remplissez `mon_cv.yaml` dans le
Bloc-notes, puis double-cliquez sur `Generer_mon_CV.bat` (le PDF arrive dans `sortie\`).

### Fabriquer le `.exe`

Double-cliquez sur `construire.bat` → `dist\GenerateurCV\GenerateurCV.exe`.

### Publier une nouvelle version

1. Faites vos modifications et vérifiez-les avec `.venv\Scripts\python.exe lancer.py`.
2. Dans `cvapp\__init__.py`, augmentez `VERSION` (ex. `1.0.0` → `1.1.0`).
3. Enregistrez les modifications avec git :
   ```
   git add -A
   git commit -m "Ce que j'ai changé"
   ```
4. Double-cliquez sur `publier.bat`. Il fabrique le `.exe`, le compresse en `.zip`
   et crée la version sur GitHub (il faut l'outil `gh`, connecté avec `gh auth login`).

Au prochain démarrage, toutes les applications installées proposeront la mise à jour.

### Comment marche la mise à jour

Au démarrage, l'application demande à GitHub la dernière *Release* du dépôt
(`DEPOT_GITHUB` dans `cvapp\__init__.py`). Si elle est plus récente, un bandeau
apparaît. **Mettre à jour** télécharge le `.zip`, le décompresse, puis un petit
script attend la fermeture de l'application, remplace les fichiers et la relance.
Les CV de l'utilisateur (dans *Documents*) ne sont jamais touchés.

En cas de souci, les erreurs sont notées dans `%LOCALAPPDATA%\GenerateurCV\journal.txt`.
