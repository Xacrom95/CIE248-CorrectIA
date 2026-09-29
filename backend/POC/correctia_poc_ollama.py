#!/usr/bin/env python3
"""CorrectIA POC: document extraction with Tesseract and local correction with Ollama."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pypdf import PdfReader

TEXT_EXTENSIONS = {".txt", ".md"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def extract_text(file_path: Path, ocr_language: str) -> str:
    """Extract text from a text file, text-based PDF, or image."""
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    extension = file_path.suffix.lower()

    if extension in TEXT_EXTENSIONS:
        return file_path.read_text(encoding="utf-8").strip()

    if extension == ".pdf":
        reader = PdfReader(str(file_path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if not text:
            raise ValueError(
                f"Le PDF {file_path.name} ne contient pas de couche texte. "
                "Pour ce POC, convertissez le PDF scanne en image PNG ou JPG."
            )
        return text

    if extension in IMAGE_EXTENSIONS:
        image = Image.open(file_path).convert("L")
        image = ImageEnhance.Contrast(image).enhance(2.0)
        image = image.filter(ImageFilter.SHARPEN)
        return pytesseract.image_to_string(image, lang=ocr_language).strip()

    raise ValueError(
        f"Format non pris en charge : {extension}. "
        "Formats acceptes : TXT, MD, PDF textuel, PNG, JPG, TIFF, BMP et WEBP."
    )


def build_prompt(question: str, reference: str, student_answer: str, maximum: float) -> str:
    """Build the correction instructions sent to the local model."""
    return f"""Tu assistes un enseignant dans la correction d'une evaluation.
La correction produite est une proposition et doit toujours etre validee par un enseignant.

Regles obligatoires :
- Compare uniquement la reponse de l'eleve avec le corrige fourni.
- N'exige aucune information absente du corrige de reference.
- Ne sanctionne pas une faute d'orthographe si elle ne change pas le sens.
- Attribue une note comprise entre 0 et {maximum}.
- Si la reponse, le corrige ou le bareme est ambigu, recommande une verification humaine.
- Retourne uniquement un objet JSON valide, sans texte avant ou apres.

QUESTION :
{question}

CORRIGE DE REFERENCE :
{reference}

REPONSE DE L'ELEVE :
{student_answer}

BAREME MAXIMAL : {maximum} points

Structure JSON obligatoire :
{{
  "note_proposee": 0,
  "note_maximale": {maximum},
  "elements_corrects": ["element correct"],
  "elements_manquants_ou_incorrects": ["element manquant ou incorrect"],
  "commentaire": "commentaire court et factuel",
  "verification_humaine_recommandee": true
}}"""


def call_ollama(base_url: str, model: str, prompt: str, timeout: int) -> dict:
    """Call Ollama's local generate endpoint and return the parsed correction JSON."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            ollama_response = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise ConnectionError(f"Erreur HTTP Ollama {error.code} : {details}") from error
    except urllib.error.URLError as error:
        raise ConnectionError(
            f"Impossible de contacter Ollama sur {base_url}. "
            "Verifiez que le service est lance. "
            f"Detail : {error}"
        ) from error

    raw_correction = ollama_response.get("response", "")
    if not raw_correction:
        raise ValueError("Ollama n'a retourne aucune correction.")

    try:
        return json.loads(raw_correction)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Le modele n'a pas retourne un objet JSON valide. "
            f"Reponse recue : {raw_correction}"
        ) from error


def validate_correction(correction: dict, maximum: float) -> None:
    """Perform basic technical checks on the model output."""
    required_fields = {
        "note_proposee",
        "note_maximale",
        "elements_corrects",
        "elements_manquants_ou_incorrects",
        "commentaire",
        "verification_humaine_recommandee",
    }

    missing_fields = required_fields - correction.keys()
    if missing_fields:
        raise ValueError(f"Champs manquants : {sorted(missing_fields)}")

    score = float(correction["note_proposee"])
    returned_maximum = float(correction["note_maximale"])

    if returned_maximum != maximum:
        raise ValueError(
            f"Bareme incoherent : le modele retourne {returned_maximum}, attendu {maximum}."
        )
    if not 0 <= score <= maximum:
        raise ValueError(f"Note invalide : {score}/{maximum}")
    if not isinstance(correction["elements_corrects"], list):
        raise ValueError("elements_corrects doit etre une liste.")
    if not isinstance(correction["elements_manquants_ou_incorrects"], list):
        raise ValueError("elements_manquants_ou_incorrects doit etre une liste.")
    if not isinstance(correction["verification_humaine_recommandee"], bool):
        raise ValueError("verification_humaine_recommandee doit etre un booleen.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="POC CorrectIA avec Tesseract, Ollama et Llama 3.1"
    )
    parser.add_argument("--question", required=True, help="Question posee a l'eleve")
    parser.add_argument("--corrige", required=True, type=Path, help="Corrige TXT, MD, PDF ou image")
    parser.add_argument("--copie", required=True, type=Path, help="Copie TXT, MD, PDF ou image")
    parser.add_argument("--bareme", required=True, type=float, help="Nombre maximal de points")
    parser.add_argument("--modele", default="llama3.1:8b", help="Nom exact affiche par ollama list")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="URL du serveur Ollama")
    parser.add_argument("--langue-ocr", default="fra", help="Code de langue Tesseract")
    parser.add_argument("--sortie", type=Path, default=Path("correction.json"), help="Fichier JSON de sortie")
    parser.add_argument("--timeout", type=int, default=300, help="Delai maximal de l'appel Ollama")
    parser.add_argument("--afficher-extraction", action="store_true", help="Verifier le texte avant correction")
    args = parser.parse_args()

    if args.bareme <= 0:
        parser.error("Le bareme doit etre superieur a zero.")

    try:
        reference = extract_text(args.corrige, args.langue_ocr)
        student_answer = extract_text(args.copie, args.langue_ocr)

        if not reference or not student_answer:
            raise ValueError("Le corrige ou la copie ne contient aucun texte exploitable.")

        if args.afficher_extraction:
            print("\n--- CORRIGE EXTRAIT ---\n")
            print(reference)
            print("\n--- COPIE EXTRAITE ---\n")
            print(student_answer)
            answer = input("\nContinuer l'envoi au modele local ? [o/N] : ").strip().lower()
            if answer not in {"o", "oui", "y", "yes"}:
                print("Envoi annule.")
                return 0

        prompt = build_prompt(args.question, reference, student_answer, args.bareme)
        correction = call_ollama(args.ollama_url, args.modele, prompt, args.timeout)
        validate_correction(correction, args.bareme)

        correction["validation_finale_requise"] = True
        correction["modele_utilise"] = args.modele
        correction["source_corrige"] = args.corrige.name
        correction["source_copie"] = args.copie.name

        args.sortie.write_text(
            json.dumps(correction, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("\n--- PROPOSITION DE CORRECTION ---\n")
        print(json.dumps(correction, ensure_ascii=False, indent=2))
        print(f"\nCorrection enregistree dans : {args.sortie}")
        print("ATTENTION : validation finale par un enseignant obligatoire.")
        return 0

    except Exception as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
