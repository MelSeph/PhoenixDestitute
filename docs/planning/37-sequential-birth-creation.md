# Sequential birth creation — 2026-11-16

Birth creation presents Name first. Saving a nonempty name reveals Appearance; saving Appearance reveals Stat Allocation. Completed earlier sections remain editable as collapsed disclosures. The existing server identity endpoint stores both name and appearance; the interface separates when those values are entered and saved.

Stat locks retain accessible checkbox semantics but display lock/unlock icons without visible checkbox boxes or adjacent text. Saving the selected stat allocation submits the current locked-attribute set through the existing locks API and automatically opens the birth review. The review can be dismissed to return to the choices.
