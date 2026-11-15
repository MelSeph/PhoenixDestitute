# Birth-first character creation — design discussion

## User-directed change

The user wants to completely redesign the opening: begin with the character being born for the first time, choose the character's looks, and start gameplay attributes at random values between 1 and 5. The requested sheet includes ID, Name, Luck, Strength (user wrote “Strenght”), Defense, Agility, social appeal/likeability, Intelligence, Health, Mana, and Condition. The user also asked for any relevant attributes previously discussed.

The user first changed Health/Mana to independent 10–35 birth rolls and approved separate current/maximum pools starting full. **The independent rolls were subsequently superseded**: Health derives from Strength, Mana from Intelligence, and Stamina from Endurance. The user approved **×10 for all three maximums**, giving birth maxima of 10–50 from parent attributes of 1–5, and confirmed **all three current pools begin full**, including Stamina. Later growth/refill/regeneration behavior remains open. These are birth ranges, not agreed lifelong caps.

The user subsequently added **player-chosen gender** to creation. Available choices, custom entries, pronouns, and any gameplay effects have not been defined; do not infer them or copy legacy gender bonuses.

The user defined **Condition as all of the proposed physical factors**: constitution/physical fitness together with current wellbeing such as hunger, fatigue, illness, and injuries. It is not limited to just constitution or just transient status. The user approved a **baseline/current split**: baseline Condition initially rolls 1–5, while current Condition is calculated from the baseline and present wellbeing. Underlying states are tracked separately to explain changes. Individual status values/scales, current-condition range, combining formula, and long-term baseline growth remain undecided.

The user approved **Endurance as a 1–5 birth attribute for sustained exertion** and **Stamina as a distinct current/maximum energy pool**, with Condition describing overall wellbeing and affecting performance. From newborn through adulthood, Stamina measures how much physical, mental, or other training the character can do before exhaustion requires rest before further activity. It is a shared training budget, not merely a combat/physical-action resource. Training costs **vary by activity and intensity and depend on the associated stat**. The direction/formula of that dependency is not chosen. Maximum Stamina is Endurance × 10 and begins full at birth; costs, exhaustion threshold, and recovery timing remain open. Individual activities, age progression, and available actions while exhausted still need design.

Agreed initial resource mapping:

- Maximum Health = Strength × 10.
- Maximum Mana = Intelligence × 10.
- Maximum Stamina = Endurance × 10.

Each parent birth attribute starts at 1–5. The approved ×10 gives starting maxima of 10–50, replacing independent 10–35 rolls. No offset, lifetime clamp, or stat-growth refill rule has been adopted. Future tuning of the constants would require a deliberate balance change.

## Creation rerolls and locks

The user requested **unlimited rerolls during character creation** and **up to three locked stats that persist across rerolls**, so players can shape their starting build. This replaces the proposal to allow only one pre-confirmation set of rolls.

- Locks apply to the eight agreed rolled base attributes: Luck, Strength, Defense, Agility, social Likeability, Intelligence, Endurance, and baseline Condition.
- Locked values persist unchanged; unlocked values reroll within the agreed 1–5 birth range.
- Maximum Health/Mana/Stamina remain derived from Strength/Intelligence/Endurance ×10, not independently rolled or separately locked. Locking a parent therefore preserves its derived capacity.
- Rerolling is a creation-draft action, not a consequence of refresh/load. Phase 2O implements independent uniform server rolls and revision-based draft retry protection. Final birth confirmation is not implemented yet and must eventually freeze/copy the selected values into permanent character/life state.
- The user confirmed players may **freely unlock and switch locks before confirmation**, with no more than three active locks at a time. No permanent-lock restriction, reroll currency, or attempt limit is imposed.

The requested sexual-appeal category must be adult-only and unscored during childhood. It is separate from nonsexual appearance and social likeability. Adult initialization/activation remains to be designed; no newborn/child sexual-appeal rating is planned.

The user clarified that appearance should accumulate the effects of life experiences from birth, with the attraction category becoming relevant later. Track early-life development as **nonsexual appearance/history and social impressions**. Sexual attraction must remain inactive for under-18 characters; it may become an adult-only metric from age 18. The user's proposed teenage activation has not been adopted for younger teens. How adult attraction derives from appearance/history remains undefined.

This is a design change, not authorization to wipe existing characters/saves or silently import legacy class/gender stat adjustments. The previous question about choosing a class was not answered by adopting a class system. Equipment work can remain at its current delivered foundation while character creation becomes the focus.

## Evidence from the existing project

- `life_foundation.create_local_player` atomically creates Player, Legacy, playable Character, and initial Playthrough.
- The current creation API always names the local Player/Character “Adventurer”; it has no appearance selection or rolled birth attributes.
- Character currently stores name, kind, and timestamp, not age, looks, or character stats. Existing Player level/experience/gold and legacy JSON are compatibility state, not the adopted new birth-stat schema.
- Earlier candidate planning and legacy code mention **Endurance and Stamina**. Legacy battle initialization uses Endurance as stamina capacity. Those observations do not require carrying the old formula into the redesign.
- Craft/repair mastery and past-life learning have been discussed separately. They are progression systems, not automatically additional 1–5 birth rolls. Equipment durability/thermal ratings likewise belong to equipment, not the birth attribute list.

## Recommendations awaiting agreement

- Treat ID and Name as identity fields rather than 1–5 rolls: server-generated Character identity and player-chosen name.
- Record birth/age-zero as the opening life stage; world calendar/date and age progression are still undefined.
- The approved Phase 2O implementation generates independent uniform integer rolls server-side, with unlimited explicit draft rerolls and up to three freely switchable locks. Refresh/create retries preserve rolls, and stale mutation revisions fail before further random generation. Later confirmation, growth, and life-transition behavior still need design.
- Endurance and a separate Stamina pool are agreed; its maximum is Endurance × 10 and its birth current amount equals that maximum.
- Health/Mana current/maximum separation and full starting pools are agreed; their capacities are now Strength × 10 and Intelligence × 10 rather than independent rolls. Later growth/refill behavior, regeneration, and resource-loss formulas remain open.
- Keep the existing life identity structure and preserve old saves. Exact model changes, migration/adoption, API replacement/compatibility, and frontend scope require a concrete implementation plan before code changes.

## Next questions

1. Define the agreed Condition split's individual status values, combining formula, current-condition range, and possible overlap with Endurance. Baseline Condition initially rolls 1–5; current Condition derives from baseline and wellbeing rather than being an independent reroll.
2. Define permanent character/life stat storage and confirmation behavior for the agreed eight rolled attributes and derived resources. Adult-only attraction remains separate from newborn creation.
3. Define appearance and gender choices, pronouns, cosmetic/mechanical implications, naming, and age progression. Appearance/history can develop from birth; adult sexual attraction cannot activate before 18.
4. Define initial creation versus later Regression/New Life stats and appearance without inventing reset/reroll behavior.
5. Define variable training-session cost formulas using activity, intensity, and associated stats, plus exhaustion gating and rest/recovery. All physical, mental, and other training draws on Stamina from infancy through adulthood; individual activities and age progression remain open.

Phase 2O now implements the stat-selection draft portion of this design; see [23-birth-stat-drafts.md](23-birth-stat-drafts.md). It creates no born characters and does not implement identity/gender/looks, final birth confirmation, current Condition, or training. No frontend files or existing actor/save data were changed.
