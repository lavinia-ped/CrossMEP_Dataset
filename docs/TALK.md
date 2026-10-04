# CrossMEP in ten minutes: talk script

The script for `docs/CrossMEP_CIBW78_talk.pptx` (the same text is in each slide's
speaker notes). Audience: CIB W78, a mix of BIM and IT researchers and MEP and
construction practitioners. Every number on the slides comes from the released
data through `scripts/make_figures.py`.

Timing: 14 slides in about 9.5 minutes; two appendix slides for questions.

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
against an open IFC project, and released openly with the generator."

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

## 9. Experiment 1: as the count rises, scenes get tighter and heavier (5:20)

**Show:** box plots of minimum clear gap and total load per tier.

**Say:** "First experiment: are the tiers actually ordered? The element count is
exact by construction, so we look at congestion. The median closest gap between
elements falls from 120 mm at C2 to about 60 mm at C8, and the median load at
the support rises from 0.1 to 1.7 kilonewtons. The trend is near-monotone — with
125 contexts per tier, neighbouring tiers can swap — so difficulty is carried
jointly by count, congestion and load, with count as the controlled axis."

## 10. Experiment 2: generated spacing follows a built project (6:15)

**Show:** measured vs generated gap distributions with the fitted lognormal and
the Wasserstein-1 distances.

**Say:** "Second experiment: is the spacing realistic? We parsed two discipline
models of the open buildingSMART Duplex Apartment with IfcOpenShell and measured
the gaps between parallel runs. They are irregular, not modular — the median is
about 108 mm. The generator samples a lognormal fitted to those gaps. The
distance between generated and measured distributions is 41 mm between
insulation surfaces and 68 mm between pipe surfaces; the building's own two
discipline models are 50 mm apart, and a fixed modular gap would be 139 mm away.
So the generated spacing sits in the range of the variation between two real
models of one building."

## 11. Experiment 3: a two-bin clamp catalog covers 1 pipe in 9 (7:05)

**Show:** coverage per tier; 11.6 %; 0 of 1,971 trays, ducts and conduits.

**Say:** "The third experiment connects the dataset to the task it serves. We
take a released two-bin clamp catalog and ask which elements it can attach.
11.6 per cent of pipes, roughly uniform across tiers, and none of the trays,
ducts and conduits. Load never binds; diameter and kind do. So the dataset turns
'generalise the catalog' into a measured requirement: small-bore clamps first,
then tray, duct and conduit attachments."

## 12. Using CrossMEP: load, filter, generate, inspect (7:50)

**Show:** six lines of Python; the interactive gallery; three uses (curriculum,
stratified evaluation, probes).

**Say:** "Using it takes a few lines. Load a split — the loader needs only the
Python standard library — filter by composition, test your own catalog against
the benchmark, or generate your own mix with the same rules. There is an
interactive gallery for inspection. And because there are no labels, the same
files serve reinforcement learning, constraint-programming baselines and human
benchmarking: a curriculum over the tiers, per-tier evaluation, and held-out
seeds and custom compositions as probes."

## 13. Scope, and what comes next (8:40)

**Show:** scope; next steps; the request to practitioners with the QR code.

**Say:** "Its scope: one section at one support — routing, branches and spacing
are outside it, although the span is recorded so a method can vary it. Realism
is checked on one open residential project; congested racks rest on practice
and standards. The trade mix is a design choice, and the data is not for
structural design. Next: measuring per-tier feasibility collapse in a
multi-element synthesis environment, verification on commercial corridor
models, and an expert plausibility review — which is where we would value your
eye."

## 14. CrossMEP: the brief, not the answer (9:10)

**Say:** "CrossMEP is the brief, not the answer: 7,000 support-design problems,
every number traced to its source, checked against a built project, and open.
The QR code takes you to the data, the code and the gallery. Thank you."

**Appendix slides:** per-tier statistics of the benchmark split; one stored
record in JSON.

---

## Questions a construction audience may ask

**"Why 25 mm as the minimum gap? We use more."** It is the published pipe-rack
minimum and it is a *floor*, not a typical value: the sampled gaps have a
median of 150 mm and quartiles of 85–263 mm, taken from measurement. If your
practice uses 50 mm, it is one documented constant, and the fit can be redone
above 50 mm.

**"Why two distances, 41 and 68 mm?"** The measurement records gaps between pipe
surfaces (it meshes the flow segments); CrossMEP elements also carry
insulation. Between insulation surfaces the generated gaps are 41 mm from the
measured ones, between pipe surfaces 68 mm; the building's own two discipline
models are 50 mm apart, and a fixed modular gap is 139 mm away.

**"A quarter of the measured gaps are under 25 mm. Why does the generator never
produce them?"** The generator treats 25 mm as a design minimum and fits the
distribution above it (n = 73 measured gaps), so it reproduces the spacing of
separately supported runs, not touching ones. Runs on a common clamp or
modelling overlaps in the IFC are likely sources of the very small gaps.

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
and `verify/compare_gaps.py` take any IFC model that exports element sizes and
give the same statistics and distances for your building.
