# CrossMEP in ten minutes: talk script

The script for `docs/CrossMEP_CIBW78_talk.pptx` (the same text is in each slide's
speaker notes). Audience: CIB W78, a mix of BIM and IT researchers and MEP and
construction practitioners. Every number on the slides comes from the released
data through `scripts/make_figures.py`.

Timing: 16 slides in about 9.5 minutes of speech at an easy pace (about 145 words a minute; slide 13 is a demo of the
Generator Studio, with its screenshot as the fallback); five appendix slides for questions,
the first with two more studio sections.

**Before the talk.**
1. The QR codes on slides 15 and 16 and the closing link open
   github.com/lavinia-ped/CrossMEP_Dataset. The repository must be public and its
   default branch must hold this release; scan both codes from a phone that is
   not signed in to GitHub.
2. Slide 13's QR code opens the hosted Generator Studio: set its link sharing to
   public and check it from a phone that is not signed in.
3. Open the studio once with internet on the presenting laptop: the 3D view and
   the fonts load from CDNs (the drawing works offline).
4. Rehearse once with a timer; the marks in the headings assume about 145 words
   a minute and 35 s for the demo on slide 13.

---

## 1. Title (0:00)

**Show:** *CrossMEP: A Tiered Synthetic Dataset of Multi-Trade MEP Cross-Sections*;
authors; a generated C8 context as title art.

**Say:** "Hello everyone, I'm Lavinia Pedrollo, from Stanford. Every pipe, duct and cable
tray in a building hangs from a support that an engineer designs by hand, from
the section at that spot. We want to teach machines to do some of that work, and
the first thing we found missing was data: there was no public set of support-
design problems. So, with David Gvadzabia, Torben Graeber and Martin Fischer, we
built one. It's called CrossMEP."

## 2. A hospital needs about 10,000 support assemblies, each designed by hand (0:30)

**Show:** (from the ISARC 2026 talk) a hospital model with its support locations,
zoomed to one modular support assembly; three figures (≈ 10,000 assemblies per
hospital; 20 min – 2 h each; ≈ ¼ of MEP design effort).

**Say:** "Here's what that looks like. In this hospital, every red mark is a place where
pipes, ducts or cable trays hang from the structure. A modular support system
groups several services onto one prefabricated frame, installed as a single
unit: a structural support assembly. A hospital of two hundred thousand square
feet needs about ten thousand of them. Each takes twenty minutes to two hours to
design by hand, roughly a quarter of the whole MEP design effort. These are
practitioner estimates."

## 3. Synthesizing an assembly from a catalog and a section has resisted automation (1:05)

**Show:** (from the ISARC 2026 talk) the synthesis problem; the route-to-section
figure from the paper; three reasons it resists automation.

**Say:** "So what is the task? At ISARC we defined it like this. You're given a fixed
catalog of components and the context: which services cross the hanger, and what
they hang from. You must find a feasible assembly that carries them to the
structure. Designers don't work from the whole model. They work from one section
at each hanger, like this one. Today's tools help coordinate the model and check
a design, but choosing the layout and the parts is still manual. It takes
judgment, interacting rules, and ever-changing catalogs. That section is the
unit of this work, and the unit of our dataset."

## 4. Learning to design supports needs many problems, and none were public (1:50)

**Show:** scarcity, coverage, control; CrossMEP at a glance (7,000 contexts ·
31,484 elements · C1–C8 · 0 labels · traced · open).

**Say:** "To teach a machine this, you need many examples, and there were none. Project
models are proprietary, the open ones aren't organized around supports, and any
one project is a narrow slice. So we built CrossMEP: seven thousand contexts,
about thirty-one and a half thousand elements, in eight difficulty tiers. They
are deliberately unlabeled: you get the problem, never the answer. Every
constant is sourced or declared a design choice, and everything is open."

## 5. We generate what a designer receives: the section at one hanger (2:20)

**Show:** one C5 context with its table of fields.

**Say:** "Here's one context: a two-dimensional section at one support location. Each
element has its kind, service and trade, its size, its insulation, and its load,
which is weight per metre times the span it was sized at, plus its position. Add
the surface, a slab or a wall, and that's all. What you won't find is the
support: no channel, no rods, no anchors, and no correct answer, because a
feasible support depends on the catalog you build from. The context is the
brief. The assembly is the answer."

## 6. Sections follow trade practice and measured spacing, not random shapes (2:55)

**Show:** six steps (tier, surface, services, rows, spacing, check) beside a
generated C7 context with its three rows and one sampled gap marked.

**Say:** "How do we make a context? Not by free randomness, but by rules an engineer
would recognize. The tier fixes how many elements there are. We pick the surface
and fill it the way trades really run services: hot and cold together, flow and
return together, conduits in groups, bulky services nearest the slab. Gaps
between neighbors are drawn from gaps measured on a built project, never below
twenty-five millimeters. On walls, electrical stays above water. Every context
is checked, and it's seeded: the same seed gives the same file, byte for byte."

## 7. Sizes, spans and loads come from standards; the choices are declared (3:35)

**Show:** sources table (pipes, insulation, trays, ducts, conduits) and layout
conventions.

**Say:** "Where do the numbers come from? Three places. Sizes, weights and spans come
from standards: European steel pipe and duct standards, IEC for conduits and
trays, ASME for spans, the German GEG for insulation. How close neighbors sit
comes from measured open buildings. And a few things are simply our choices,
like the trade mix, and we label them that way. Loads are computed in code from
all of this."

## 8. 7,000 contexts in four splits; the test seeds are never trained on (4:05)

**Show:** splits table; elements by kind; pipes by nominal size.

**Say:** "The release has four splits on disjoint seeds, so a method is never tested on
what it trained on: five thousand contexts for training, five hundred each for
validation and test, and a benchmark of one thousand, a hundred and twenty-five
per tier. Everything is plain JSON with a schema and a datasheet."

## 9. Difficulty is one number: tier Cn holds exactly n elements (4:25)

**Show:** one benchmark context per tier, C1 to C8, ceilings and walls.

**Say:** "Here's one benchmark context per tier. C1 is a single element, the most common
support in any building. By C8 you have eight services on three rows. Within a
tier everything else varies: kinds, trades, surfaces, stacking. So the element
count is the one controlled axis of difficulty. And notice the walls: the
section rotates, and electrical sits above water."

## 10. Higher tiers are heavier and, overall, tighter, as designed (4:50)

**Show:** per-tier boxes of the closest gap and the load (benchmark), with the
median of 2,000 freshly generated contexts per tier as diamonds; C6–C8 shaded
("two or three rows").

**Say:** "Now three analyses. The first is a design check, not a discovery: does
difficulty grow with the tier? The count is fixed by construction, and load and
congestion follow from the rules, so this shows the dataset behaves as designed.
The load at the support rises at every step, from 0.1 to 1.7 kilonewtons. The
closest gap shrinks from 120 to about 62 millimeters, but widens again at C6,
where elements start stacking in two or three rows. So: report methods tier by
tier."

**Numbers** (`verify/tier_trends.py`): rank correlation of tier with load
+0.56, with the closest gap -0.36; population median gap
C5 70 mm, C6 75 mm; elements per row (median) 5 at C5, 3 at C6.

## 11. Spacing holds up on a clinic the generator never saw (5:25)

**Show:** left, gaps between side-by-side pipes measured on the clinic vs
generated; right, Wasserstein-1 distances with 95 % intervals between the
generator and three real models, and between the real models themselves.

**Say:** "The second analysis is the one the generator could fail. Is the spacing
realistic in a building it has never seen? The gap distribution was fitted on a
residential duplex. We kept a second open building aside, a medical-dental
clinic, cut it into sections every 250 millimeters, the way a context is
defined, and measured the gaps between pipes running side by side. On the left,
the clinic: generated gaps are close to measured ones, though not identical. On
the right, the distances. Generator to clinic: 28 millimeters. That is above the
8 a perfect generator would show, so not a perfect match, but about as close as
the duplex's own two models are to each other. A fixed 25-millimeter gap would
be about 190 off."

**Numbers** (`verify/compare_sections.py`, pairs weighted by shared length):
generated ↔ clinic 28 mm (95 % CI 16–44; noise floor 8); duplex MEP ↔ duplex
Plumbing 26; generated ↔ duplex 70 / 85; clinic ↔ duplex 71 / 85;
797 measured pipe pairs on the clinic, 74 and 41 on the duplex. Across 11 settings
of the cut, generated ↔ clinic stays at 27–36 mm.

## 12. A two-size catalog attaches 1 pipe in 9; the dataset shows what to cover (6:15)

**Show:** benchmark pipes by nominal size with the attachable ones in blue (only
DN40); the best share of pipes any k clamp sizes could attach (43 % with two,
80 % with six, 100 % with twelve); 11.6 % (95 % CI 10.1–13.0); 0 of 1,971 trays,
ducts and conduits.

**Say:** "The third analysis is a use of the dataset, not a test of it: what must a
catalog of clamps cover? Our paper's two-size catalog attaches 11.6 percent of
the pipes, with an interval of 10 to 13, all one size, DN40. Load is never the
limit, and trays, ducts and conduits aren't covered at all. On the right is what
the dataset asks of any catalog: two well-placed sizes could attach 43 percent,
six sizes 80, twelve sizes every pipe. So 'what should the catalog contain'
becomes a measurement."

## 13. Set the parameters and the generator returns the designer's brief (6:55)

**Show:** the Generator Studio (live; the slide is its screenshot): the
parameters bar, the section drawn as an A4 support detail and the same run in
3D; QR code to the hosted studio.

**Say:** "Let me show it. This is the Generator Studio. I choose what crosses the hanger,
a tier or an exact mix, and a seed. Out comes the section a support designer
receives, drawn the way an engineer would issue it: every service at true size,
its level below the slab, its load, the closest clear gap, and the same run in
3D. Every section is a stored output of the released generator, with the Python
call that reproduces it. Scan the code to try it yourself."

**Do (about 30 s):** switch to the studio; click C3, then *Generate another*
twice; then *Exact mix*, add a duct. If the demo fails, stay on the slide;
appendix slide 17 shows two more sections. (See "Before the talk" above.)

## 14. Train on the generator, evaluate on the benchmark, report per tier (8:05)

**Show:** six lines of Python, including `score` and `compare`; the interactive
gallery; train, evaluate, report.

**Say:** "Using it takes a few lines: load a split, filter by composition, or generate
your own mix. Because there are no labels, the same files serve reinforcement
learning, constraint programming, and benchmarking people. We ship the scoring
too. Train on the generator, from C1 up to C8. Evaluate on the benchmark, the
same 125 contexts per tier for every method. Report per tier, with 95 percent
intervals and paired tests."

## 15. One section at one support today; a checker and real data come next (8:35)

**Show:** scope; next steps; the request to practitioners with the QR code.

**Say:** "A word on scope. CrossMEP is one section at one support. Routing and branches
are outside it, but the span is recorded, so a method can vary it. Pipe spacing
was checked on two open buildings; the rest rests on practice and standards, and
the trade mix is a design choice. It's not for structural design of real
installations. Next: a public checker, with best-known costs, so we can compare
methods on the answer; the catalog as an input; and a real test set from
commercial projects, with supports designed by engineers. That's where I'd value
your eye."

## 16. Support design now has open problems to learn from (9:15)

**Say:** "To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design
problems, every constant sourced or declared a design choice, pipe spacing
checked on two open buildings, and all of it open. If you coordinate services or
design supports, try the studio and tell me what looks wrong. Thank you."

**Appendix slides:** two more sections from the Generator Studio (the demo
fallback); per-tier statistics of the benchmark split; the realism
check in detail (samples, both weightings, noise floors, sensitivity to the cut);
the catalog stress test with error bars (per tier, per split, sensitivity to the
diameter rule and bin tolerance); one stored record in JSON.

---

## Questions a construction audience may ask

**"Are these really experiments?"** No, and the talk calls them analyses: a
design check, a test against a building the generator never saw, and a use of the
dataset. For a dataset the question is not whether a method wins but whether the
problems are grounded and well behaved.

**"What is the generator actually grounded on?"** Three things. Standards, for
what each element is and weighs: pipe sizes and walls (EN 10220, EN 10255),
insulation (GEG Anlage 8, a chilled-water schedule), duct sizes (EN 1505, 1506)
with a manufacturer weight table, conduit sizes (IEC 61386-1), trays (a
manufacturer series), spans (ASME B31.1 for water pipes; practice values for
trays, ducts and conduits). Measured open buildings, for how close neighbours
sit: pipe gaps and stagger from a buildingSMART duplex, checked on a clinic.
And declared choices, for what is not measured: the trade mix, the surface mix,
the number of rows and the tier composition. Each constant carries its status in
`VERIFICATION_LOG.md`. What is not validated against any data is the
composition (which services appear together); that rests on coordination
practice.

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
