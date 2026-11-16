# Age-stage character display — 2026-11-16

The Character Sheet and character-selection roster display identity and age together. Birth records expose their saved gender and existing `newborn` life stage through the roster API. Legacy characters without birth identity or age retain unknown/unavailable labels rather than receiving invented values.

The React age icon model covers baby, toddler, kid, young adult, adult, middle age, elderly, and deceased stages. The currently supported `newborn` stage uses the baby icon while retaining the newborn label in the character sheet. Age progression and deceased-state gameplay are not implemented by this display change.
