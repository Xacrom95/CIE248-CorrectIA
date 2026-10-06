import json
import os
from pathlib import Path


FICHIER_STATISTIQUES = Path(
    os.environ.get(
        "CORRECTIA_STATISTIQUES_FILE",
        Path(__file__).resolve().parent.parent / "data" / "evaluations.json",
    )
)


def _charger_notes() -> list[dict]:
    if not FICHIER_STATISTIQUES.exists():
        return []

    with FICHIER_STATISTIQUES.open("r", encoding="utf-8") as fichier:
        notes = json.load(fichier)

    if not isinstance(notes, list) or not all(isinstance(note, dict) for note in notes):
        raise ValueError("Le fichier de statistiques doit contenir une liste de notes.")

    return notes


def enregistrer_note(note: dict) -> dict:
    notes = _charger_notes()
    nouvelle_note = dict(note)
    nouvelle_note["note_sur_six"] = round(
        (nouvelle_note["points"] / nouvelle_note["points_max"]) * 5 + 1,
        2,
    )

    cle = _cle_note(nouvelle_note)
    index_existant = next(
        (index for index, existante in enumerate(notes) if _cle_note(existante) == cle),
        None,
    )
    if index_existant is None:
        notes.append(nouvelle_note)
    else:
        notes[index_existant] = nouvelle_note

    FICHIER_STATISTIQUES.parent.mkdir(parents=True, exist_ok=True)
    fichier_temporaire = FICHIER_STATISTIQUES.with_suffix(".tmp")
    with fichier_temporaire.open("w", encoding="utf-8") as fichier:
        json.dump(notes, fichier, ensure_ascii=False, indent=2)
    fichier_temporaire.replace(FICHIER_STATISTIQUES)

    return nouvelle_note


def lire_statistiques() -> dict:
    classes = {}

    for note in _charger_notes():
        classe = classes.setdefault(note["classe"], {})
        cle_evaluation = (note["evaluation"], note["date"])
        evaluation = classe.setdefault(
            cle_evaluation,
            {"evaluation": note["evaluation"], "date": note["date"], "eleves": []},
        )
        evaluation["eleves"].append(note)

    resultat = []
    for nom_classe, evaluations in sorted(classes.items(), key=lambda entree: entree[0].casefold()):
        evaluations_triees = []
        for evaluation in evaluations.values():
            eleves = sorted(
                evaluation["eleves"],
                key=lambda eleve: (eleve["nom"].casefold(), eleve["prenom"].casefold()),
            )
            nombres = len(eleves)
            notes_sur_six = [eleve["note_sur_six"] for eleve in eleves]
            points = [eleve["points"] for eleve in eleves]
            evaluations_triees.append({
                **evaluation,
                "eleves": eleves,
                "questions": _statistiques_questions(eleves),
                "nombre_eleves": nombres,
                "moyenne_points": round(sum(points) / nombres, 2),
                "moyenne_sur_six": round(sum(notes_sur_six) / nombres, 2),
                "minimum_sur_six": min(notes_sur_six),
                "maximum_sur_six": max(notes_sur_six),
            })
        evaluations_triees.sort(
            key=lambda evaluation: (evaluation["date"], evaluation["evaluation"].casefold())
        )
        resultat.append({"classe": nom_classe, "evaluations": evaluations_triees})

    return {"classes": resultat}


def _statistiques_questions(eleves: list[dict]) -> list[dict]:
    questions = {}
    for eleve in eleves:
        for question in eleve.get("questions", []):
            numero = int(question["numero"])
            statistique = questions.setdefault(numero, {
                "numero": numero,
                "intitule": question["intitule"],
                "points_max": question["points_max"],
                "nombre_reponses": 0,
                "nombre_justes": 0,
            })
            statistique["nombre_reponses"] += 1
            if question["points"] >= question["points_max"]:
                statistique["nombre_justes"] += 1

    for statistique in questions.values():
        nombre = statistique["nombre_reponses"]
        statistique["pourcentage_justes"] = round(
            statistique["nombre_justes"] / nombre * 100,
            1,
        ) if nombre else 0

    return [questions[numero] for numero in sorted(questions)]


def _cle_note(note: dict) -> tuple[str, str, str, str, str]:
    return (
        str(note["classe"]).strip().casefold(),
        str(note["evaluation"]).strip().casefold(),
        str(note["date"]).strip().casefold(),
        str(note["nom"]).strip().casefold(),
        str(note["prenom"]).strip().casefold(),
    )