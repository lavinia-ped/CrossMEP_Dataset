# CrossMEP in ten minutes: talk script

The script for `docs/CrossMEP_CIBW78_talk.pptx` (the same text is in each slide's
speaker notes). Audience: CIB W78, a mix of BIM and IT researchers and MEP and
construction practitioners. Every number on the slides comes from the released
data through `scripts/make_figures.py`.

Timing: 14 slides in about 9.5 minutes; four appendix slides for questions.

---

## 1. Title (0:00)

**Show:** *CrossMEP: A Tiered Synthetic Dataset of Multi-Trade MEP Cross-Sections*;
authors; a generated C8 context as title art.

**Say:** "Hello, I'm Lavinia Pedrollo from Stanford's Center for Integrated
Facility Engineering. This is CrossMEP, joint work with David Gvadzabia, Torben
Graeber and Martin Fischer: a dataset of the problems a support designer solves,
made for training and testing methods that design MEP supports."

## 2. Every pipe, duct and tray hangs from a support designed by hand (0:15)

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
deliberately unlabeled, with every constant traced to its source, checked
against open IFC buildings, and released openly with the generator."

## 4. A context is the section at one hanger: the brief, not the answer (1:40)

**Show:** one C5 context with its table of fields.

**Say:** "Here is one context. It is a 2-D section at one support location. Each
element carries its kind, service and trade, its bare size, its insulation, its
load per metre and the span it was sized at — so the load at this support — and
its position along and out from the surface. Plus the surface itself: slab or
wall, substrate, thickness. What is not in it is the support: no channel, no
rods, no anchors, and no 'correct answer', because a feasible support depends on
the catalog you build from. The context is the brief; the assembly is the
answer."

## 5. How a context is generated: rules, not free randomness (2:30)

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

## 6. Every number has a source, and every load is computed from it (3:20)

**Show:** sources table (pipes, insulation, trays, ducts, conduits) and layout
conventions.

**Say:** "Every number in a context has a source. Pipe sizes and walls from EN
10220 and 10255, filled with water, at ASME B31.1 water-service spans.
Insulation from the German GEG for heated lines and a condensation-control
schedule for chilled water. Trays at IEC 61537 widths, loaded full. Ducts at the
EN preferred sizes with a manufacturer weight table. Conduits at IEC 61386 sizes
with 40 per cent cable fill. The loads are computed from these sources in the
code, and every constant is documented with its source and status. Things that
are choices — the trade mix, the tier composition — are labelled as design
choices, not presented as measurements."

## 7. The release: 7,000 contexts in four splits on disjoint seeds (4:05)

**Show:** splits table; elements by kind; pipes by nominal size.

**Say:** "The release has four splits on disjoint seeds: 5,000 contexts for
training, 500 for validation, 500 for test, and a 1,000-context benchmark with
125 per tier. 31,484 elements in total — mostly pipes, then conduits, trays and
ducts; pipe sizes from DN15 to DN100, mostly small bore, as in the measured
project. Four in five contexts hang from a ceiling, one in five from a wall, and
electrical containment is the largest trade by count. Everything is plain JSON
with a schema, metadata and a datasheet."

## 8. Eight difficulty tiers: tier Cn holds exactly n elements (4:45)

**Show:** one benchmark context per tier, C1 to C8, ceilings and walls.

**Say:** "This is what the data looks like: one benchmark context per tier. C1 is
a single element — the most common support in any building. By C8 you have
eight services on three rows. Within a tier everything else varies — kinds,
trades, surfaces and stacking — so the element count is the one controlled
difficulty axis. Note the walls: the section rotates, and electrical sits above
water."

## 9. Experiment 1: higher tiers are heavier and, on average, tighter (5:20)

**Show:** per-tier boxes of the closest gap and the load (benchmark), with the
median of 2,000 freshly generated contexts per tier as diamonds; C6–C8 shaded
("two or three rows").

**Say:** "First experiment: are the tiers ordered by difficulty? The count is
exact by construction, so we look at congestion and load. The boxes are the
benchmark; the diamonds are medians over 2,000 freshly generated contexts per
tier — the generator itself, not sampling noise. Load at the support rises at
every step, from 0.1 to 1.7 kilonewtons. Congestion rises overall — the closest
gap falls from 120 to about 62 millimetres — but at C6 the generator starts
stacking in two or three rows, so each row holds fewer elements and the gap
widens again. So the tier fixes the count; congestion and load follow on
average, and methods should be compared tier by tier."

**Numbers** (`verify/tier_trends.py`): rank correlation of tier with load
+0.56, with the closest gap -0.36; population median gap
C5 70 mm, C6 75 mm; elements per row (median) 5 at C5, 3 at C6.

## 10. Experiment 2: generated spacing matches a building it never saw (6:15)

**Show:** left, gaps between side-by-side pipes measured on the clinic vs
generated; right, Wasserstein-1 distances with 95 % intervals between the
generator and three real models, and between the real models themselves.

**Say:** "Second experiment: is the spacing realistic? We took two open buildings
from buildingSMART — a residential duplex and a medical-dental clinic, which is a
real building — and cut sections every 250 millimetres, the way a context is
defined, measuring the gap between pipes running side by side. On the left, the
clinic, which the generator never saw: the generated gaps follow the measured
ones closely. On the right, the distances. Generated to clinic: 28 millimetres,
about as close as the duplex's own two models are to each other. The small
duplex is as far from the generator as it is from the clinic. A fixed modular gap
would be about 190 millimetres off."

**Numbers** (`verify/compare_sections.py`, pairs weighted by shared length):
generated ↔ clinic 28 mm (95 % CI 16–44; noise floor 8); duplex MEP ↔ duplex
Plumbing 26; generated ↔ duplex 70 / 85; clinic ↔ duplex 71 / 85;
797 measured pipe pairs on the clinic, 74 and 41 on the duplex. Across 11 settings
of the cut, generated ↔ clinic stays at 27–36 mm.

## 11. Experiment 3: a two-size clamp catalog attaches 1 pipe in 9 (7:05)

**Show:** benchmark pipes by nominal size with the attachable ones in blue (only
DN40); the best share of pipes any k clamp sizes could attach (43 % with two,
80 % with six, 100 % with twelve); 11.6 % (95 % CI 10.1–13.0); 0 of 1,971 trays,
ducts and conduits.

**Say:** "The third experiment connects the dataset to the task it serves: what
must a catalog of clamps cover? Take the two-size catalog from the paper as an
illustration. It attaches 11.6 per cent of the pipes — 293 of 2,529, interval 10
to 13 — and every one is a single size, DN40. Load never binds: the heaviest pipe
is 0.88 kilonewtons against a 2.5 kilonewton clamp. Trays, ducts and conduits are
not covered at all. On the right is what the dataset asks of any catalog: two
sizes placed where the pipes are would attach 43 per cent, six sizes 80, and
twelve sizes every pipe. So 'what should the catalog contain' becomes a
measurement."

## 12. Using CrossMEP: train, evaluate, report (7:50)

**Show:** six lines of Python, including `score` and `compare`; the interactive
gallery; train, evaluate, report.

**Say:** "Using it takes a few lines. Load a split — only the Python standard
library is needed — filter by composition, or generate your own mix with the
same rules; there is an interactive gallery for inspection. Because there are no
labels, the same files serve reinforcement learning, constraint-programming
baselines and human benchmarking, and we ship the scoring too: train on the
generator with as many seeds as you like, from C1 up to C8; evaluate on the
benchmark, the same 125 contexts per tier for every method; and report per tier
with 95 per cent intervals and paired tests, so two methods can be compared
fairly."

## 13. Scope, and what comes next (8:40)

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

## 14. CrossMEP: the brief, not the answer (9:10)

**Say:** "CrossMEP is the brief, not the answer: 7,000 support-design problems,
every number traced to its source, checked against two open buildings, and open.
The QR code takes you to the data, the code and the gallery. Thank you."

**Appendix slides:** per-tier statistics of the benchmark split; the realism
check in detail (samples, both weightings, noise floors, sensitivity to the cut);
the catalog stress test with error bars (per tier, per split, sensitivity to the
diameter rule and bin tolerance); one stored record in JSON.

---

## Questions a construction audience may ask

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
both and explains the difference (`verify/VERIFICATION.md`).

**"Why is the duplex further away than the clinic?"** It is a small residential
model (74 and 41 pipe pairs) with its own habits: a quarter of its pipe gaps
are below 25 mm and many sit near 470 mm. It is as far from the clinic as from the
generator, so it is the duplex that is unusual, and its intervals are wide.

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

**"What catalog is that? Is it a manufacturer's range?"** It is the two-size clamp
family the paper describes as the safe-to-share catalog of the companion SSA
codebase (48–54 mm up to 2.5 kN; 108–114 mm up to 4.0 kN), reflecting real
configurations. It is deliberately small: a stress test, not a full range. The
conclusion does not depend on it: the right-hand chart asks the same question of
any catalog, namely how many sizes, and where, this dataset needs.

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
