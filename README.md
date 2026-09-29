# CIE248-CorrectIA

Projet du CIE 248 (2026) : application locale d'assistance à la correction de travaux scolaires à partir d'un corrigé et d'une copie d'élève.

## Fonctionnement

CorrectIA utilise trois services locaux :

```text
Navigateur → Frontend :8080 → API FastAPI :8000 → Ollama :11434
```

- Le frontend permet de sélectionner le corrigé et la copie au format `.txt`.
- FastAPI reçoit le contenu des deux fichiers et orchestre la correction.
- Ollama analyse les réponses avec le modèle local `llama3.1:8b`.
- Le backend récupère les textes exacts dans les documents et utilise le modèle pour attribuer les points et rédiger l'analyse.

La correction reste une proposition : sa validation finale par un enseignant est obligatoire.

## Prérequis

- Windows, macOS ou Linux
- Python 3.12 recommandé
- Ollama installé et démarré
- Le modèle Ollama `llama3.1:8b`

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
python -m pip install fastapi uvicorn
```

Installez ensuite le modèle :

```powershell
ollama pull llama3.1:8b
```

Un modèle plus léger peut être utilisé pour les tests :

```powershell
ollama pull llama3.2:3b
$env:OLLAMA_MODEL = "llama3.2:3b"
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

Le frontend est servi par le serveur HTTP Python de développement. Il n'est pas encore servi par Apache ou Docker Compose.

## Utilisation

1. Sélectionnez un fichier `.txt` contenant le corrigé complet et ses barèmes.
2. Sélectionnez un fichier `.txt` contenant la copie de l'élève.
3. Cliquez sur **Corriger la copie**.
4. Consultez la note, les réponses comparées, l'analyse détaillée et les points à améliorer.

Le frontend affiche :

- la question extraite du corrigé ;
- la réponse exacte de l'élève ;
- la réponse exacte attendue ;
- la note obtenue et le barème ;
- une analyse détaillée du niveau de maîtrise ;
- les éléments à améliorer.

Pendant l'analyse, le temps écoulé est affiché. Le bouton **Annuler la correction** permet d'interrompre l'attente côté navigateur. Le calcul déjà lancé par Ollama peut toutefois continuer côté serveur.

## Format des fichiers

Le format recommandé est une question par bloc, suivie de sa réponse :

```text
Questions & Réponses

Que signifie l’acronyme « CPU » ?
Réponse : CPU signifie « Central Processing Unit », c’est-à-dire processeur en français.

Quel est le rôle principal de la mémoire RAM ? (1 point)
Réponse : La RAM stocke temporairement les données et les programmes.
```

Pour la copie de l'élève, les questions peuvent être numérotées :

```text
1. Que signifie l’acronyme « CPU » ? (1 point)
Central Processing Unit.
```

Le backend extrait les textes des documents afin d'éviter que le modèle n'invente les réponses affichées. Les formats PDF et image ne sont pas encore pris en charge par l'interface web actuelle.

## API

Endpoints disponibles :

| Méthode | Endpoint | Fonction |
| --- | --- | --- |
| `GET` | `/` | Informations sur l'application |
| `GET` | `/health` | État de santé de l'API |
| `POST` | `/correction` | Génération d'une correction |

Documentation interactive :

http://127.0.0.1:8000/docs

Exemple d'appel :

```powershell
$body = @{
		corrige = Get-Content .\backend\corrige3.txt -Raw
		copie_eleve = Get-Content .\backend\copie3.txt -Raw
} | ConvertTo-Json

Invoke-RestMethod `
		-Uri http://127.0.0.1:8000/correction `
		-Method Post `
		-ContentType "application/json; charset=utf-8" `
		-Body $body
```

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
	POC/                   # Ancien prototype en ligne de commande
	requirements_ollama.txt
	corrige3.txt           # Exemple de corrigé à 3 questions
	copie3.txt             # Exemple de copie à 3 questions
frontend/
	index.html             # Interface web
	app.js                 # Appels API et affichage
	style.css              # Styles et mode nocturne
database/
compose.yaml             # Préparation de l'orchestration Docker
```

## État du projet

Le parcours local frontend, API FastAPI et Ollama est fonctionnel. Docker Compose, la base de données, l'authentification et la prise en charge des PDF/images dans l'interface web restent à finaliser.
