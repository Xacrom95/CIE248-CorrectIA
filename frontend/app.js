const API_URL = "http://127.0.0.1:8000/correction";

const boutonCorriger = document.getElementById("bouton-corriger");
const zoneChargement = document.getElementById("chargement");
const tempsEcoule = document.getElementById("temps-ecoule");
const zoneErreur = document.getElementById("erreur");
const zoneResultat = document.getElementById("resultat");
const contenuResultat = document.getElementById("contenu-resultat");

let intervalleTemps = null;
let debutCorrection = null;

boutonCorriger.addEventListener("click", corrigerCopie);

async function corrigerCopie() {
    const corrige = document.getElementById("corrige").value.trim();
    const copieEleve = document.getElementById("copie").value.trim();

    masquerErreur();
    masquerResultat();

    if (!corrige || !copieEleve) {
        afficherErreur("Veuillez remplir le corrigé et la copie de l'élève.");
        return;
    }

    activerChargement();

    try {
        const reponse = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                corrige: corrige,
                copie_eleve: copieEleve
            })
        });

        let donnees;

        try {
            donnees = await reponse.json();
        } catch {
            throw new Error("Le serveur n'a pas renvoyé une réponse JSON valide.");
        }

        if (!reponse.ok) {
            const detail = Array.isArray(donnees.detail)
                ? donnees.detail.map((item) => item.msg).join(" ; ")
                : donnees.detail;

            throw new Error(detail || `Erreur HTTP ${reponse.status}`);
        }

        afficherCorrection(donnees);
    } catch (erreur) {
        console.error(erreur);

        const message = erreur instanceof TypeError
            ? "Impossible de joindre FastAPI. Vérifiez que Uvicorn fonctionne et que CORS est configuré."
            : erreur.message;

        afficherErreur(`Erreur pendant la correction : ${message}`);
    } finally {
        desactiverChargement();
    }
}

function activerChargement() {
    boutonCorriger.disabled = true;
    boutonCorriger.textContent = "Correction en cours...";
    zoneChargement.classList.remove("cache");

    debutCorrection = Date.now();
    tempsEcoule.textContent = "Temps écoulé : 0 s";

    intervalleTemps = setInterval(() => {
        const secondes = Math.floor((Date.now() - debutCorrection) / 1000);
        tempsEcoule.textContent = `Temps écoulé : ${secondes} s`;
    }, 1000);
}

function desactiverChargement() {
    boutonCorriger.disabled = false;
    boutonCorriger.textContent = "Corriger la copie";
    zoneChargement.classList.add("cache");

    if (intervalleTemps !== null) {
        clearInterval(intervalleTemps);
        intervalleTemps = null;
    }
}

function afficherErreur(message) {
    zoneErreur.textContent = message;
    zoneErreur.classList.remove("cache");
}

function masquerErreur() {
    zoneErreur.textContent = "";
    zoneErreur.classList.add("cache");
}

function masquerResultat() {
    contenuResultat.innerHTML = "";
    zoneResultat.classList.add("cache");
}

function afficherCorrection(correction) {
    const questions = Array.isArray(correction.questions)
        ? correction.questions
        : [];

    const htmlQuestions = questions.map((question) => `
        <article class="question-resultat">
            <h3>
                Question ${echapperHtml(question.numero)} :
                ${echapperHtml(question.intitule)}
            </h3>

            <p>
                <strong>Note proposée :</strong>
                ${echapperHtml(question.note_proposee)} /
                ${echapperHtml(question.note_maximale)}
            </p>

            <h4>Éléments corrects</h4>
            ${creerListe(question.elements_corrects)}

            <h4>Éléments manquants ou incorrects</h4>
            ${creerListe(question.elements_manquants_ou_incorrects)}

            <p>
                <strong>Commentaire :</strong>
                ${echapperHtml(question.commentaire)}
            </p>

            ${question.verification_humaine_recommandee
                ? '<p class="avertissement">Vérification humaine recommandée pour cette question.</p>'
                : ''}
        </article>
    `).join("");

    const verificationGlobale = correction.verification_humaine_recommandee
        ? '<p class="avertissement">Une vérification humaine particulière est recommandée.</p>'
        : '';

    contenuResultat.innerHTML = `
        <p class="note-totale">
            Note totale proposée :
            ${echapperHtml(correction.note_totale_proposee)} /
            ${echapperHtml(correction.note_totale_maximale)}
        </p>

        ${htmlQuestions}

        <h3>Commentaire global</h3>
        <p>${echapperHtml(correction.commentaire_global)}</p>

        ${verificationGlobale}

        <p class="avertissement">
            Cette proposition doit toujours être validée par un enseignant.
        </p>
    `;

    zoneResultat.classList.remove("cache");
    zoneResultat.scrollIntoView({ behavior: "smooth", block: "start" });
}

function creerListe(elements) {
    if (!Array.isArray(elements) || elements.length === 0) {
        return "<p>Aucun élément signalé.</p>";
    }

    const liste = elements
        .map((element) => `<li>${echapperHtml(element)}</li>`)
        .join("");

    return `<ul>${liste}</ul>`;
}

function echapperHtml(texte) {
    const element = document.createElement("div");
    element.textContent = String(texte ?? "");
    return element.innerHTML;
}
