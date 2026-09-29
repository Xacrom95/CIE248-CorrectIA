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

Règles d'analyse des documents :

1. Commence par analyser séparément le corrigé et la copie de l'élève.

2. Dans le corrigé, chaque exercice contient obligatoirement :
   - une ligne commençant par "Question" ;
   - une section commençant par "Réponse attendue" ;
   - une ligne commençant par "Barème".

3. Seul le texte situé après "Question X :" correspond à l'intitulé
   de la question.

4. Le texte situé après "Réponse attendue :" correspond à la réponse
   de référence. Ce texte ne doit jamais être utilisé comme intitulé
   de question.

5. Le nombre indiqué après "Barème :" correspond à la note maximale
   de la question.

6. Dans la copie de l'élève, associe chaque bloc commençant par
   "Question X :" à la question portant le même numéro dans le corrigé.

7. Le champ "intitule" doit reprendre exactement l'intitulé situé après
   "Question X :" dans le corrigé.

8. Le champ "reponse_eleve" doit reprendre exactement le texte situé
   après "Question X :" dans la copie de l'élève.

9. Ne reformule pas la question ni la réponse de l'élève dans les champs
   "intitule" et "reponse_eleve".

10. Ne confonds jamais :
    - l'intitulé de la question ;
    - la réponse attendue ;
    - la réponse de l'élève ;
    - le barème.

11. Si une question ne peut pas être associée avec certitude, ne devine
    pas. Utilise une réponse vide et recommande une vérification humaine.


Règles de notation :

12. Décompose la réponse attendue en plusieurs éléments importants.

13. Vérifie séparément quels éléments sont présents dans la réponse
    de l'élève.

14. Accorde des points pour chaque élément correct réellement présent.

15. Une réponse partiellement correcte doit obtenir une partie des points.

16. Une réponse contenant l'idée principale doit recevoir des points,
    même si des précisions sont absentes.

17. La note maximale est réservée à une réponse complète ou presque
    complète.

18. Une réponse vide, totalement fausse ou hors sujet reçoit zéro point.

19. Une omission entraîne une perte partielle de points, mais ne doit
    pas être présentée comme une erreur.

20. Une information qui contredit le corrigé entraîne une perte plus
    importante de points.

21. Les synonymes et reformulations équivalentes sont acceptés.

22. Ne sanctionne pas les fautes d'orthographe si elles ne modifient
    pas le sens.

23. N'exige aucune information absente du corrigé.

24. Ne dépasse jamais le barème maximal de la question.

25. La note totale correspond à la somme des notes de chaque question.


Règles de cohérence de la sortie :

26. Chaque élément de "elements_corrects" doit être présent dans la
    réponse de l'élève.

27. Chaque élément de "elements_manquants_ou_incorrects" doit être :
    - un élément attendu mais absent ;
    - ou une information réellement fausse dans la réponse.

28. Un même élément ne peut pas apparaître à la fois dans
    "elements_corrects" et dans
    "elements_manquants_ou_incorrects".

29. Si une réponse est qualifiée d'incomplète, précise les informations
    absentes dans "elements_manquants_ou_incorrects".

30. Si aucune information n'est manquante ou incorrecte, ne qualifie pas
    la réponse d'incomplète.

31. Recommande une vérification humaine en cas d'ambiguïté réelle.

32. La correction reste une proposition devant être validée par un
    enseignant.

33. Retourne uniquement un objet JSON valide, sans texte supplémentaire.

34.  Un même concept ne doit pas apparaître à la fois dans
  elements_corrects et dans elements_manquants_ou_incorrects,
  même s'il est formulé différemment.

35.  Avant de signaler un élément manquant, vérifie si l'élève a déjà
  exprimé ce concept avec des synonymes ou une reformulation.

36. Si l'idée principale est correctement exprimée, ne la considère
  pas comme manquante. Signale uniquement les précisions réellement
  absentes.

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

Exemple de structure correcte :

CORRIGÉ :

Question 1 : Expliquez le rôle du DNS.

Réponse attendue :
Le DNS associe un nom de domaine à une adresse IP.

Barème : 5 points.


COPIE DE L'ÉLÈVE :

Question 1 :
Le DNS transforme les noms des sites en adresses IP.


Extraction attendue :

- numero : 1
- intitule : "Expliquez le rôle du DNS."
- reponse_eleve :
  "Le DNS transforme les noms des sites en adresses IP."
- note_maximale : 5

La phrase située dans "Réponse attendue" ne doit jamais devenir
l'intitulé de la question.

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
