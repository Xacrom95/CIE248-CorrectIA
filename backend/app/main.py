from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.correction import corriger_copie


app = FastAPI(
    title="CorrectIA API",
    description=(
        "API d'assistance à la correction d'évaluations. "
        "Toutes les corrections doivent être validées "
        "par un enseignant."
    ),
    version="0.3.0"
)


# Configuration CORS adaptée au prototype local.
#
# Le frontend fonctionne actuellement sur le port 8080
# et FastAPI sur le port 8000.
#
# Dans une version de production, il faudra remplacer "*"
# par l'adresse exacte du frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
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
        "version": "0.3.0"
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
