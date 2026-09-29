async function corriger() {

    const corrige =
        document.getElementById("corrige").value;

    const copie =
        document.getElementById("copie").value;

    const response = await fetch(
        "http://127.0.0.1:8000/correction",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                corrige: corrige,
                copie_eleve: copie
            })
        }
    );

    const data = await response.json();

    document.getElementById("resultat")
        .textContent =
        JSON.stringify(data, null, 2);
}
