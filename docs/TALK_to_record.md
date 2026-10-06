# CrossMEP talk: script to record

Read-aloud text only, one block per slide, in the order of the slides. About 1,100 words: roughly 7 minutes 40 seconds at an easy pace, plus about 35 seconds on slide 13 while you click through the studio.

**Recording tips**

- One take per slide, then join them: a pause of about a second between slides, and a short breath at every full stop.
- Smile on the first sentence of slide 1 and on the last of slide 16; slow down on the three numbers worth remembering: *10,000 assemblies* (slide 2), *32 millimeters* (slide 11), *14.5 percent* (slide 12).
- Slides 3 and 7 carry the two words everything else uses: *context* is the brief, *assembly* is the answer. Say them slowly the first time.
- Slide 13: say the first two sentences, then screen-record the studio (click C3, *Generate another* twice, then *Exact mix* and add a duct) while you narrate what you click; say the last two sentences back on the slide.
- Where a sentence feels long, split it at the comma. The numbers are written the way you would say them.
- Check the total length after joining; if it is over 9 minutes, cut slide 9 (sources) to its first two sentences.

## Slide 1, Title (starts at 0:00)

I'm Lavinia Pedrollo, from Stanford. Every pipe, duct and cable tray in a building hangs
from a support that an engineer designs by hand. We want machines to do some of that, and
the first thing missing was data: no public set of support-design problems existed. So we
built one, CrossMEP, with David Gvadzabia, Torben Graeber and Martin Fischer.

## Slide 2, A hospital needs about 10,000 support assemblies, each designed by hand (starts at 0:25)

Here is the scale. Every red mark in this hospital is a place where services hang from the
structure. A modular support groups several services on one prefabricated frame: a
structural support assembly. A hospital this size needs about ten thousand. Each takes
twenty minutes to two hours to design, roughly a quarter of the MEP design effort.
Practitioner estimates, but these are the numbers people live with.

## Slide 3, A designer turns one cross-section into verified support assemblies (starts at 0:55)

What exactly is designed, and from what? In: one cross-section at a hanger. The structure
it hangs from, and the services crossing it, each with trade, position, size and weight
per metre. That is the context: the brief. Out: assemblies of catalog parts that carry
those services to the structure, checked for statics, anchors, connectors and
buildability, ranked by cost. That is the answer. Keep the two apart: CrossMEP is
contexts. It contains no assemblies.

## Slide 4, Synthesizing the assembly from a catalog and a context has resisted automation (starts at 1:25)

Why is this still done by hand? Designers work from one section at each hanger, after
coordination. Tools coordinate and check; they do not choose the layout or the parts.
Three reasons: the topology comes from experience, the rules interact across thousands of
combinations, and catalogs change faster than rule systems can be rewritten.

## Slide 5, Whatever the method, it needs problems to learn from and a fixed set to compare on (starts at 1:45)

What would a method look like? The context and a catalog go in. Rules say which actions
are legal; each action adds parts. In the middle, a black box chooses the next action: a
rule table, a search, or a learned policy. A verifier checks every finished design and
feeds pass or fail back. Whatever sits in the black box, it needs problems to learn from,
a fixed set to compare on, and problems that look like practice.

## Slide 6, Real designs cover one corner of the design space; CrossMEP covers all of it (starts at 2:20)

The real designs we had were few, from one kind of project with one trade mix: one corner
of the design space. A method tuned on them measures fit to that project. So we generate.
CrossMEP fills the space by construction, without limit: a new seed is a new set, uniform
over the tiers or any mix you ask for. Seven thousand contexts are the release, not the
ceiling.

## Slide 7, We generate what a designer receives: the section at one hanger (starts at 2:45)

Here is one context: a two-dimensional section at one support. Each element has its kind,
service and trade, its size, insulation and position, and its load: weight per metre times
the span it was sized at. Add the surface, slab or wall, and that is all. No channel, no
rods, no anchors, no correct answer, because a feasible support depends on the catalog you
build from.

## Slide 8, Sections follow trade practice and measured spacing, not random shapes (starts at 3:15)

How is a context made? By rules an engineer would recognize. The tier fixes the element
count. We pick the surface and fill it the way trades run services: hot and cold together,
flow and return together, conduits in groups, bulky services nearest the slab. Gaps are
drawn from gaps measured on a built project, never below twenty-five millimetres. On
walls, electrical stays above water. Same seed, same file.

## Slide 9, Sizes, spans and loads come from standards; the choices are declared (starts at 3:45)

Where do the numbers come from? Sizes, weights and spans from standards: EN for pipes and
ducts, IEC for conduits and trays, ASME for spans, GEG for insulation. Spacing from
measured open buildings. And a few choices of our own, like the trade mix, labelled as
choices.

## Slide 10, Tier Cn holds exactly n elements; higher tiers are heavier and tighter, as designed (starts at 4:00)

Three analyses. The first is a design check. One benchmark context per tier: C1 is a
single element, the most common support in any building; C8 has eight services on three
rows. Within a tier everything else varies, so the element count is the one controlled
axis. Load at the support rises with the tier, from about 0.3 to 2.0 kilonewtons, and the
closest gap narrows at every step, from 130 to about 51 millimetres. The dataset behaves
as designed.

## Slide 11, Spacing holds up on a clinic the generator never saw (starts at 4:35)

The second is the one the generator could fail: is the spacing realistic in a building it
has never seen? The gap distribution was fitted on a residential duplex. We held out a
medical clinic, cut it into sections every 250 millimetres, and measured the gaps between
pipes side by side. Generator to clinic: 32 millimetres. Above the 8 a perfect generator
would show, but about as close as the duplex's own two models are to each other. A fixed
25-millimetre gap would be about 190 off.

## Slide 12, A two-size catalog attaches 1 pipe in 7; the dataset shows what to cover (starts at 5:10)

The third is a use of the dataset: what must a catalog of clamps cover? Our paper's two-
size catalog attaches 14.5 percent of the pipes, interval 13 to 16, all one size, DN40.
Trays, ducts and conduits are not covered at all. On the right, what the dataset asks of
any catalog: two well-placed sizes reach 38 percent, six sizes 76, fifteen every pipe.
What the catalog should contain becomes a measurement.

## Slide 13, Set the parameters and the generator returns the designer's brief (starts at 5:40)

Let me show it. This is the Generator Studio. I choose what crosses the hanger, a tier or
an exact mix, and a seed. Out comes the section a designer receives, drawn as an engineer
would issue it: every service at true size, its level, its load, the closest gap, and the
run in 3D. Every section is a stored output of the released generator. Scan the code to
try it.

## Slide 14, Train on the generator, evaluate on the benchmark, report per tier (starts at 6:45)

Using it takes a few lines: load a split, filter by composition, or generate your own mix.
Four splits on disjoint seeds: five thousand to train, five hundred each for validation
and test, and a benchmark of a thousand, a hundred and twenty-five per tier. The same
files serve reinforcement learning, constraint programming and benchmarking, and we ship
the scoring. Train on the generator. Evaluate on the benchmark, the same contexts for
every method. Report per tier, with intervals and paired tests.

## Slide 15, One section at one support today; a checker and real data come next (starts at 7:20)

Scope. CrossMEP is one section at one support. Pipe spacing was checked on two open
buildings; the rest rests on practice and standards, and the trade mix is a design choice.
It is not for the structural design of real installations. Next: a public checker, so
methods can be compared on the answer; the catalog as an input; and a real test set from
commercial projects, with supports designed by engineers. That is where I would value your
eye.

## Slide 16, Support design now has open problems to learn from (starts at 7:50)

To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design problems,
every constant sourced or declared, spacing checked on two open buildings, all of it open.
If you coordinate services or design supports, try the studio and tell me what looks
wrong. Thank you.
