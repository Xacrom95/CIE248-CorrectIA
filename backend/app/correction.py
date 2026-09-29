import json
import urllib.error
import urllib.request


OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"

def construire_prompt_copie(
    corrige: str,
    copie_eleve: str
) -> str:

    return f"""
Tu assistes un enseignant dans la correction d'une évaluation complète.

Le corrigé contient :
- les questions ;
- les réponses attendues ;
- les barèmes.

La copie contient les réponses de l'élève.

Règles obligatoires :
- Identifie les questions présentes dans le corrigé.
- Associe chaque réponse de l'élève à la question correspondante.
- Compare uniquement les réponses avec le corrigé fourni.
- N'exige aucune information absente du corrigé.
- Respecte le barème associé à chaque question.
- Ne sanctionne pas l'orthographe si elle ne modifie pas le sens.
- Signale les questions absentes ou impossibles à associer.
- Ne dépasse jamais le total des points prévu.
- Recommande une vérification humaine en cas d'ambiguïté.
- Retourne uniquement un objet JSON valide.
- La note finale doit toujours être validée par un enseignant.

CORRIGÉ COMPLET :
{corrige}

COPIE DE L'ÉLÈVE :
{copie_eleve}

Structure JSON obligatoire :
{{
  "questions": [
    {{
      "numero": 1,
      "intitule": "Question identifiée",
      "note_proposee": 0,
      "note_maximale": 0,
      "elements_corrects": [],
      "elements_manquants_ou_incorrects": [],
      "commentaire": "Commentaire court"
    }}
  ],
  "note_totale_proposee": 0,
  "note_totale_maximale": 0,
  "commentaire_global": "Commentaire global",
  "verification_humaine_recommandee": true
}}
"""

def appeler_ollama(
    prompt: str,
    modele: str = OLLAMA_MODEL,
    ollama_url: str = OLLAMA_URL
) -> dict:
    """
    Envoie le prompt à l'API locale d'Ollama.
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


def valider_correction(
    correction: dict,
    bareme: float
) -> None:
    """
    Vérifie que le résultat produit par Llama respecte
    la structure attendue.
    """

    champs_obligatoires = {
        "note_proposee",
        "note_maximale",
        "elements_corrects",
        "elements_manquants_ou_incorrects",
        "commentaire",
        "verification_humaine_recommandee"
    }

    champs_manquants = (
        champs_obligatoires - correction.keys()
    )

    if champs_manquants:
        raise ValueError(
            f"Champs manquants dans la correction : "
            f"{sorted(champs_manquants)}"
        )

    try:
        note = float(correction["note_proposee"])
        note_maximale = float(
            correction["note_maximale"]
        )

    except (TypeError, ValueError) as erreur:
        raise ValueError(
            "La note proposée et la note maximale "
            "doivent être des nombres."
        ) from erreur

    if note_maximale != bareme:
        raise ValueError(
            f"Barème incohérent : Llama retourne "
            f"{note_maximale}, mais le barème attendu "
            f"est {bareme}."
        )

    if not 0 <= note <= bareme:
        raise ValueError(
            f"Note invalide : {note}/{bareme}"
        )

    if not isinstance(
        correction["elements_corrects"],
        list
    ):
        raise ValueError(
            "Le champ elements_corrects doit être une liste."
        )

    if not isinstance(
        correction["elements_manquants_ou_incorrects"],
        list
    ):
        raise ValueError(
            "Le champ elements_manquants_ou_incorrects "
            "doit être une liste."
        )

    if not isinstance(
        correction["verification_humaine_recommandee"],
        bool
    ):
        raise ValueError(
            "Le champ verification_humaine_recommandee "
            "doit être un booléen."
        )

def corriger_copie(
    corrige: str,
    copie_eleve: str
) -> dict:
    if not corrige.strip():
        raise ValueError(
            "Le corrigé ne peut pas être vide."
        )

    if not copie_eleve.strip():
        raise ValueError(
            "La copie de l'élève ne peut pas être vide."
        )

    prompt = construire_prompt_copie(
        corrige=corrige,
        copie_eleve=copie_eleve
    )

    correction = appeler_ollama(prompt)

    valider_correction_copie(correction)

    correction["validation_finale_requise"] = True
    correction["modele_utilise"] = OLLAMA_MODEL

    return correction
