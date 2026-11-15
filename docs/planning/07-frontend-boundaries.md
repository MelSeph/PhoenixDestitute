# What remains in the frontend — provisional findings

Do not implement or redesign the frontend during planning.

- HTML layout, menus, text panels, input widgets: `legacy_game/index.html`.
- Browser CSS and normalization: `legacy_game/css/*.css`, `legacy_game/flow/normalize.css`.
- DOM value synchronization: `js/updateplayer.js`, `js/updateenemy.js`, `js/updateshop.js`, `js/updatebuildings.js`, `js/updatepotions.js`.
- Text/number display formatting: `js/textconversion.js`, `js/numberconversion.js`.
- Menu hide/show presentation: relevant portions of `js/open_and_close.js`.

**Unresolved:** `open_and_close.js` also has progression/unlock flags. A persisted unlock condition may belong to the backend even if its button visibility is frontend presentation. Likewise an input check that alters game state is a rule, not just presentation. Boundaries await discussion.
