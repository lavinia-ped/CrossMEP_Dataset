# CrossMEP talk: script to record

Read-aloud text only, one block per slide, in the order of the slides. About 1,330 words: roughly 9 minutes at an easy pace, plus about 35 seconds on slide 13 while you click through the studio.

**Recording tips**

- One take per slide, then join them: a pause of about a second between slides, and a short breath at every full stop.
- Smile on the first sentence of slide 1 and on the last of slide 16; slow down on the three numbers worth remembering: *10,000 assemblies* (slide 2), *28 millimeters* (slide 11), *11.6 percent* (slide 12).
- Slide 13: say the first two sentences, then screen-record the studio (click C3, *Generate another* twice, then *Exact mix* and add a duct) while you narrate what you click; say the last two sentences back on the slide.
- Where a sentence feels long, split it at the comma. The numbers are written the way you would say them.
- Check the total length after joining; if it is over 10 minutes, cut slide 7 (sources) to its first two sentences and slide 8 (splits) to its first one.

## Slide 1, Title (starts at 0:00)

Next time you're in a hospital, look up. Above the ceiling, pipes, ducts and cable trays
run in every direction, and not one of them floats. Each hangs from a support that an
engineer designed by hand, one at a time. And until now, there was no public data to teach
a machine to do that. I'm Lavinia Pedrollo, from Stanford, and with David Gvadzabia,
Torben Graeber and Martin Fischer, we built that data: CrossMEP.

## Slide 2, A hospital needs about 10,000 support assemblies, each designed by hand (starts at 0:30)

Here's what that looks like. In this hospital, every red mark is a place where pipes,
ducts or cable trays hang from the structure. A modular support system groups several
services onto one prefabricated frame, installed as a single unit: a structural support
assembly. A hospital of two hundred thousand square feet needs about ten thousand of them.
Each takes twenty minutes to two hours to design by hand, roughly a quarter of the whole
MEP design effort. These are practitioner estimates.

## Slide 3, Synthesizing an assembly from a catalog and a section has resisted automation (starts at 1:05)

So what is the task? At ISARC we defined it like this. You're given a fixed catalog of
components and the context: which services cross the hanger, and what they hang from. You
must find a feasible assembly that carries them to the structure. Designers don't work
from the whole model. They work from one section at each hanger, like this one. Today's
tools help coordinate the model and check a design, but choosing the layout and the parts
is still manual. It takes judgment, interacting rules, and ever-changing catalogs. That
section is the unit of this work, and the unit of our dataset.

## Slide 4, Learning to design supports needs many problems, and none were public (starts at 1:50)

To teach a machine this, you need many examples, and there were none. Project models are
proprietary, the open ones aren't organized around supports, and any one project is a
narrow slice. So we built CrossMEP: seven thousand contexts, about thirty-one and a half
thousand elements, in eight difficulty tiers. They are deliberately unlabeled: you get the
problem, never the answer. Every constant is sourced or declared a design choice, and
everything is open.

## Slide 5, We generate what a designer receives: the section at one hanger (starts at 2:20)

Here's one context: a two-dimensional section at one support location. Each element has
its kind, service and trade, its size, its insulation, and its load, which is weight per
metre times the span it was sized at, plus its position. Add the surface, a slab or a
wall, and that's all. What you won't find is the support: no channel, no rods, no anchors,
and no correct answer, because a feasible support depends on the catalog you build from.
The context is the brief. The assembly is the answer.

## Slide 6, Sections follow trade practice and measured spacing, not random shapes (starts at 2:55)

How do we make a context? Not by free randomness, but by rules an engineer would
recognize. The tier fixes how many elements there are. We pick the surface and fill it the
way trades really run services: hot and cold together, flow and return together, conduits
in groups, bulky services nearest the slab. Gaps between neighbors are drawn from gaps
measured on a built project, never below twenty-five millimeters. On walls, electrical
stays above water. Every context is checked, and it's seeded: the same seed gives the same
file, byte for byte.

## Slide 7, Sizes, spans and loads come from standards; the choices are declared (starts at 3:35)

Where do the numbers come from? Each comes from a cited source or is declared a design
choice. Pipes follow the European steel pipe standards, filled with water, at ASME B31.1
spans. Insulation follows the German GEG, and a condensation schedule for chilled water.
Trays and conduits follow IEC standards, ducts European sizes with a manufacturer's weight
table. Loads are computed in code, and pure choices, like the trade mix, are labeled as
choices.

## Slide 8, 7,000 contexts in four splits; the test seeds are never trained on (starts at 4:05)

The release has four splits on disjoint seeds, so a method is never tested on what it
trained on: five thousand contexts for training, five hundred each for validation and
test, and a benchmark of one thousand, a hundred and twenty-five per tier. Mostly pipes,
then conduits, trays and ducts. Four in five hang from a ceiling, one in five from a wall.
Everything is plain JSON with a schema and a datasheet.

## Slide 9, Difficulty is one number: tier Cn holds exactly n elements (starts at 4:35)

Here's one benchmark context per tier. C1 is a single element, the most common support in
any building. By C8 you have eight services on three rows. Within a tier everything else
varies: kinds, trades, surfaces, stacking. So the element count is the one controlled axis
of difficulty. And notice the walls: the section rotates, and electrical sits above water.

## Slide 10, Higher tiers are heavier and, overall, tighter, as designed (starts at 5:00)

Now three experiments. The first is a design check, not a discovery: does difficulty grow
with the tier? The count is fixed by construction, and load and congestion follow from the
rules, so this shows the dataset behaves as designed. The load at the support rises at
every step, from 0.1 to 1.7 kilonewtons. The closest gap shrinks from 120 to about 62
millimeters, but widens again at C6, where elements start stacking in two or three rows.
So: report methods tier by tier.

## Slide 11, Spacing holds up on a clinic the generator never saw (starts at 5:35)

The second experiment is the one the generator could fail. Is the spacing realistic in a
building it has never seen? The gap distribution was fitted on a residential duplex. We
kept a second open building aside, a medical-dental clinic, cut it into sections every 250
millimeters, the way a context is defined, and measured the gaps between pipes running
side by side. On the left, the clinic: generated gaps are close to measured ones, though
not identical. On the right, the distances. Generator to clinic: 28 millimeters. That is
above the 8 a perfect generator would show, so not a perfect match, but about as close as
the duplex's own two models are to each other. A fixed 25-millimeter gap would be about
190 off.

## Slide 12, A two-size catalog attaches 1 pipe in 9; the dataset shows what to cover (starts at 6:25)

The third experiment is a use of the dataset, not a test of it: what must a catalog of
clamps cover? Our paper's two-size catalog attaches 11.6 percent of the pipes, with an
interval of 10 to 13, all one size, DN40. Load is never the limit, and trays, ducts and
conduits aren't covered at all. On the right is what the dataset asks of any catalog: two
well-placed sizes could attach 43 percent, six sizes 80, twelve sizes every pipe. So 'what
should the catalog contain' becomes a measurement.

## Slide 13, Set the parameters and the generator returns the designer's brief (starts at 7:05)

Let me show it. This is the Generator Studio. I choose what crosses the hanger, a tier or
an exact mix, and a seed. Out comes the section a support designer receives, drawn the way
an engineer would issue it: every service at true size, its level below the slab, its
load, the closest clear gap, and the same run in 3D. Every section is a stored output of
the released generator, with the Python call that reproduces it. Scan the code to try it
yourself.

## Slide 14, Train on the generator, evaluate on the benchmark, report per tier (starts at 8:15)

Using it takes a few lines: load a split, filter by composition, or generate your own mix.
Because there are no labels, the same files serve reinforcement learning, constraint
programming, and benchmarking people. We ship the scoring too. Train on the generator,
from C1 up to C8. Evaluate on the benchmark, the same 125 contexts per tier for every
method. Report per tier, with 95 percent intervals and paired tests.

## Slide 15, One section at one support today; a checker and real data come next (starts at 8:45)

A word on scope. CrossMEP is one section at one support. Routing and branches are outside
it, but the span is recorded, so a method can vary it. Pipe spacing was checked on two
open buildings; the rest rests on practice and standards, and the trade mix is a design
choice. It's not for structural design of real installations. Next: a public checker, with
best-known costs, so we can compare methods on the answer; the catalog as an input; and a
real test set from commercial projects, with supports designed by engineers. That's where
I'd value your eye.

## Slide 16, Support design now has open problems to learn from (starts at 9:25)

To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design problems,
every constant sourced or declared a design choice, pipe spacing checked on two open
buildings, and all of it open. If you coordinate services or design supports, try the
studio and tell me what looks wrong. Thank you.
