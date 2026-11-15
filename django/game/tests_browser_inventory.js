// Runs against production functions and catalog objects in a real browser.
(async () => {
try {
    let passed = 0;
    function check(condition, message) {
        if (!condition) throw new Error(message);
        passed++;
    }
    function rejects(action) {
        try { action(); return false; } catch { return true; }
    }
    function reset() {
        for (const [key, template] of inventoryCatalog) {
            for (const property of Object.keys(template)) delete template[property];
            Object.assign(template, cloneInventory(inventoryCatalogDefaults.get(key)));
        }
        equippedItems.splice(0, equippedItems.length);
        for (const position of equipmentPositions) playerInfo[position] = "Empty";
        playerStats.numHealthPotions = playerStats.numStaminaPotions = playerStats.numManaPotions = 0;
        browserInventory = { version: 1, playthrough_id: 7, revision: null, items: [] };
    }
    reset();
    playerInfo.rightHand = dilapidatedSword.name;
    equippedItems.push(dilapidatedSword);
    dilapidatedSword.durability = 17;
    dilapidatedSword.upgrades = { rune: "fire", level: 4 };
    const first = createInventorySnapshot();
    check(first.items[0].properties.durability === 17 && first.items[0].properties.upgrades.level === 4,
        "Unique equipment properties were lost");
    check(createInventorySnapshot().items[0].token === first.items[0].token, "Repeated save changed identity");
    const saved = { playerInfo: cloneInventory(playerInfo), playerStats: cloneInventory(playerStats),
        inventory: { ...cloneInventory(first), revision: "saved" } };
    const originalArray = equippedItems;
    for (let i = 0; i < 3; i++) applyInventoryRestore(prepareInventoryRestore(saved, 7));
    check(equippedItems === originalArray && equippedItems.length === 1 &&
        equippedItems[0] === dilapidatedSword && dilapidatedSword.durability === 17,
        "Repeated load duplicated items or broke catalog references");
    equippedItems.splice(0, 1);
    equippedItems.push(dilapidatedSword);
    check(createInventorySnapshot().items[0].token !== first.items[0].token,
        "Reacquisition reused the disposed instance identity");
    reset();
    const old = { playerInfo: { rightHand: nonStaff.name, leftHand: nonStaff.name },
        playerStats: { numHealthPotions: 2, numStaminaPotions: 0, numManaPotions: 0 },
        equippedItems: [nonStaff.name, healthPotion.name, healthPotion.name, healthPotion.name] };
    const prepared = prepareInventoryRestore(old, 7);
    Object.assign(playerInfo, old.playerInfo);
    Object.assign(playerStats, old.playerStats);
    applyInventoryRestore(prepared);
    let snapshot = createInventorySnapshot();
    check(snapshot.items.filter(item => item.kind === "equipment").length === 1 &&
        snapshot.items[0].properties.equipment_positions.length === 2, "Two-handed staff duplicated");
    check(snapshot.items.find(item => item.kind === "consumable").quantity === 2,
        "Stale potion array entries replaced remaining count");
    playerStats.numHealthPotions = 0;
    check(!createInventorySnapshot().items.some(item => item.kind === "consumable"),
        "Consumed potions returned");
    const ambiguous = cloneInventory(old);
    ambiguous.equippedItems.push(nonStaff.name);
    check(rejects(() => prepareInventoryRestore(ambiguous, 7)), "Ambiguous legacy item accepted");
    check(rejects(() => prepareInventoryRestore(saved, 8)), "Stale-life inventory accepted");
    const extra = { token: crypto.randomUUID(), definition_key: "Unique Sword", kind: "equipment",
        location: "stored", slot: null, quantity: 1, properties: { durability: 8, custom: true } };
    browserInventory.items.push(extra);
    const unknownPotion = { ...cloneInventory(extra), token: crypto.randomUUID(), kind: "consumable",
        definition_key: "Elixir", location: "carried", slot: 9 };
    browserInventory.items.push(unknownPotion);
    snapshot = createInventorySnapshot();
    check(snapshot.items.some(item => item.token === extra.token && item.properties.custom) &&
        snapshot.items.some(item => item.token === unknownPotion.token && item.slot === 9),
        "Explicit stored or carried items were lost");
    const bad = cloneInventory(saved);
    bad.inventory.items.push(cloneInventory(bad.inventory.items[0]));
    check(rejects(() => prepareInventoryRestore(bad, 7)), "Duplicate identity accepted on load");
    reset();
    dilapidatedSword.durability = 999;
    const legacy = { equippedItems: ["Rusted Sword"], playerInfo: { rightHand: "Rusted Sword" },
        playerStats: { numHealthPotions: 0, numStaminaPotions: 0, numManaPotions: 0 } };
    applyInventoryRestore(prepareInventoryRestore(legacy, 7));
    check(!Object.hasOwn(dilapidatedSword, "durability"), "Legacy load inherited another instance's properties");
    // Exercise production save/load functions with HTTP responses supplied in memory.
    reset();
    browserSaveLoaded = false;
    browserSaveExtras = { customQuest: { completed: true } };
    window.materialStats = { ore: 3 };
    window.timesMined = window.timesChopped = window.timesScooped = window.gathered = 0;
    for (const name of ["jance", "reno", "raj", "grey", "thane", "hildt", "weaponSmithy", "armorSmithy", "apothecary"]) {
        window[`${name}Stats`] = { progress: 1 };
    }
    synchronizeBuildingUnlocks = restoreStoryInterface = restoreGatheringInterface =
        restoreProductionInterface = restoreShopInterface = () => {};
    playerInfo.rightHand = dilapidatedSword.name;
    equippedItems.push(dilapidatedSword);
    dilapidatedSword.durability = 21;
    let remote = null;
    let revision = 0;
    window.fetch = async (url, options = {}) => {
        if (url === "/api/player/create/") return { ok: true };
        if (options.method === "POST") {
            remote = JSON.parse(options.body);
            remote.inventory.revision = String(++revision);
            remote.inventory.items.forEach((entry, index) => entry.id = index + 1);
            return { ok: true, json: async () => ({ success: true, inventory: remote.inventory }) };
        }
        return remote ? { ok: true, status: 200, json: async () => ({ success: true,
            data: cloneInventory(remote), playthrough_id: 7, updated_at: "timestamp" }) } :
            { ok: false, status: 404, json: async () => ({ playthrough_id: 7 }) };
    };
    check(await savePlayerToDjango() !== null && remote.inventory.items[0].properties.durability === 21,
        "Initial browser save failed");
    const savedToken = remote.inventory.items[0].token;
    check(await savePlayerToDjango() !== null && remote.inventory.items.length === 1 &&
        remote.inventory.items[0].token === savedToken, "Repeated browser save duplicated equipment");
    dilapidatedSword.durability = 1;
    check(await restorePlayerFromDjango() === true && dilapidatedSword.durability === 21 &&
        equippedItems.length === 1, "Full browser load lost properties or duplicated equipment");
    check(browserSaveExtras.customQuest.completed && !Object.hasOwn(browserSaveExtras, "_browserUpdatedAt"),
        "Unknown save fields were lost or transport metadata leaked");
    remote.buildings = null;
    remote.playerStats.gold = 999;
    const gold = playerStats.gold;
    check(await restorePlayerFromDjango() === false && playerStats.gold === gold,
        "Invalid legacy fields partially changed live state");
    document.getElementById("result").textContent = `PASS: ${passed} browser inventory checks`;
} catch (error) {
    document.getElementById("result").textContent = `FAIL: ${error.stack}`;
}
})();
