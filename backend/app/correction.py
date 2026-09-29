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
    Construit le prompt envoyé à Llama 3.1.

    Le corrigé doit contenir :
    - les questions ;
    - les réponses attendues ;
    - le barème de chaque question.
    """

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

- Le champ intitule doit contenir la question exacte extraite
  du corrigé.

- Le champ reponse_eleve doit contenir la réponse exacte extraite
  de la copie.

- Ne reformule pas et ne corrige pas la réponse de l'élève dans
  le champ reponse_eleve.

- Si aucune réponse n'est présente pour une question, utilise une
  chaîne vide dans reponse_eleve et attribue zéro point.

- Compare uniquement les informations présentes dans la réponse
  de l'élève avec les éléments attendus dans le corrigé.

- N'exige aucune information qui ne figure pas explicitement
  dans le corrigé.

- Les synonymes, les reformulations et les explications
  équivalentes sont acceptés.

- Ne pénalise pas une réponse correcte uniquement parce qu'elle
  est formulée différemment du corrigé.

- Ne sanctionne pas les fautes d'orthographe ou de grammaire si
  elles ne changent pas le sens de la réponse.

- Évalue séparément chaque idée importante présente dans le
  corrigé.

- Chaque idée correcte présente dans la réponse de l'élève doit
  rapporter une partie des points.

- Chaque idée importante absente doit entraîner une réduction
  progressive de la note.

- Une réponse partiellement correcte doit obtenir une partie
  des points.

- Une réponse contenant l'idée principale attendue doit recevoir
  une partie importante des points, mais pas nécessairement la
  note maximale.

- La note maximale doit être réservée aux réponses complètes ou
  quasiment complètes.

- Une réponse correcte mais incomplète doit recevoir une note
  intermédiaire.

- Une simple omission ne doit pas être considérée comme une
  information incorrecte.

- Fais clairement la distinction entre :
  1. une information correcte ;
  2. une information absente ;
  3. une information incorrecte.

- Une information absente entraîne une perte partielle de points.

- Une information qui contredit le corrigé entraîne une perte
  plus importante de points.

- La note zéro doit uniquement être attribuée lorsque la réponse
  est vide, totalement fausse ou sans rapport avec la question.

- N'accorde pas tous les points lorsqu'une seule partie du
  corrigé est présente et que plusieurs éléments importants
  sont attendus.

- Respecte strictement le barème de chaque question.

- Ne dépasse jamais le nombre maximal de points prévu.

- Les éléments corrects doivent uniquement contenir les
  informations réellement présentes dans la réponse de l'élève.

- Les éléments manquants ou incorrects doivent uniquement contenir :
  1. les éléments attendus mais absents ;
  2. les informations réellement incorrectes dans la réponse.

- Si le commentaire indique qu'une réponse est incomplète,
  elements_manquants_ou_incorrects doit préciser ce qui manque.

- Si elements_manquants_ou_incorrects est vide, ne qualifie pas
  la réponse d'incomplète.

- Ne qualifie une réponse d'erronée que si elle contient une
  information qui contredit réellement le corrigé.

- Calcule la note totale en additionnant les notes de chaque
  question.

- Recommande une vérification humaine lorsqu'une question, une
  réponse, une association ou un barème est réellement ambigu.

- La correction produite est une proposition et doit toujours
  être validée par un enseignant.

- Retourne uniquement un objet JSON valide, sans texte avant
  ou après.

Exemple de notation :

Question :
Expliquez le rôle du DHCP.

Réponse attendue :
Le DHCP attribue automatiquement une adresse IP, un masque de
sous-réseau, une passerelle et des serveurs DNS.

Barème :
5 points.

Réponse de l'élève :
Le DHCP attribue automatiquement une adresse IP.

Cette réponse contient une idée correcte importante, mais plusieurs
éléments sont absents. Elle doit recevoir une note partielle et non
zéro point ou la note maximale.

CORRIGÉ COMPLET :

{corrige}

COPIE DE L'ÉLÈVE :

{copie_eleve}

Structure JSON obligatoire :

{{
  "questions": [
    {{
      "numero": 1,
      "intitule": "Intitulé exact de la question",
      "reponse_eleve": "Réponse exacte donnée par l'élève",
      "note_proposee": 0,
      "note_maximale": 0,
      "elements_corrects": [
        "Élément correct réellement présent dans la réponse"
      ],
      "elements_manquants_ou_incorrects": [
        "Élément attendu absent ou information réellement incorrecte"
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

    if not isinstance(
        question["intitule"],
        str
    ):
        raise ValueError(
            f"L'intitulé de la question {index} "
            "doit être une chaîne de caractères."
        )

    if not question["intitule"].strip():
        raise ValueError(
            f"L'intitulé de la question {index} "
            "ne peut pas être vide."
        )

    if not isinstance(
        question["reponse_eleve"],
        str
    ):
        raise ValueError(
            f"La réponse de l'élève pour la question {index} "
            "doit être une chaîne de caractères."
        )

    if not isinstance(
        question["commentaire"],
        str
    ):
        raise ValueError(
            f"Le commentaire de la question {index} "
            "doit être une chaîne de caractères."
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

    if not isinstance(
        correction["commentaire_global"],
        str
    ):
        raise ValueError(
            "commentaire_global doit être une chaîne "
            "de caractères."
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

    if abs(
        maximum_modele - maximum_recalcule
    ) > tolerance:
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

    valider_correction(
        correction=correction
    )

    correction["validation_finale_requise"] = True
    correction["modele_utilise"] = OLLAMA_MODEL

    return correction
