# CrossMEP in ten minutes — a talk for construction people

Audience: CIB W78 — BIM/IT researchers and MEP/construction practitioners. The
paper is written for the learning-based-synthesis reader; this talk is written
for the person who has coordinated a corridor or designed a trapeze. Every
slide answers "why should a construction engineer care?" before it says
anything about learning. Figures are in `docs/figures/` and regenerate with
`python scripts/make_figures.py`.

Timing: 10 slides, ~55 s each, 1 min of slack for the honesty slide (8).

---

## 1. Title (0:00)

**CrossMEP: the support designer's brief, as a dataset.**
Lavinia Pedrollo, David Gvadzabia, Torben Graeber, Martin Fischer.

*Say:* "Every pipe, duct and tray in a building hangs from something. I am
going to talk about the piece of information a support designer starts from —
and why we turned it into a public dataset."

## 2. The problem on site (0:50)

*Show:* the paper's Figure 1 (route → section).

- A 200,000 sq ft hospital: on the order of 10,000 support assemblies, each
  20 minutes to 2 hours by hand; roughly a quarter of MEP design effort.
- Support design starts **after** coordination: the designer receives the
  coordinated model and works hanger by hanger.
- At each hanger the brief is a cross-section: what passes, how big, how heavy,
  how far apart, what it hangs from.

*Say:* "Nobody designs a support from the whole model. You design it from the
section at that hanger. That section is the unit of work — and the unit of our
dataset."

## 3. Why a dataset, and why synthetic (1:40)

- Automating support design with learning needs **many** of those sections —
  the full spread of what shows up in buildings, not one project.
- Project models are proprietary; the few open ones are not organised around
  supports and often export no sizes. One project is one narrow slice (one
  building type, one trade mix).
- So: a **rule-based generator** — no learned model, no free randomness —
  that encodes the conventions you already use, verified against a built
  project, and public.

*Say:* "We are not claiming a building. We are claiming the rules, and we show
where each rule comes from."

## 4. What a context is (2:30)

*Show:* `01_what_a_context_is.png`.

- One 2-D section perpendicular to the run at one support location.
- Each element: kind, service and trade; bare size; insulation per side;
  **load per metre and the span it was sized at, so load per support = kN/m ×
  span**; position along the surface and standoff from it.
- The surface: slab or wall, substrate, thickness.
- **Deliberately absent:** channel, rods, clamps, anchors. The context is the
  brief; the assembly is the answer. There are no "correct" answers in the
  files because a feasible support depends on the catalog you build from.

*Say:* "If you have ever been handed a section and a catalog and asked to make
it hang — that is exactly what is in each record, in millimetres and kN."

## 5. Where the numbers come from (3:20)

*Show:* a table (no figure): element → standard → what we take from it.

| element | sizes | load basis |
|---|---|---|
| pipes DN15–100 | EN 10220 / EN 10255 medium series | steel + water × ASME B31.1 water-service span (published points only) |
| insulation | GEG Anlage 8 (heated), 30/50 mm condensation control (chilled) | — |
| cable trays 150–600 | IEC 61537 systems | full tray: 50 kg/m at 300 mm datum, × 2.0 m |
| ducts | EN 1505 rectangular, EN 1506 round | manufacturer duct-weight table incl. flanges, × 2.4 m |
| conduits Ø20–50 | IEC 61386-1 | steel tube + 40 %-of-bore cable fill, × 2.0 m |

- Layout conventions: ducts nearest the slab, then containment, then pipes;
  trades run in banks (hot + cold pairs, flow + return); electrical above wet
  on walls; **clear gaps drawn from a distribution measured on a built project**.
- Every constant has a source and a status in the repo; the loads are
  *computed* from those sources in the code, and the tests pin them.

*Say:* "If you disagree with a number, there is one line to change and one
test that will tell you what moved."

## 6. Difficulty tiers (4:10)

*Show:* `02_tiers_examples.png` then `03_tiers_stats.png`.

- Tier Cn = exactly n elements, C1 to C8; everything else (trades, kinds,
  surfaces, stacking) varies within the tier.
- C1 is the most common support in any building: one pipe, one tray, one duct.
  C8 is the congested rack.
- As the count rises the median clear gap falls from 120 mm to 62 mm and the
  median load at the support rises from 0.10 kN to 1.7 kN.

*Say:* "Difficulty here means a tighter, heavier scene — not that the support
is harder to calculate. Whether it is harder to *solve* is for the method to
show."

## 7. Checked against a built project (5:00)

*Show:* `04_gaps_vs_measured.png`.

- buildingSMART Duplex Apartment, MEP and Plumbing discipline models, parsed
  with IfcOpenShell: 427 and 231 segments; sizes, parallel-run counts,
  elevation spread and clear gaps measured.
- Gaps are irregular, not modular: median 108 mm, quartiles 24–238. We fit a
  lognormal to the measurement and sample from it.
- Distance between generated and measured gap distributions: **41 mm** — the
  two real discipline models of the *same building* are 50 mm apart; a fixed
  modular gap would be 139 mm away.

*Say:* "The generator sits inside the variation you get between two
disciplines' models of one building. That is the realism claim, no more."

## 8. What we found preparing the public release (5:50) — the honesty slide

*Show:* `05_v3_vs_v4.png`.

- Rebuilding the release for publication we found the generator added a 25 mm
  routing envelope on each element **on top of** the 25 mm minimum gap: every
  neighbour sat 50 mm further apart than the sampled gap, and nothing was
  ever closer than 75 mm — while 42 % of the measured gaps are.
- The 41 mm in the paper was computed on the sampled gap, not the physical
  one. Measured physically, the paper's files were 89 mm from the project.
- Revision 4.0 removes the offset. Same elements, same loads, same rows — the
  spacing moved. The physical gaps are now the sampled ones, and the 41 mm
  holds for the geometry you can measure in the files.
- Everything is reproducible: all eight files regenerate byte-for-byte on
  every CI run; every number in the paper that reproduces is a test, and the
  ones that do not (the paper's composition figures came from an internal
  build) are listed with the public values.

*Say:* "I would rather tell you this than have you find it. The fix changed no
element and no load; it changed where things sit, and it made the
verification honest."

## 9. The catalog test (7:00)

*Show:* `06_catalog_coverage.png`.

- Take a released two-bin clamp catalog (48–54 mm at 2.5 kN; 108–114 mm at
  4.0 kN). Which of the 4,500 benchmark elements can it attach?
- 11.6 % of pipes; none of the 1,971 trays, ducts and conduits. Loads are
  never the limit; diameter and kind are.
- So "generalise the catalog" is a measurable requirement: small-bore clamps
  first, then tray, duct and conduit attachments.

*Say:* "This is the dataset telling the catalog what it is missing."

## 10. Limits, and what we want from you (7:50)

- One section only: routing, slope, branches, support spacing are outside it
  (span is recorded per element, so a method can vary it).
- DN ≤ 100, concrete substrates, no anchor capacity, no duct insulation.
- Stagger is drawn per element: a bank on one trapeze would be co-planar — we
  know, and it is next.
- Verified on one residential project: small-bore statistics are checked,
  congested racks rest on practice and standards.
- **Ask:** the thing we cannot compute is plausibility. If you coordinate or
  design supports, open the gallery and tell us what looks wrong.

*Close (9:00):* "CrossMEP is the brief, not the answer: 7,000 sections, every
number traced, verified against a built project, reproducible to the byte, and
public. github.com/lavinia-ped/CrossMEP_Dataset."

---

## Questions a construction audience will ask

**"Why 25 mm as the minimum gap? We use more."** It is the published pipe-rack
minimum; it is a *floor*, not a typical value. The sampled gaps have a median
of 150 mm and quartiles 85–263, taken from measurement. If your practice uses
50 mm, say so — it is one constant, and the fit can be re-done above 50 mm.

**"A quarter of your measured gaps are under 25 mm — why does the generator
never produce them?"** True: 26 % of the Duplex MEP gaps are below 25 mm (the
first bar in the histogram). We have not classified them; candidates are runs
on a common clamp or trapeze and modelling overlaps in the IFC. The generator
treats 25 mm as a design minimum and fits the distribution above it, so it
reproduces the spacing of separately supported runs, not touching ones. That
is a stated scope choice, and the fit's n = 73 is the above-floor sample.

**"What are the spikes at 500 mm?"** The generator caps a sampled gap at
500 mm (a design parameter); everything the lognormal would have placed
beyond lands there. In the paper's files the cap sat at 550 mm because of the
envelope offset.

**"Those spans look short/long."** They are ASME B31.1 Table 121.5
water-service points (2.1 / 3.0 / 3.7 / 4.3 m for NPS 1 / 2 / 3 / 4), assigned
by a floor rule, no interpolation; trays 2.0 m, ducts 2.4 m, conduits 2.0 m.
Every element carries its span, so a method can treat it as a variable.

**"Insulation: chilled at 30/50 but cold water bare?"** Heated lines follow GEG
Anlage 8 verbatim; chilled follows a 30/50 mm condensation-control employer
schedule; domestic cold and sprinkler are modelled bare (anti-sweat sleeves
are geometrically negligible). The divergence is documented.

**"Why is a hot and a cold pipe of one pair at different heights?"** Stagger is
drawn per element, calibrated to the elevation spread measured across a
bundle. A bank on one trapeze is co-planar; per-group stagger is the next
revision and needs re-calibration against the measurement.

**"Your row spacing is 120 mm — a trapeze is deeper than that."** 120 mm is a
clear gap between the rows' elements, not the trapeze depth; the standoff of
the first row from the slab is 90 mm. Both are design parameters, labelled as
such.

**"Where is seismic bracing / thermal movement / anchor capacity?"** Outside the
context by design: those belong to the support solution and the structure,
which the dataset deliberately does not describe.

**"Why no steel deck, masonry, drywall, larger pipes, plastics?"** The internal
build the paper describes has them; the public element library does not yet.
The repository lists which paper numbers depend on that and gives the public
values.

**"How do I use this if I am not training a model?"** As a test set for any
placement tool or rule engine: 1,000 stratified scenes with known difficulty,
a filter API to pull exactly the composition you want (e.g. three pipes and one
tray on a wall), and a custom generator for your own mix.

**"Can I run it on my own project?"** The IFC measurement script and the
comparison script are in `verify/`; point them at your model (sizes must be
exported) and you get the same statistics and distances for your building.
