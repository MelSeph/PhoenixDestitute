# Orphaned character recovery — 2026-11-15

The user clarified that recovery should be an admin-level operation, so already-created characters can appear in another browser session. The local database inspection found two unrostered local Players with permanent birth records; neither was deleted. Because an unowned record cannot establish which new browser belongs to its creator, the backend does not expose a global orphan list to game clients or automatically attach all records.

## Recovery flow

1. A staff member opens **Players** in Django admin and selects exactly one intended orphaned player.
2. The **Issue one-use recovery code** action creates a cryptographically random code that expires after 24 hours. Issuing a new code revokes that player's other unredeemed codes. The raw code is shown once in the admin success message; only its SHA-256 digest is stored. The recovery-code model itself is read-only.
3. In the target browser, open **Recover a saved character** in the React character list and submit the code. The API adds the existing Player to that browser's `LocalCharacter` roster inside a transaction, consumes the code, and returns the updated roster. The player can then use Load. It does not create or copy a birth, life, save, inventory, or character record.

Invalid, expired, redeemed, account-owned, or already-rostered saves all return the same conflict response. Recovery codes are bearer credentials: anyone who obtains one before redemption can claim that particular save. Issuance and redemption are CSRF-protected; ordinary game requests cannot enumerate orphaned players. The action requires existing Django staff access and does not create or alter accounts/passwords.

## Implementation and verification

Migration 0019 adds only `CharacterRecoveryCode`; existing character rows are not modified by the migration. Tests cover admin issuance/plaintext-hash storage, cross-browser roster recovery, preserved birth identity/record, one-use enforcement, expiry, invalidation of an older code, and already-owned rejection. The React recovery form is covered by a browser test. No `legacy_game/` files are changed.

Before applying migration 0019 to the working SQLite database, make and integrity-check a backup, then compare the existing Players, BirthRecords, and LocalCharacters before/after. The migration does not itself assign any browser ownership. No commit/push unless separately requested.
