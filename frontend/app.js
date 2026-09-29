const API_URL = "http://127.0.0.1:8000/correction";
const TAILLE_MAXIMALE = 2 * 1024 * 1024;

const champCorrige = document.getElementById("corrige");
const champCopie = document.getElementById("copie");
const nomCorrige = document.getElementById("nom-corrige");
const nomCopie = document.getElementById("nom-copie");
const boutonCorriger = document.getElementById("bouton-corriger");
const boutonAnnuler = document.getElementById("bouton-annuler");
const boutonTheme = document.getElementById("bouton-theme");
const boutonNouvelleCorrection = document.getElementById("bouton-nouvelle-correction");
const zoneChargement = document.getElementById("chargement");
const tempsEcoule = document.getElementById("temps-ecoule");
const zoneErreur = document.getElementById("erreur");
const zoneResultat = document.getElementById("resultat");
const contenuResultat = document.getElementById("contenu-resultat");

let intervalleTemps = null;
let debutCorrection = null;
let controleurCorrection = null;

function appliquerTheme(theme) {
    const nocturne = theme === "dark";
    document.documentElement.dataset.theme = nocturne ? "dark" : "light";
    boutonTheme.textContent = nocturne ? "Mode diurne" : "Mode nocturne";
    boutonTheme.setAttribute(
        "aria-label",
        nocturne ? "Activer le mode diurne" : "Activer le mode nocturne"
    );
    localStorage.setItem("correctia-theme", nocturne ? "dark" : "light");
}

appliquerTheme(localStorage.getItem("correctia-theme") || "light");
boutonTheme.addEventListener("click", () => {
    appliquerTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});

champCorrige.addEventListener("change", () => afficherNomFichier(champCorrige, nomCorrige));
champCopie.addEventListener("change", () => afficherNomFichier(champCopie, nomCopie));
boutonCorriger.addEventListener("click", corrigerCopie);
boutonAnnuler.addEventListener("click", annulerCorrection);
boutonNouvelleCorrection.addEventListener("click", reinitialiserInterface);

function annulerCorrection() {
    if (controleurCorrection) {
        controleurCorrection.abort();
    }
}

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

function extraireNomEleve(copie) {
    const nom = copie.match(/^\s*Nom\s*:\s*(.+)$/im)?.[1]?.trim() || "";
    const prenom = copie.match(/^\s*Prénom\s*:\s*(.+)$/im)?.[1]?.trim() || "";
    return [prenom, nom].filter(Boolean).join(" ") || "Élève non identifié";
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
        controleurCorrection = new AbortController();

        const [corrige, copieEleve] = await Promise.all([
            lireFichierTexte(fichierCorrige),
            lireFichierTexte(fichierCopie)
        ]);

        const reponse = await fetch(API_URL, {
            method: "POST",
            signal: controleurCorrection.signal,
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

        if (erreur.name === "AbortError") {
            afficherErreur("Correction annulée.");
            return;
        }

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
                        afficherCorrection(donnees, extraireNomEleve(copieEleve));
    controleurCorrection = null;

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
        <div class="question-originale">
            <h3>
                Question ${echapperHtml(question.numero)}
            </h3>

            <p class="intitule-question">
                ${echapperHtml(question.intitule)}
            </p>
        </div>

        <div class="reponse-originale">
            <h4>Réponse de l'élève</h4>

            <p>
                ${
                    question.reponse_eleve &&
                    question.reponse_eleve.trim()
                        ? echapperHtml(question.reponse_eleve)
                        : "<em>Aucune réponse fournie.</em>"
                }
            </p>
        </div>

        <div class="note-question">
            <label for="note-${echapperHtml(question.numero)}">
                Note attribuée
            </label>
            <input
                id="note-${echapperHtml(question.numero)}"
                class="note-manuelle"
                type="number"
                min="0"
                max="${echapperHtml(question.note_maximale)}"
                step="0.5"
                value="${echapperHtml(question.note_proposee)}"
                data-note-max="${echapperHtml(question.note_maximale)}"
            >
            <span>/ ${echapperHtml(question.note_maximale)}</span>
        </div>

        <div class="details-correction">
            <div class="bloc-correct">
                <label for="corrects-${echapperHtml(question.numero)}">
                    Éléments corrects
                </label>
                <textarea id="corrects-${echapperHtml(question.numero)}" class="champ-manuel" rows="3">${echapperHtml((question.elements_corrects || []).join("\n"))}</textarea>
            </div>

            <div class="bloc-manquant">
                <label for="manquants-${echapperHtml(question.numero)}">
                    Éléments à améliorer
                </label>
                <textarea id="manquants-${echapperHtml(question.numero)}" class="champ-manuel" rows="3">${echapperHtml((question.elements_manquants_ou_incorrects || []).join("\n"))}</textarea>
            </div>
        </div>

        <div class="commentaire-question">
            <label for="commentaire-${echapperHtml(question.numero)}">
                Commentaire enseignant
            </label>
            <textarea id="commentaire-${echapperHtml(question.numero)}" class="champ-manuel" rows="3">${echapperHtml(question.commentaire || "")}</textarea>
        </div>

        ${
            question.verification_humaine_recommandee
                ? `
                    <p class="avertissement">
                        Vérification humaine recommandée
                        pour cette question.
                    </p>
                `
                : ""
        }
    </article>
`).join("");

    const verificationGlobale = correction.verification_humaine_recommandee
        ? '<p class="avertissement">Une vérification humaine particulière est recommandée.</p>'
        : '';

    contenuResultat.innerHTML = `
        <div class="eleve-corrige">
            <span>Élève corrigé</span>
            <strong>${echapperHtml(nomEleve)}</strong>
        </div>

        <p class="note-totale">
            Note totale :
            <span id="note-totale-valeur">${echapperHtml(correction.note_totale_proposee)}</span> /
            <span>${echapperHtml(correction.note_totale_maximale)}</span>
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
    contenuResultat.querySelectorAll(".note-manuelle").forEach((champ) => {
        champ.addEventListener("input", mettreAJourNoteTotale);
        champ.addEventListener("change", limiterNote);
    });
    zoneResultat.scrollIntoView({ behavior: "smooth", block: "start" });
}

function limiterNote(event) {
    const champ = event.currentTarget;
    const maximum = Number(champ.dataset.noteMax);
    const valeur = Math.max(0, Math.min(maximum, Number(champ.value) || 0));
    champ.value = valeur;
    mettreAJourNoteTotale();
}

function mettreAJourNoteTotale() {
    const total = [...contenuResultat.querySelectorAll(".note-manuelle")]
        .reduce((somme, champ) => somme + (Number(champ.value) || 0), 0);
    const totalElement = document.getElementById("note-totale-valeur");
    if (totalElement) {
        totalElement.textContent = Number.isInteger(total) ? total : total.toFixed(1);
    }
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
