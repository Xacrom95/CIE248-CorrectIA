import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
import urllib.error
import urllib.request
import logging
import time


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.1:8b"
)

logger = logging.getLogger("correctia")

DEBUT_QUESTION = re.compile(r"^\s*(?:question\s+)?(\d+)[.):]\s+(.*)$", re.IGNORECASE)


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
    """Extrait les questions multilignes et les réponses du corrigé."""
    document = _reunir_baremes_multilignes(document)
    if not prefixe_reponse:
        return extraire_document_legacy(document)

    lignes = [ligne.strip() for ligne in document.splitlines()]
    blocs = []
    index = 0
    numero_suivant = 1
    marqueur_reponse = re.compile(
        r"\b(?:réponse\s+attendue|réponse)\s*[:：]?\s*",
        re.IGNORECASE,
    )

    while index < len(lignes):
        ligne = lignes[index]
        numero_match = DEBUT_QUESTION.match(ligne)
        intitule = numero_match.group(2) if numero_match else ligne
        if ("?" not in intitule and not numero_match) or ligne.lower().startswith(("nom", "prénom", "questions")):
            index += 1
            continue

        numero = int(numero_match.group(1)) if numero_match else numero_suivant
        intitule_lignes = [intitule]
        reponse_lignes = []
        reponse_trouvee = False
        index += 1

        while index < len(lignes):
            suivante = lignes[index]
            marqueur = marqueur_reponse.search(suivante)
            if marqueur:
                avant_marqueur = suivante[:marqueur.start()].strip()
                apres_marqueur = suivante[marqueur.end():].strip()
                if avant_marqueur:
                    intitule_lignes.append(avant_marqueur)
                if apres_marqueur:
                    reponse_lignes.append(apres_marqueur)
                index += 1
                reponse_trouvee = True
                break

            if DEBUT_QUESTION.match(suivante):
                break

            if "?" in suivante and any("?" in morceau for morceau in intitule_lignes):
                break

            intitule_lignes.append(suivante)
            index += 1

        if not reponse_trouvee:
            return extraire_document_legacy(document)

        while index < len(lignes):
            suivante = lignes[index]
            if DEBUT_QUESTION.match(suivante):
                break
            if "?" in suivante:
                break
            if suivante:
                reponse_lignes.append(suivante)
            index += 1

        intitule = " ".join(intitule_lignes).strip()
        points_match = re.search(r"\(\s*(\d+(?:[.,]\d+)?)\s+points?\s*\)", intitule, re.IGNORECASE)
        maximum = float(points_match.group(1).replace(",", ".")) if points_match else 1.0
        intitule = re.sub(r"\s*\(\s*\d+(?:[.,]\d+)?\s+points?\s*\)\s*$", "", intitule, flags=re.IGNORECASE).strip()

        blocs.append({
            "numero": numero,
            "intitule": intitule,
            "reponse": _retirer_bareme_reponse(" ".join(reponse_lignes))
            or "Aucune réponse fournie.",
            "note_maximale": maximum
        })
        numero_suivant = numero + 1

    return blocs


def extraire_document_legacy(document: str) -> list[dict]:
    """Fallback pour les copies non numérotées ou sans intitulés répétés."""
    document = _reunir_baremes_multilignes(document)
    lignes = [ligne.strip() for ligne in document.splitlines()]
    blocs = []
    index = 0
    numero_suivant = 1

    while index < len(lignes):
        ligne = lignes[index]
        numero_match = DEBUT_QUESTION.match(ligne)
        intitule = numero_match.group(2) if numero_match else ligne
        if "?" not in intitule or ligne.lower().startswith(("nom", "prénom", "questions")):
            index += 1
            continue

        numero = int(numero_match.group(1)) if numero_match else numero_suivant
        maximum = _extraire_bareme(ligne)
        index += 1
        reponse_lignes = []

        while index < len(lignes):
            suivante = lignes[index]
            if "?" in re.sub(r"^\d+[.)]\s+", "", suivante) and not suivante.lower().startswith("réponse"):
                break
            if suivante:
                reponse_lignes.append(suivante)
            index += 1

        intitule = _retirer_bareme(intitule)
        blocs.append({
            "numero": numero,
            "intitule": intitule,
            "reponse": " ".join(reponse_lignes).strip() or "Aucune réponse fournie.",
            "note_maximale": maximum
        })
        numero_suivant = numero + 1

    return blocs


def extraire_reponses_eleve(copie_eleve: str, corriges: list[dict]) -> dict[int, dict]:
    """Retire les intitulés répétés des blocs numérotés de la copie élève."""
    copie_eleve = _reunir_baremes_multilignes(copie_eleve)
    numeros_attendus = {question["numero"] for question in corriges}
    blocs_lignes = {}
    numero_courant = None

    for ligne in copie_eleve.splitlines():
        numero_match = DEBUT_QUESTION.match(ligne)
        if numero_match and int(numero_match.group(1)) in numeros_attendus:
            numero_courant = int(numero_match.group(1))
            blocs_lignes[numero_courant] = [numero_match.group(2).strip()]
        elif numero_courant is not None:
            blocs_lignes[numero_courant].append(ligne.strip())

    if not blocs_lignes:
        return {
            bloc["numero"]: bloc
            for bloc in extraire_document_legacy(copie_eleve)
        }

    reponses = {}
    for question in corriges:
        numero = question["numero"]
        lignes = blocs_lignes.get(numero)
        if lignes is None:
            continue

        contenu_reponse = _retirer_intitule_question(lignes, question["intitule"])
        reponses[numero] = {
            "numero": numero,
            "reponse": " ".join(ligne for ligne in contenu_reponse if ligne).strip()
            or "Aucune réponse fournie."
        }

    return reponses


def valider_correspondance_documents(corrige: str, copie_eleve: str) -> None:
    """Refuse de corriger lorsque les questions des deux documents divergent."""
    questions_corrige = extraire_document(corrige, "Réponse :")
    if not questions_corrige:
        raise ValueError(
            "Aucune question exploitable n'a été trouvée dans le corrigé. "
            "Vérifiez que chaque question est suivie de sa réponse attendue."
        )

    questions_copie = _extraire_intitules_copie(copie_eleve)
    if not questions_copie:
        raise ValueError(
            "Impossible de comparer la copie au corrigé : aucun intitulé de question "
            "n'a été trouvé dans la copie. Ajoutez les questions numérotées à la copie."
        )

    numeros_corrige = {question["numero"] for question in questions_corrige}
    numeros_copie = set(questions_copie)
    if numeros_corrige != numeros_copie:
        manquants = sorted(numeros_corrige - numeros_copie)
        supplementaires = sorted(numeros_copie - numeros_corrige)
        details = []
        if manquants:
            details.append(f"questions absentes de la copie : {', '.join(map(str, manquants))}")
        if supplementaires:
            details.append(f"questions absentes du corrigé : {', '.join(map(str, supplementaires))}")
        raise ValueError("Le corrigé et la copie ne contiennent pas les mêmes questions (" + "; ".join(details) + ").")

    divergences = []
    for question in questions_corrige:
        numero = question["numero"]
        jetons_corrige = _jetons_intitule(question["intitule"])
        jetons_copie = _jetons_intitule(questions_copie[numero])
        if not jetons_corrige or not jetons_copie:
            divergences.append(numero)
            continue

        fenetre_copie = jetons_copie[:len(jetons_corrige)]
        similarite = SequenceMatcher(None, jetons_corrige, fenetre_copie).ratio()
        seuil = max(0.75, 1 - 1.5 / len(jetons_corrige))
        if similarite < seuil:
            divergences.append(numero)

    if divergences:
        liste = ", ".join(map(str, divergences))
        raise ValueError(
            f"Le corrigé et la copie semblent porter sur des questions différentes "
            f"(question(s) {liste}). Vérifiez les deux documents avant de corriger."
        )


def _extraire_intitules_copie(copie_eleve: str) -> dict[int, str]:
    blocs = {}
    numero_courant = None
    for ligne in copie_eleve.splitlines():
        correspondance = DEBUT_QUESTION.match(ligne)
        if correspondance:
            numero_courant = int(correspondance.group(1))
            blocs.setdefault(numero_courant, []).append(correspondance.group(2).strip())
        elif numero_courant is not None:
            blocs[numero_courant].append(ligne.strip())

    if blocs:
        intitules = {}
        for numero, lignes in blocs.items():
            texte = " ".join(ligne for ligne in lignes if ligne)
            intitules[numero] = texte.split("?", 1)[0] + ("?" if "?" in texte else "")
        return intitules

    blocs_legacy = extraire_document_legacy(copie_eleve)
    return {bloc["numero"]: bloc["intitule"] for bloc in blocs_legacy}


def _jetons_intitule(intitule: str) -> list[str]:
    intitule = _retirer_bareme(intitule)
    intitule = re.sub(r"^\s*(?:question\s+)?\d+[.):]?\s*", "", intitule, flags=re.IGNORECASE)
    return [_normaliser_jeton(jeton) for jeton in re.findall(r"\w+", intitule, re.UNICODE)]


def _retirer_intitule_question(lignes: list[str], intitule: str) -> list[str]:
    jetons_question = [
        _normaliser_jeton(jeton)
        for jeton in re.findall(r"\w+", intitule, re.UNICODE)
    ]
    jetons_copie = []
    for index, ligne in enumerate(lignes):
        jetons_copie.extend(
            (index, correspondance.start(), correspondance.end(), _normaliser_jeton(correspondance.group()))
            for correspondance in re.finditer(r"\w+", ligne, re.UNICODE)
        )

    correspondance_complete = (
        len(jetons_copie) >= len(jetons_question)
        and [jeton[3] for jeton in jetons_copie[:len(jetons_question)]] == jetons_question
    )
    if correspondance_complete and jetons_question:
        index_ligne, _, fin_jeton = jetons_copie[len(jetons_question) - 1][:3]
        suffixe = re.sub(
            r"^\s*(?:[?!.»”’\"']\s*)*(?:\(\s*\d+(?:[.,]\d+)?\s+points?\s*\))?\s*",
            "",
            lignes[index_ligne][fin_jeton:],
            flags=re.IGNORECASE,
        )
        return _retirer_bareme_debut_reponse(
            ([suffixe] if suffixe else []) + lignes[index_ligne + 1:]
        )

    for index, ligne in enumerate(lignes):
        if "?" in ligne:
            suffixe = ligne.split("?", 1)[1].strip()
            return _retirer_bareme_debut_reponse(
                ([suffixe] if suffixe else []) + lignes[index + 1:]
            )

    separateur_vide = next((index for index, ligne in enumerate(lignes) if not ligne), None)
    if separateur_vide is not None:
        return _retirer_bareme_debut_reponse(lignes[separateur_vide + 1:])
    return _retirer_bareme_debut_reponse(lignes[1:])


def _retirer_bareme_debut_reponse(lignes: list[str]) -> list[str]:
    resultat = list(lignes)
    motif_bareme = re.compile(
        r"^\s*[\(\[]\s*\d+(?:[.,]\d+)?\s*(?:points?|pts?)\s*[\)\]]\s*",
        re.IGNORECASE,
    )

    for index, ligne in enumerate(resultat):
        if not ligne.strip():
            continue
        ligne_nettoyee = motif_bareme.sub("", ligne, count=1)
        if ligne_nettoyee != ligne:
            if ligne_nettoyee.strip():
                resultat[index] = ligne_nettoyee
            else:
                resultat.pop(index)
        break

    return resultat


def _normaliser_jeton(jeton: str) -> str:
    decomposes = unicodedata.normalize("NFKD", jeton.casefold())
    return "".join(caractere for caractere in decomposes if not unicodedata.combining(caractere))


def _reunir_baremes_multilignes(document: str) -> str:
    return re.sub(
        r"\(\s*(\d+(?:[.,]\d+)?)\s*\r?\n\s*(points?)\s*\)",
        r"(\1 \2)",
        document,
        flags=re.IGNORECASE,
    )


def _retirer_bareme_reponse(texte: str) -> str:
    reponse = re.split(r"\bbar[èe]me\b", texte, maxsplit=1, flags=re.IGNORECASE)[0]
    reponse = re.sub(r"^\s*réponse(?:\s+attendue)?\s*[:：]?\s*", "", reponse, flags=re.IGNORECASE)
    return reponse.strip()


def _extraire_bareme(texte: str) -> float:
    correspondance = re.search(r"\(\s*(\d+(?:[.,]\d+)?)\s+points?\s*\)", texte, re.IGNORECASE)
    return float(correspondance.group(1).replace(",", ".")) if correspondance else 1.0


def _retirer_bareme(texte: str) -> str:
    return re.sub(r"\s*\(\s*\d+(?:[.,]\d+)?\s+points?\s*\)\s*$", "", texte, flags=re.IGNORECASE).strip()


def normaliser_donnees_source(correction: dict, corrige: str, copie_eleve: str) -> None:
    """Remplace les textes générés par les textes exacts des documents sélectionnés."""
    corriges = extraire_document(corrige, "Réponse :")
    copies = extraire_reponses_eleve(copie_eleve, corriges)

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


def retirer_fragments_grammaticaux(correction: dict) -> None:
    """Retire les amorces grammaticales isolées des arguments manquants."""
    for question in correction["questions"]:
        elements = question.get("elements_manquants_ou_incorrects", [])
        question["elements_manquants_ou_incorrects"] = [
            element
            for element in elements
            if _normaliser_jeton(" ".join(re.findall(r"\w+", element, re.UNICODE))) != "c est"
        ]


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
- Ne signale pas comme élément manquant un simple mot introductif ou grammatical (par exemple « C'est ») lorsque l'idée attendue est déjà exprimée.
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

    # Conserve le modèle chargé en mémoire pendant 30 minutes.
    # Les corrections suivantes devraient démarrer plus rapidement.
    "keep_alive": "30m",

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

    debut_appel = time.monotonic()

    logger.info(
        "Envoi du prompt à Ollama : modèle=%s, taille=%d caractères",
        modele,
        len(prompt)
    )

    try:
        with urllib.request.urlopen(
            requete,
            timeout=600
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

    duree_appel = time.monotonic() - debut_appel

    logger.info(
        "Réponse Ollama reçue en %.2f secondes",
        duree_appel
    )

    logger.info(
        (
            "Mesures Ollama : total_duration=%s, "
            "load_duration=%s, prompt_eval_count=%s, "
            "eval_count=%s"
        ),
        resultat_ollama.get("total_duration"),
        resultat_ollama.get("load_duration"),
        resultat_ollama.get("prompt_eval_count"),
        resultat_ollama.get("eval_count")
    )
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

    valider_correspondance_documents(corrige, copie_eleve)

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

    retirer_fragments_grammaticaux(correction)
    appliquer_reponses_essentielles(correction)

    valider_correction(
        correction=correction,
        nombre_questions_attendu=len(extraire_document(corrige, "Réponse :")) or None
    )

    correction["validation_finale_requise"] = True
    correction["modele_utilise"] = OLLAMA_MODEL

    return correction
