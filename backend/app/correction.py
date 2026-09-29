import json
import os
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


def construire_prompt(
    corrige: str,
    copie_eleve: str
) -> str:
    """
    Construit le prompt transmis à Llama 3.1.

    Le corrigé doit contenir :
    - les questions ;
    - les réponses attendues ;
    - les barèmes.
    """

    return f"""
Tu assistes un enseignant dans la correction d'une évaluation complète.

Le document CORRIGÉ contient :
- les questions de l'évaluation ;
- les réponses attendues ;
- le barème de chaque question.

Le document COPIE DE L'ÉLÈVE contient les réponses données par l'élève.

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
      "note_proposee": 0,
      "note_maximale": 0,
      "elements_corrects": [
        "Élément correct présent dans la réponse"
      ],
      "elements_manquants_ou_incorrects": [
        "Élément attendu absent ou réellement incorrect"
      ],
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
    Transmet le prompt à l'API locale d'Ollama
    et retourne la réponse JSON de Llama.
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
    Vérifie la structure et les notes d'une question.

    Retourne :
    - la note proposée ;
    - la note maximale.
    """

    champs_obligatoires = {
        "numero",
        "intitule",
        "note_proposee",
        "note_maximale",
        "elements_corrects",
        "elements_manquants_ou_incorrects",
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
            f"elements_manquants_ou_incorrects "
            f"de la question {index} doit être une liste."
        )

    if not isinstance(
        question["verification_humaine_recommandee"],
        bool
    ):
        raise ValueError(
            f"verification_humaine_recommandee "
            f"de la question {index} doit être un booléen."
        )

    return note_proposee, note_maximale


def valider_correction(
    correction: dict
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

    total_modele = convertir_en_nombre(
        correction["note_totale_proposee"],
        "note_totale_proposee"
    )

    maximum_modele = convertir_en_nombre(
        correction["note_totale_maximale"],
        "note_totale_maximale"
    )

    tolerance = 0.01

    if abs(total_modele - total_recalcule) > tolerance:
        raise ValueError(
            "Le total calculé par le modèle est incohérent : "
            f"{total_modele}, alors que la somme des questions "
            f"donne {total_recalcule}."
        )

    if abs(maximum_modele - maximum_recalcule) > tolerance:
        raise ValueError(
            "Le barème total calculé par le modèle est incohérent : "
            f"{maximum_modele}, alors que la somme des barèmes "
            f"donne {maximum_recalcule}."
        )

    if not isinstance(
        correction["verification_humaine_recommandee"],
        bool
    ):
        raise ValueError(
            "verification_humaine_recommandee "
            "doit être un booléen."
        )

    # Les totaux sont réécrits avec les valeurs recalculées
    # par le backend afin d'éviter une erreur d'addition du LLM.
    correction["note_totale_proposee"] = total_recalcule
    correction["note_totale_maximale"] = maximum_recalcule


def corriger_copie(
    corrige: str,
    copie_eleve: str
) -> dict:
    """
    Fonction principale utilisée par FastAPI.
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

    valider_correction(
        correction=correction
    )

    correction["validation_finale_requise"] = True
    correction["modele_utilise"] = OLLAMA_MODEL

    return correction
