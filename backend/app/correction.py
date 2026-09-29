import json
import os
import re
import urllib.error
import urllib.request


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.1:8b"
)


def extraire_questions(corrige: str) -> list[tuple[int, str]]:
    """Extrait les questions numérotées présentes dans le corrigé."""
    questions = []
    numeros_vus = set()
    for ligne in corrige.splitlines():
        correspondance = re.match(r"^\s*(\d+)[.)]\s+(.+?)\s*$", ligne)
        if correspondance:
            numero = int(correspondance.group(1))
            if numero not in numeros_vus:
                numeros_vus.add(numero)
                questions.append((numero, correspondance.group(2)))
    return questions


def extraire_document(document: str, prefixe_reponse: str = "") -> list[dict]:
    """Extrait chaque question et la réponse qui la suit dans un document texte."""
    lignes = [ligne.strip() for ligne in document.splitlines()]
    blocs = []
    index = 0
    numero_suivant = 1

    while index < len(lignes):
        ligne = lignes[index]
        numero_match = re.match(r"^(\d+)[.)]\s+(.*)$", ligne)
        intitule = numero_match.group(2) if numero_match else ligne
        if "?" not in intitule or ligne.lower().startswith(("nom", "prénom", "questions")):
            index += 1
            continue

        numero = int(numero_match.group(1)) if numero_match else numero_suivant
        points_match = re.search(r"\(\s*(\d+(?:[.,]\d+)?)\s+points?\s*\)", ligne, re.IGNORECASE)
        maximum = float(points_match.group(1).replace(",", ".")) if points_match else 1.0
        intitule = re.sub(r"\s*\(\s*\d+(?:[.,]\d+)?\s+points?\s*\)\s*$", "", intitule, flags=re.IGNORECASE).strip()
        index += 1
        reponse_lignes = []

        while index < len(lignes):
            suivante = lignes[index]
            if "?" in re.sub(r"^\d+[.)]\s+", "", suivante) and not suivante.lower().startswith("réponse"):
                break
            if suivante:
                reponse_lignes.append(suivante)
            index += 1

        reponse = " ".join(reponse_lignes).strip()
        if prefixe_reponse and reponse.lower().startswith(prefixe_reponse.lower()):
            reponse = reponse[len(prefixe_reponse):].strip()

        blocs.append({
            "numero": numero,
            "intitule": intitule,
            "reponse": reponse or "Aucune réponse fournie.",
            "note_maximale": maximum
        })
        numero_suivant = numero + 1

    return blocs


def normaliser_donnees_source(correction: dict, corrige: str, copie_eleve: str) -> None:
    """Remplace les textes générés par les textes exacts des documents sélectionnés."""
    corriges = extraire_document(corrige, "Réponse :")
    copies = {bloc["numero"]: bloc for bloc in extraire_document(copie_eleve)}

    for index, question in enumerate(correction["questions"]):
        if index >= len(corriges):
            continue
        source = corriges[index]
        reponse_copie = copies.get(source["numero"])
        question["numero"] = source["numero"]
        question["intitule"] = source["intitule"]
        question["reponse_attendue"] = source["reponse"]
        question["reponse_eleve"] = reponse_copie["reponse"] if reponse_copie else "Aucune réponse fournie."
        question["note_maximale"] = source["note_maximale"]


def appliquer_reponses_essentielles(correction: dict) -> None:
    """Garantit les points d'une réponse essentielle objectivement présente."""
    for question in correction["questions"]:
        intitule = question["intitule"].lower()
        eleve = re.sub(r"[^\w\s]", "", question["reponse_eleve"].lower())
        eleve = re.sub(r"\s+", " ", eleve).strip()
        attendu = re.sub(r"[^\w\s]", "", question["reponse_attendue"].lower())
        attendu = re.sub(r"\s+", " ", attendu).strip()

        if "acronyme" in intitule and eleve and eleve in attendu:
            question["note_proposee"] = question["note_maximale"]
            question["elements_manquants_ou_incorrects"] = []
            question["commentaire"] = (
                "Le développement de l'acronyme est exact. "
                "La réponse fournit l'information essentielle demandée."
            )
            question["analyse_detaillee"] = (
                "La notion principale est maîtrisée : l'élève donne le "
                "développement correct de l'acronyme."
            )


def construire_prompt(
    corrige: str,
    copie_eleve: str
) -> str:
    """
    Construit le prompt envoyé à Llama 3.1.

    Le corrigé doit contenir :
    - les questions ;
    - les réponses attendues ;
    - le barème de chaque question.
    """

    nombre_questions = len(extraire_document(corrige, "Réponse :"))

    return f"""
Tu assistes un enseignant dans la correction d'une évaluation complète.

Le document CORRIGÉ contient :
- les questions de l'évaluation ;
- les réponses attendues ;
- le barème de chaque question.

Le document COPIE DE L'ÉLÈVE contient les réponses données
par l'élève.

Règles obligatoires :

- Identifie toutes les questions présentes dans le corrigé.
- Retrouve le barème associé à chaque question.
- Associe chaque réponse de l'élève à la question correspondante.
- Évalue les réponses comme un enseignant bienveillant et réaliste.
- Accorde des points dès qu'une partie de la réponse est correcte.
- Une réponse partiellement correcte doit obtenir une partie des points.
- Une réponse qui contient l'idée principale attendue doit recevoir une partie importante des points.Cependant, chaque élément important du corrigé qui est absent doit entraîner une réduction progressive de la note.
- Une réponse partielle ne doit généralement pas recevoir la note maximale.
- La note maximale doit être réservée aux réponses complètes ou quasiment complètes.
- Une réponse correcte mais incomplète doit recevoir une note intermédiaire.
- N'utilise la note zéro que si la réponse est vide, totalement fausse ou hors sujet.
- Ne sanctionne pas une simple omission aussi sévèrement qu'une erreur.
- Fais la différence entre :
  - une information absente ;
  - une information incorrecte.
- Une information absente justifie une perte partielle de points.
- Une information incorrecte justifie une perte plus importante de points.
- Les synonymes, reformulations et explications équivalentes sont acceptés.
- Ne pénalise pas une réponse correcte formulée différemment du corrigé.
- Ne sanctionne pas les fautes d'orthographe si elles ne changent pas le sens.
- N'exige aucune information qui ne figure pas explicitement dans le corrigé.
- Respecte le barème associé à chaque question.
- Ne dépasse jamais le nombre maximal de points prévu.
- Si un commentaire indique qu'une réponse est incomplète, le champ
  elements_manquants_ou_incorrects doit préciser les éléments manquants.
- Si une réponse contient l'idée principale attendue, elle doit apparaître dans elements_corrects.
- Calcule la note totale en additionnant les notes de chaque question.
- Recommande une vérification humaine uniquement lorsqu'une réponse, une question ou un barème est réellement ambigu.
- La correction produite est une proposition et doit toujours être validée par un enseignant.
- Retourne uniquement un objet JSON valide, sans texte avant ou après.
- Le champ intitule doit contenir la question exacte extraite du corrigé.
- Le champ reponse_eleve doit contenir la réponse exacte extraite de la copie.
- Ne reformule pas et ne corrige pas la réponse de l'élève dans le champ reponse_eleve.
- Si aucune réponse n'est présente, utilise une chaîne vide pour reponse_eleve.
- Les éléments corrects doivent uniquement contenir les informations réellement présentes dans la réponse de l'élève.
- Les éléments manquants doivent uniquement contenir les informations attendues dans le corrigé mais absentes de la réponse.
- Le nom et le prénom de l'élève ne doivent pas être pris en compte pour la correction des questions.

CORRIGÉ COMPLET :

{corrige}

COPIE DE L'ÉLÈVE :

{copie_eleve}

SStructure JSON obligatoire :

{{
  "questions": [
    {{
      "numero": 1,
      "intitule": "Intitulé exact de la question",
      "reponse_eleve": "Réponse exacte donnée par l'élève",
    "reponse_attendue": "Réponse exacte du corrigé",
      "note_proposee": 0,
      "note_maximale": 0,
      "elements_corrects": [
        "Élément correct réellement présent dans la réponse"
      ],
      "elements_manquants_ou_incorrects": [
        "Élément attendu absent ou information réellement incorrecte"
      ],
            "analyse_detaillee": "Explication précise du niveau de maîtrise",
      "commentaire": "Commentaire court et factuel",
      "verification_humaine_recommandee": false
    }}
  ],
  "note_totale_proposee": 0,
  "note_totale_maximale": 0,
  "commentaire_global": "Commentaire global court et factuel",
  "verification_humaine_recommandee": false
}}
"""


def appeler_ollama(
    prompt: str,
    modele: str = OLLAMA_MODEL,
    ollama_url: str = OLLAMA_URL
) -> dict:
    """
    Envoie le prompt à l'API locale d'Ollama
    et retourne le résultat produit par Llama.
    """

    donnees = {
        "model": modele,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0
        }
    }

    requete = urllib.request.Request(
        url=f"{ollama_url.rstrip('/')}/api/generate",
        data=json.dumps(donnees).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            requete,
            timeout=300
        ) as reponse:
            resultat_ollama = json.loads(
                reponse.read().decode("utf-8")
            )

    except urllib.error.HTTPError as erreur:
        details = erreur.read().decode(
            "utf-8",
            errors="replace"
        )

        raise ConnectionError(
            f"Erreur HTTP retournée par Ollama : "
            f"{erreur.code}. Détails : {details}"
        ) from erreur

    except urllib.error.URLError as erreur:
        raise ConnectionError(
            f"Impossible de contacter Ollama sur {ollama_url}. "
            "Vérifie que le service Ollama est lancé."
        ) from erreur

    reponse_modele = resultat_ollama.get("response")

    if not reponse_modele:
        raise ValueError(
            "Ollama n'a retourné aucune correction."
        )

    try:
        return json.loads(reponse_modele)

    except json.JSONDecodeError as erreur:
        raise ValueError(
            "Llama n'a pas retourné un objet JSON valide. "
            f"Réponse reçue : {reponse_modele}"
        ) from erreur


def convertir_en_nombre(
    valeur,
    nom_champ: str
) -> float:
    """
    Convertit une valeur retournée par Llama en nombre.
    """

    try:
        return float(valeur)

    except (TypeError, ValueError) as erreur:
        raise ValueError(
            f"Le champ {nom_champ} doit être un nombre."
        ) from erreur


def valider_question(
    question: dict,
    index: int
) -> tuple[float, float]:
    """
    Vérifie la structure et les valeurs d'une question.

    Retourne :
    - la note proposée ;
    - la note maximale.
    """

    champs_obligatoires = {
        "numero",
        "intitule",
        "reponse_eleve",
        "reponse_attendue",
        "note_proposee",
        "note_maximale",
        "elements_corrects",
        "elements_manquants_ou_incorrects",
        "analyse_detaillee",
        "commentaire",
        "verification_humaine_recommandee"
    }
    champs_manquants = (
        champs_obligatoires - question.keys()
    )

    if champs_manquants:
        raise ValueError(
            f"Champs manquants dans la question {index} : "
            f"{sorted(champs_manquants)}"
        )

    note_proposee = convertir_en_nombre(
        question["note_proposee"],
        f"note_proposee de la question {index}"
    )

    note_maximale = convertir_en_nombre(
        question["note_maximale"],
        f"note_maximale de la question {index}"
    )

    for champ in (
        "intitule",
        "reponse_eleve",
        "reponse_attendue",
        "analyse_detaillee"
    ):
        if not isinstance(question[champ], str):
            raise ValueError(
                f"{champ} de la question {index} doit être une chaîne."
            )

    if note_maximale <= 0:
        raise ValueError(
            f"Le barème de la question {index} "
            "doit être supérieur à zéro."
        )

    if not 0 <= note_proposee <= note_maximale:
        raise ValueError(
            f"Note invalide pour la question {index} : "
            f"{note_proposee}/{note_maximale}"
        )

    if not isinstance(
        question["elements_corrects"],
        list
    ):
        raise ValueError(
            f"elements_corrects de la question {index} "
            "doit être une liste."
        )

    if not isinstance(
        question["elements_manquants_ou_incorrects"],
        list
    ):
        raise ValueError(
            "elements_manquants_ou_incorrects "
            f"de la question {index} doit être une liste."
        )

    if not isinstance(
        question["verification_humaine_recommandee"],
        bool
    ):
        raise ValueError(
            "verification_humaine_recommandee "
            f"de la question {index} doit être un booléen."
        )

    return note_proposee, note_maximale


def valider_correction(
    correction: dict,
    nombre_questions_attendu: int | None = None
) -> None:
    """
    Vérifie la structure globale de la correction
    et recalcule les totaux.
    """

    champs_obligatoires = {
        "questions",
        "note_totale_proposee",
        "note_totale_maximale",
        "commentaire_global",
        "verification_humaine_recommandee"
    }

    champs_manquants = (
        champs_obligatoires - correction.keys()
    )

    if champs_manquants:
        raise ValueError(
            "Champs manquants dans la correction : "
            f"{sorted(champs_manquants)}"
        )

    questions = correction["questions"]

    if not isinstance(questions, list):
        raise ValueError(
            "Le champ questions doit être une liste."
        )

    if not questions:
        raise ValueError(
            "Aucune question n'a été identifiée "
            "dans le corrigé."
        )

    if nombre_questions_attendu and len(questions) != nombre_questions_attendu:
        raise ValueError(
            "Le modèle n'a pas traité toutes les questions : "
            f"{len(questions)} reçue(s), "
            f"{nombre_questions_attendu} attendue(s)."
        )

    total_recalcule = 0.0
    maximum_recalcule = 0.0

    for index, question in enumerate(
        questions,
        start=1
    ):
        if not isinstance(question, dict):
            raise ValueError(
                f"La question {index} doit être "
                "un objet JSON."
            )

        note, maximum = valider_question(
            question=question,
            index=index
        )

        total_recalcule += note
        maximum_recalcule += maximum

    if not isinstance(
        correction["verification_humaine_recommandee"],
        bool
    ):
        raise ValueError(
            "verification_humaine_recommandee "
            "doit être un booléen."
        )

    # Le backend recalcule les totaux pour ne pas dépendre
    # des capacités d'addition du LLM.
    correction["note_totale_proposee"] = total_recalcule
    correction["note_totale_maximale"] = maximum_recalcule


def corriger_copie(
    corrige: str,
    copie_eleve: str
) -> dict:
    """
    Fonction principale appelée par FastAPI.
    """

    if not corrige.strip():
        raise ValueError(
            "Le corrigé ne peut pas être vide."
        )

    if not copie_eleve.strip():
        raise ValueError(
            "La copie de l'élève ne peut pas être vide."
        )

    prompt = construire_prompt(
        corrige=corrige,
        copie_eleve=copie_eleve
    )

    correction = appeler_ollama(
        prompt=prompt
    )

    normaliser_donnees_source(
        correction=correction,
        corrige=corrige,
        copie_eleve=copie_eleve
    )

    appliquer_reponses_essentielles(correction)

    valider_correction(
        correction=correction,
        nombre_questions_attendu=len(extraire_document(corrige, "Réponse :")) or None
    )

    correction["validation_finale_requise"] = True
    correction["modele_utilise"] = OLLAMA_MODEL

    return correction
