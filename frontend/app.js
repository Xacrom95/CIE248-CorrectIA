const API_URL = "http://127.0.0.1:8000/correction";
const TAILLE_MAXIMALE = 2 * 1024 * 1024;

const champCorrige = document.getElementById("corrige");
const champCopie = document.getElementById("copie");
const nomCorrige = document.getElementById("nom-corrige");
const nomCopie = document.getElementById("nom-copie");
const boutonCorriger = document.getElementById("bouton-corriger");
const boutonNouvelleCorrection = document.getElementById("bouton-nouvelle-correction");
const zoneChargement = document.getElementById("chargement");
const tempsEcoule = document.getElementById("temps-ecoule");
const zoneErreur = document.getElementById("erreur");
const zoneResultat = document.getElementById("resultat");
const contenuResultat = document.getElementById("contenu-resultat");

let intervalleTemps = null;
let debutCorrection = null;

champCorrige.addEventListener("change", () => afficherNomFichier(champCorrige, nomCorrige));
champCopie.addEventListener("change", () => afficherNomFichier(champCopie, nomCopie));
boutonCorriger.addEventListener("click", corrigerCopie);
boutonNouvelleCorrection.addEventListener("click", reinitialiserInterface);

function afficherNomFichier(champ, zoneNom) {
    const fichier = champ.files[0];
    zoneNom.textContent = fichier ? fichier.name : "Aucun fichier sélectionné";
}

function verifierFichier(fichier, libelle) {
    if (!fichier) {
        throw new Error(`Veuillez sélectionner ${libelle}.`);
    }

    if (!fichier.name.toLowerCase().endsWith(".txt")) {
        throw new Error(`${libelle} doit être au format .txt.`);
    }

    if (fichier.size === 0) {
        throw new Error(`${libelle} est vide.`);
    }

    if (fichier.size > TAILLE_MAXIMALE) {
        throw new Error(`${libelle} dépasse la taille maximale de 2 Mo.`);
    }
}

async function lireFichierTexte(fichier) {
    const contenu = await fichier.text();

    if (!contenu.trim()) {
        throw new Error(`Le fichier ${fichier.name} ne contient aucun texte exploitable.`);
    }

    return contenu;
}

async function corrigerCopie() {
    masquerErreur();
    masquerResultat();

    try {
        const fichierCorrige = champCorrige.files[0];
        const fichierCopie = champCopie.files[0];

        verifierFichier(fichierCorrige, "un corrigé");
        verifierFichier(fichierCopie, "une copie d’élève");

        activerChargement();

        const [corrige, copieEleve] = await Promise.all([
            lireFichierTexte(fichierCorrige),
            lireFichierTexte(fichierCopie)
        ]);

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
            throw new Error("Le serveur n’a pas renvoyé une réponse JSON valide.");
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

        afficherErreur(`Erreur : ${message}`);
    } finally {
        desactiverChargement();
    }
}

function activerChargement() {
    boutonCorriger.disabled = true;
    champCorrige.disabled = true;
    champCopie.disabled = true;
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
    champCorrige.disabled = false;
    champCopie.disabled = false;
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

function reinitialiserInterface() {
    champCorrige.value = "";
    champCopie.value = "";
    nomCorrige.textContent = "Aucun fichier sélectionné";
    nomCopie.textContent = "Aucun fichier sélectionné";
    masquerErreur();
    masquerResultat();
    window.scrollTo({ top: 0, behavior: "smooth" });
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

    return `<ul>${elements.map((element) => `<li>${echapperHtml(element)}</li>`).join("")}</ul>`;
}

function echapperHtml(texte) {
    const element = document.createElement("div");
    element.textContent = String(texte ?? "");
    return element.innerHTML;
}
