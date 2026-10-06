# CrossMEP talk: script to record

Read-aloud text only, one block per slide, in the order of the slides. About 1,350 words: roughly 9 minutes 20 seconds at an easy pace, plus about 35 seconds on slide 15 while you click through the studio.

**Recording tips**

- One take per slide, then join them: a pause of about a second between slides, and a short breath at every full stop.
- Smile on the first sentence of slide 1 and on the last of slide 18; slow down on the three numbers worth remembering: *10,000 assemblies* (slide 2), *32 millimeters* (slide 13), *14.5 percent* (slide 14).
- Slides 3 and 7 carry the two words everything else uses: *context* is the brief, *assembly* is the answer. Say them slowly the first time.
- Slide 15: say the first two sentences, then screen-record the studio (click C3, *Generate another* twice, then *Exact mix* and add a duct) while you narrate what you click; say the last two sentences back on the slide.
- Where a sentence feels long, split it at the comma. The numbers are written the way you would say them.
- Check the total length after joining; if it is over 10 minutes, cut slide 9 (sources) to its first two sentences and slide 10 (splits) to its first one.

## Slide 1, Title (starts at 0:00)

Hello everyone, I'm Lavinia Pedrollo, from Stanford. Every pipe, duct and cable tray in a
building hangs from a support that an engineer designs by hand, from the section at that
spot. We want to teach machines to do some of that work, and the first thing we found
missing was data: there was no public set of support-design problems. So, with David
Gvadzabia, Torben Graeber and Martin Fischer, we built one. It's called CrossMEP.

## Slide 2, A hospital needs about 10,000 support assemblies, each designed by hand (starts at 0:30)

Here is the scale of it. In this hospital, every red mark is a place where pipes, ducts or
cable trays hang from the structure. A modular support system groups several services onto
one prefabricated frame: a structural support assembly. A hospital of two hundred thousand
square feet needs about ten thousand of them. Each takes twenty minutes to two hours to
design by hand, roughly a quarter of the whole MEP design effort. These are practitioner
estimates.

## Slide 3, A designer turns one cross-section into verified support assemblies (starts at 1:05)

What exactly is designed, and from what? At ISARC we defined the task like this. In: one
cross-section at a hanger. The structure it hangs from, with its anchor zones, and the
services crossing it, each with trade, position, size and weight per metre. We call that a
context: the brief. Out: assemblies of catalog parts that carry those services to the
structure, each checked for statics, anchors, connectors and buildability, up to ten,
ranked by cost. The assembly is the answer. Keep the two apart: CrossMEP is contexts. It
contains no assemblies.

## Slide 4, Synthesizing the assembly from a catalog and a context has resisted automation (starts at 1:40)

Why has this resisted automation? Designers don't work from the whole model: after
coordination they work from one section at each hanger, like this one. Today's tools
coordinate and check; choosing the layout and the parts is still manual. Three reasons.
The topology comes from experience. Code, load and material rules interact across
thousands of combinations. And catalogs change faster than rule systems can be rewritten.

## Slide 5, Whatever the method, it needs problems to learn from and a fixed set to compare on (starts at 2:10)

What would a method look like? On the left, the context and a catalog of parts with
prices. The rules say which actions are legal; each action adds parts. In the middle, a
black box chooses the next action: a rule table, a search, or a learned policy. A verifier
judges every finished design, statics, anchors, buildability, and feeds pass or fail back.
Whatever sits in that black box, it needs problems to learn from, a fixed set to compare
on, and problems that look like practice.

## Slide 6, Real designs cover one corner of the design space; CrossMEP covers all of it (starts at 2:45)

The real designs we had were few, and they sat in one corner of the design space: one kind
of project, one trade mix. A method tuned to them measures fit to that project. So we
generate. CrossMEP covers the space by construction, and without limit: a new seed is a
new set of problems, uniform over the tiers, or shaped to whatever mix you ask for. The
seven thousand contexts in eight tiers are the release, not the ceiling: deliberately
unlabeled, every constant sourced or declared, and all of it open.

## Slide 7, We generate what a designer receives: the section at one hanger (starts at 3:25)

Here's one context: a two-dimensional section at one support location. Each element has
its kind, service and trade, its size, its insulation, and its load, which is weight per
metre times the span it was sized at, plus its position. Add the surface, a slab or a
wall, and that's all. What you won't find is the support: no channel, no rods, no anchors,
and no correct answer, because a feasible support depends on the catalog you build from.

## Slide 8, Sections follow trade practice and measured spacing, not random shapes (starts at 3:55)

How do we make a context? By rules an engineer would recognize, not free randomness. The
tier fixes how many elements there are. We pick the surface and fill it the way trades
really run services: hot and cold together, flow and return together, conduits in groups,
bulky services nearest the slab. Gaps between neighbors are drawn from gaps measured on a
built project, never below twenty-five millimeters. On walls, electrical stays above
water. Every context is checked; same seed, same file, byte for byte.

## Slide 9, Sizes, spans and loads come from standards; the choices are declared (starts at 4:30)

Where do the numbers come from? Three places. Sizes, weights and spans come from
standards: European steel pipe and duct standards, IEC for conduits and trays, ASME for
spans, the German GEG for insulation. How close neighbors sit comes from measured open
buildings. And a few things are simply our choices, like the trade mix, and we label them
that way.

## Slide 10, 7,000 contexts in four splits; the test seeds are never trained on (starts at 4:55)

The release has four splits on disjoint seeds, so a method is never tested on what it
trained on: five thousand contexts for training, five hundred each for validation and
test, and a benchmark of one thousand, a hundred and twenty-five per tier. Everything is
plain JSON with a schema and a datasheet.

## Slide 11, Difficulty is one number: tier Cn holds exactly n elements (starts at 5:20)

Here's one benchmark context per tier. C1 is a single element, the most common support in
any building. By C8 you have eight services on three rows. Within a tier everything else
varies, so the element count is the one controlled axis of difficulty. And notice the
walls: the section rotates, and electrical sits above water.

## Slide 12, Higher tiers are heavier and tighter, as designed (starts at 5:40)

Now three analyses. The first is a design check, not a discovery: the count is fixed by
construction, and load and congestion follow from the rules, so this shows the dataset
behaves as designed. The load at the support rises with the tier, from about 0.3 to 2.0
kilonewtons. The closest gap narrows at every step, from 130 to about 51 millimeters.

## Slide 13, Spacing holds up on a clinic the generator never saw (starts at 6:05)

The second analysis is the one the generator could fail. Is the spacing realistic in a
building it has never seen? The gap distribution was fitted on a residential duplex. We
kept a second open building aside, a medical-dental clinic, cut it into sections every 250
millimeters, and measured the gaps between pipes running side by side. Generator to
clinic: 32 millimeters. Above the 8 a perfect generator would show, but about as close as
the duplex's own two models are to each other. A fixed 25-millimeter gap would be about
190 off.

## Slide 14, A two-size catalog attaches 1 pipe in 7; the dataset shows what to cover (starts at 6:45)

The third analysis is a use of the dataset, not a test of it: what must a catalog of
clamps cover? Our paper's two-size catalog attaches 14.5 percent of the pipes, with an
interval of 13 to 16, all one size, DN40. Load is never the limit, and trays, ducts and
conduits aren't covered at all. On the right is what the dataset asks of any catalog: two
well-placed sizes could attach 38 percent, six sizes 76, fifteen sizes every pipe. So
'what should the catalog contain' becomes a measurement.

## Slide 15, Set the parameters and the generator returns the designer's brief (starts at 7:25)

Let me show it. This is the Generator Studio. I choose what crosses the hanger, a tier or
an exact mix, and a seed. Out comes the section a support designer receives, drawn the way
an engineer would issue it: every service at true size, its level below the slab, its
load, the closest clear gap, and the same run in 3D. Every section is a stored output of
the released generator, with the call that reproduces it. Scan the code to try it
yourself.

## Slide 16, Train on the generator, evaluate on the benchmark, report per tier (starts at 8:35)

Using it takes a few lines: load a split, filter by composition, or generate your own mix.
With no labels, the same files serve reinforcement learning, constraint programming, and
benchmarking. We ship the scoring too. Train on the generator, from C1 up to C8. Evaluate
on the benchmark, the same 125 contexts per tier for every method. Report per tier, with
95 percent intervals and paired tests.

## Slide 17, One section at one support today; a checker and real data come next (starts at 9:00)

A word on scope. CrossMEP is one section at one support. Pipe spacing was checked on two
open buildings; the rest rests on practice and standards, and the trade mix is a design
choice. It's not for structural design of real installations. Next: a public checker, so
we can compare methods on the answer; the catalog as an input; and a real test set from
commercial projects, with supports designed by engineers. That's where I'd value your eye.

## Slide 18, Support design now has open problems to learn from (starts at 9:35)

To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design problems,
every constant sourced or declared a design choice, pipe spacing checked on two open
buildings, and all of it open. If you coordinate services or design supports, try the
studio and tell me what looks wrong. Thank you.
