// Identity lives outside catalog properties so it cannot leak into item stats.
const browserItemIdentity = new WeakMap();
let browserInventory = { version: 1, playthrough_id: null, revision: null, items: [] };
let browserSaveLoaded = false;
let inventoryError = "";
let browserSaveExtras = {};
const equipmentPositions = ["head", "armor", "hands", "waist", "legs", "feet",
    "rightHand", "leftHand", "upperClothes", "lowerClothes", "legCoverings"];

function inventoryAcquired(item) {
    browserItemIdentity.set(item, { token: crypto.randomUUID(), definition_key: item.name });
}

function potionCounters() {
    return [[healthPotion, "numHealthPotions"], [staminaPotion, "numStaminaPotions"],
        [manaPotion, "numManaPotions"]];
}

function cloneInventory(value) {
    return JSON.parse(JSON.stringify(value));
}

function validateEquipmentPositions(info, occupied) {
    for (const position of equipmentPositions) {
        if (inventoryCatalog.has(info[position]) && !occupied.has(position)) {
            throw new Error(`Equipment at ${position} is missing from inventory. Save was not changed.`);
        }
    }
}

function createInventorySnapshot() {
    const potions = potionCounters();
    // Explicit carried/stored entries are retained without guessing from names.
    const items = cloneInventory(browserInventory.items.filter(item =>
        item.location !== "equipped" && !(item.kind === "consumable" &&
            item.location === "carried" && potions.some(([potion]) => item.definition_key === potion.name))));
    const usedPositions = new Set();
    const seen = new Set();
    for (const item of equippedItems) {
        if (potions.some(([potion]) => potion.name === item.name)) continue;
        if (seen.has(item)) throw new Error("Ambiguous repeated equipment object. Save was not changed.");
        seen.add(item);
        const positions = equipmentPositions.filter(position => playerInfo[position] === item.name);
        if (!positions.length || positions.some(position => usedPositions.has(position))) {
            throw new Error(`Cannot safely determine equipment position for ${item.name}. Save was not changed.`);
        }
        positions.forEach(position => usedPositions.add(position));
        if (!browserItemIdentity.has(item)) inventoryAcquired(item);
        const identity = browserItemIdentity.get(item);
        items.push({ ...identity, definition_key: identity.definition_key || item.name,
            kind: "equipment", quantity: 1, location: "equipped", slot: null,
            properties: { ...cloneInventory(item), equipment_positions: positions } });
    }
    validateEquipmentPositions(playerInfo, usedPositions);
    const occupied = new Set(items.filter(item => item.location === "carried").map(item => item.slot));
    for (const [potion, counter] of potions) {
        const quantity = playerStats[counter];
        if (!Number.isSafeInteger(quantity) || quantity < 0) throw new Error(`Invalid ${counter}.`);
        if (!quantity) continue;
        const previous = browserInventory.items.find(item => item.kind === "consumable" &&
            item.location === "carried" && item.definition_key === potion.name);
        if (!browserItemIdentity.has(potion)) inventoryAcquired(potion);
        let slot = previous ? previous.slot : 0;
        while (occupied.has(slot)) slot++;
        occupied.add(slot);
        const entry = previous ? cloneInventory(previous) : {
            ...browserItemIdentity.get(potion), definition_key: potion.name, kind: "consumable",
            location: "carried", properties: cloneInventory(potion)
        };
        items.push({ ...entry, quantity, slot });
    }
    // Retain new tokens even if the HTTP response is lost.
    browserInventory.items = cloneInventory(items);
    return { ...browserInventory, items };
}

function prepareInventoryRestore(savedData, playthroughId) {
    for (const [, counter] of potionCounters()) {
        if (!Number.isSafeInteger(savedData.playerStats[counter]) || savedData.playerStats[counter] < 0) {
            throw new Error(`Invalid saved ${counter}. Original save preserved.`);
        }
    }
    const inventory = savedData.inventory;
    if (inventory) {
        if (inventory.version !== 1 || inventory.playthrough_id !== playthroughId ||
            !Array.isArray(inventory.items)) throw new Error("Unsupported saved inventory.");
        const equipment = [];
        const used = new Set();
        const tokens = new Set();
        for (const [potion] of potionCounters()) {
            if (inventory.items.filter(item => item.kind === "consumable" &&
                item.location === "carried" && item.definition_key === potion.name).length > 1) {
                throw new Error("Multiple legacy potion stacks are unsupported.");
            }
        }
        for (const entry of inventory.items) {
            if (!entry.token || tokens.has(entry.token) || !entry.properties ||
                typeof entry.properties !== "object") throw new Error("Invalid saved item identity.");
            tokens.add(entry.token);
            if (entry.location !== "equipped") continue;
            const positions = entry.properties.equipment_positions;
            const template = inventoryCatalog.get(entry.definition_key);
            if (!template || !Array.isArray(positions) || !positions.length ||
                new Set(positions).size !== positions.length ||
                positions.some(position => !equipmentPositions.includes(position) || used.has(position) ||
                    savedData.playerInfo[position] !== entry.properties.name) ||
                equipment.some(item => item.template === template)) {
                throw new Error("Cannot safely restore equipped item positions.");
            }
            positions.forEach(position => used.add(position));
            equipment.push({ template, entry });
        }
        validateEquipmentPositions(savedData.playerInfo, used);
        return { inventory: cloneInventory(inventory), equipment };
    }
    if (!Array.isArray(savedData.equippedItems)) throw new Error("Saved equipment is missing.");
    const equipment = [];
    const used = new Set();
    for (const name of savedData.equippedItems) {
        if (potionCounters().some(([potion]) => potion.name === name)) continue;
        const template = inventoryCatalog.get(name);
        const positions = equipmentPositions.filter(position => savedData.playerInfo[position] === name);
        if (!template || !positions.length || positions.some(position => used.has(position))) {
            throw new Error(`Ambiguous legacy equipment: ${name}. Original save preserved.`);
        }
        positions.forEach(position => used.add(position));
        equipment.push({ template, entry: { token: crypto.randomUUID(), definition_key: name,
            properties: cloneInventory(inventoryCatalogDefaults.get(name)) } });
    }
    validateEquipmentPositions(savedData.playerInfo, used);
    return { inventory: { version: 1, playthrough_id: playthroughId, revision: null,
        base_updated_at: savedData._browserUpdatedAt || null, items: [] }, equipment };
}

function applyInventoryRestore(prepared) {
    for (const { template, entry } of prepared.equipment) {
        for (const key of Object.keys(template)) delete template[key];
        Object.assign(template, cloneInventory(entry.properties));
        delete template.equipment_positions;
        browserItemIdentity.set(template, { id: entry.id, token: entry.token,
            definition_key: entry.definition_key });
    }
    equippedItems.splice(0, equippedItems.length, ...prepared.equipment.map(item => item.template));
    browserInventory = prepared.inventory;
    if (prepared.inventory.revision !== null) {
        for (const [potion, counter] of potionCounters()) {
            const stacks = prepared.inventory.items.filter(item => item.kind === "consumable" &&
                item.location === "carried" && item.definition_key === potion.name);
            playerStats[counter] = stacks.reduce((sum, item) => sum + item.quantity, 0);
            if (stacks.length) {
                Object.assign(potion, cloneInventory(stacks[0].properties));
                browserItemIdentity.set(potion, { id: stacks[0].id, token: stacks[0].token,
                    definition_key: stacks[0].definition_key });
            }
        }
    }
    browserSaveLoaded = true;
}

async function loadPlayerFromDjango(playerId) {
    try {
        const response = await fetch(`/api/players/${playerId}/`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const player = await response.json();

        console.log("Player loaded from Django:", player);

        return player;
    } catch (error) {
        console.error("Unable to load player:", error);
        return null;
    }
}

function createPlayerSnapshot() {
    const snapshot = {
        ...browserSaveExtras,
        playerInfo: playerInfo,
        playerStats: playerStats,
        inventory: createInventorySnapshot(),

        // Save equipped item names.
        equippedItems: equippedItems.map(
            item => item.name
        ),

        // Save collected materials and resource progress.
        materialStats: { ...materialStats },

        // Save gathering counters.
        gatheringProgress: {
            timesMined: timesMined,
            timesChopped: timesChopped,
            timesScooped: timesScooped,
            gathered: gathered
        },

        // Save building reconstruction progress.
        buildings: {
            jance: { ...janceStats },
            reno: { ...renoStats },
            raj: { ...rajStats },
            grey: { ...greyStats },
            thane: { ...thaneStats },
            hildt: { ...hildtStats },
            weaponSmithy: { ...weaponSmithyStats },
            armorSmithy: { ...armorSmithyStats },
            apothecary: { ...apothecaryStats }
        }
    };

    const json = JSON.stringify(snapshot);

    console.log("Player snapshot:", json);

    return json;
}

function getGameCsrfToken() {
    const token = document.cookie.split("; ").find(part => part.startsWith("csrftoken="));
    return token ? decodeURIComponent(token.slice("csrftoken=".length)) : "";
}

async function ensureLocalGamePlayer() {
    const response = await fetch("/api/player/create/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": getGameCsrfToken() }
    });
    if (!response.ok) throw new Error(`Character initialization failed: HTTP ${response.status}`);
}

async function savePlayerToDjango() {
    try {
        await ensureLocalGamePlayer();
        if (!browserSaveLoaded) {
            const current = await fetch("/api/game/load/", { credentials: "same-origin" });
            const result = await current.json();
            if (current.status !== 404 || !result.playthrough_id) {
                throw new Error("Load your existing save before saving with the inventory update.");
            }
            browserInventory.playthrough_id = result.playthrough_id;
        }
        const snapshot = createPlayerSnapshot();

        const response = await fetch(
            "/api/game/save/",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getGameCsrfToken()
                },
                body: snapshot,
                credentials: "same-origin"
            }
        );

        if (!response.ok) {
            const problem = await response.json();
            throw new Error(problem.error || `Save failed: HTTP ${response.status}`);
        }

        const result = await response.json();
        browserInventory = result.inventory;
        browserSaveLoaded = true;
        for (const item of equippedItems) {
            const identity = browserItemIdentity.get(item);
            const saved = identity && browserInventory.items.find(entry => entry.token === identity.token);
            if (saved) browserItemIdentity.set(item, { id: saved.id, token: saved.token,
                definition_key: saved.definition_key });
        }

        console.log("Game saved successfully:", result);

        return result;
    } catch (error) {
        inventoryError = error.message;
        console.error("Unable to save game:", error);
        return null;
    }
}

async function loadGameFromDjango() {
    try {
        const response = await fetch(
            "/api/game/load/",
            { credentials: "same-origin" }
        );

        if (!response.ok) {
            throw new Error(
                `Load failed: HTTP ${response.status}`
            );
        }

        const result = await response.json();

        if (
            !result.success ||
            !result.data ||
            !result.data.playerInfo ||
            !result.data.playerStats
        ) {
            throw new Error("Invalid save data received");
        }

        result.data._browserPlaythroughId = result.playthrough_id;
        result.data._browserUpdatedAt = result.updated_at;
        console.log("Saved game loaded:", result.data);

        return result.data;
    } catch (error) {
        console.error("Unable to load game:", error);
        return null;
    }
}

async function restorePlayerFromDjango() {
    const savedData = await loadGameFromDjango();

    if (!savedData) {
        console.error("No saved data available.");
        return false;
    }

    if (
        typeof savedData.playerInfo !== "object" ||
        savedData.playerInfo === null ||
        Array.isArray(savedData.playerInfo) ||
        typeof savedData.playerStats !== "object" ||
        savedData.playerStats === null ||
        Array.isArray(savedData.playerStats)
    ) {
        console.error("Saved character data is invalid.");
        return false;
    }

    // Prepare inventory first; apply only after all legacy save fields validate.
    const preparedInventory = prepareInventoryRestore(savedData, savedData._browserPlaythroughId);


    // Validate saved material and gathering data.
    if (
        !savedData.materialStats ||
        typeof savedData.materialStats !== "object" ||
        Array.isArray(savedData.materialStats) ||
        !savedData.gatheringProgress ||
        typeof savedData.gatheringProgress !== "object" ||
        Array.isArray(savedData.gatheringProgress)
    ) {
        console.error("Saved material or gathering data is invalid.");
        return false;
    }

    const progress = savedData.gatheringProgress;

    const counters = [
        "timesMined",
        "timesChopped",
        "timesScooped",
        "gathered"
    ];

    if (
        !counters.every(
            name =>
                typeof progress[name] === "number" &&
                Number.isFinite(progress[name])
        )
    ) {
        console.error("Saved gathering counters are invalid.");
        return false;
    }

    console.log("Materials and gathering progress restored.");

    // Restore building reconstruction progress.
    const buildingTargets = {
        jance: janceStats,
        reno: renoStats,
        raj: rajStats,
        grey: greyStats,
        thane: thaneStats,
        hildt: hildtStats,
        weaponSmithy: weaponSmithyStats,
        armorSmithy: armorSmithyStats,
        apothecary: apothecaryStats
    };

    const savedBuildings = savedData.buildings;

    // Validate all nine buildings before restoring any.
    if (
        !savedBuildings ||
        typeof savedBuildings !== "object" ||
        Array.isArray(savedBuildings)
    ) {
        console.error("Saved building data is missing or invalid.");
        return false;
    }

    for (const name of Object.keys(buildingTargets)) {
        const savedBuilding = savedBuildings[name];

        if (
            !savedBuilding ||
            typeof savedBuilding !== "object" ||
            Array.isArray(savedBuilding)
        ) {
            console.error(`Invalid saved building: ${name}`);
            return false;
        }

        // Check the expected building properties.
        for (const property of Object.keys(buildingTargets[name])) {
            if (
                typeof savedBuilding[property] !==
                typeof buildingTargets[name][property]
            ) {
                console.error(
                    `Invalid ${property} in building ${name}`
                );
                return false;
            }
        }
    }

    Object.assign(playerInfo, savedData.playerInfo);
    Object.assign(playerStats, savedData.playerStats);
    applyInventoryRestore(preparedInventory);
    browserSaveExtras = cloneInventory(savedData);
    delete browserSaveExtras._browserPlaythroughId;
    delete browserSaveExtras._browserUpdatedAt;
    Object.assign(materialStats, savedData.materialStats);
    timesMined = progress.timesMined;
    timesChopped = progress.timesChopped;
    timesScooped = progress.timesScooped;
    gathered = progress.gathered;

    // Update the original objects without rebuilding.
    for (const name of Object.keys(buildingTargets)) {
        Object.assign(
            buildingTargets[name],
            savedBuildings[name]
        );
    }

    synchronizeBuildingUnlocks();

    console.log("Building reconstruction progress restored.");

    console.log("Player state restored:", {
        playerInfo,
        playerStats
    });

    // Restore the story text for the player's current location.
    restoreStoryInterface();
    restoreGatheringInterface();
    restoreProductionInterface();
    restoreShopInterface();

    return true;
}

function synchronizeBuildingUnlocks() {
    allEndoraRebuilt = [
        janceStats,
        renoStats,
        rajStats,
        greyStats,
        thaneStats,
        hildtStats,
        weaponSmithyStats,
        armorSmithyStats,
        apothecaryStats
    ].every(building => building.rebuilt === 1);

    prodFacRebuilt = [
        weaponSmithyStats,
        armorSmithyStats,
        apothecaryStats
    ].some(building => building.rebuilt === 1);

    console.log("Building unlocks synchronized:", {
        allEndoraRebuilt,
        prodFacRebuilt
    });
}

function synchronizeBuildingButtons() {
    // Rebuilding is available until all buildings are rebuilt.
    const showRebuildButton =
        isRebuildUnlocked && !allEndoraRebuilt;

    // Production is available when unlocked.
    const showProductionButton =
        isProductionUnlocked || prodFacRebuilt;

    // Set visibility directly rather than toggling.
    getRebuildButton.style.display =
        showRebuildButton ? "block" : "none";

    getProductionButton.style.display =
        showProductionButton ? "block" : "none";

    // Keep internal button flags synchronized.
    toggleRebuildButtonStatus = showRebuildButton;
    toggleProductionButtonStatus = showProductionButton;

    console.log("Building buttons synchronized:", {
        showRebuildButton,
        showProductionButton
    });
}

function restoreStoryInterface() {
    const consoleBox = document.querySelector(".console-box");

    if (!consoleBox) {
        console.error("Story console was not found.");
        return false;
    }

    const openingQuestion = consoleBox.querySelector("p");

    if (!openingQuestion) {
        console.error("Story paragraph was not found.");
        return false;
    }

    switch (playerInfo.area) {
        case "Post-Battle-Reprieve":
            openingQuestion.textContent =
                "You are currently in Endora. Your adventure continues. " +
                "You may explore your available options or proceed toward the city gates.";
            break;

        default:
            console.log(
                "No story restoration text defined for:",
                playerInfo.area
            );
            return false;
    }

    return true;
}

function restoreGatheringInterface() {
    const gatheringUnlocked = gathered > 0;

    const gatheringAllowedHere =
        playerInfo.area === "Post-Battle-Reprieve";

    const showGatheringButton =
        gatheringUnlocked && gatheringAllowedHere;

    getGatherButton.style.display =
        showGatheringButton ? "block" : "none";

    toggleGatherButtonStatus = showGatheringButton;

    // Keep the gathering screen closed after loading.
    const gatheringScreen =
        document.querySelector(".gather-wrapper");

    if (gatheringScreen) {
        gatheringScreen.style.display = "none";
    }

    return true;
}

function restoreProductionInterface() {
    const productionAvailableHere =
        playerInfo.area === "Post-Battle-Reprieve";

    const showProductionButton =
        productionAvailableHere && prodFacRebuilt;

    getProductionButton.style.display =
        showProductionButton ? "block" : "none";

    toggleProductionButtonStatus = showProductionButton;

    // Restore individual production facilities.
    const productionFacilities = [
        {
            selector: ".forge-visible",
            rebuilt: weaponSmithyStats.rebuilt
        },
        {
            selector: ".tanner-visible",
            rebuilt: armorSmithyStats.rebuilt
        },
        {
            selector: ".apothecary-visible",
            rebuilt: apothecaryStats.rebuilt
        }
    ];

    productionFacilities.forEach(facility => {
        const element = document.querySelector(facility.selector);

        if (element) {
            element.style.display =
                productionAvailableHere && facility.rebuilt === 1
                    ? "block"
                    : "none";
        }
    });

    // Keep the production screen closed after loading.
    const productionScreen =
        document.querySelector(".endora-secret-wrapper");

    if (productionScreen) {
        productionScreen.style.display = "none";
    }

    return true;
}

function restoreShopInterface() {
    // The player has survived the introductory battle
    // and is currently in Endora.
    const shopAvailableHere =
        playerInfo.area === "Post-Battle-Reprieve";

    // Restore the Shop button.
    getShopButton.style.display =
        shopAvailableHere ? "block" : "none";

    toggleShopButtonStatus = shopAvailableHere;

    // Keep the Shop screen closed until clicked.
    const shopScreen =
        document.querySelector(".shop-wrapper");

    if (shopScreen) {
        shopScreen.style.display = "none";
    }

    return true;
}

let notificationTimeout;

function showGameNotification(message, type = "success") {
    const notification =
        document.getElementById("game-notification");

    // Cancel the previous notification timer.
    clearTimeout(notificationTimeout);

    // Remove the previous message.
    notification.textContent = "";

    // Create the appropriate icon.
    const icon = document.createElement("span");

    if (type === "error") {
        icon.textContent = "✕";
    } else {
        icon.textContent = "✓";
    }

    notification.appendChild(icon);
    notification.appendChild(
        document.createTextNode(" " + message)
    );

    // Apply the appropriate styling.
    notification.classList.remove("success", "error");
    notification.classList.add(type);

    // Show the notification.
    notification.classList.add("visible");

    // Hide it automatically after three seconds.
    notificationTimeout = setTimeout(function () {
        notification.classList.remove("visible");
    }, 3000);
}

function initializeGameMenu() {
    const gameMenuButton =
        document.getElementById("game-menu-button");

    const gameMenu =
        document.getElementById("game-menu");

    const closeGameMenuButton =
        document.getElementById("close-game-menu-button");

    const saveGameButton =
        document.getElementById("save-game-button");

    const loadGameButton =
        document.getElementById("load-game-button");

    const loadConfirmation =
        document.getElementById("load-confirmation");

    const cancelLoadButton =
        document.getElementById("cancel-load-button");

    const confirmLoadButton =
        document.getElementById("confirm-load-button");

    // Open or close the menu.
    gameMenuButton.addEventListener("click", function () {
        const menuIsHidden =
            getComputedStyle(gameMenu).display === "none";

        gameMenu.style.display =
            menuIsHidden ? "block" : "none";
    });

    // Return to the game.
    closeGameMenuButton.addEventListener("click", function () {
        gameMenu.style.display = "none";
        loadConfirmation.style.display = "none";
    });
    
    // Save the game to Django.
    saveGameButton.addEventListener("click", async function () {
        // Prevent additional clicks while saving.
        saveGameButton.disabled = true;
        saveGameButton.textContent = "Saving...";
        loadGameButton.disabled = true;

        try {
            const result = await savePlayerToDjango();

            if (result !== null) {
                showGameNotification("Game saved successfully!");
            } else {
                showGameNotification(inventoryError || "Unable to save your game.", "error");
            }
        } finally {
            // Restore the button after saving finishes.
            saveGameButton.disabled = false;
            saveGameButton.textContent = "Save Game";
            loadGameButton.disabled = false;
        }
    });

    // Open the Load Game confirmation panel.
    loadGameButton.addEventListener("click", function () {
        loadConfirmation.style.display = "block";
    });

    // Cancel loading without changing the game.
    cancelLoadButton.addEventListener("click", function () {
        loadConfirmation.style.display = "none";
    });

    // Confirm loading the saved character from Django.
    confirmLoadButton.addEventListener("click", async function () {
        // Prevent repeated clicks while loading.
        confirmLoadButton.disabled = true;
        confirmLoadButton.textContent = "Loading...";
        saveGameButton.disabled = true;
        loadGameButton.disabled = true;

        try {
            const restored = await restorePlayerFromDjango();

            if (restored === true) {
                showGameNotification("Game loaded successfully!");

                // Hide the confirmation panel and Game Menu.
                loadConfirmation.style.display = "none";
                gameMenu.style.display = "none";
            } else {
                showGameNotification(
                    "Unable to load your saved game.",
                    "error"
                );
            }
        } catch (error) {
            console.error("Load failed:", error);

            showGameNotification(
                error.message || "An error occurred while loading your game.",
                "error"
            );
        } finally {
            // Restore the buttons regardless of the result.
            confirmLoadButton.disabled = false;
            confirmLoadButton.textContent = "Yes, Load Game";
            saveGameButton.disabled = false;
            loadGameButton.disabled = false;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeGameMenu);
} else {
    initializeGameMenu();
}
