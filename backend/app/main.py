from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.correction import corriger_copie


app = FastAPI(
    title="CorrectIA API",
    description=(
        "API permettant de proposer une correction "
        "à partir d'un corrigé de référence."
    ),
    version="0.1.0"
)


class CorrectionRequest(BaseModel):
    corrige: str = Field(
        min_length=1,
        description=("Corrigé complet contenant les questions,"
        "les réponses attendues et les barèmes"
        )
    )

    copie_eleve: str = Field(
        min_length=1,
        description="Contenu complet de la copie de l'élève"
    )

    bareme: float = Field(
        gt=0,
        description="Nombre maximal de points"
    )


@app.get("/")
def accueil():
    return {
        "application": "CorrectIA",
        "status": "opérationnel",
        "version": "0.1.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/correction")
def correction(demande: CorrectionRequest):
    try:
        resultat = corriger_copie(
            corrige=demande.corrige,
            copie_eleve=demande.copie_eleve
        )

        return resultat

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
            detail=f"Erreur interne pendant la correction : {erreur}"
        ) from erreur
