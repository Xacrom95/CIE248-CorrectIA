const API_URL = "http://127.0.0.1:8000/correction/fichiers";
const API_STATISTIQUES_URL = "http://127.0.0.1:8000/statistiques";
const TAILLE_MAXIMALE = 10 * 1024 * 1024;

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
const boutonValiderCorrection = document.getElementById("bouton-valider-correction");
const statutValidation = document.getElementById("statut-validation");
const boutonPdf = document.getElementById("bouton-pdf");
const boutonReediter = document.getElementById("bouton-reediter");
const boutonCorrection = document.getElementById("bouton-correction");
const boutonStatistiques = document.getElementById("bouton-statistiques");
const boutonExporterStatistiques = document.getElementById("bouton-export-statistiques");
const sectionFormulaire = document.getElementById("section-formulaire");
const sectionStatistiques = document.getElementById("section-statistiques");
const filtresStatistiques = document.getElementById("filtres-statistiques");
const selecteurClasse = document.getElementById("selecteur-classe");
const selecteurEvaluation = document.getElementById("selecteur-evaluation");
const contenuStatistiques = document.getElementById("contenu-statistiques");
const erreurStatistiques = document.getElementById("erreur-statistiques");
const dialogSuppression = document.getElementById("dialog-confirmation-suppression");
const messageConfirmationSuppression = document.getElementById("message-confirmation-suppression");
const erreurSuppression = document.getElementById("erreur-suppression");
const boutonNonSuppression = document.getElementById("bouton-non-suppression");
const boutonOuiSuppression = document.getElementById("bouton-oui-suppression");

let intervalleTemps = null;
let debutCorrection = null;
let controleurCorrection = null;
let correctionCourante = null;
let correctionValidee = false;
let statistiquesDisponibles = [];
let resultatEnAttenteSuppression = null;
let evaluationStatistiquesCourante = null;
let classeStatistiquesCourante = "";
const preferenceThemeSysteme = window.matchMedia("(prefers-color-scheme: dark)");

function appliquerTheme(theme) {
    const themeChoisi = ["light", "dark", "system"].includes(theme)
        ? theme
        : "system";
    const nocturne = themeChoisi === "dark" || (
        themeChoisi === "system" && preferenceThemeSysteme.matches
    );
    document.documentElement.dataset.theme = nocturne ? "dark" : "light";
    const prochainTheme = { light: "dark", dark: "system", system: "light" }[themeChoisi];
    const nomTheme = { light: "clair", dark: "sombre", system: "système" }[themeChoisi];
    const nomProchainTheme = { light: "clair", dark: "sombre", system: "système" }[prochainTheme];
    boutonTheme.dataset.theme = themeChoisi;
    boutonTheme.setAttribute("aria-label", `Thème ${nomTheme}. Passer au mode ${nomProchainTheme}.`);
    boutonTheme.title = `Thème ${nomTheme}. Cliquer pour passer au mode ${nomProchainTheme}.`;
    localStorage.setItem("correctia-theme", themeChoisi);
}

appliquerTheme(localStorage.getItem("correctia-theme") || "system");
preferenceThemeSysteme.addEventListener("change", () => {
    if (boutonTheme.dataset.theme === "system") {
        appliquerTheme("system");
    }
});

champCorrige.addEventListener("change", () => afficherNomFichier(champCorrige, nomCorrige));
champCopie.addEventListener("change", () => afficherNomFichier(champCopie, nomCopie));
boutonCorriger.addEventListener("click", corrigerCopie);
boutonAnnuler.addEventListener("click", () => controleurCorrection?.abort());
boutonValiderCorrection.addEventListener("click", validerCorrection);
boutonPdf.addEventListener("click", exporterPdf);
boutonReediter.addEventListener("click", autoriserModification);
boutonStatistiques.addEventListener("click", afficherStatistiques);
boutonCorrection.addEventListener("click", revenirAuxCorrections);
boutonExporterStatistiques.addEventListener("click", exporterStatistiquesPdf);
selecteurClasse.addEventListener("change", afficherEvaluationsClasse);
selecteurEvaluation.addEventListener("change", afficherEvaluationSelectionnee);
contenuStatistiques.addEventListener("click", (evenement) => {
    const boutonSuppression = evenement.target.closest(".bouton-supprimer-resultat");
    if (boutonSuppression) {
        demanderSuppressionResultat(Number(boutonSuppression.dataset.studentIndex));
    }
});
boutonNonSuppression.addEventListener("click", () => dialogSuppression.close());
boutonOuiSuppression.addEventListener("click", supprimerResultatConfirme);
dialogSuppression.addEventListener("close", () => {
    resultatEnAttenteSuppression = null;
});
boutonTheme.addEventListener("click", () => {
    const prochainTheme = { light: "dark", dark: "system", system: "light" }[
        boutonTheme.dataset.theme
    ];
    appliquerTheme(prochainTheme);
});
boutonNouvelleCorrection.addEventListener("click", reinitialiserInterface);
contenuResultat.addEventListener("input", mettreAJourCorrection);
contenuResultat.addEventListener("change", (evenement) => {
    if (evenement.target.matches(".confirmation-question")) {
        mettreAJourDisponibiliteValidation();
    }
});

function afficherNomFichier(champ, zoneNom) {
    const fichier = champ.files[0];
    zoneNom.textContent = fichier ? fichier.name : "Aucun fichier sélectionné";
}

function verifierFichier(fichier, libelle) {
    if (!fichier) {
        throw new Error(`Veuillez sélectionner ${libelle}.`);
    }

    const extension = fichier.name.split(".").pop().toLowerCase();
    if (!["txt", "pdf", "docx"].includes(extension)) {
        throw new Error(`${libelle} doit être au format .txt, .pdf ou .docx.`);
    }

    if (fichier.size === 0) {
        throw new Error(`${libelle} est vide.`);
    }

    if (fichier.size > TAILLE_MAXIMALE) {
        throw new Error(`${libelle} dépasse la taille maximale de 10 Mo.`);
    }
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

        const fichiers = new FormData();
        fichiers.append("corrige", fichierCorrige);
        fichiers.append("copie_eleve", fichierCopie);

        const reponse = await fetch(API_URL, {
            method: "POST",
            signal: controleurCorrection.signal,
            body: fichiers
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

        afficherCorrection(donnees, donnees.identite_eleve || "");
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
    zoneChargement.classList.add("cache");
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
    correctionCourante = null;
    reinitialiserValidation();
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

function afficherCorrection(correction, texteCopieEleve = "") {
    correctionCourante = structuredClone(correction);
    const identiteEleve = extraireIdentite(texteCopieEleve);
    const questions = Array.isArray(correctionCourante.questions)
        ? correctionCourante.questions
        : [];

    const htmlQuestions = questions.map((question, index) => {
        const noteMaximale = Number.isFinite(Number(question.note_maximale))
            ? Number(question.note_maximale)
            : 0;
        const noteProposee = Number.isFinite(Number(question.note_proposee))
            ? Number(question.note_proposee)
            : 0;

        return `
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

        <label class="champ-note">
            Note attribuée
            <span class="saisie-note">
                <input type="number" min="0" max="${noteMaximale}" step="any" required
                    value="${noteProposee}"
                    data-editable="true" data-question-index="${index}" data-field="note_proposee"
                    aria-label="Note attribuée à la question ${echapperAttribut(question.numero)}">
                <span>/ ${echapperHtml(question.note_maximale)}</span>
            </span>
        </label>

        <div class="details-correction">
            <div class="bloc-correct">
                ${creerChampTexte("Arguments corrects", question.elements_corrects, `data-question-index="${index}" data-field="elements_corrects"`, 4)}
            </div>

            <div class="bloc-manquant">
                ${creerChampTexte("Arguments manquants ou incorrects", question.elements_manquants_ou_incorrects, `data-question-index="${index}" data-field="elements_manquants_ou_incorrects"`, 4)}
            </div>
        </div>

        <div class="commentaire-question">
            ${creerChampTexte("Commentaire", question.commentaire, `data-question-index="${index}" data-field="commentaire"`, 3)}
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

        <div class="validation-question">
            <label class="case-validation" for="validation-question-${index}">
                <input id="validation-question-${index}" class="confirmation-question" type="checkbox"
                    data-validation-index="${index}">
                Question vérifiée par l’enseignant
            </label>
        </div>
    </article>
`;
    }).join("");

    const verificationGlobale = correction.verification_humaine_recommandee
        ? '<p class="avertissement">Une vérification humaine particulière est recommandée.</p>'
        : '';

    contenuResultat.innerHTML = `
        <div class="identite-eleve">
            <label class="champ-identite" for="nom-eleve">
                Nom
                <input id="nom-eleve" type="text" autocomplete="family-name" data-editable="true" value="${echapperAttribut(identiteEleve.nom)}">
            </label>
            <label class="champ-identite" for="prenom-eleve">
                Prénom
                <input id="prenom-eleve" type="text" autocomplete="given-name" data-editable="true" value="${echapperAttribut(identiteEleve.prenom)}">
            </label>
            <label class="champ-identite" for="classe-eleve">
                Classe
                <input id="classe-eleve" type="text" data-editable="true" value="${echapperAttribut(identiteEleve.classe)}">
            </label>
            <label class="champ-identite" for="date-eleve">
                Date
                <input id="date-eleve" type="text" data-editable="true" value="${echapperAttribut(identiteEleve.date)}">
            </label>
        </div>

        <p class="note-sur-six">
            Note : <strong id="note-sur-six-valeur">${calculerNoteSurSix(correctionCourante.note_totale_proposee, correctionCourante.note_totale_maximale)}</strong> / 6
        </p>
        <p class="note-totale">
            Points attribués :
            <span id="note-totale-valeur">${echapperHtml(correctionCourante.note_totale_proposee)}</span> /
            ${echapperHtml(correctionCourante.note_totale_maximale)}
        </p>

        ${htmlQuestions}

        ${creerChampTexte("Commentaire global", correctionCourante.commentaire_global, "data-global-field=\"commentaire_global\"", 4)}

        ${verificationGlobale}

        <p class="avertissement">
            Cette proposition doit toujours être validée par un enseignant.
        </p>
    `;

    contenuResultat.querySelectorAll(
        'textarea[data-field="commentaire"], textarea[data-global-field="commentaire_global"]'
    ).forEach(actualiserCommentaireImpression);

    reinitialiserValidation();
    zoneResultat.classList.remove("cache");
    zoneResultat.scrollIntoView({ behavior: "smooth", block: "start" });
}

function creerChampTexte(libelle, valeur, attributs, lignes) {
    const contenu = Array.isArray(valeur) ? valeur.join("\n") : valeur;

    return `
        <label class="champ-texte">
            ${libelle}
            <textarea rows="${lignes}" ${attributs} data-editable="true">${echapperHtml(contenu)}</textarea>
        </label>
    `;
}

function mettreAJourCorrection(evenement) {
    const champ = evenement.target;

    if (!correctionCourante) {
        return;
    }

    if (champ.dataset.globalField) {
        correctionCourante[champ.dataset.globalField] = champ.value;
        actualiserCommentaireImpression(champ);
        contenuResultat.querySelectorAll(".confirmation-question").forEach((caseQuestion) => {
            caseQuestion.checked = false;
        });
        mettreAJourDisponibiliteValidation();
        return;
    }

    const index = Number(champ.dataset.questionIndex);
    const question = correctionCourante.questions[index];
    const champModifie = champ.dataset.field;

    if (!question || !champModifie) {
        return;
    }

    const validationQuestion = contenuResultat.querySelector(
        `.confirmation-question[data-validation-index="${index}"]`
    );
    validationQuestion.checked = false;
    mettreAJourDisponibiliteValidation();

    if (champModifie === "note_proposee") {
        question[champModifie] = Number(champ.value);
        const total = correctionCourante.questions.reduce(
            (somme, element) => somme + Number(element.note_proposee || 0),
            0
        );
        correctionCourante.note_totale_proposee = Number(total.toFixed(2));
        document.getElementById("note-totale-valeur").textContent = correctionCourante.note_totale_proposee;
        document.getElementById("note-sur-six-valeur").textContent = calculerNoteSurSix(
            correctionCourante.note_totale_proposee,
            correctionCourante.note_totale_maximale
        );
        return;
    }

    question[champModifie] = champModifie.startsWith("elements_")
        ? champ.value.split(/\r?\n/).map((element) => element.trim()).filter(Boolean)
        : champ.value;

    if (champModifie === "commentaire") {
        actualiserCommentaireImpression(champ);
    }
}

function actualiserCommentaireImpression(champ) {
    const contientRecommandation = /\brecommand|vérification humaine|vérifier les réponses manuellement/i.test(champ.value);
    champ.closest(".champ-texte")?.classList.toggle("masquer-impression", contientRecommandation);
}

async function validerCorrection() {
    if (!correctionCourante || !toutesQuestionsValidees()) {
        return;
    }

    const notes = contenuResultat.querySelectorAll('input[type="number"]');
    const noteInvalide = Array.from(notes).find((note) => !note.reportValidity());

    if (noteInvalide) {
        return;
    }

    const nomEleve = document.getElementById("nom-eleve").value.trim();
    const prenomEleve = document.getElementById("prenom-eleve").value.trim();
    const classeEleve = document.getElementById("classe-eleve").value.trim();
    const fichierCorrige = champCorrige.files[0];

    if (!nomEleve || !prenomEleve || !classeEleve || !fichierCorrige) {
        statutValidation.textContent = "Renseignez le nom, le prénom et la classe, puis vérifiez le corrigé sélectionné.";
        document.getElementById(!nomEleve ? "nom-eleve" : !prenomEleve ? "prenom-eleve" : "classe-eleve").focus();
        return;
    }

    const champDate = document.getElementById("date-eleve");
    if (!champDate.value.trim()) {
        const maintenant = new Date();
        champDate.value = [maintenant.getFullYear(), String(maintenant.getMonth() + 1).padStart(2, "0"), String(maintenant.getDate()).padStart(2, "0")].join("-");
    }

    boutonValiderCorrection.disabled = true;
    statutValidation.textContent = "Enregistrement des résultats…";

    try {
        const reponse = await fetch(`${API_STATISTIQUES_URL}/notes`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                classe: classeEleve,
                evaluation: fichierCorrige.name.replace(/\.[^.]+$/, ""),
                date: champDate.value.trim(),
                nom: nomEleve,
                prenom: prenomEleve,
                points: Number(correctionCourante.note_totale_proposee),
                points_max: Number(correctionCourante.note_totale_maximale),
                questions: correctionCourante.questions.map(question => ({
                    numero: Number(question.numero),
                    intitule: question.intitule,
                    points: Number(question.note_proposee),
                    points_max: Number(question.note_maximale)
                }))
            })
        });
        const donnees = await reponse.json();
        if (!reponse.ok) {
            throw new Error(donnees.detail || `Erreur HTTP ${reponse.status}`);
        }

        correctionValidee = true;
        actualiserEtatValidation();
        statutValidation.textContent = "Correction validée et résultats enregistrés.";
    } catch (erreur) {
        statutValidation.textContent = `Enregistrement impossible : ${erreur.message}`;
        mettreAJourDisponibiliteValidation();
    }
}

function autoriserModification() {
    correctionValidee = false;
    contenuResultat.querySelectorAll(".confirmation-question").forEach((caseQuestion) => {
        caseQuestion.checked = false;
        caseQuestion.disabled = false;
    });
    actualiserEtatValidation();
}

function reinitialiserValidation() {
    correctionValidee = false;
    boutonValiderCorrection.disabled = true;
    boutonValiderCorrection.classList.remove("cache");
    statutValidation.textContent = "";
    boutonPdf.disabled = true;
    boutonReediter.classList.add("cache");
    contenuResultat.querySelectorAll("[data-editable='true']").forEach((champ) => {
        champ.disabled = false;
    });
    contenuResultat.querySelectorAll(".confirmation-question").forEach((caseQuestion) => {
        caseQuestion.checked = false;
        caseQuestion.disabled = false;
    });
    mettreAJourDisponibiliteValidation();
}

function actualiserEtatValidation() {
    contenuResultat.querySelectorAll("[data-editable='true']").forEach((champ) => {
        champ.disabled = correctionValidee;
    });
    contenuResultat.querySelectorAll(".confirmation-question").forEach((caseQuestion) => {
        caseQuestion.disabled = correctionValidee;
    });
    boutonValiderCorrection.classList.toggle("cache", correctionValidee);
    mettreAJourDisponibiliteValidation();
    boutonPdf.disabled = !correctionValidee;
    boutonReediter.classList.toggle("cache", !correctionValidee);
    statutValidation.textContent = correctionValidee
        ? "Correction validée par l’enseignant."
        : "";
}

function toutesQuestionsValidees() {
    const cases = Array.from(contenuResultat.querySelectorAll(".confirmation-question"));
    return cases.length > 0 && cases.every((caseQuestion) => caseQuestion.checked);
}

function mettreAJourDisponibiliteValidation() {
    boutonValiderCorrection.disabled = correctionValidee || !toutesQuestionsValidees();
}

function calculerNoteSurSix(nbPoints, nbTotaux) {
    const points = Number(nbPoints);
    const total = Number(nbTotaux);

    if (!Number.isFinite(points) || !Number.isFinite(total) || total <= 0) {
        return "—";
    }

    return ((points / total) * 5 + 1).toLocaleString("fr-FR", {
        maximumFractionDigits: 2
    });
}

async function afficherStatistiques() {
    erreurStatistiques.textContent = "";
    erreurStatistiques.classList.add("cache");
    contenuStatistiques.innerHTML = '<p class="chargement-statistiques">Chargement des statistiques…</p>';
    sectionFormulaire.classList.add("cache");
    zoneResultat.classList.add("cache");
    sectionStatistiques.classList.remove("cache");

    try {
        const reponse = await fetch(API_STATISTIQUES_URL);
        const donnees = await reponse.json();
        if (!reponse.ok) {
            throw new Error(donnees.detail || `Erreur HTTP ${reponse.status}`);
        }
        afficherTableauStatistiques(donnees.classes || []);
    } catch (erreur) {
        contenuStatistiques.innerHTML = "";
        erreurStatistiques.textContent = `Impossible de charger les statistiques : ${erreur.message}`;
        erreurStatistiques.classList.remove("cache");
    }

    sectionStatistiques.scrollIntoView({ behavior: "smooth", block: "start" });
}

function afficherTableauStatistiques(classes) {
    statistiquesDisponibles = classes;

    if (!classes.length) {
        filtresStatistiques.classList.add("cache");
        contenuStatistiques.innerHTML = '<p class="etat-statistiques">Aucune évaluation enregistrée. Les résultats apparaîtront ici après validation par l’enseignant.</p>';
        return;
    }

    filtresStatistiques.classList.remove("cache");
    selecteurClasse.innerHTML = classes.map(classe => `
        <option value="${echapperAttribut(classe.classe)}">${echapperHtml(classe.classe)}</option>
    `).join("");
    afficherEvaluationsClasse();
}

function afficherEvaluationsClasse() {
    const classe = statistiquesDisponibles.find(element => element.classe === selecteurClasse.value);
    if (!classe?.evaluations.length) {
        selecteurEvaluation.innerHTML = "";
        boutonExporterStatistiques.disabled = true;
        contenuStatistiques.innerHTML = '<p class="etat-statistiques">Aucune évaluation enregistrée pour cette classe.</p>';
        return;
    }

    selecteurEvaluation.innerHTML = classe.evaluations.map((evaluation, index) => `
        <option value="${index}">${echapperHtml(evaluation.evaluation)} · ${echapperHtml(evaluation.date)}</option>
    `).join("");
    afficherEvaluationSelectionnee();
}

function afficherEvaluationSelectionnee() {
    const classe = statistiquesDisponibles.find(element => element.classe === selecteurClasse.value);
    const evaluation = classe?.evaluations[Number(selecteurEvaluation.value)];
    if (!evaluation) {
        evaluationStatistiquesCourante = null;
        classeStatistiquesCourante = "";
        boutonExporterStatistiques.disabled = true;
        contenuStatistiques.innerHTML = '<p class="etat-statistiques">Sélectionnez une évaluation.</p>';
        return;
    }

    evaluationStatistiquesCourante = evaluation;
    classeStatistiquesCourante = classe.classe;
    boutonExporterStatistiques.disabled = false;
    const questions = evaluation.questions || [];
    contenuStatistiques.innerHTML = `
        <p class="titre-impression-statistiques">Classe ${echapperHtml(classe.classe)} · ${echapperHtml(evaluation.evaluation)} · ${echapperHtml(evaluation.date)}</p>
        <div class="resume-evaluation">
            <span>${evaluation.nombre_eleves} élève${evaluation.nombre_eleves > 1 ? "s" : ""}</span>
            <span>Moyenne : ${formaterNombre(evaluation.moyenne_sur_six)} / 6</span>
            <span>Moyenne des points : ${formaterNombre(evaluation.moyenne_points)}</span>
        </div>
        ${questions.length ? `
            <section class="graphique-questions" aria-labelledby="titre-graphique-questions">
                <h3 id="titre-graphique-questions">Réponses entièrement justes par question</h3>
                ${questions.map(question => `
                    <div class="ligne-graphique-question">
                        <div class="libelle-graphique-question">
                            <span>Q${question.numero} · ${echapperHtml(question.intitule)}</span>
                            <strong>${question.nombre_justes} / ${question.nombre_reponses}</strong>
                        </div>
                        <div class="barre-graphique-question" role="img" aria-label="Question ${question.numero} : ${question.nombre_justes} réponses justes sur ${question.nombre_reponses}">
                            <span style="width: ${question.pourcentage_justes}%"></span>
                        </div>
                    </div>
                `).join("")}
            </section>
        ` : '<p class="etat-statistiques">Aucun score détaillé par question enregistré pour cette évaluation.</p>'}
        <div class="tableau-statistiques-scroll">
            <table class="tableau-statistiques">
                <thead><tr>
                    <th scope="col">Nom</th><th scope="col">Prénom</th>
                    ${questions.map(question => `<th scope="col" title="${echapperAttribut(question.intitule)}">Q${question.numero}<span class="sous-titre-colonne">/${formaterNombre(question.points_max)}</span></th>`).join("")}
                    <th scope="col">Total</th><th scope="col">Note / 6</th><th scope="col">Action</th>
                </tr></thead>
                <tbody>
                    ${evaluation.eleves.map((eleve, index) => `
                        <tr>
                            <td>${echapperHtml(eleve.nom)}</td><td>${echapperHtml(eleve.prenom)}</td>
                            ${questions.map(question => {
                                const score = eleve.questions?.find(element => Number(element.numero) === Number(question.numero));
                                return `<td>${score ? formaterNombre(score.points) : "—"}</td>`;
                            }).join("")}
                            <td>${formaterNombre(eleve.points)} / ${formaterNombre(eleve.points_max)}</td>
                            <td>${formaterNombre(eleve.note_sur_six)} / 6</td>
                            <td><button class="bouton-supprimer-resultat" type="button" data-student-index="${index}" aria-label="Supprimer le résultat de ${echapperAttribut(eleve.prenom)} ${echapperAttribut(eleve.nom)}">Supprimer</button></td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

function formaterNombre(valeur) {
    return Number(valeur).toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function exporterStatistiquesPdf() {
    const classe = statistiquesDisponibles.find(element => element.classe === selecteurClasse.value);
    const evaluation = classe?.evaluations[Number(selecteurEvaluation.value)];
    if (!classe || !evaluation) {
        return;
    }

    const titreOriginal = document.title;
    document.title = ["Statistiques", classe.classe, evaluation.evaluation, evaluation.date]
        .map(nettoyerSegmentNomFichier)
        .join("_");
    document.body.dataset.printView = "statistiques";
    window.addEventListener("afterprint", () => {
        document.title = titreOriginal;
        delete document.body.dataset.printView;
    }, { once: true });
    window.print();
}

function revenirAuxCorrections() {
    sectionStatistiques.classList.add("cache");
    sectionFormulaire.classList.remove("cache");
    if (correctionCourante) {
        zoneResultat.classList.remove("cache");
    }
    sectionFormulaire.scrollIntoView({ behavior: "smooth", block: "start" });
}

function exporterPdf() {
    const titreOriginal = document.title;
    const nomCorrigePdf = champCorrige.files[0]?.name.replace(/\.txt$/i, "") || "corrige";
    const nomEleve = document.getElementById("nom-eleve")?.value || "nom";
    const prenomEleve = document.getElementById("prenom-eleve")?.value || "prenom";
    const classeEleve = document.getElementById("classe-eleve")?.value || "classe";
    const dateEleve = document.getElementById("date-eleve")?.value || "date";
    const titrePdf = [nomCorrigePdf, nomEleve, prenomEleve, classeEleve, dateEleve]
        .map(nettoyerSegmentNomFichier)
        .join("_");

    document.title = titrePdf;
    window.addEventListener("afterprint", () => {
        document.title = titreOriginal;
    }, { once: true });
    window.print();
}

function nettoyerSegmentNomFichier(segment) {
    return String(segment ?? "")
        .trim()
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
        .replace(/\s+/g, "_")
        .replace(/_+/g, "_")
        .replace(/^_+|_+$/g, "") || "sans_nom";
}

function extraireIdentite(texte) {
    if (texte && typeof texte === "object") {
        return {
            nom: String(texte.nom ?? ""),
            prenom: String(texte.prenom ?? ""),
            classe: String(texte.classe ?? ""),
            date: String(texte.date ?? "")
        };
    }

    const nom = String(texte).match(/^\s*Nom\s*[:：]\s*(.*?)\s*$/im)?.[1] || "";
    const prenom = String(texte).match(/^\s*Pr[ée]nom\s*[:：]\s*(.*?)\s*$/im)?.[1] || "";
    const classe = String(texte).match(/^\s*Classe\s*[:：]\s*(.*?)\s*$/im)?.[1] || "";
    const date = String(texte).match(/^\s*Date(?!\s+de\s+naissance)\s*[:：]\s*(.*?)\s*$/im)?.[1] || "";

    return { nom, prenom, classe, date };
}

function echapperHtml(texte) {
    const element = document.createElement("div");
    element.textContent = String(texte ?? "");
    return element.innerHTML;
}

function echapperAttribut(texte) {
    return echapperHtml(texte).replaceAll('"', "&quot;");
}
