# CrossMEP in ten minutes: talk script

The script for `docs/CrossMEP_CIBW78_talk.pptx` (the same text is in each slide's
speaker notes). Audience: CIB W78, a mix of BIM and IT researchers and MEP and
construction practitioners. Every number on the slides comes from the released
data through `scripts/make_figures.py`.

Timing: 15 slides in about 9.5 minutes (slide 12 is a live demo of the Generator
Studio, with its screenshot as the fallback); five appendix slides for questions,
the first with two more studio sections.

**Before the talk.**
1. The QR codes on slides 14 and 15 and the closing link open
   github.com/lavinia-ped/CrossMEP_Dataset. The repository must be public and its
   default branch must hold this release; scan both codes from a phone that is
   not signed in to GitHub.
2. Slide 12's QR code opens the hosted Generator Studio: set its link sharing to
   public and check it from a phone that is not signed in.
3. Open the studio once with internet on the presenting laptop: the 3D view and
   the fonts load from CDNs (the drawing works offline).
4. Rehearse once with a timer; the marks in the headings assume about 145 words
   a minute and 30 s for the demo.

---

## 1. Title (0:00)

**Show:** *CrossMEP: A Tiered Synthetic Dataset of Multi-Trade MEP Cross-Sections*;
authors; a generated C8 context as title art.

**Say:** "Hello, I'm Lavinia Pedrollo from Stanford's Center for Integrated
Facility Engineering. This is CrossMEP, joint work with David Gvadzabia, Torben
Graeber and Martin Fischer: a dataset of the problems a support designer solves,
made for training and testing methods that design MEP supports."

## 2. Every pipe, duct and tray hangs from a support designed by hand (0:20)

**Show:** three figures (≈ 10,000 assemblies per hospital; 20 min – 2 h each; ≈ ¼
of MEP design effort), the route-to-section figure from the paper.

**Say:** "Every pipe, duct and tray in a building hangs from a support assembly:
anchors, rods, channel, clamps. On a 200,000 square-foot hospital that is on the
order of 10,000 assemblies, each taking 20 minutes to two hours by hand —
together roughly a quarter of the MEP design effort. These are practitioner
estimates. The work starts after coordination: at every hanger location the
designer takes the section across the run and designs a support for exactly
what passes through it. That section is the unit of work, and it is the unit of
our dataset."

## 3. There was no public dataset of support-design problems (1:00)

**Show:** scarcity, coverage, control; CrossMEP at a glance (7,000 contexts ·
31,484 elements · C1–C8 · 0 labels · traced · open).

**Say:** "Learning-based methods for this task need many such sections, and none
were public. Project models are proprietary, the open ones are not organised
around supports, and any one project covers one narrow slice. So we built
CrossMEP: 7,000 contexts with about 31,500 elements, stratified into eight tiers,
deliberately unlabeled, with every constant traced to its source or declared a
design choice, pipe gaps checked against open IFC buildings, and released openly
with the generator."

## 4. A context is the section at one hanger: the brief, not the answer (1:25)

**Show:** one C5 context with its table of fields.

**Say:** "Here is one context. It is a 2-D section at one support location. Each
element carries its kind, service and trade, its bare size, its insulation, its
load per metre and the span it was sized at — so the load at this support — and
its position along and out from the surface. Plus the surface itself: slab or
wall, substrate, thickness. What is not in it is the support: no channel, no
rods, no anchors, and no 'correct answer', because a feasible support depends on
the catalog you build from. The context is the brief; the assembly is the
answer."

## 5. How a context is generated: rules, not free randomness (2:10)

**Show:** six steps (tier, surface, services, rows, spacing, check) beside a
generated C7 context with its three rows and one sampled gap marked.

**Say:** "How is a context made? Not by free randomness: by rules you would
recognise. The tier fixes the number of elements. We pick the surface. We fill
the count with services the way trades actually run — hot and cold together,
flow and return together, conduits in groups. Bulky services go nearest the
slab: ducts, then containment, then pipes. Gaps between neighbours are drawn
from gaps measured on a built project, with a 25 millimetre minimum, plus a
small stagger within rows; on walls, electrical stays above water. Finally every
context is checked — every pair at least 25 millimetres clear — and it is
seeded: the same seed gives the same file, byte for byte."

## 6. Every constant is sourced or declared a choice; every load is computed (2:55)

**Show:** sources table (pipes, insulation, trays, ducts, conduits) and layout
conventions.

**Say:** "Every number in a context comes from a cited source or a declared
design choice. Pipe sizes and walls from EN
10220 and 10255, filled with water, at ASME B31.1 water-service spans.
Insulation from the German GEG for heated lines and a condensation-control
schedule for chilled water. Trays at IEC 61537 widths, loaded full. Ducts at the
EN preferred sizes with a manufacturer weight table. Conduits at IEC 61386 sizes
with 40 per cent cable fill. The loads are computed from these sources in the
code, and every constant is documented with its source and status. Things that
are choices — the trade mix, the tier composition — are labelled as design
choices, not presented as measurements."

## 7. The release: 7,000 contexts in four splits on disjoint seeds (3:40)

**Show:** splits table; elements by kind; pipes by nominal size.

**Say:** "The release has four splits on disjoint seeds: 5,000 contexts for
training, 500 for validation, 500 for test, and a 1,000-context benchmark with
125 per tier. 31,484 elements in total — mostly pipes, then conduits, trays and
ducts; pipe sizes from DN15 to DN100, mostly small bore, as in the measured
project. Four in five contexts hang from a ceiling, one in five from a wall, and
electrical containment is the largest trade by count. Everything is plain JSON
with a schema, metadata and a datasheet."

## 8. Eight difficulty tiers: tier Cn holds exactly n elements (4:15)

**Show:** one benchmark context per tier, C1 to C8, ceilings and walls.

**Say:** "This is what the data looks like: one benchmark context per tier. C1 is
a single element — the most common support in any building. By C8 you have
eight services on three rows. Within a tier everything else varies — kinds,
trades, surfaces and stacking — so the element count is the one controlled
difficulty axis. Note the walls: the section rotates, and electrical sits above
water."

## 9. Experiment 1, a design check: difficulty grows with the tier (4:45)

**Show:** per-tier boxes of the closest gap and the load (benchmark), with the
median of 2,000 freshly generated contexts per tier as diamonds; C6–C8 shaded
("two or three rows").

**Say:** "The first experiment is a design check, not a discovery: does
difficulty grow with the tier, as intended? The count is fixed by construction;
load and congestion follow from the rules, so this shows the dataset behaves as
designed. Load at the support rises at every step, from 0.1 to 1.7 kilonewtons.
The closest gap falls from 120 to about 62 millimetres, but widens again at C6,
where the generator starts stacking in two or three rows. So report methods tier
by tier."

**Numbers** (`verify/tier_trends.py`): rank correlation of tier with load
+0.56, with the closest gap -0.36; population median gap
C5 70 mm, C6 75 mm; elements per row (median) 5 at C5, 3 at C6.

## 10. Experiment 2, the real test: spacing in a building it never saw (5:20)

**Show:** left, gaps between side-by-side pipes measured on the clinic vs
generated; right, Wasserstein-1 distances with 95 % intervals between the
generator and three real models, and between the real models themselves.

**Say:** "The second experiment is the one the generator could fail: is the
spacing realistic in a building it never saw? The gap distribution was fitted on
a residential duplex from buildingSMART. We held out a second open building, a
medical-dental clinic, which is a real building, cut it into sections every 250
millimetres, the way a context is defined, and measured the gap between pipes
running side by side. On the left, the clinic: the generated gaps are close to
the measured ones, though not identical. On the right, the distances: generated
to clinic 28 millimetres. That is above the 8 a perfect generator would show, so
not a perfect match, but about as close as the duplex's own two models are to
each other. A fixed gap at the 25 millimetre minimum would be about 190
millimetres off."

**Numbers** (`verify/compare_sections.py`, pairs weighted by shared length):
generated ↔ clinic 28 mm (95 % CI 16–44; noise floor 8); duplex MEP ↔ duplex
Plumbing 26; generated ↔ duplex 70 / 85; clinic ↔ duplex 71 / 85;
797 measured pipe pairs on the clinic, 74 and 41 on the duplex. Across 11 settings
of the cut, generated ↔ clinic stays at 27–36 mm.

## 11. Experiment 3, a use: what must a clamp catalog cover? (6:05)

**Show:** benchmark pipes by nominal size with the attachable ones in blue (only
DN40); the best share of pipes any k clamp sizes could attach (43 % with two,
80 % with six, 100 % with twelve); 11.6 % (95 % CI 10.1–13.0); 0 of 1,971 trays,
ducts and conduits.

**Say:** "The third is a use of the dataset, not a test of it: what must a
catalog of clamps cover? Take the paper's two-size catalog as an illustration. It
attaches 11.6 per cent of the pipes, interval 10 to 13, all of one size, DN40;
load never binds, and trays, ducts and conduits are not covered at all. On the
right is what the dataset asks of any catalog: two well-placed sizes attach 43
per cent, six 80, twelve every pipe. So 'what should the catalog contain' becomes
a measurement."

## 12. See it: set the parameters, get the support designer's brief (6:40)

**Show:** the Generator Studio (live; the slide is its screenshot): the
parameters bar, the section drawn as an A4 support detail and the same run in
3D; QR code to the hosted studio.

**Say:** "Here is what that means in practice. In the studio I choose what
crosses the hanger: a tier, or an exact mix, and the seed. Out comes the section
a support designer receives, drawn the way an engineer would issue it: every
service at true size, its level below the slab, its load at the support, the
closest clear gap; and the same run in 3D. Every section is a stored output of
the released generator, with the Python call that reproduces it."

**Do (about 30 s):** switch to the studio; click C3, then *Generate another*
twice; then *Exact mix*, add a duct. If the demo fails, stay on the slide;
appendix slide 16 shows two more sections. (See "Before the talk" above.)

## 13. Using CrossMEP: train, evaluate, report (7:45)

**Show:** six lines of Python, including `score` and `compare`; the interactive
gallery; train, evaluate, report.

**Say:** "Using it takes a few lines: load a split with the Python standard
library, filter by composition, or generate your own mix with the same rules.
Because there are no labels, the same files serve reinforcement learning,
constraint-programming baselines and human benchmarking, and we ship the
scoring: train on the generator, from C1 up to C8; evaluate on the benchmark,
the same 125 contexts per tier for every method; report per tier with 95 per
cent intervals and paired tests."

## 14. Scope, and what comes next (8:20)

**Show:** scope; next steps; the request to practitioners with the QR code.

**Say:** "Its scope: one section at one support — routing, branches and spacing
are outside it, although the span is recorded so a method can vary it. Realism
is checked on sections of two open buildings; congested racks rest on practice
and standards. The trade mix is a design choice, and the data is not for
structural design. Next: a public checker for support designs, with best-known
costs, so methods can be compared on the answer and not only on the brief; the
catalog as an input, so a method is tested on catalogs it has never seen; and a
real test set from commercial projects, with supports designed by engineers —
which is where we would value your eye."

## 15. CrossMEP: the brief, not the answer (9:10)

**Say:** "CrossMEP is the brief, not the answer: 7,000 support-design problems,
every constant traced to its source or declared a design choice, pipe gaps
checked against two open buildings, and open.
The QR code takes you to the data, the code, the gallery and the studio.
Thank you."

**Appendix slides:** two more sections from the Generator Studio (the demo
fallback); per-tier statistics of the benchmark split; the realism
check in detail (samples, both weightings, noise floors, sensitivity to the cut);
the catalog stress test with error bars (per tier, per split, sensitivity to the
diameter rule and bin tolerance); one stored record in JSON.

---

## Questions a construction audience may ask

**"Isn't Experiment 1 circular? The generator makes higher tiers heavier."**
Yes, and the slide says so: it is a design check that the dataset behaves as
intended, which a benchmark needs before anyone reports per tier. The test the
generator could fail is Experiment 2.

**"Was the generator tuned to the clinic?"** No. The gap distribution was fitted
in June 2026 on the duplex; the clinic was measured afterwards and never used for
fitting. Against the duplex the generator is 70–85 mm away, about as far as the
clinic is from the duplex.

**"Where do the numbers come from?"** Sizes, spans, weights and insulation from
published standards (each constant cites its source in the code and the
datasheet); the spacing from the buildingSMART sample buildings (CC BY 4.0). The
clamp catalog of Experiment 3 is the illustrative two-size family printed in the
paper.

**"Why 25 mm as the minimum gap? We use more."** It is the published pipe-rack
minimum and it is a *floor*, not a typical value: the sampled gaps have a
median of 150 mm and quartiles of 85–263 mm, taken from measurement. If your
practice uses 50 mm, it is one documented constant, and the fit can be redone
above 50 mm.

**"How exactly was the spacing measured?"** With IfcOpenShell: every flow
segment of the model is meshed; horizontal runs are cut by sections every
250 mm; runs whose centres lie within 400 mm of height form a row; the clear gap
between neighbours in a row is measured between bare pipe surfaces (the
measurement meshes flow segments only, so insulation is not included). Each pair of pipes counts by the
length over which they run side by side, so the distribution is what a designer
meets at a random hanger. The result barely moves with these settings
(27–36 mm across 11 variations).

**"The paper reports 41 mm against the duplex. Why different numbers?"** The
paper compared with gaps measured in June 2026 by grouping parallel runs. We have
since measured on sections — the definition of a context — and added a second,
real building. The section-based numbers are on the slide; the repository keeps
both and explains the difference (`verify/VERIFICATION.md`). The June sample
also cannot be reproduced exactly: re-running the documented grouping procedure
gives a different sample, so the section measurement is now the verification of
record.

**"Why is the duplex further away than the clinic?"** Partly the duplex, partly
the generator. The duplex is a small residential model (74 and 41 pipe pairs, so
its intervals are wide); a quarter of its pipe gaps are below 25 mm and many sit
near 470 mm. The generator draws no gap below its 25 mm minimum, and it applies
the fitted gap between insulation surfaces, so its bare-pipe gaps run wider.
With two real buildings we cannot say which one is typical; what the slide shows
is that the generator is as close to a building it never saw as the duplex's two
models are to each other.

**"A quarter of the duplex's gaps are under 25 mm. Why does the generator never
produce them?"** The generator treats 25 mm as a design minimum, so it reproduces
the spacing of separately supported runs, not touching ones; runs on a common
clamp or modelling overlaps are likely sources of the very small gaps. In the
clinic only 2 % of pipe gaps are below 25 mm.

**"Why does the closest gap widen again at C6?"** From six elements the generator
starts stacking in two or three rows (C5: about half the contexts on one row; C6:
almost none), so each row holds fewer elements and the tightest pair is less
tight. The tier controls the element count, not congestion at every step; that
is why results should be reported per tier.

**"How should results on CrossMEP be reported?"** Per tier, with intervals, on
the benchmark split, which no method trains on: `python -m crossmep evaluate
results.json` takes one outcome per context (feasible or not, or a cost) and
prints per-tier rates with 95 % intervals, the tier-balanced mean, a mean weighted
to a building's mix if given, and a paired test against another method.

**"What is the spike at 500 mm?"** The generator caps a sampled gap at 500 mm,
a design parameter; everything the lognormal would place beyond lands there.

**"Those spans look short / long."** They are ASME B31.1 Table 121.5
water-service points (2.1 / 3.0 / 3.7 / 4.3 m for NPS 1 / 2 / 3 / 4), assigned
by a floor rule with no interpolation; trays 2.0 m, ducts 2.4 m, conduits 2.0 m.
Every element records its span and load per metre, so a method can treat the
span as a variable.

**"Insulation: chilled at 30/50 mm but cold water bare?"** Heated lines follow
GEG Anlage 8; chilled water follows a 30/50 mm condensation-control schedule;
domestic cold and sprinkler are modelled bare (thin anti-sweat sleeves are
geometrically negligible). The choice is documented.

**"Why are a hot and a cold pipe of one pair at different heights?"** Stagger is
drawn per element, calibrated to the elevation spread measured across a bundle.
A bank on one trapeze would be co-planar; per-bank stagger is a natural next
step.

**"A trapeze is deeper than 120 mm."** 120 mm is the clear gap between the
elements of two rows, not the trapeze depth; the first row sits 90 mm from the
slab. Both are labelled design parameters.

**"Which pipe materials and substrates are in the public files?"** Carbon-steel
pipe to EN 10255, DN15–100, on concrete slabs and walls (C25/C30, 150–300 mm).
Other materials and substrates are the next extension of the public element
library.

**"Where are seismic bracing, thermal movement and anchor capacity?"** Outside
the context by design: they belong to the support solution and the structure,
which the dataset deliberately does not describe.

**"How do I use this if I am not training a model?"** As a test set for any
placement tool or rule engine: 1,000 stratified scenes of known difficulty, a
filter to pull exactly the composition you want (for example three pipes and one
tray on a wall), and a generator for your own mix.

**"Can I run the comparison on my own project?"** Yes: `verify/measure_ifc.py`
cuts any IFC model into sections and measures the gaps; `verify/compare_sections.py`
gives the same distances and intervals for your building.

**"What catalog is that? Is it a manufacturer's range?"** It is the
illustrative two-size family printed in the paper (48–54 mm up to 2.5 kN;
108–114 mm up to 4.0 kN); no product catalog ships with the dataset. It is
deliberately small: a stress test, not a full range. The conclusion does not
depend on it: the right-hand chart asks the same question of any catalog, namely
how many sizes, and where, this dataset needs, and `verify/catalog_stress.py
--bins` runs it on yours.

**"How certain is 11.6 %?"** The 95 % interval over contexts is 10.1–13.0
(cluster bootstrap: the elements of one context are correlated); over 16,000
freshly generated contexts it is 10.8 % (10.5–11.2), and the eight tiers lie
between 10.4 and 11.4 %. The value is sensitive to one edge: DN100
(114.3 mm) lies 0.3 mm above the 108–114 mm bin, so widening the bins by 0.5 mm
gives 12.9 %. What does not change is that only DN40 is attached.

**"Is that coverage what a designer could install?"** No, it is an upper bound:
only size and capacity are tested. Clearance to neighbours, the insert on cold
lines, anchors and rods are not modelled.

**"The paper says 11.5 %, the slide 11.6 %."** The paper's figure was computed
on an internal build with a larger pipe library; the public files give 11.6 %
and 1,971 trays, ducts and conduits (paper: 1,832). `RESULTS.md` lists every
value for the public files and the tests pin them.
