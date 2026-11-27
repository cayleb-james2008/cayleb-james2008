# Copy rules (owner-approved, frozen)

Cayleb approved this copy on 27 Nov 2026. The README's About section is his own spoken answers, with only the grammar fixed, laid out as question and answer.

**For any agent or sync job (portfolio sync, release sync, swarm):**

1. **Don't rewrite prose.** The block between `FROZEN-COPY-START` and `FROZEN-COPY-END` in `README.md` is frozen. So are these fields in `data/profile.json`: `open_to`, `intro`, `work`, `repos`, `repo_order`, `now`, `stack`, `stack_groups`, `sections`. Only Cayleb changes them.
2. **What you may update:** the numbers text the profile-graphics workflow writes, and links outside the frozen block.
3. **What you may not add:**
   - feature lists, taglines or blurbs for OpenRO, Fleet or OpenBell (they are a name and a link)
   - version pins in prose
   - test counts or benchmark numbers
4. **Ergon** is the only project with descriptive copy, and that copy is Cayleb's own words.
5. **Projects Cayleb removed never come back.** The list is in `scripts/copy_guard.py`. No finance-engine wording either.
6. **Releases don't need a profile commit.**

`scripts/copy_guard.py` runs first in the profile-graphics workflow and inside `scripts/static_assets.py`, and fails if any of this is broken. Don't edit the guard or its hashes to get past it. Ask Cayleb.
