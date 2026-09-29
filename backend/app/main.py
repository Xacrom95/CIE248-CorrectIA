from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.correction import corriger_copie


app = FastAPI(
    title="CorrectIA API",
    description=(
        "API d'assistance à la correction d'évaluations. "
        "Toutes les corrections doivent être validées "
        "par un enseignant."
    ),
    version="0.2.0"
)


class CorrectionRequest(BaseModel):
    corrige: str = Field(
        min_length=1,
        description=(
            "Corrigé complet contenant les questions, "
            "les réponses attendues et les barèmes"
        )
    )

    copie_eleve: str = Field(
        min_length=1,
        description=(
            "Copie complète contenant les réponses de l'élève"
        )
    )


@app.get("/")
def accueil():
    return {
        "application": "CorrectIA",
        "status": "opérationnel",
        "version": "0.2.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/correction")
def correction(
    demande: CorrectionRequest
):
    try:
        return corriger_copie(
            corrige=demande.corrige,
            copie_eleve=demande.copie_eleve
        )

    except ConnectionError as erreur:
        raise HTTPException(
            status_code=503,
            detail=str(erreur)
        ) from erreur

    except ValueError as erreur:
        raise HTTPException(
            status_code=422,
            detail=str(erreur)
        ) from erreur

    except Exception as erreur:
        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur interne est survenue "
                f"pendant la correction : {erreur}"
            )
        ) from erreur
