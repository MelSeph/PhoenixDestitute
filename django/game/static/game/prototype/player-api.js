(() => {
    "use strict";
    const status = document.getElementById("player-api-status");
    const details = document.getElementById("player-api-details");
    const create = document.getElementById("player-create-button");
    if (!status || !details || !create) return;

    function cookie(name) {
        const match = document.cookie.split("; ").find(part => part.startsWith(name + "="));
        return match ? decodeURIComponent(match.slice(name.length + 1)) : "";
    }
    function show(player) {
        status.textContent = "Character loaded from Django database";
        details.textContent = `${player.name} — Level ${player.level} — Experience ${player.experience}`;
        details.hidden = false;
        create.hidden = true;
    }
    async function load() {
        try {
            const response = await fetch("/api/player/", {credentials: "same-origin"});
            if (response.status === 404) {
                status.textContent = "No local character yet.";
                details.hidden = true;
                create.hidden = false;
                return;
            }
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            show((await response.json()).player);
        } catch (error) {
            status.textContent = `Could not load character: ${error.message}`;
        }
    }
    create.addEventListener("click", async () => {
        create.disabled = true;
        status.textContent = "Creating character…";
        try {
            const response = await fetch("/api/player/create/", {
                method: "POST", credentials: "same-origin",
                headers: {"X-CSRFToken": cookie("csrftoken")},
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            show((await response.json()).player);
        } catch (error) {
            status.textContent = `Could not create character: ${error.message}`;
            create.disabled = false;
        }
    });
    load();
})();
