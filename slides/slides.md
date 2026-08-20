---
theme: seriph
title: Where Do the Cells Go?
info: |
  Chao & Das (2015) — a Suspension Balance Model for the rotating HARV
  bioreactor, re-implemented and verified in Julia/Gridap.jl.
class: text-center
transition: fade
mdc: true
---

# Where Do the Cells Go?

Suspension dynamics in a rotating bioreactor

<div class="pt-8 text-sm opacity-70">
Chao &amp; Das (2015), <em>Chem. Eng. J.</em> — re-implemented &amp; verified
</div>

<!--
Open with the question, not the acronym: in a rotating bioreactor, what
actually decides where the cells end up?

Context for the room: NASA developed the HARV (High Aspect Ratio Vessel) —
a rotating-wall vessel — specifically to grow cells in a low-shear,
microgravity-analog environment. The whole point of rotating the vessel is
to suspend cells without the mechanical stirring that would damage them.
But "low shear" doesn't mean "no physics" — there's still a real
competition happening inside the vessel between forces that want to move
cells around, and this talk is about that competition, the model Chao &
Das wrote down for it, and a from-scratch verified implementation of that
model.

Roadmap: the physical system (2 min) → the model (3-4 min) → judgment
calls we had to make, both the paper's and ours (3-4 min) → our
implementation and how we verified it (5-6 min) → a qualitative result
(2-3 min) → discussion.
-->

---
layout: center
---

# The System

<svg viewBox="0 0 360 200" class="mx-auto" style="max-height:55vh">
  <circle cx="110" cy="100" r="70" fill="none" stroke="currentColor" stroke-width="2.5" opacity="0.85"/>
  <path d="M 165 55 A 72 72 0 0 1 178 100" fill="none" stroke="currentColor" stroke-width="2.5" marker-end="url(#arrow)"/>
  <text x="110" y="104" text-anchor="middle" font-size="13" opacity="0.6">ω</text>
  <line x1="230" y1="60" x2="230" y2="140" stroke="currentColor" stroke-width="2.5"/>
  <line x1="290" y1="60" x2="290" y2="140" stroke="currentColor" stroke-width="2.5"/>
  <line x1="230" y1="60" x2="290" y2="60" stroke="currentColor" stroke-width="1" stroke-dasharray="3,3" opacity="0.5"/>
  <line x1="230" y1="140" x2="290" y2="140" stroke="currentColor" stroke-width="1" stroke-dasharray="3,3" opacity="0.5"/>
  <text x="260" y="105" text-anchor="middle" font-size="12" opacity="0.6">thin gap</text>
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 z" fill="currentColor" opacity="0.85"/>
    </marker>
  </defs>
</svg>

<!--
The HARV: a horizontally-rotating, disk-shaped vessel with a very thin
gap between two circular plates. Rotating the whole vessel — rather than
stirring the fluid inside it with an impeller — is what gets you the
low-shear environment: in the frame of the vessel, the fluid mostly just
goes along for the ride.

But "mostly" is the operative word. Cells are denser or lighter than the
medium (in this paper, actually lighter — cells float), so gravity/
buoyancy is always acting on them, all the time, independent of rotation.
Meanwhile, wherever the flow does shear — near walls, near other cells —
there's a shear-induced migration effect that pushes particles around
too, completely independent of buoyancy. Those two effects don't
generally agree on where cells should go. That disagreement is the entire
physical content of this talk.

Chao & Das's contribution was to write down a continuum model — a
Suspension Balance Model — that puts a number on both effects and couples
them to the fluid flow and nutrient transport, self-consistently.
-->

---
layout: center
---

# The Model

5 coupled fields: $u,\ p,\ \Phi,\ C,\ \Gamma$

$$J_s = J_{s\mu} + J_{sc} + J_{st}$$

<!--
Five fields, one monolithic system, solved together every timestep:
- u, p: momentum + incompressibility (Navier-Stokes, with a Krieger-
  Dougherty viscosity that depends on local particle concentration Φ —
  viscosity diverges as Φ approaches a maximum packing fraction, so it
  physically resists over-concentration on its own)
- Φ: particle volume fraction — the thing we actually care about
- C: nutrient (glucose) concentration, advected, diffused, consumed by
  cells, driving a growth-kinetics source term
- Γ: local shear rate, carried as its OWN field rather than computed
  on the fly — the true shear-rate expression has a singularity at zero
  shear, and giving it its own smoothed/projected field avoids that
  blowing up the nonlinear solve.

The particle flux J_s is where the actual competition lives, three pieces:
- J_sμ: migration toward regions of lower viscosity (i.e. away from where
  particles have already crowded)
- J_sc: migration driven by shear-rate and concentration gradients — the
  "shear-induced migration" effect, particles literally bumping into each
  other more in high-shear regions and getting pushed out
- J_st: sedimentation/buoyancy — a Stokes settling velocity corrected for
  hindered settling at higher concentrations

Note there's no "the flow carries the cells" term missing — advection of
Φ by u is in the transport equation, separately; J_s is specifically the
extra migration on top of that advection.
-->

---
layout: center
---

# Judgment Calls

<div class="grid grid-cols-2 gap-12 pt-8 text-xl">
<div class="text-center opacity-80">the paper</div>
<div class="text-center opacity-80">our port</div>
</div>

<!--
This is the credibility slide, and I want to spend real time here because
an audience like this will (rightly) ask "how do you know your
implementation matches the paper" — and the honest answer is: in a few
places, it can't, because the paper doesn't fully agree with itself.

The paper's own inconsistencies:
- Eq. 12 and Eq. 14 disagree on the power of Φ in the J_sc shear-induced-
  migration term — one is linear in Φ, the other quadratic. These aren't
  two different regimes, they're the same term written twice with
  different exponents. We had to pick one (we went with Eq. 14's form) —
  this is disclosed in the tutorial notebook, not buried.
- The equation numbering itself skips/mismatches around Eq. 27 in the
  manuscript — minor, but it's the kind of thing that makes you check
  everything else twice.

Our own explicit approximations, disclosed the same way:
- Φ_avg (used in the hindered-settling correction) should, by the
  model's own logic, be recomputed as a domain integral every timestep —
  the code currently hardcodes it as a constant. Settling never adapts
  to the evolving concentration field. This is a real simplification,
  not a bug we're hiding — flagged directly in the tutorial notebook.
- The paper uses two distinct symbols for the growth-rate constant and
  the nutrient-consumption constant; our code currently reuses one
  parameter (kc) for both.
- One deliberate, defensible choice: the momentum equation's buoyancy
  term uses bare g, not ρg as literally written in the paper's Eq. 1 —
  because density-weighted buoyancy is already fully carried by the
  settling flux J_st, and including it twice would double-count it.

None of this is "the model is wrong" — it's "here is exactly where we
had to exercise judgment, and why," which is a more useful thing to tell
a room of experts than a claim of perfect fidelity.
-->

---
layout: center
---

# Implementation

<div class="text-2xl pt-4 opacity-90">
Julia · Gridap.jl
</div>

<div class="pt-6 text-sm opacity-60">
monolithic finite-element solver, 5 fields, 1 nonlinear system
</div>

<!--
Rewritten from scratch as a monolithic finite-element solver: all five
fields, one coupled nonlinear system, solved together each timestep with
Newton's method (BackTracking line search for stability) — not a
segregated/split scheme where you solve for flow, then transport,
then update, and hope it's consistent. Monolithic is more expensive per
step but avoids splitting error entirely.

Time discretization: BDF1 (backward Euler) for the first step, BDF2 for
every step after, for better-than-first-order accuracy without a
multi-stage scheme.

One implementation detail worth a sentence if there's time: Gridap can
differentiate the residual automatically (autodiff) to get the Jacobian
for Newton's method, but doing that for this particular 5-field coupled
system is expensive to compile — so we hand-derived the Jacobian
analytically instead. That's a compile-time/engineering story, not a
physics one; happy to go into it in discussion if anyone's curious, but
the important claim for this room is the next slide: however we got the
Jacobian, we checked it.
-->

---
layout: center
---

# Verification

<div class="text-4xl pt-8 font-mono opacity-90">
&lt; 1e-8
</div>
<div class="text-sm pt-2 opacity-60">
relative error, analytic vs. automatic-differentiation Jacobian
</div>

<!--
Two independent checks, both load-bearing:

1. The hand-derived analytic Jacobian is checked against Gridap's own
   automatic differentiation of the same residual — to a relative
   Frobenius-norm error under 1e-8, i.e. machine precision for this
   problem, on both the BDF1 and BDF2 branches. This is a regression
   test that runs in CI, not a one-off check — if anyone changes a
   nonlinear term in the residual and forgets to update the analytic
   Jacobian to match, this test fails loudly.

2. Separately — because a correct Jacobian doesn't prove the discretized
   equations themselves are right — the whole nonlinear system is
   checked against the Method of Manufactured Solutions: pick an
   arbitrary smooth function for every field, substitute it into the PDE
   to derive exactly the source term that makes it an exact solution,
   then confirm the solver actually converges to that manufactured
   solution to near machine precision. This tests the solver's
   correctness independent of whether the manufactured solution is
   physically realistic — it's a math check, not a physics check.

Together: we're not just trusting that the plots look plausible. Every
term in the residual and Jacobian has been exercised against a
ground truth with a known, exact answer.
-->

---
layout: center
---

# Results

<div class="grid grid-cols-2 gap-4">
<div>
<video src="/phi.mp4" controls loop autoplay muted class="mx-auto rounded shadow" style="max-height:50vh"></video>
<div class="text-sm pt-2 opacity-60 text-center">Φ(t) — particle concentration</div>
</div>
<div>
<video src="/velocity.mp4" controls loop autoplay muted class="mx-auto rounded shadow" style="max-height:50vh"></video>
<div class="text-sm pt-2 opacity-60 text-center">|u|(t) — flow speed</div>
</div>
</div>

<!--
Same simulation, same timestamps, two views side by side — the flow
driving the migration (right) next to the concentration field it's
redistributing (left).

This is a deliberately adversarial initial condition, not a "nice" one:
cells are placed in the upper half of the disk at t=0 — which, since
these cells are less dense than the surrounding medium (buoyant), is
exactly the configuration buoyancy alone would want anyway. If buoyancy
were the only thing going on, the concentration field would just... sit
there.

What to watch for: does the concentration field visibly redistribute
away from that buoyancy-favored configuration as the simulation runs,
and does that redistribution track where the flow field is most active?
If yes, that's shear-induced migration actively fighting the passive
buoyant equilibrium, which is the qualitative claim the whole paper is
built on — that shear-induced migration is a real, non-negligible
transport mechanism in this geometry, not a small correction to
buoyancy.

Caveat to state plainly: this is a coarse mesh, short run, rendered for
qualitative illustration (frames interpolated for smooth playback, not
one frame per solved timestep) — not a converged production result.
That distinction matters to this audience and I'd rather say it than
have someone ask.
-->

---
layout: center
---

# Takeaways

- The paper's physics holds up — but wasn't internally consistent everywhere
- Every judgment call we made is disclosed, not buried
- The solver is verified against exact, known solutions — not just "it looks right"

<!--
Discussion prompts, pick whichever lands with this room:

- Is the 2D depth-averaged approximation (with a Hele-Shaw drag term
  standing in for the out-of-plane wall friction) actually defensible for
  this specific gap-to-radius geometry, or does it need a fully 3D
  treatment to trust quantitatively?
- Given the paper's own ambiguity in the shear-induced migration term
  (linear vs. quadratic in Φ), how much does that choice actually change
  the qualitative picture we just watched? That's an open question we
  haven't run down yet.
- More generally: how much should a reader trust a single-paper model
  when the paper itself has internal inconsistencies in its own core
  equations? What's the right level of skepticism vs. charitable
  interpretation when re-implementing someone else's model exactly this
  situation?

Close by inviting the room into whichever of these they want to pull on.
-->
