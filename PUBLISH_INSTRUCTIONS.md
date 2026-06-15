# Publishing CrossMEP (10 minutes total)

## A. GitHub (3 commands)
1. Create an empty repo named `crossmep` at https://github.com/new (public, NO readme/license — we have them).
2. In this folder:
   git init && git add -A && git commit -m "CrossMEP v3.1 - count-stratified MEP cross-section dataset"
   git branch -M main && git remote add origin https://github.com/<YOUR_USERNAME>/crossmep.git
   git push -u origin main
3. Tag the release: on GitHub -> Releases -> "Draft a new release" -> tag `v3.1.0`, title "v3.1 - count-stratified + custom generation". (Optionally also upload crossmep_release_v2.1.zip as an asset labeled "archived T1-T4 benchmark".)

## B. Zenodo DOI (5 minutes)
1. Log in at https://zenodo.org with your GitHub account.
2. Profile -> GitHub -> flip the toggle ON for `crossmep`.
3. Back on GitHub, publish the v3.1.0 release (step A3) — Zenodo archives it automatically and mints the DOI.
4. Copy the DOI badge from the Zenodo record page.

## C. Tell Claude the two strings
- https://github.com/<YOUR_USERNAME>/crossmep
- the DOI (10.5281/zenodo.XXXXXXX)
and the paper + CITATION.cff get patched and re-rendered in one pass.
