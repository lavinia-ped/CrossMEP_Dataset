# CrossMEP talk: script to record

Read-aloud text only, one block per slide, in the order of the slides. About 1,340 words: roughly 9 and a half minutes at an easy pace, plus about 35 seconds on slide 14 while you click through the studio.

**Recording tips**

- One take per slide, then join them: a pause of about a second between slides, and a short breath at every full stop.
- Smile on the first sentence of slide 1 and on the last of slide 17; slow down on the three numbers worth remembering: *10,000 assemblies* (slide 2), *32 millimeters* (slide 12), *14.5 percent* (slide 13).
- Slide 14: say the first two sentences, then screen-record the studio (click C3, *Generate another* twice, then *Exact mix* and add a duct) while you narrate what you click; say the last two sentences back on the slide.
- Where a sentence feels long, split it at the comma. The numbers are written the way you would say them.
- Check the total length after joining; if it is over 10 minutes, cut slide 8 (sources) to its first two sentences and slide 9 (splits) to its first one.

## Slide 1, Title (starts at 0:00)

Hello everyone, I'm Lavinia Pedrollo, from Stanford. Every pipe, duct and cable tray in a
building hangs from a support that an engineer designs by hand, from the section at that
spot. We want to teach machines to do some of that work, and the first thing we found
missing was data: there was no public set of support-design problems. So, with David
Gvadzabia, Torben Graeber and Martin Fischer, we built one. It's called CrossMEP.

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
tools coordinate and check; choosing the layout and the parts is still manual. That
section is the unit of this work, and the unit of our dataset.

## Slide 4, One section in, verified supports out: learnable, given problems to learn from (starts at 1:40)

What would a method look like? Think of it as a pipeline. On the left, the brief: the
context, and a catalog of parts with prices. The rules say which actions are legal in a
given state; each action adds parts. In the middle, a black box chooses the next action.
It could be a rule table, a search, or a learned policy; the pipeline doesn't care. A
verifier judges every finished design, statics, anchors, buildability, and feeds pass or
fail back. Out come verified designs, ranked by cost. Whatever sits in that black box, it
needs problems to learn from, a fixed set to compare on, and problems that look like
practice.

## Slide 5, Learning to design supports needs many problems, and none were public (starts at 2:30)

And there were none. Project models are proprietary, the open ones aren't organized around
supports, and any one project is a narrow slice. So we built CrossMEP: seven thousand
contexts, about thirty-one and a half thousand elements, in eight difficulty tiers. They
are deliberately unlabeled: you get the problem, never the answer. Every constant is
sourced or declared a design choice, and everything is open.

## Slide 6, We generate what a designer receives: the section at one hanger (starts at 2:55)

Here's one context: a two-dimensional section at one support location. Each element has
its kind, service and trade, its size, its insulation, and its load, which is weight per
metre times the span it was sized at, plus its position. Add the surface, a slab or a
wall, and that's all. What you won't find is the support: no channel, no rods, no anchors,
and no correct answer, because a feasible support depends on the catalog you build from.
The context is the brief. The assembly is the answer.

## Slide 7, Sections follow trade practice and measured spacing, not random shapes (starts at 3:35)

How do we make a context? Not by free randomness, but by rules an engineer would
recognize. The tier fixes how many elements there are. We pick the surface and fill it the
way trades really run services: hot and cold together, flow and return together, conduits
in groups, bulky services nearest the slab. Gaps between neighbors are drawn from gaps
measured on a built project, never below twenty-five millimeters. On walls, electrical
stays above water. Every context is checked, and it's seeded: the same seed gives the same
file, byte for byte.

## Slide 8, Sizes, spans and loads come from standards; the choices are declared (starts at 4:10)

Where do the numbers come from? Three places. Sizes, weights and spans come from
standards: European steel pipe and duct standards, IEC for conduits and trays, ASME for
spans, the German GEG for insulation. How close neighbors sit comes from measured open
buildings. And a few things are simply our choices, like the trade mix, and we label them
that way. Loads are computed in code from all of this.

## Slide 9, 7,000 contexts in four splits; the test seeds are never trained on (starts at 4:40)

The release has four splits on disjoint seeds, so a method is never tested on what it
trained on: five thousand contexts for training, five hundred each for validation and
test, and a benchmark of one thousand, a hundred and twenty-five per tier. Everything is
plain JSON with a schema and a datasheet.

## Slide 10, Difficulty is one number: tier Cn holds exactly n elements (starts at 5:00)

Here's one benchmark context per tier. C1 is a single element, the most common support in
any building. By C8 you have eight services on three rows. Within a tier everything else
varies: kinds, trades, surfaces, stacking. So the element count is the one controlled axis
of difficulty. And notice the walls: the section rotates, and electrical sits above water.

## Slide 11, Higher tiers are heavier and tighter, as designed (starts at 5:25)

Now three analyses. The first is a design check, not a discovery: does difficulty grow
with the tier? The count is fixed by construction, and load and congestion follow from the
rules, so this shows the dataset behaves as designed. The load at the support rises with
the tier, from about 0.3 to 2.0 kilonewtons. The closest gap narrows at every step, from
130 to about 51 millimeters. So: report methods tier by tier.

## Slide 12, Spacing holds up on a clinic the generator never saw (starts at 6:00)

The second analysis is the one the generator could fail. Is the spacing realistic in a
building it has never seen? The gap distribution was fitted on a residential duplex. We
kept a second open building aside, a medical-dental clinic, cut it into sections every 250
millimeters, the way a context is defined, and measured the gaps between pipes running
side by side. On the left, the clinic: generated gaps are close to measured ones, though
not identical. On the right, the distances. Generator to clinic: 32 millimeters. That is
above the 8 a perfect generator would show, so not a perfect match, but about as close as
the duplex's own two models are to each other. A fixed 25-millimeter gap would be about
190 off.

## Slide 13, A two-size catalog attaches 1 pipe in 7; the dataset shows what to cover (starts at 6:50)

The third analysis is a use of the dataset, not a test of it: what must a catalog of
clamps cover? Our paper's two-size catalog attaches 14.5 percent of the pipes, with an
interval of 13 to 16, all one size, DN40. Load is never the limit, and trays, ducts and
conduits aren't covered at all. On the right is what the dataset asks of any catalog: two
well-placed sizes could attach 38 percent, six sizes 76, fifteen sizes every pipe. So
'what should the catalog contain' becomes a measurement.

## Slide 14, Set the parameters and the generator returns the designer's brief (starts at 7:25)

Let me show it. This is the Generator Studio. I choose what crosses the hanger, a tier or
an exact mix, and a seed. Out comes the section a support designer receives, drawn the way
an engineer would issue it: every service at true size, its level below the slab, its
load, the closest clear gap, and the same run in 3D. Every section is a stored output of
the released generator, with the Python call that reproduces it. Scan the code to try it
yourself.

## Slide 15, Train on the generator, evaluate on the benchmark, report per tier (starts at 8:35)

Using it takes a few lines: load a split, filter by composition, or generate your own mix.
Because there are no labels, the same files serve reinforcement learning, constraint
programming, and benchmarking people. We ship the scoring too. Train on the generator,
from C1 up to C8. Evaluate on the benchmark, the same 125 contexts per tier for every
method. Report per tier, with 95 percent intervals and paired tests.

## Slide 16, One section at one support today; a checker and real data come next (starts at 9:05)

A word on scope. CrossMEP is one section at one support. Routing and branches are outside
it, but the span is recorded, so a method can vary it. Pipe spacing was checked on two
open buildings; the rest rests on practice and standards, and the trade mix is a design
choice. It's not for structural design of real installations. Next: a public checker, with
best-known costs, so we can compare methods on the answer; the catalog as an input; and a
real test set from commercial projects, with supports designed by engineers. That's where
I'd value your eye.

## Slide 17, Support design now has open problems to learn from (starts at 9:45)

To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design problems,
every constant sourced or declared a design choice, pipe spacing checked on two open
buildings, and all of it open. If you coordinate services or design supports, try the
studio and tell me what looks wrong. Thank you.
