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
        playerInfo: playerInfo,
        playerStats: playerStats,

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

async function savePlayerToDjango(playerId) {
    try {
        const snapshot = createPlayerSnapshot();

        const response = await fetch(
            `/api/players/${playerId}/save/`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: snapshot
            }
        );

        if (!response.ok) {
            throw new Error(`Save failed: HTTP ${response.status}`);
        }

        const result = await response.json();

        console.log("Game saved successfully:", result);

        return result;
    } catch (error) {
        console.error("Unable to save game:", error);
        return null;
    }
}

async function loadGameFromDjango(playerId) {
    try {
        const response = await fetch(
            `/api/players/${playerId}/load/`
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

        console.log("Saved game loaded:", result.data);

        return result.data;
    } catch (error) {
        console.error("Unable to load game:", error);
        return null;
    }
}

async function restorePlayerFromDjango(playerId) {
    const savedData = await loadGameFromDjango(playerId);

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

    // Find the original equipment objects by name.
    if (!Array.isArray(savedData.equippedItems)) {
        console.error("Saved equipment list is missing or invalid.");
        return false;
    }

    const restoredEquipment = savedData.equippedItems.map(
        itemName => equipArray.find(item => item.name === itemName)
    );

    // Stop if any equipment name cannot be found.
    if (restoredEquipment.some(item => item === undefined)) {
        console.error(
            "Some saved equipment could not be found:",
            savedData.equippedItems
        );
        return false;
    }

    // Preserve the existing equippedItems array.
    equippedItems.splice(
        0,
        equippedItems.length,
        ...restoredEquipment
    );

    Object.assign(playerInfo, savedData.playerInfo);
    Object.assign(playerStats, savedData.playerStats);


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

    // Restore the existing material object.
    Object.assign(materialStats, savedData.materialStats);

    // Restore gathering counters.
    timesMined = progress.timesMined;
    timesChopped = progress.timesChopped;
    timesScooped = progress.timesScooped;
    gathered = progress.gathered;

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
            const result = await savePlayerToDjango(2);

            if (result !== null) {
                showGameNotification("Game saved successfully!");
            } else {
                showGameNotification("Unable to save your game.", "error");
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
            const restored = await restorePlayerFromDjango(2);

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
                "An error occurred while loading your game.",
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
