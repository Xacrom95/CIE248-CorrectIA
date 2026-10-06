# CIE248-CorrectIA

Projet du CIE 248 (2026) : application locale d'assistance à la correction de travaux scolaires à partir d'un corrigé et d'une copie d'élève.

## Fonctionnement

CorrectIA utilise trois services locaux :

```text
Navigateur → Frontend :8080 → API FastAPI :8000 → Ollama :11434
```

- Le frontend permet de sélectionner le corrigé et la copie au format `.txt`, `.pdf` ou `.docx`.
- FastAPI extrait le texte des fichiers, vérifie la correspondance des questions, puis orchestre la correction.
- Ollama analyse les réponses avec le modèle local `llama3.1:8b`.
- Le backend récupère les textes exacts dans les documents et utilise le modèle pour attribuer les points et rédiger l'analyse.
- Après validation enseignant, les points par question alimentent les statistiques de classe.

La correction reste une proposition : sa validation finale par un enseignant est obligatoire.

## Prérequis

- Windows, macOS ou Linux
- Python 3.12 recommandé
- Ollama installé et démarré
- Le modèle Ollama `llama3.1:8b`
- Accès Internet nécessaire à l'installation et au téléchargement du modèle; l'application fonctionne ensuite localement.

Vérification :

```powershell
python --version
ollama --version
```

## Installation

Depuis la racine du dépôt :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\backend\requirements_ollama.txt
```

Si l'activation PowerShell est bloquée, vous pouvez utiliser directement `..\.venv\Scripts\python.exe` dans les commandes des étapes suivantes sans activer l'environnement.

Sur macOS/Linux, l'activation est `source .venv/bin/activate`; remplacez ensuite `..\.venv\Scripts\python.exe` par `python` dans les commandes.

Installez ensuite le modèle :

```powershell
ollama pull llama3.1:8b
```

Un modèle plus léger peut être utilisé pour les tests :

```powershell
ollama pull llama3.2:3b
$env:OLLAMA_MODEL = "llama3.2:3b"
```

## Démarrage avec Docker Compose

Cette méthode nécessite Docker avec Docker Compose ; elle n'exige pas
d'installation locale de Python ni d'Ollama.

Docker Compose lance le frontend, l'API FastAPI et Ollama. Au premier démarrage,
Compose télécharge également le modèle configuré (par défaut `llama3.1:8b`),
ce qui peut prendre du temps et plusieurs gigaoctets d'espace disque.

Depuis la racine du dépôt :

```bash
docker compose up --build
```

L'interface est disponible sur http://localhost:8080 et la documentation de
l'API sur http://localhost:8000/docs. Les ports sont publiés uniquement sur
l'interface locale de la machine. Le modèle Ollama reste stocké dans le volume
Docker `ollama-data` entre les redémarrages.

Pour arrêter les services, utilisez `Ctrl+C`, puis :

```bash
docker compose down
```

Pour choisir un autre modèle, définissez `OLLAMA_MODEL` avant le démarrage, par
exemple :

```bash
OLLAMA_MODEL=llama3.2:3b docker compose up --build
```

## Démarrage

### 1. Démarrer Ollama

Dans un terminal :

```powershell
ollama serve
```

### 2. Démarrer l'API FastAPI

Dans un deuxième terminal :

```powershell
cd .\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Vérification de l'API :

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

Réponse attendue :

```json
{"status":"ok"}
```

### 3. Démarrer le frontend

Dans un troisième terminal :

```powershell
cd .\frontend
..\.venv\Scripts\python.exe -m http.server 8080
```

Ouvrez ensuite :

http://127.0.0.1:8080

Cette méthode lance le frontend avec le serveur HTTP Python de développement. Les étapes suivantes décrivent aussi le lancement de l'application avec Docker Compose.

Contrôlez séparément `http://127.0.0.1:8000/health` pour l'API et `http://127.0.0.1:8080` pour l'interface.

### Démarrage avec Docker Compose

Depuis la racine du dépôt, construisez et démarrez les services :

```powershell
docker compose up --build -d
```

Ouvrez `http://127.0.0.1:8080`. L'API est disponible sur `http://127.0.0.1:8000`. Au premier démarrage, le téléchargement du modèle Ollama peut prendre du temps; suivez son avancement avec `docker compose logs -f ollama-model` et attendez sa fin avant de lancer une correction. Les statistiques restent disponibles pendant ce téléchargement. Le fichier `backend/data/evaluations.json` est partagé avec le conteneur API, de sorte que les résultats existants et les nouvelles corrections validées alimentent le même fichier.

Pour arrêter les services sans supprimer le modèle Ollama :

```powershell
docker compose down
```

N'ajoutez pas `-v` à cette commande, car cela supprimerait aussi le volume contenant les modèles Ollama.

## Utilisation

1. Sélectionnez le corrigé et la copie correspondante (`.txt`, `.pdf` ou `.docx`).
2. Cliquez sur **Corriger la copie** et attendez la réponse d'Ollama.
3. Vérifiez ou modifiez les champs d'identité, les notes, arguments et commentaires.
4. Cochez chaque question après vérification, puis cliquez sur **Valider la correction**.
5. Utilisez **Exporter en PDF**, puis choisissez **Enregistrer au format PDF** dans la boîte d'impression.
6. Ouvrez **Statistiques**, sélectionnez une classe puis une évaluation pour consulter les réussites par question et les points par élève.

Une modification après validation exige une nouvelle validation. Classe, nom, prénom et corrigé sont nécessaires à l'enregistrement; la date du jour est proposée si elle est absente. L'évaluation est identifiée par le nom du fichier corrigé sans son extension.

Le frontend affiche :

- la question extraite du corrigé ;
- la réponse exacte de l'élève ;
- la réponse exacte attendue ;
- la note obtenue et le barème ;
- une analyse détaillée du niveau de maîtrise ;
- les éléments à améliorer.

Le bouton circulaire du thème fait défiler les modes clair, sombre et système. Le PDF est imprimé en mode clair et son nom reprend le corrigé, le nom, le prénom, la classe et la date, séparés par des underscores.

Pendant l'analyse, le temps écoulé est affiché. Le bouton **Annuler la correction** permet d'interrompre l'attente côté navigateur. Le calcul déjà lancé par Ollama peut toutefois continuer côté serveur.

## Format des fichiers

Les fichiers `.txt`, `.pdf` et `.docx` contenant du texte sont acceptés (10 Mo maximum chacun). Les tableaux Word sont lus. Les anciens fichiers `.doc` ne sont pas supportés. Un PDF scanné sans texte sélectionnable nécessite un OCR, qui n'est pas inclus.

Le format recommandé est une question par bloc, suivie de sa réponse attendue :

```text
Questions & Réponses

Que signifie l’acronyme « CPU » ?
Réponse : CPU signifie « Central Processing Unit », c’est-à-dire processeur en français.

Quel est le rôle principal de la mémoire RAM ? (1 point)
Réponse attendue : La RAM stocke temporairement les données et les programmes.
```

Pour la copie de l'élève, les questions peuvent être numérotées :

```text
Nom : Martin
Prénom : Léa
Classe : E.EI-D1A
Date : 06/10/2026

1. Que signifie l’acronyme « CPU » ? (1 point)
Central Processing Unit.
```

Les intitulés des questions doivent figurer dans le corrigé et la copie, idéalement avec les mêmes numéros. Les retours à la ligne, la ponctuation et les barèmes peuvent différer. Avant d'appeler le modèle, le backend refuse une question manquante ou un intitulé manifestement différent (HTTP `422`) pour éviter de corriger deux évaluations différentes. Une copie sans intitulé de question ne peut donc pas être comparée automatiquement.

Dans le corrigé, utilisez `Réponse :` ou `Réponse attendue :` pour séparer l'intitulé de la réponse attendue. Le backend affiche les réponses extraites des fichiers plutôt que des reformulations du modèle.

## Statistiques des classes

Le bouton **Statistiques** permet de sélectionner une classe puis une évaluation. Un graphique indique, pour chaque question, le nombre de réponses ayant obtenu tous les points. Le tableau affiche les points de chaque élève par question (`0`, le maximum ou une valeur partielle), le total et la note sur 6. Une réponse compte comme « juste » dans le graphique uniquement si elle obtient tous les points; les points partiels restent visibles dans le tableau. La note sur 6 suit la formule fédérale `((points / points_max) * 5) + 1`.

La liste **Élèves inclus dans les statistiques** permet de décocher temporairement des élèves pour l'évaluation sélectionnée. Les élèves décochés ne figurent plus dans le tableau et ne sont plus pris en compte dans le graphique et les moyennes. Le bouton **Réinclure tous les élèves de cette évaluation** annule la sélection. Ce filtre n'altère pas les notes enregistrées et est réinitialisé au rechargement de la page.

Le bouton **Exporter les statistiques en PDF** imprime uniquement la classe et l'évaluation sélectionnées, avec le graphique et le tableau. Dans la boîte d'impression, choisissez **Enregistrer au format PDF**; le nom proposé reprend la classe, l'évaluation et la date.

Les scores individuels sont enregistrés dans `backend/data/evaluations.json` après validation de toutes les questions. Le fichier est créé lors du premier enregistrement. Une nouvelle validation du même élève pour la même classe, évaluation et date met à jour sa ligne. Pour changer l'emplacement sous PowerShell, définir la variable avant de démarrer FastAPI :

```powershell
$env:CORRECTIA_STATISTIQUES_FILE = "C:\CorrectIA\evaluations.json"
```

Ce fichier contient des données scolaires nominatives : ne le publiez pas dans un dépôt public. Les corrections antérieures au stockage par question doivent être validées de nouveau pour apparaître dans le graphique détaillé.

## API

Endpoints disponibles :

| Méthode | Endpoint | Fonction |
| --- | --- | --- |
| `GET` | `/` | Informations sur l'application |
| `GET` | `/health` | État de santé de l'API |
| `POST` | `/correction` | Génération d'une correction |
| `POST` | `/correction/fichiers` | Génération d'une correction à partir de fichiers `.txt`, `.pdf` ou `.docx` |
| `POST` | `/statistiques/notes` | Enregistrement d'une correction validée, avec les points par question |
| `GET` | `/statistiques` | Lecture des statistiques regroupées par classe et évaluation |

Documentation interactive :

http://127.0.0.1:8000/docs

Exemple d'appel :

```powershell
$corrige = @'
Quel est le rôle principal de la mémoire RAM ? (1 point)
Réponse attendue : La RAM stocke temporairement les données et les programmes.
'@

$copieEleve = @'
1. Quel est le rôle principal de la mémoire RAM ? (1 point)
Elle stocke temporairement les données.
'@

$body = @{
		corrige = $corrige
		copie_eleve = $copieEleve
} | ConvertTo-Json

Invoke-RestMethod `
		-Uri http://127.0.0.1:8000/correction `
		-Method Post `
		-ContentType "application/json; charset=utf-8" `
		-Body $body
```

Exemple d'envoi de fichiers à l'endpoint utilisé par le frontend (PowerShell avec `curl.exe`) :

```powershell
curl.exe -X POST `
	-F "corrige=@C:\chemin\corrige.pdf" `
	-F "copie_eleve=@C:\chemin\copie.docx" `
	http://127.0.0.1:8000/correction/fichiers
```

Lire les statistiques enregistrées :

```powershell
Invoke-RestMethod http://127.0.0.1:8000/statistiques | ConvertTo-Json -Depth 8
```

La route `POST /statistiques/notes` attend la classe, le nom, le prénom, l'évaluation, la date, le total et une liste `questions` contenant `numero`, `intitule`, `points` et `points_max`. L'interface effectue cet appel après la validation enseignant.

## Dépannage

### `ERR_CONNECTION_REFUSED` sur le port 8080

Le frontend n'est pas démarré. Relancez :

```powershell
cd .\frontend
..\.venv\Scripts\python.exe -m http.server 8080
```

### Erreur de connexion à FastAPI ou erreur CORS

Vérifiez que l'API tourne sur le port `8000` et que l'adresse utilisée est bien :

```text
http://127.0.0.1:8000
```

Le backend autorise les origines locales `127.0.0.1:8080` et `localhost:8080`.

Lancez Uvicorn depuis `backend/` pour que le module `app` soit importable. Après l'installation ou la mise à jour de dépendances, redémarrez le backend.

### `ModuleNotFoundError: No module named 'app'`

La commande est probablement lancée depuis la racine. Dans le terminal de l'API, faites `cd .\backend`, puis lancez `..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`.

### Format non pris en charge ou document vide

Vérifiez l'extension réelle : `.txt`, `.pdf` ou `.docx` (pas `.doc`), et une taille inférieure à 10 Mo. Le texte doit être sélectionnable dans le PDF; les PDF scannés nécessitent un OCR externe.

Après une mise à jour du frontend, faites un rechargement forcé dans Chrome avec `Ctrl+Shift+R` si l'ancienne version reste affichée.

### Corrigé et copie refusés

Le backend renvoie HTTP `422` si les numéros ou les intitulés des questions diffèrent. Vérifiez que les deux fichiers correspondent à la même évaluation et que la copie contient les questions numérotées.

### Statistiques vides

Un résultat n'est enregistré qu'après validation de toutes les questions. Les corrections déjà validées avant la mise en place des scores par question ne sont pas importées automatiquement.

### `model not found`

Installez le modèle demandé :

```powershell
ollama pull llama3.1:8b
```

Vous pouvez observer l'activité du modèle avec :

```powershell
ollama ps
```

### Analyse lente

`llama3.1:8b` produit des analyses détaillées et peut prendre plusieurs minutes. Pour un test plus rapide, utilisez `llama3.2:3b` si ce modèle est installé.

### La correction ne contient pas toutes les questions

Le backend vérifie le nombre de blocs question/réponse extraits du corrigé. Utilisez une question suivie de sa ligne `Réponse :`, et évitez de mélanger plusieurs questions dans un même bloc.

## Structure du dépôt

```text
backend/
	app/
		main.py              # API FastAPI
		correction.py        # Prompt, extraction et validation
		documents.py         # Lecture des fichiers TXT, PDF et DOCX
		statistiques.py      # Stockage JSON et agrégations par question
		Dockerfile           # Image de l'API
		POC/                   # Ancien prototype en ligne de commande
		requirements_ollama.txt
		data/evaluations.json  # Créé après la première validation
frontend/
		index.html             # Interface web
		app.js                 # Appels API et affichage
		style.css              # Styles et mode nocturne
		Dockerfile             # Image du frontend
		nginx.conf             # Désactivation du cache des ressources
database/
compose.yaml             # Services Docker Compose
```

## État du projet

Le parcours frontend, API FastAPI et Ollama fonctionne en mode local ou avec Docker Compose. Les données de statistiques sont conservées dans `backend/data/evaluations.json`, partagé avec le conteneur backend lorsque Docker Compose est utilisé. Une base de données serveur et l'authentification restent à finaliser.
