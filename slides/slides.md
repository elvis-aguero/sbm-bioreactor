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

# The Model — Momentum

<v-switch transition="fade">

<template #0>
<div class="text-sm opacity-70 mb-2">Momentum balance</div>

$$
\rho \frac{\partial \mathbf{u}}{\partial t} + \rho (\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p + \nabla\cdot\left[\mu\left(\nabla\mathbf{u} + \nabla\mathbf{u}^{T}\right)\right] + \rho \mathbf{g}
$$

<div class="text-xs opacity-40 text-right">Eq. 1</div>
</template>

<template #1>
<div class="text-sm opacity-70 mb-2">closure: mixture density</div>

$$
\rho \frac{\partial \mathbf{u}}{\partial t} + \rho (\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p + \nabla\cdot\left[\mu\left(\nabla\mathbf{u} + \nabla\mathbf{u}^{T}\right)\right] + \textcolor{#c2410c}{\left[(1-\Phi)\rho_f^\circ + \Phi \rho_s^\circ\right]} \mathbf{g}
$$

<div class="text-xs opacity-40 text-right">Eq. 1, 2</div>
</template>

<template #2>
<div class="text-sm opacity-70 mb-2">closure: Krieger-Dougherty viscosity</div>

$$
\mu = \mu_f \left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}
$$

<div class="text-xs opacity-40 text-right">Eq. 3</div>
</template>

</v-switch>

<!--
Real KaTeX, not video: each click swaps in the next equation, with the
newly-introduced or changed piece colored so it's visually obvious what
just got substituted, rather than needing to re-read the whole line.
-->

---
layout: center
---

# From two phases to one Φ-equation

<v-switch transition="fade">

<template #0>
<div class="text-sm opacity-70 mb-2">solid-phase transport</div>

$$
\frac{\partial \Phi}{\partial t} + \nabla\cdot(\Phi \mathbf{u}_s) = 0
$$

<div class="text-xs opacity-40 text-right">Eq. 5</div>
</template>

<template #1>
<div class="text-sm opacity-70 mb-2">substitute: u_s = u + slip velocity</div>

$$
\frac{\partial \Phi}{\partial t} - \nabla\cdot\left[\Phi\left(\mathbf{u} + \textcolor{#c2410c}{(1-c_s)\mathbf{u}_{slip}}\right)\right] = 0
$$

<div class="text-xs opacity-40 text-right">Eq. 5, 6</div>
</template>

<template #2>
<div class="text-sm opacity-70 mb-2">define the migration flux J_s</div>

$$
\frac{\partial \Phi}{\partial t} + \nabla\cdot(\mathbf{u}\Phi) = \textcolor{#c2410c}{-\frac{\nabla\cdot\mathbf{J}_s}{\rho_s^\circ}}
$$

<div class="text-xs opacity-40 text-right">Eq. 7</div>
</template>

<template #3>
<div class="text-sm opacity-70 mb-2">meanwhile, mixture continuity</div>

$$
(\rho_s^\circ-\rho_f^\circ)\left[\nabla\cdot\left(\Phi(1-c_s)\mathbf{u}_{slip}\right)\right] - \rho_f^\circ (\nabla\cdot\mathbf{u}) = 0
$$

<div class="text-xs opacity-40 text-right">Eq. 4</div>
</template>

<template #4>
<div class="text-sm opacity-70 mb-2">rearrange: continuity in terms of ∇·J_s</div>

$$
\textcolor{#c2410c}{\nabla\cdot\mathbf{u}} = \frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s
$$

<div class="text-xs opacity-40 text-right">Eq. 8</div>
</template>

<template #5>
<div class="text-sm opacity-70 mb-2">combine with Eq. 7: the master Φ-transport equation</div>

$$
\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi = \underbrace{\frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}}_{\textcolor{#c2410c}{\kappa}}\,\nabla\cdot\mathbf{J}_s
$$

<div class="text-xs opacity-40 text-right">Eq. 10</div>
<div class="text-xs pt-2" style="color:#c2410c">κ has units of inverse density — a dimensional slip here is exactly the bug our own test suite caught this session.</div>
</template>

</v-switch>

---
layout: center
---

# Closing the flux J_s

<v-switch transition="fade">

<template #0>
<div class="text-sm opacity-70 mb-2">decompose J_s</div>

$$
\mathbf{J}_s = \mathbf{J}_{s\mu} + \mathbf{J}_{sc}
$$

<div class="text-xs opacity-40 text-right">Eq. 11</div>
</template>

<template #1>
<div class="text-sm opacity-70 mb-2">shear-induced migration flux</div>

$$
\mathbf{J}_{sc} = -a^2\Phi^2 k_{sc}\nabla(\dot{\gamma}\Phi)
$$

<div class="text-xs opacity-40 text-right">Eq. 12</div>
</template>

<template #2>
<div class="text-sm opacity-70 mb-2">viscosity-gradient flux</div>

$$
\mathbf{J}_{s\mu} = -a^2\Phi^2 k_\mu \nabla(\ln \mu)
$$

<div class="text-xs opacity-40 text-right">Eq. 13</div>
</template>

<template #3>
<div class="text-sm opacity-70 mb-2">add sedimentation, divide by ρ_s: hindered settling</div>

$$
\frac{\mathbf{J}_s}{\rho_s} = -\left[\Phi D_\Phi \nabla(\dot{\gamma}\Phi) + \Phi^2 D_\mu \dot{\gamma}\nabla(\ln \mu)\right] \textcolor{#c2410c}{- f_h \mathbf{u}_{st}\Phi}
$$

<div class="text-xs opacity-40 text-right">Eq. 14</div>
</template>

<template #4>
<div class="text-sm opacity-70 mb-2">empirical prefactors</div>

$$
D_\Phi = 0.41 a^2 \qquad D_\mu = 0.62 a^2
$$

<div class="text-xs opacity-40 text-right">Eq. 15, 16</div>
</template>

<template #5>
<div class="text-sm opacity-70 mb-2">Stokes settling velocity</div>

$$
\mathbf{u}_{st} = \frac{2a^2(\rho_s-\rho_f)}{9\mu}\,\mathbf{g}
$$

<div class="text-xs opacity-40 text-right">Eq. 17</div>
</template>

<template #6>
<div class="text-sm opacity-70 mb-2">hindered-settling function</div>

$$
f_h = \frac{\mu_f(1-\Phi_{avg})}{\mu}
$$

<div class="text-xs opacity-40 text-right">Eq. 18</div>
</template>

</v-switch>

---
layout: center
---

# Shear rate

<v-switch transition="fade">

<template #0>
<div class="text-sm opacity-70 mb-2">shear-rate tensor</div>

$$
\dot{\boldsymbol{\gamma}} = \nabla\mathbf{u} + \nabla\mathbf{u}^{T}
$$

<div class="text-xs opacity-40 text-right">Eq. 19</div>
</template>

<template #1>
<div class="text-sm opacity-70 mb-2">its scalar magnitude</div>

$$
\dot{\gamma} = \left[\tfrac{1}{2}\left(\dot{\boldsymbol{\gamma}}\cdot\dot{\boldsymbol{\gamma}}\right)\right]^{1/2} = \textcolor{#c2410c}{\left[\tfrac{1}{2}\left(4u_x^2 + 2(u_y+v_x)^2 + 4v_y^2\right)\right]^{1/2}}
$$

<div class="text-xs opacity-40 text-right">Eq. 20</div>
</template>

</v-switch>

---
layout: center
---

# Assemble: the master Φ-equation

<v-switch transition="fade">

<template #0>
<div class="text-sm opacity-70 mb-2">Eq. 10 + Eq. 14-18, combined</div>

$$
\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi = \kappa\,\nabla\cdot\mathbf{J}_s
$$

$$
\frac{\mathbf{J}_s}{\rho_s} = -\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right] - f_h\mathbf{u}_{st}\Phi
$$

<div class="text-xs opacity-40 text-right">Eq. 10, 14-18</div>
</template>

<template #1>
<div class="text-sm opacity-70 mb-2">assembled — this is the one equation that determines where the cells go</div>

$$
\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi = \frac{\rho_f^\circ-\rho_s^\circ}{\rho_s^\circ\rho_f^\circ}\nabla\cdot \rho_s^\circ\left\{\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right]- \Phi \frac{2\mu_f a^2(1-\Phi_{avg})(\rho_s-\rho_f)}{9\mu^2}\mathbf{g}\right\}
$$

<div class="text-xs opacity-40 text-right">Eq. 21</div>
</template>

</v-switch>

---
layout: center
---

# The rest of the model

<v-switch transition="fade">

<template #0>
<div class="text-sm opacity-70 mb-2">wall shear & rotational boundary</div>

$$
\tau_w = \frac{4\mu_f(\mathbf{u}-\mathbf{u}_w)}{L} \qquad \mathbf{u}_r = \omega (y,-x)
$$

<div class="text-xs opacity-40 text-right">Eq. 22, 23</div>
</template>

<template #1>
<div class="text-sm opacity-70 mb-2">nutrient transport & consumption</div>

$$
\frac{dC}{dt} + \mathbf{u}\cdot\nabla C = D_f \nabla^2 C + r_c \qquad r_c = -\mu_c \cdot d
$$

<div class="text-xs opacity-40 text-right">Eq. 24, 25</div>
</template>

<template #2>
<div class="text-sm opacity-70 mb-2">growth kinetics</div>

$$
\frac{\partial d}{\partial t} = k_c \cdot C \cdot d_0 \cdot e^{k_e t}
$$

<div class="text-xs opacity-40 text-right">Eq. 26</div>
</template>

<template #3>
<div class="text-sm opacity-70 mb-2">Φ ↔ cell density</div>

$$
\Phi = \frac{\pi}{6} d\, a^3
$$

<div class="text-xs opacity-40 text-right">Eq. 28</div>
</template>

</v-switch>

---
layout: center
---

# The Complete Model

<div class="text-sm space-y-3">

**Momentum:** $\rho \dot{\mathbf{u}} + \rho(\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p + \nabla\cdot[\mu(\nabla\mathbf{u}+\nabla\mathbf{u}^T)] + \rho\mathbf{g}$

**Mixture density / viscosity:** $\rho=(1-\Phi)\rho_f^\circ+\Phi\rho_s^\circ \quad \mu=\mu_f(1-\Phi/\Phi_{\max})^{-2.5\Phi_{\max}}$

**Φ-transport (master eq.):** $\dot{\Phi} + \mathbf{u}\cdot\nabla\Phi = \kappa\,\nabla\cdot\mathbf{J}_s$

**Flux closure:** $\mathbf{J}_s/\rho_s = -[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)] - f_h\mathbf{u}_{st}\Phi$

**Shear rate:** $\dot{\gamma} = [\tfrac{1}{2}(\dot{\boldsymbol{\gamma}}:\dot{\boldsymbol{\gamma}})]^{1/2}$

**Nutrient:** $\dot{C} + \mathbf{u}\cdot\nabla C = D_f\nabla^2 C + r_c$

**Growth:** $\dot{d} = k_c\, C\, d_0\, e^{k_e t} \qquad \Phi = \tfrac{\pi}{6} d\, a^3$

</div>

<!--
Every equation that defines the model, together, on one screen — the
payoff after walking through where each one came from.

This whole section (7 slides, ~25 keystroke-driven equation steps) is
native Slidev/KaTeX + v-switch, not a video. Each click swaps in the
next equation via a real Vue transition; the newly-introduced or
changed term is colored so the "how it simplifies, combines, and gets
to where it ends up" is visible without a full re-derivation each time,
and it's real, selectable, crisp-at-any-resolution math text, not
rendered video frames.

(An earlier version of this section used Manim to bake the derivation
into a video, embedded via an interactive manim-slides player. That
depended on an external CDN, corrupted its own embedded video streams
under one export mode, and left videos stuck failing to load under
another -- three separate integration bugs, each only caught by actually
opening the result in a browser. Dropping video entirely for what
Slidev already does natively removed all three at once, along with the
mismatch between "a video of equations" and what was actually asked
for: real, live, keystroke-triggered equation transitions.)
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
- Caught, not disclosed-as-a-choice: the momentum equation's buoyancy
  term used bare g instead of ρg (Eq. 1's literal form) for most of this
  project — briefly rationalized as avoiding double-counting with the
  settling flux J_st, but that rationalization doesn't hold: momentum
  (bulk flow) and J_st (migration relative to the bulk) are different
  equations, each needing its own buoyancy term. A bare, Φ-independent g
  can always be fully absorbed into the pressure field with zero effect
  on velocity — so this bug meant buoyancy could never actually drive
  any flow, for any particle distribution. Found by the physical-
  consistency test suite (an exact rigid-body-rotation steady-state
  check), confirmed against the paper, and fixed. The right story for
  this room isn't "we made a defensible call" — it's "our own tests
  caught a real bug in a place hand-inspection had missed."

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

<div class="text-xs pt-4 opacity-50 text-center">
buoyancy artificially scaled ~10⁶× to be visible on this clip — real Stokes settling is ~nm/s
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

Two caveats to state plainly, both on-slide as a compact note, not buried:

1. The timestep here (dt=0.015s) was chosen specifically to resolve the
   Hele-Shaw drag relaxation time (τ≈0.04s) — the one fast physical
   process in this model. An earlier attempt used a timestep ~60x too
   coarse for that timescale and the flow field never actually developed;
   this run's real transient is honestly resolved, not aliased past.
2. Buoyancy is artificially scaled up by ~10^6 for this clip only (the
   note on-slide says so). The real Stokes settling velocity for these
   particles is nanometers/second — physically real, but it would take
   months to visibly cross the domain, useless for an illustrative
   video. Scaling it up makes buoyancy's pull visible on the same
   timescale as shear-induced migration, so the audience can watch the
   two effects compete directly. The momentum equation's own gravity term
   is untouched — only the settling flux J_st is scaled, and only in this
   script.

The simulated window is 30s — about 3.75 vessel rotations and ~2.7
buoyancy-crossing times under the artificial scaling above — chosen so the
field has room to settle into a repeating pattern rather than show a single
partial transient. Otherwise: coarse-for-a-slide mesh, frames interpolated
between real solves for smooth playback — not a converged production
result. That distinction matters to this audience and I'd rather say it
than have someone ask.
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
