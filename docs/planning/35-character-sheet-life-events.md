# Character sheet and Life Events pane — 2026-11-16

The character sheet hides Starting Resources and presents Body and Starting Attributes in collapsed sections by default. The birth creation and review flows still show starting resources.

The Character Sheet section is labeled “Attributes”; the inner stat fieldset has no duplicate legend. An information icon appears before “Baseline Condition”; its accessible tooltip contains the explanation about starting physical condition, hunger, fatigue, illness, and injuries.

The Character Sheet omits the birth-draft helper sentence “These are your confirmed birth attributes.” The lock/reroll instruction remains visible during editable birth creation.

The Body details omit Name and Gender because the name is already shown in the sheet heading. The heading displays the saved gender between the name and age state.

The Character Sheet does not repeat Hair color as its own row; the selected color is shown in the Hair length portrait. Hair Texture has an SVG swatch model for each texture, colored with the selected hair color, in both the Character Sheet and birth choices.

The first attribute row has no top separator; row separators begin after Luck.

In the active game, Options opens as its own right pane, replacing the currently visible pane. Its Close action restores the pane that was open immediately before Options. Landing and character-selection Options remain dropdown menus.

## Pane navigation

- The game tracks the pane that was active before opening the character sheet.
- Life Events opens as its own right pane and closes the sheet. Its Back button returns to the sheet.
- Toggling the character sheet from either the sheet or Life Events restores the prior pane. Opening the sheet again returns directly to the sheet.
- The left tool pane and visible right pane stretch to the same CSS Grid row height, including Life Events.
- The Character Sheet wrapper is a flex column whose bordered birth panel fills the wrapper; hidden panes are removed from the grid row.
- Life Events uses the same minimum viewport height as the crib pane.

## Event storage

- A `LifeEvent` belongs to a playthrough and stores its event type, text, and timestamp.
- Confirming a birth records: “Welcome into the world `<name>`! What will you become?”
- A migration adds that welcome event to existing confirmed births. The character roster response exposes events across the character's legacy; the console displays them in time order.
- Loading a birth record also ensures the welcome event exists. Opening the console fetches events by the selected roster character ID through an ownership-checked API, instead of relying on a session's active-character pointer or an older roster snapshot.
- Account deletion archives and restores life events with the rest of the playable story. Django admin exposes read-only event inspection.

## Verification

Backend tests cover birth event creation/idempotence, admin inspection, and account archive restoration. Browser coverage exercises collapsed sections, hidden resources, pane height, event text, Back navigation, and both character-sheet toggle paths. `legacy_game/` is unchanged.
