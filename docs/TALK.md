# CrossMEP in ten minutes: talk script

The script for `docs/CrossMEP_CIBW78_talk.pptx` (the same text is in each slide's
speaker notes). Audience: CIB W78, a mix of BIM and IT researchers and MEP and
construction practitioners. Every number on the slides comes from the released
data through `scripts/make_figures.py`.

Timing: 16 slides in about 8.3 minutes of speech at an easy pace (about 145 words a minute; slide 13 is a demo of the
Generator Studio, with its screenshot as the fallback). No appendix slides: the
questions below are answered from the main slides.

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

**Say:** "Hi, I'm Lavinia, a PhD student at Stanford University, and today I am happy to
present CrossMEP, which is the dataset we built when we found that the data to
learn support design from did not exist. Support design is the one part of MEP
that every tool coordinates, every tool checks, and no tool does. A hospital has
ten thousand of these supports, each chosen by hand from a catalog. We think a
machine can learn to choose them, and what has stopped anyone trying is not the
algorithm. It is that nobody had the problems to practise on. So we built the
problems."

## 2. The synthesis of structural support assemblies (SSAs) takes 25% of MEP design effort because every assembly must be designed individually (0:45)

**Show:** (from the ISARC 2026 talk) a hospital model with its support locations,
zoomed to one modular support assembly; three figures (≈ 10,000 assemblies per
hospital; 20 min – 2 h each; ≈ ¼ of MEP design effort).

**Say:** "Here is the scale. This is a hospital, and every red mark is a place where
services hang from the structure. A modular support groups several services on
one prefabricated frame: a structural support assembly. A hospital this size
needs about ten thousand of them, each designed individually, twenty minutes to
two hours apiece. Add it up and it is about a quarter of the MEP design effort.
Practitioner estimates, but these are the numbers people live with."

## 3. An SSA designer turns one MEP cross-section into a feasible structural support assembly (1:15)

**Show:** (from the ISARC 2026 talk) the problem as a diagram: in, one
cross-section at a hanger (the structure with its anchor zones; the services
with trade, position, size and weight per metre); out, a stack of verified
support designs (a rod trapeze, checked for statics, anchors, connectors and
buildability; up to ten, ranked by installed cost). Below, the two words the
talk relies on: the *context* is the brief and is what CrossMEP contains; the
*assembly* is the answer and is what a method produces.

**Say:** "So what exactly is designed, and from what? In: one cross-section at a hanger.
The structure it hangs from, and the services crossing it, each with its trade,
position, size and weight per metre. We call that the context. It is the brief.
Out: assemblies of catalog parts that carry those services to the structure,
checked for statics, anchors, connectors and buildability, ranked by cost. That
is the answer. Hold on to these two words, because CrossMEP is contexts only. It
contains no assemblies."

## 4. Existing tools coordinate and verify modular support assemblies, but their synthesis remains manual because it relies on tacit engineering expertise and complex catalog-driven rules (1:50)

**Show:** (from the ISARC 2026 talk) the route-to-section figure from the paper;
where practice stands (tools coordinate and check; topology and parts are chosen
by hand); three reasons it resists automation.

**Say:** "Why is this still done by hand? A designer works from one section at each
hanger, after coordination. Tools coordinate the model and check a design, but
they do not choose the layout or the parts. Three reasons it has resisted
automation: the topology comes from experience, the rules interact across
thousands of combinations, and catalogs change faster than rule systems can be
rewritten."

## 5. A learning method needs thousands of contexts to practise on, and real projects give too few, so we generate them (2:15)

**Show:** the learning loop: a context goes into a black-box method, which
proposes a design; the design is checked; pass or fail is fed back and the
method improves. Below, where the contexts come from: real projects (a few
near-identical sections, then empty slots) versus CrossMEP (a thumbnail per tier,
unlimited), with an arrow from CrossMEP into the loop's context box. The method
itself stays a black box: the approaches are unpublished.

**Say:** "So how would a machine learn it? Give it a context. Let it propose an assembly.
Check the assembly, and feed pass or fail back. Round after round, it gets
better. But every round needs a new context, and that is where it stops. Real
projects give a handful of sections, all from the same kind of job and
confidential: too few to practise on, and a method tuned on them only fits that
job. So we generate the contexts, as many as a method needs, and we fix one
benchmark to judge every method on."

## 6. The ninety real designs we had came from one project and filled one corner of the design space, so CrossMEP covers all of it by construction (2:55)

**Show:** the design space twice (element count across, kinds, trades and
surface up). Left: the ninety real designs, a duct with many pipes each, ringed
in one corner, with the note "ducts and many pipes, no trays, nothing as simple
as one pipe". Right: a CrossMEP thumbnail for every tier, on ceilings and walls.
Beside them, CrossMEP at a glance.

**Say:** "How scarce? The real designs we could get were ninety, from one project. Nearly
every one had a duct and many pipes. Not one had a cable tray, and not one was
as simple as a single pipe: one corner of the design space. A method tuned on
them measures fit to that project. So CrossMEP fills the space by construction:
every tier from one element to eight, kinds and surfaces varied, without limit.
A new seed is a new set. Seven thousand contexts are the release, not the
ceiling."

## 7. One context is exactly what a support designer receives at one hanger, without the answer (3:35)

**Show:** one C5 context from the Generator Studio: its drawing sheet and 3D view
(grey run, the section face in the trade colour) on the left with the fields every
element carries as chips; on the right the record as the designer reads it (element,
trade, insulation, load per metre, span, load at the support), three facts about
the context (slab, total load, closest gap) and the band of what is deliberately
absent: channel, rods, clamps, anchors, and any correct answer.

**Say:** "Here is one context: a two-dimensional section at one support. Each element has
its kind, service and trade, its size, insulation and position, and its load:
weight per metre times the span it was sized at. Add the surface, slab or wall,
and that is all. No channel, no rods, no anchors, no correct answer, because a
feasible support depends on the catalog you build from."

## 8. Every section is built the way trades run services, with gaps measured on a real building (4:00)

**Show:** six step cards (tier, surface, services, rows, spacing, check) beside a
generated C8 context from the Generator Studio: its drawing sheet with one sampled
gap marked, and its 3D view with the three rows.

**Say:** "How is a context made? By rules an engineer would recognize. The tier fixes the
element count. We pick the surface and fill it the way trades run services: hot
and cold together, flow and return together, conduits in groups, bulky services
nearest the slab. Gaps are drawn from gaps measured on a built project, never
below twenty-five millimetres. On walls, electrical stays above water. Same
seed, same file."

## 9. Every number is traced to a standard, to a measurement, or to a choice we declare as ours (4:30)

**Show:** the five element kinds, each with a glyph, its size standard and its load
basis, with the citation numbers; beside them the three kinds of ground, colour
coded: standards, measured (the two open buildings) and declared choices.

**Say:** "Where do the numbers come from? Sizes, weights and spans from standards: EN for
pipes and ducts, IEC for conduits and trays, ASME for spans, GEG for insulation.
Spacing from measured open buildings. And a few choices of our own, like the
trade mix, labelled as choices."

## 10. The tier fixes the element count, and load and congestion grow with it as the rules intend (4:50)

**Show:** two bar charts of medians per tier, benchmark and population: load at
the support rises, the closest clear gap narrows; a caption says this is a design
check and that everything else varies within a tier.

**Say:** "Three analyses. The first is a design check. Each tier adds one element: C1 is
a single service, the most common support in any building; C8 has eight. Within
a tier everything else varies, so the element count is the one controlled axis.
Load at the support rises with the tier, from about 0.3 to 2.0 kilonewtons, and
the closest gap narrows at every step, from 130 to about 51 millimetres. The
dataset behaves as designed."

**Numbers** (`verify/tier_trends.py`, revision 4.1): rank correlation of tier
with load +0.46, with the closest gap −0.38 (benchmark medians 0.30 → 2.04 kN,
130 → 51 mm); population medians (2,000 per tier) rise at every step in load
(0.21 → 2.47 kN) and narrow at every step in gap (149 → 55 mm). In revision 4.0
the gap widened again at C6, where the generator always stacked two or three
rows; 4.1 draws rows by count, so that step is gone.

## 11. Generated spacing matches a clinic the generator never saw to within 32 millimetres (5:20)

**Show:** left, the two gap distributions (clinic measured, generator) as a
native chart; right, the Wasserstein distances with 95 % intervals, generated
versus real and real versus real, with the noise floor; three tiles: 32 mm,
26 mm (duplex to duplex), 190 mm (a fixed 25 mm gap).

**Say:** "The second is the one the generator could fail: is the spacing realistic in a
building it has never seen? The gap distribution was fitted on a residential
duplex. We held out a medical clinic, cut it into sections every 250
millimetres, and measured the gaps between pipes side by side. Generator to
clinic: 32 millimetres. Above the 8 a perfect generator would show, but about as
close as the duplex's own two models are to each other. A fixed 25-millimetre
gap would be about 190 off."

**Numbers** (`verify/compare_sections.py`, pairs weighted by shared length):
generated ↔ clinic 32 mm (95 % CI 17–48; noise floor 8); duplex MEP ↔ duplex
Plumbing 26; generated ↔ duplex 76 / 88; clinic ↔ duplex 71 / 85;
797 measured pipe pairs on the clinic, 74 and 41 on the duplex. Across 11 settings
of the cut, generated ↔ clinic stays at 31–41 mm. (Revision 4.0: 28 mm, 27–36
across settings; 4.1 widens the DN bands, so more insulation and slightly wider
bare gaps. The gap draw itself is unchanged.)

## 12. The paper's two clamp sizes reach one pipe in seven, and the dataset says which sizes to add (5:55)

**Show:** benchmark pipes by nominal size with the attachable ones in blue (only
DN40); the best share of pipes any k clamp sizes could attach (38 % with two,
76 % with six, 100 % with fifteen); 14.5 % (95 % CI 12.7–16.2); 0 of 2,012 trays,
ducts and conduits.

**Say:** "The third is a use of the dataset: what must a catalog of clamps cover? Our
paper's two-size catalog attaches 14.5 percent of the pipes, interval 13 to 16,
all one size, DN40. Trays, ducts and conduits are not covered at all. On the
right, what the dataset asks of any catalog: two well-placed sizes reach 38
percent, six sizes 76, fifteen every pipe. What the catalog should contain
becomes a measurement."

## 13. Pick a tier or an exact mix and a seed, and the Generator Studio returns the designer's brief (6:25)

**Show:** the Generator Studio (live; the slide is its screenshot): in, the
parameters bar; out, the section drawn as an A4 support detail with its facts line,
and the same run in 3D cut at the section; QR code to the hosted studio.

**Say:** "Let me show it. This is the Generator Studio. I choose what crosses the hanger,
a tier or an exact mix, and a seed. Out comes the section a designer receives,
drawn as an engineer would issue it: every service at true size, its level, its
load, the closest gap, and the run in 3D. Every section is a stored output of
the released generator. Scan the code to try it."

**Do (about 30 s):** switch to the studio; click C3, then *Generate another*
twice; then *Exact mix*, add a duct. If the demo fails, stay on the slide: its
screenshot is the fallback. (See "Before the talk" above.)

## 14. Methods train on the generator and are compared on one fixed benchmark, tier by tier (7:30)

**Show:** the protocol as a flow, generator → train (5,000; validation and
test 500 each) → benchmark (1,000, 125 per tier, never trained on) → report per
tier; four lines of Python to load, score and compare.

**Say:** "Using it takes a few lines: load a split, filter by composition, or generate
your own mix. Four splits on disjoint seeds: five thousand to train, five
hundred each for validation and test, and a benchmark of a thousand, a hundred
and twenty-five per tier. The same files serve reinforcement learning,
constraint programming and benchmarking, and we ship the scoring. Train on the
generator. Evaluate on the benchmark, the same contexts for every method. Report
per tier, with intervals and paired tests."

## 15. Today CrossMEP is one section at one support, and next come a checker and real projects (8:05)

**Show:** scope as four icon rows, next steps as three numbered rows; the
request to practitioners with the QR code.

**Say:** "Scope. CrossMEP is one section at one support. Pipe spacing was checked on two
open buildings; the rest rests on practice and standards, and the trade mix is a
design choice. It is not for the structural design of real installations. Next:
a public checker, so methods can be compared on the answer; the catalog as an
input; and a real test set from commercial projects, with supports designed by
engineers. That is where I would value your eye."

## 16. Support design finally has open problems to learn from (8:35)

**Say:** "To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design
problems, every constant sourced or declared, spacing checked on two open
buildings, all of it open. If you coordinate services or design supports, try
the studio and tell me what looks wrong. Thank you."

---

## Questions a construction audience may ask

**"Are these really experiments?"** No, and the talk calls them analyses: a
design check, a test against a building the generator never saw, and a use of the
dataset. For a dataset the question is not whether a method wins but whether the
problems are grounded and well behaved.

**"What is the generator actually grounded on?"** Three things. Standards, for
what each element is and weighs: pipe sizes and walls (EN 10220, EN 10255),
insulation (GEG Anlage 8, a chilled-water schedule), duct sizes (EN 1505, 1506)
with a manufacturer weight table, conduit sizes (IEC 61386-1), trays (the
NEMA VE 1 width series), spans (ASME B31.1 for water pipes, confirmed by the
ASHRAE Handbook; the IET table for conduits; SMACNA's maximum for ducts; the
NEMA class span for trays). Measured open buildings, for how close neighbours
sit: pipe gaps and stagger from a buildingSMART duplex, checked on a clinic.
And declared choices, for what is not measured: the trade mix, the surface mix,
the number of rows and the tier composition. Each constant carries its status in
`VERIFICATION_LOG.md`. The composition (which services appear together) is
declared; it was compared against what hanger locations carry in the two open
buildings (`verify/compare_composition.py`), and data revision 4.1 adjusted four
of its parameters after that comparison (rows drawn by count, kind continuity,
duct pairs, DN bands to DN150), so for the current files the comparison is in
sample: a design check. The electrical share cannot be tested: the open
electrical models hold fixtures only.

**"Is the trade mix realistic?"** Partly, and we say which part. We cut the
clinic's plumbing and HVAC models together and recorded what each hanger
location carries. On the 4.0 files the pipe-to-duct split by count was within a
total-variation distance of 0.10 of the clinic's for three to eight elements
but 0.20 for pairs, and the generator mixed kinds in one bundle and stacked
rows far more often than the clinic (six elements: 47 % mixed vs 24 %, 100 %
stacked vs 38 %). Revision 4.1 changed four design parameters in response:
rows are drawn by count, the next group tends to repeat the previous kind, duct
pairs exist, and the DN bands reach DN150. On the 4.1 files the split is within
0.13 for every count, mixing is within about ten points up to seven elements
and stacking within seven points; that is in sample, so it is a design check,
not evidence. What did not change: 70 % of clinic locations carry one element
and 96 % three or fewer, so the congested tiers are rare in these two small
buildings; and pipe sizes differ by building more than either differs from the
generator (the clinic is a hospital with DN100+ mains, the duplex is 87 % DN25).
The numbers are in `RESULTS.md` with intervals.

**"Why these standards and not others?"** Four rules, in order. Geometry is
metric and DN-keyed, so sizes follow the European series an EU contractor
orders against (EN 10220/10255, EN 1505/1506, IEC 61386, IEC 61537). Where the
European standard fixes no value, we take the international reference whose
values are openly republished: NEMA VE 1 for tray widths and class spans, ASME
B31.1 for pipe spans (the ASHRAE Handbook prints the same four values), SMACNA
for duct hangers, the IET table under BS 7671 for conduits. We prefer sources
whose full text can be checked, which is why insulation follows the German GEG,
a statute with public text. And we prefer values stable across editions. Where
the value is not the standard's exact figure, the log says how the standard
brackets it. Section 10 of the log lists the alternatives we did not use and
why (BS EN 806-4, NEC, DIN 4140, DW/144).

**"Isn't Experiment 1 circular? The generator makes higher tiers heavier."**
Yes, and the slide says so: it is a design check that the dataset behaves as
intended, which a benchmark needs before anyone reports per tier. The test the
generator could fail is Experiment 2.

**"Was the generator tuned to the clinic?"** No. The gap distribution was fitted
in June 2026 on the duplex; the clinic was measured afterwards and never used for
fitting. Against the duplex the generator is 76–88 mm away, about as far as the
clinic is from the duplex. Composition, not spacing, was adjusted after the
clinic comparison (revision 4.1), and the composition check is marked in sample.

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
water-service points (2.1 / 3.0 / 3.7 / 4.3 m for NPS 1 / 2 / 3 / 4, the same
values as the ASHRAE Handbook hanger table), assigned by a floor rule with no
interpolation; trays 2.0 m (below the shortest NEMA VE 1 class span), ducts
2.4 m (under the SMACNA 10 ft maximum), conduits 2.0 m (the IET table).
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
pipe to EN 10255, DN15–150 (DN125 and DN150 since revision 4.1), on concrete
slabs and walls (C25/C30, 150–300 mm).
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
gives the same distances and intervals for your building, and
`verify/compare_composition.py` the same composition comparison.

**"What catalog is that? Is it a manufacturer's range?"** It is the
illustrative two-size family printed in the paper (48–54 mm up to 2.5 kN;
108–114 mm up to 4.0 kN); no product catalog ships with the dataset. It is
deliberately small: a stress test, not a full range. The conclusion does not
depend on it: the right-hand chart asks the same question of any catalog, namely
how many sizes, and where, this dataset needs, and `verify/catalog_stress.py
--bins` runs it on yours.

**"How certain is 14.5 %?"** The 95 % interval over contexts is 12.7–16.2
(cluster bootstrap: the elements of one context are correlated); over 16,000
freshly generated contexts it is 14.3 % (13.8–14.7), and the eight tiers lie
between 12.7 and 14.9 %. The value is sensitive to one edge: DN100
(114.3 mm) lies 0.3 mm above the 108–114 mm bin, so widening the bins by 0.5 mm
gives 19.8 %. What does not change is that only DN40 is attached.

**"Is that coverage what a designer could install?"** No, it is an upper bound:
only size and capacity are tested. Clearance to neighbours, the insert on cold
lines, anchors and rods are not modelled.

**"The paper says 11.5 %, the slide 14.5 %."** The paper's figure was computed
on an internal build with a larger pipe library; the public 4.0 files give
11.6 %, and the current 4.1 files 14.5 % (wider DN bands put more pipes at DN40)
with 2,012 trays, ducts and conduits (paper: 1,832). `RESULTS.md` lists every
value for the public files and the tests pin them.
