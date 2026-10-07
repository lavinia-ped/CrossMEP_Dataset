# CrossMEP talk: script to record

Read-aloud text only, one block per slide, in the order of the slides. About 1,180 words: roughly 8 minutes 10 seconds at an easy pace, plus about 35 seconds on slide 13 while you click through the studio.

**Recording tips**

- One take per slide, then join them: a pause of about a second between slides, and a short breath at every full stop.
- Smile on the first sentence of slide 1 and on the last of slide 16; slow down on the three numbers worth remembering: *10,000 assemblies* (slide 2), *32 millimeters* (slide 11), *14.5 percent* (slide 12).
- Slides 3 and 7 carry the two words everything else uses: *context* is the brief, *assembly* is the answer. Say them slowly the first time.
- Slide 13: say the first two sentences, then screen-record the studio (click C3, *Generate another* twice, then *Exact mix* and add a duct) while you narrate what you click; say the last two sentences back on the slide.
- Where a sentence feels long, split it at the comma. The numbers are written the way you would say them.
- Check the total length after joining; if it is over 9 minutes, cut slide 9 (sources) to its first two sentences.

## Slide 1, Title (starts at 0:00)

Good morning. Every pipe, duct and cable tray in a building hangs from a support, and
every one of those supports is designed by hand. We want machines to learn to design them.
A learning machine needs problems to practise on, and in public there were none. So we
built them. I'm Lavinia Pedrollo, from Stanford, and this is CrossMEP, with David
Gvadzabia, Torben Graeber and Martin Fischer.

## Slide 2, In a hospital like this one, ten thousand structural support assemblies are each designed individually, which is why they take about a quarter of the MEP design effort (starts at 0:30)

Here is the scale. This is a hospital, and every red mark is a place where services hang
from the structure. A modular support groups several services on one prefabricated frame:
a structural support assembly. A hospital this size needs about ten thousand of them, each
designed individually, twenty minutes to two hours apiece. Add it up and it is about a
quarter of the MEP design effort. Practitioner estimates, but these are the numbers people
live with.

## Slide 3, A support designer turns one cross-section into a set of verified support assemblies (starts at 1:00)

So what exactly is designed, and from what? In: one cross-section at a hanger. The
structure it hangs from, and the services crossing it, each with its trade, position, size
and weight per metre. We call that the context. It is the brief. Out: assemblies of
catalog parts that carry those services to the structure, checked for statics, anchors,
connectors and buildability, ranked by cost. That is the answer. Hold on to these two
words, because CrossMEP is contexts only. It contains no assemblies.

## Slide 4, Choosing the assembly from a catalog is still done by hand, one section at a time (starts at 1:35)

Why is this still done by hand? A designer works from one section at each hanger, after
coordination. Tools coordinate the model and check a design, but they do not choose the
layout or the parts. Three reasons it has resisted automation: the topology comes from
experience, the rules interact across thousands of combinations, and catalogs change
faster than rule systems can be rewritten.

## Slide 5, A learning method needs thousands of contexts to practise on, and real projects give too few, so we generate them (starts at 2:00)

So how would a machine learn it? Give it a context. Let it propose an assembly. Check the
assembly, and feed pass or fail back. Round after round, it gets better. But every round
needs a new context, and that is where it stops. Real projects give a handful of sections,
all from the same kind of job and confidential: too few to practise on, and a method tuned
on them only fits that job. So we generate the contexts, as many as a method needs, and we
fix one benchmark to judge every method on.

## Slide 6, The ninety real designs we had came from one project and filled one corner of the design space, so CrossMEP covers all of it by construction (starts at 2:40)

How scarce? The real designs we could get were ninety, from one project. Nearly every one
had a duct and many pipes. Not one had a cable tray, and not one was as simple as a single
pipe: one corner of the design space. A method tuned on them measures fit to that project.
So CrossMEP fills the space by construction: every tier from one element to eight, kinds
and surfaces varied, without limit. A new seed is a new set. Seven thousand contexts are
the release, not the ceiling.

## Slide 7, One context is exactly what a support designer receives at one hanger, without the answer (starts at 3:20)

Here is one context: a two-dimensional section at one support. Each element has its kind,
service and trade, its size, insulation and position, and its load: weight per metre times
the span it was sized at. Add the surface, slab or wall, and that is all. No channel, no
rods, no anchors, no correct answer, because a feasible support depends on the catalog you
build from.

## Slide 8, Every section is built the way trades run services, with gaps measured on a real building (starts at 3:45)

How is a context made? By rules an engineer would recognize. The tier fixes the element
count. We pick the surface and fill it the way trades run services: hot and cold together,
flow and return together, conduits in groups, bulky services nearest the slab. Gaps are
drawn from gaps measured on a built project, never below twenty-five millimetres. On
walls, electrical stays above water. Same seed, same file.

## Slide 9, Every number is traced to a standard, to a measurement, or to a choice we declare as ours (starts at 4:15)

Where do the numbers come from? Sizes, weights and spans from standards: EN for pipes and
ducts, IEC for conduits and trays, ASME for spans, GEG for insulation. Spacing from
measured open buildings. And a few choices of our own, like the trade mix, labelled as
choices.

## Slide 10, The tier fixes the element count, and load and congestion grow with it as the rules intend (starts at 4:35)

Three analyses. The first is a design check. Each tier adds one element: C1 is a single
service, the most common support in any building; C8 has eight. Within a tier everything
else varies, so the element count is the one controlled axis. Load at the support rises
with the tier, from about 0.3 to 2.0 kilonewtons, and the closest gap narrows at every
step, from 130 to about 51 millimetres. The dataset behaves as designed.

## Slide 11, Generated spacing matches a clinic the generator never saw to within 32 millimetres (starts at 5:05)

The second is the one the generator could fail: is the spacing realistic in a building it
has never seen? The gap distribution was fitted on a residential duplex. We held out a
medical clinic, cut it into sections every 250 millimetres, and measured the gaps between
pipes side by side. Generator to clinic: 32 millimetres. Above the 8 a perfect generator
would show, but about as close as the duplex's own two models are to each other. A fixed
25-millimetre gap would be about 190 off.

## Slide 12, The paper's two clamp sizes reach one pipe in seven, and the dataset says which sizes to add (starts at 5:40)

The third is a use of the dataset: what must a catalog of clamps cover? Our paper's two-
size catalog attaches 14.5 percent of the pipes, interval 13 to 16, all one size, DN40.
Trays, ducts and conduits are not covered at all. On the right, what the dataset asks of
any catalog: two well-placed sizes reach 38 percent, six sizes 76, fifteen every pipe.
What the catalog should contain becomes a measurement.

## Slide 13, Pick a tier or an exact mix and a seed, and the Generator Studio returns the designer's brief (starts at 6:10)

Let me show it. This is the Generator Studio. I choose what crosses the hanger, a tier or
an exact mix, and a seed. Out comes the section a designer receives, drawn as an engineer
would issue it: every service at true size, its level, its load, the closest gap, and the
run in 3D. Every section is a stored output of the released generator. Scan the code to
try it.

## Slide 14, Methods train on the generator and are compared on one fixed benchmark, tier by tier (starts at 7:15)

Using it takes a few lines: load a split, filter by composition, or generate your own mix.
Four splits on disjoint seeds: five thousand to train, five hundred each for validation
and test, and a benchmark of a thousand, a hundred and twenty-five per tier. The same
files serve reinforcement learning, constraint programming and benchmarking, and we ship
the scoring. Train on the generator. Evaluate on the benchmark, the same contexts for
every method. Report per tier, with intervals and paired tests.

## Slide 15, Today CrossMEP is one section at one support, and next come a checker and real projects (starts at 7:50)

Scope. CrossMEP is one section at one support. Pipe spacing was checked on two open
buildings; the rest rests on practice and standards, and the trade mix is a design choice.
It is not for the structural design of real installations. Next: a public checker, so
methods can be compared on the answer; the catalog as an input; and a real test set from
commercial projects, with supports designed by engineers. That is where I would value your
eye.

## Slide 16, Support design finally has open problems to learn from (starts at 8:20)

To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design problems,
every constant sourced or declared, spacing checked on two open buildings, all of it open.
If you coordinate services or design supports, try the studio and tell me what looks
wrong. Thank you.
