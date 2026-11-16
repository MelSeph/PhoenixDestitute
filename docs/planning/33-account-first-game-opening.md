# Account-first opening and crib scene — 2026-11-15

The user requested an account-only landing page with Options, followed by account character selection/creation, then entry into the game after a character is created or loaded. A new confirmed newborn opens with the player waking in their crib.

## Screen flow

1. The landing screen shows account sign-in/registration and the appearance Options menu. It does not show the character roster or creation controls.
2. After authentication, the player sees their account character roster and an explicit Create a character action. Existing incomplete birth drafts resume through that action.
3. Loading a roster entry opens the game screen. Creating a character remains in the creation panel until birth confirmation; confirmation then opens the game screen.
4. Confirmed newborns see the crib opening and their saved birth details. Older characters open a generic return-to-story screen without being described as newborns. Choose another character returns to the account roster; sign-out returns to the landing screen.

## Implementation notes

- React `CharacterManager` controls landing, selection/creation, and game states from the authenticated account and selected character returned by Django.
- Appearance settings remain the landing-only Options menu.
- Birth confirmation now writes `character_screen="loaded"` together with the active player to the transactionally updated session and synchronizes Django's request-session cache. This lets a subsequent roster read identify the new character as ready for the game screen, including after refresh.
- No game actions, age progression, or new persistence schema are introduced. The crib screen is an opening presentation using the existing immutable birth payload.
- Account/game records and existing saves are not reset or converted. `legacy_game/` is unchanged.

## Verification

All **34 browser scenarios pass** across the complete run and isolated reruns, covering account-only landing, retrying a failed sign-in, hidden Options after sign-in, selecting/creating a character, crib entry after confirmation, returning to the game after loading, and account access after browser restart/sign-in. The React settings suite passes all **6 tests** and the production build succeeds. All **322 Django tests passed** in a full run; a later rerun had one unrelated Edge GPU/cache process crash in the pre-existing inventory JavaScript test, while the focused 30 account/birth tests passed. Django check and migration drift checks pass. `legacy_game/` is unchanged.

## Compact controls and section options — 2026-11-15

The player requested smaller, icon-based controls; one Sign in action plus Create new below the username/password fields; and an Options control at the upper right of account and character sections. Options appears in the sign-in, character-selection, and current game-entry sections; its gear icon keeps an accessible Options label. Character roster load/delete controls use compact icons with accessible names. Account actions remain labeled and include sign-in/add icons. The game-entry placement is being used as the closest current React section to the user's “Console” wording; the application does not currently name a component Console.

## Pane sizing and birth resource strip — 2026-11-16

For paired left/right game panes, both visible panes fill the same CSS Grid row, including when toggling from the crib to the character sheet. The Character Sheet's bordered panel fills its pane wrapper. Hidden panes do not affect the active row. Apply this rule to future paired-pane areas beginning with birth. Health, Mana, and Stamina gauges sit in a full-width strip below the masthead; their cards have compact spacing and centered text.

The next pane extension adds the collapsible character sheet sections and Life Events console described in [35-character-sheet-life-events.md](35-character-sheet-life-events.md). All panes use the visible-right-pane sizing rule above.
