"""
manim-slides presentation: "Where Do the Cells Go?" -- a from-scratch,
Manim-native rebuild of the journal-club deck (previously a Slidev +
embedded-iframe hybrid, which fought Vite's asset serving at every turn).
Everything -- title, schematic, full equation derivation, judgment calls,
implementation, verification, results video, takeaways -- lives in this one
keystroke-triggered Manim scene. Presenter notes (this class's next_slide
`notes=` strings) carry the talk's actual narration; on-screen content stays
compact, matching the rest of this deck's style.

Render:
    manim-slides render -q h presentation.py Presentation
Present (keystroke-driven, arrow keys / space to advance):
    manim-slides present Presentation
Export to a self-contained, offline HTML player:
    manim-slides convert Presentation ../public/presentation.html --offline

Implementation note (carried over from the derivation-only script this
supersedes): Transform(A, B) mutates A in place and leaves it as the live
mobject; TransformMatchingTex/FadeTransform do not reliably follow that
contract. Every step below transforms FROM one tracked live mobject per
slot via the _start_*/_set_* helpers, confirmed correct by rendering and
inspecting frames, not just by reading the animation-class docs.
"""
from pathlib import Path

from manim import *
from manim_slides import Slide

EQ_FONT = 40
MAX_EQ_WIDTH = 12.3

RESULTS_VIDEO = Path(__file__).parent / "results_combined.mp4"


def eq(tex, font_size=EQ_FONT):
    m = MathTex(tex, font_size=font_size)
    if m.width > MAX_EQ_WIDTH:
        m.scale_to_fit_width(MAX_EQ_WIDTH)
    return m


class Presentation(Slide):
    def construct(self):
        # Persistent slide-number counter, bottom-right, present from the
        # first slide on -- a plain page number, not a paper-equation tag
        # (those live near their own equations instead). Updated in place
        # (never repositioned relative to another mobject), so it can't
        # trigger the frozen-frame corruption next_to() caused elsewhere.
        self._slide_no = 1
        self._page = Text("1", font_size=20, color=GRAY).to_corner(DR, buff=0.4)
        self.add(self._page)

        self.chapter_0_title()
        self.chapter_1_system()
        self.chapter_2_model()
        self.chapter_3_judgment_calls()
        self.chapter_4_implementation()
        self.chapter_5_verification()
        self.chapter_6_results()
        self.chapter_7_takeaways()

    def next_slide(self, *args, **kwargs):
        # Cut the current slide first (so its frozen frame keeps the OLD
        # number), then bump the counter for whatever comes next.
        result = super().next_slide(*args, **kwargs)
        self._slide_no += 1
        self._page.become(Text(str(self._slide_no), font_size=20, color=GRAY).to_corner(DR, buff=0.4))
        return result

    # ------------------------------------------------------------------
    def _header(self, text):
        # A persistent chapter heading -- created once, shown alongside the
        # chapter's first content (never as its own empty slide), and never
        # changed/re-captioned mid-chapter. All narration lives in notes.
        return Text(text, font_size=36, weight=BOLD).to_edge(UP, buff=0.5)

    def _start_eq(self, mobj):
        self.eq = mobj
        return self.eq

    def _set_eq(self, new_mobj, anim=TransformMatchingTex):
        self.play(anim(self.eq, new_mobj))
        self.eq = new_mobj

    def _hard_settle(self, fade_outs, fade_ins):
        # FadeOut's default remover only removes top-level scene mobjects; a
        # mobject nested inside a still-alive VGroup (as every term-isolated
        # substitution here is) never gets removed that way, and at low fps
        # the animation's own opacity tail can land a frame short of fully
        # settled -- both leave a faint residual outline of the "old" term
        # ghosting into the frozen paused frame. Force the exact end state
        # explicitly rather than trust the animation's tail frame.
        for m in fade_outs:
            self.remove(m)
            m.set_opacity(0)
        for m in fade_ins:
            m.set_opacity(1)

    # ------------------------------------------------------------------
    def chapter_0_title(self):
        title = Text("Where Do the Cells Go?", font_size=52, weight=BOLD)
        subtitle = Text(
            "Suspension dynamics in a rotating bioreactor", font_size=28, color=GRAY_B
        ).next_to(title, DOWN, buff=0.5)
        citation = Text(
            "Chao & Das (2015), Chem. Eng. J. -- re-implemented & verified",
            font_size=20, color=GRAY,
        ).next_to(subtitle, DOWN, buff=0.6)

        self.play(FadeIn(title, shift=UP * 0.3))
        self.play(FadeIn(subtitle))
        self.play(FadeIn(citation))
        self.next_slide(
            notes="""
            Open with the question, not the acronym: in a rotating bioreactor,
            what actually decides where the cells end up?

            Context for the room: NASA developed the HARV (High Aspect Ratio
            Vessel) -- a rotating-wall vessel -- specifically to grow cells in a
            low-shear, microgravity-analog environment. The whole point of
            rotating the vessel is to suspend cells without the mechanical
            stirring that would damage them. But "low shear" doesn't mean "no
            physics" -- there's still a real competition happening inside the
            vessel between forces that want to move cells around, and this talk
            is about that competition, the model Chao & Das wrote down for it,
            and a from-scratch verified implementation of that model.

            Roadmap: the physical system (2 min) -> the model (3-4 min) ->
            judgment calls we had to make, both the paper's and ours (3-4 min)
            -> our implementation and how we verified it (5-6 min) -> a
            qualitative result (2-3 min) -> discussion.
            """
        )
        self.play(FadeOut(title), FadeOut(subtitle), FadeOut(citation))

    # ------------------------------------------------------------------
    def chapter_1_system(self):
        title = Text("The System", font_size=40, weight=BOLD).to_edge(UP, buff=0.6)

        disk = Circle(radius=2.0, color=WHITE, stroke_width=2.5).shift(LEFT * 2.8)
        rot_arrow = CurvedArrow(
            disk.get_top() + RIGHT * 0.15,
            disk.get_right() + UP * 0.15,
            angle=-TAU / 5, color=WHITE, stroke_width=2.5,
        )
        omega_label = MathTex(r"\omega", font_size=32).move_to(disk.get_center())

        gap_top = Line(UP * 1.1, UP * 1.1 + RIGHT * 1.4, color=WHITE, stroke_width=2.5).shift(RIGHT * 2.6)
        gap_left = Line(UP * 1.1, DOWN * 1.1, color=WHITE, stroke_width=2.5).shift(RIGHT * 2.0)
        gap_right = Line(UP * 1.1, DOWN * 1.1, color=WHITE, stroke_width=2.5).shift(RIGHT * 3.2)
        gap_dash_top = DashedLine(gap_left.get_top(), gap_right.get_top(), color=GRAY, stroke_width=1.5)
        gap_dash_bot = DashedLine(gap_left.get_bottom(), gap_right.get_bottom(), color=GRAY, stroke_width=1.5)
        gap_label = Text("thin gap", font_size=22, color=GRAY_B).move_to(
            (gap_left.get_center() + gap_right.get_center()) / 2
        )

        schematic = VGroup(disk, rot_arrow, omega_label, gap_left, gap_right, gap_dash_top, gap_dash_bot, gap_label)

        self.play(FadeIn(title))
        self.play(Create(disk), FadeIn(omega_label))
        self.play(Create(rot_arrow))
        self.play(Create(gap_left), Create(gap_right), Create(gap_dash_top), Create(gap_dash_bot), FadeIn(gap_label))
        self.next_slide(
            notes="""
            The HARV: a horizontally-rotating, disk-shaped vessel with a very
            thin gap between two circular plates. Rotating the whole vessel --
            rather than stirring the fluid inside it with an impeller -- is
            what gets you the low-shear environment: in the frame of the
            vessel, the fluid mostly just goes along for the ride.

            But "mostly" is the operative word. Cells are denser or lighter
            than the medium (in this paper, actually lighter -- cells float),
            so gravity/buoyancy is always acting on them, all the time,
            independent of rotation. Meanwhile, wherever the flow does shear --
            near walls, near other cells -- there's a shear-induced migration
            effect that pushes particles around too, completely independent of
            buoyancy. Those two effects don't generally agree on where cells
            should go. That disagreement is the entire physical content of
            this talk.

            Chao & Das's contribution was to write down a continuum model -- a
            Suspension Balance Model -- that puts a number on both effects and
            couples them to the fluid flow and nutrient transport,
            self-consistently.
            """
        )
        self.play(FadeOut(title), FadeOut(schematic))

    # ------------------------------------------------------------------
    def chapter_2_model(self):
        self.chapter_2a_momentum()
        self.chapter_2b_continuity_transport()
        self.chapter_2c_flux_closure()
        self.chapter_2d_shear_rate()
        self.chapter_2e_assemble()
        self.chapter_2f_rest_of_model()
        self.chapter_2g_summary()

    def chapter_2a_momentum(self):
        header = self._header("Modeling. Momentum.")

        eq1 = VGroup(
            MathTex(r"\rho \frac{\partial \mathbf{u}}{\partial t}", font_size=30),
            MathTex(r"+ \rho (\mathbf{u}\cdot\nabla)\mathbf{u}", font_size=30),
            MathTex(r"= -\nabla p", font_size=30),
            MathTex(r"+ \nabla\cdot\left[\mu\left(\nabla\mathbf{u} + \nabla\mathbf{u}^{T}\right)\right]", font_size=30),
            MathTex(r"+", font_size=30),
            MathTex(r"\rho", font_size=30),
            MathTex(r"\mathbf{g}", font_size=30),
        ).arrange(RIGHT, buff=0.12)
        eq1.move_to(UP * 1.1)

        eq2 = MathTex(r"\rho = (1-\Phi)\rho_f^\circ + \Phi \rho_s^\circ", font_size=26)
        eq3 = MathTex(r"\mu = \mu_f \left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}", font_size=26)
        closures = VGroup(eq2, eq3).arrange(DOWN, buff=0.4).next_to(eq1, DOWN, buff=0.9)

        # Momentum and its two closures appear together -- they're all
        # needed to make Eq. 1 solvable, so the slide isn't one equation
        # sitting alone.
        self.play(FadeIn(header), Write(eq1))
        self.play(FadeIn(closures))
        self.next_slide(
            notes="""
            This is the derivation, live: a keystroke-triggered walkthrough of
            every numbered equation in the paper (Eq. 1-26, 28). On-screen
            content stays compact -- a persistent chapter header plus the
            equations and their numbers, nothing that narrates itself. This
            spoken narration carries the why.

            Momentum balance (Eq. 1) needs two closures before it's a
            solvable system: mixture density (Eq. 2) and the Krieger-
            Dougherty viscosity law (Eq. 3). Both are independent
            constitutive relations, not derived from the momentum balance --
            shown together with it rather than as a continuation of its
            algebra.
            """
        )

        # Real substitution: highlight, then make room, then swap -- in
        # that order. The trailing "g" has to move out of the way BEFORE
        # the wider bracket appears, or the new content and "g" would
        # briefly occupy the same space.
        self.play(eq1[5].animate.set_color(ORANGE), eq2.animate.set_color(ORANGE))
        rho_expr = MathTex(
            r"\left[(1-\Phi)\rho_f^\circ + \Phi \rho_s^\circ\right]", font_size=30, color=ORANGE
        )
        rho_expr.move_to(eq1[5], aligned_edge=LEFT)
        shift = rho_expr.width - eq1[5].width
        if shift > 1e-3:
            self.play(eq1[6].animate.shift(RIGHT * shift))
        self.play(FadeOut(eq1[5]), FadeIn(rho_expr))
        self._hard_settle([eq1[5]], [rho_expr])
        eq1.submobjects[5] = rho_expr
        self.next_slide(
            notes="""
            Plugging Eq. 2's mixture density into the gravity term of Eq. 1
            makes the buoyancy contribution explicit -- the term that has to
            carry the physics of "cells are lighter/denser than the medium."
            Only that one term changes; every other term in the momentum
            balance is the same mobject, untouched, which is the whole point
            of showing it this way instead of fading the whole line.
            """
        )
        self.play(FadeOut(header), FadeOut(eq1), FadeOut(closures))

    def chapter_2b_continuity_transport(self):
        header = self._header("Modeling. From two phases to one Φ-equation.")

        # --- Eq. 5, u_s isolated as its own addressable chunk ---
        eq5 = VGroup(
            MathTex(r"\frac{\partial \Phi}{\partial t}", font_size=32),
            MathTex(r"+ \nabla\cdot(\Phi", font_size=32),
            MathTex(r"\mathbf{u}_s", font_size=32),
            MathTex(r") = 0", font_size=32),
        ).arrange(RIGHT, buff=0.1).move_to(UP * 2.4)
        self.play(FadeIn(header), Write(eq5))
        self.next_slide()

        # --- Real substitution -- only u_s changes. Highlight, reveal the
        #     definition, make room, THEN swap -- in that order, so the
        #     trailing ")=0" is already out of the way before the wider
        #     replacement appears. ---
        self.play(eq5[2].animate.set_color(ORANGE))
        definition = MathTex(
            r"\mathbf{u}_s = \mathbf{u} + (1-c_s)\mathbf{u}_{slip}", font_size=26, color=ORANGE
        ).next_to(eq5, DOWN, buff=0.7)
        self.play(FadeIn(definition))
        self.next_slide()

        replacement = MathTex(
            r"\left(\mathbf{u} + (1-c_s)\mathbf{u}_{slip}\right)", font_size=32, color=ORANGE
        ).move_to(eq5[2], aligned_edge=LEFT)
        new_sign = MathTex(r"- \nabla\cdot(\Phi", font_size=32, color=ORANGE).move_to(eq5[1], aligned_edge=LEFT)
        shift = replacement.width - eq5[2].width
        if shift > 1e-3:
            self.play(eq5[3].animate.shift(RIGHT * shift))
        self.play(FadeOut(definition), FadeOut(eq5[1]), FadeOut(eq5[2]), FadeIn(new_sign), FadeIn(replacement))
        self._hard_settle([definition, eq5[1], eq5[2]], [new_sign, replacement])
        eq5.submobjects[1] = new_sign
        eq5.submobjects[2] = replacement
        self.next_slide(
            notes="""
            This is the derivation, live: a keystroke-triggered walkthrough of
            every numbered equation in the paper (Eq. 1-26, 28). On-screen
            content stays compact -- a persistent chapter header plus the
            equations, nothing that narrates itself. This spoken narration
            carries the why.

            Substituting u_s = u + (1-c_s) u_slip turns the solid-phase
            transport equation (Eq. 5) into Eq. 6. Only the u_s term changes
            -- the time-derivative and divergence wrapper are the same
            mobjects, untouched. The sign flip on the divergence term (+ to
            -) matches the paper's own Eq. 6 exactly as written.
            """
        )

        # --- Mixture continuity (Eq. 4): an independent relation, but kept
        #     visible alongside Eq. 6 rather than replacing it, since it's
        #     needed again two steps from now. Chunked so div(u) can be
        #     isolated in place. ---
        eq4 = VGroup(
            MathTex(r"(\rho_s^\circ-\rho_f^\circ)\left[\nabla\cdot\left(\Phi(1-c_s)\mathbf{u}_{slip}\right)\right]", font_size=26),
            MathTex(r"- \rho_f^\circ (\nabla\cdot\mathbf{u}) = 0", font_size=26),
        ).arrange(RIGHT, buff=0.1).next_to(eq5, DOWN, buff=1.1)
        self.play(FadeIn(eq4))
        self.next_slide(
            notes="""
            Mixture continuity (Eq. 4) is not derived from Eq. 5/6 -- it's a
            separate statement (conservation of total mixture mass). Kept on
            screen alongside Eq. 6 because both feed into the combination
            two steps from now.
            """
        )

        # Isolate div(u): highlight, then swap Eq. 4 for its rearranged
        # form (Eq. 8) -- a structural rearrangement, not a single term
        # growing in place, so there's no trailing content to displace.
        self.play(eq4[1].animate.set_color(ORANGE))
        eq8 = VGroup(
            MathTex(r"\nabla\cdot\mathbf{u}", font_size=28, color=ORANGE),
            MathTex(
                r"= \frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s",
                font_size=28,
            ),
        ).arrange(RIGHT, buff=0.15).move_to(eq4)
        self.play(FadeOut(eq4), FadeIn(eq8))
        self._hard_settle([eq4], [eq8])
        self.next_slide(
            notes="""
            Isolating div(u): move the rho_f-times-div(u) term to the other
            side and divide through by rho_f -- straightforward algebra,
            landing on Eq. 8. The bracketed slip-flux term from Eq. 4 is the
            same quantity the next chapter names J_s; written here already
            in that shorthand to keep this line readable. Eq. 6 stays on
            screen above -- Eq. 8 is about to combine with it.
            """
        )

        # --- Eq. 6 -> Eq. 7 (flux form, defines J_s), with Eq. 8 still
        #     visible below as the thing about to be substituted in. ---
        eq7 = VGroup(
            MathTex(r"\frac{\partial \Phi}{\partial t} + \nabla\cdot(\mathbf{u}\Phi)", font_size=30),
            MathTex(r"= -\frac{\nabla\cdot\mathbf{J}_s}{\rho_s^\circ}", font_size=30),
        ).arrange(RIGHT, buff=0.15).move_to(eq5)
        self.play(FadeOut(eq5), FadeIn(eq7))
        self._hard_settle([eq5], [eq7])
        self.next_slide(
            notes="""
            J_s is defined to absorb the slip-velocity terms from Eq. 6
            (J_s := rho_s * Phi * (1-c_s) * u_slip), dividing through by
            rho_s. Eq. 6's u.grad(Phi) advection term is unpacked into the
            div(u*Phi) form here to match the flux-conservation style used
            by Rao et al., which is the form the rest of the derivation
            builds on.
            """
        )

        # --- Expand via the product rule (adds a term -- Eq. 8 is still
        #     on screen, about to be substituted into it). ---
        expanded = VGroup(
            MathTex(r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi", font_size=30),
            MathTex(r"+ \Phi(\nabla\cdot\mathbf{u})", font_size=30, color=ORANGE),
            MathTex(r"= -\frac{\nabla\cdot\mathbf{J}_s}{\rho_s^\circ}", font_size=30),
        ).arrange(RIGHT, buff=0.12).move_to(eq7)
        self.play(FadeOut(eq7), FadeIn(expanded))
        self._hard_settle([eq7], [expanded])
        self.next_slide(
            notes="""
            Expanding div(u*Phi) via the product rule adds this new term --
            Eq. 8 (still visible below) is exactly what substitutes into it
            next.
            """
        )

        # Substitute Eq. 8's div(u): highlight, make room, THEN swap -- and
        # Eq. 8 fades out in the same beat since it's now used up.
        self.play(expanded[1].animate.set_color(ORANGE))
        kappa_term = MathTex(
            r"+ \Phi\,\kappa\,\nabla\cdot\mathbf{J}_s", font_size=30, color=ORANGE
        ).move_to(expanded[1], aligned_edge=LEFT)
        shift2 = kappa_term.width - expanded[1].width
        if shift2 > 1e-3:
            self.play(expanded[2].animate.shift(RIGHT * shift2))
        self.play(FadeOut(expanded[1]), FadeIn(kappa_term), FadeOut(eq8))
        self._hard_settle([expanded[1], eq8], [kappa_term])
        expanded.submobjects[1] = kappa_term
        note = Text(
            "The paper folds the remaining Φκ∇·J_s term into Eq. 10 without\n"
            "fully spelling out the step -- and its own text states the κ\n"
            "coefficient two different ways here. Flagged, not hidden.",
            font_size=20, color=YELLOW,
        ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(note))
        self.next_slide(
            notes="""
            kappa*div(J_s) substituted in, using Eq. 8. Two honest flags
            here, both disclosed on-screen rather than smoothed over:

            1. The Phi*kappa*div(J_s) term that appears when you expand
               div(u*Phi) via the product rule and substitute Eq. 8 isn't
               explicitly cancelled or justified in the paper's text -- this
               repo's own transcription of the paper already notes
               inconsistencies around Eqs. 7-10, and this is a concrete
               instance of it. Presenting a fabricated clean cancellation
               would be worse than flagging the gap.
            """
        )

        eq10 = eq(
            r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi"
            r"= \underbrace{\frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}}_{\kappa}"
            r"\,\nabla\cdot\mathbf{J}_s",
            font_size=32,
        ).move_to(expanded)
        self.play(FadeOut(expanded), FadeIn(eq10))
        self._hard_settle([expanded], [eq10])
        dim_note = Text(
            "κ has units of inverse density -- a dimensional slip here is\n"
            "exactly the bug our own test suite caught this session.",
            font_size=20, color=YELLOW,
        ).to_edge(DOWN, buff=0.5)
        self.play(Transform(note, dim_note))
        self.next_slide(
            notes="""
            Landing on Eq. 10, the master Phi-transport equation. Kappa has
            units of inverse density -- a dimensional slip here is exactly
            the bug this session's physical-consistency test suite caught
            and fixed in our own code -- worth reinforcing on-screen since
            it's the same quantity.
            """
        )
        self.play(FadeOut(header), FadeOut(eq10), FadeOut(note))

    def chapter_2c_flux_closure(self):
        header = self._header("Modeling. Closing the flux J_s.")

        # --- The flux decomposition and its two named pieces, all at once:
        #     independent closures, not a chain derived line-by-line. ---
        e11 = MathTex(r"\mathbf{J}_s = \mathbf{J}_{s\mu} + \mathbf{J}_{sc}", font_size=32)
        e12 = MathTex(r"\mathbf{J}_{sc} = -a^2\Phi^2 k_{sc}\nabla(\dot{\gamma}\Phi)", font_size=26)
        e13 = MathTex(r"\mathbf{J}_{s\mu} = -a^2\Phi^2 k_\mu \nabla(\ln \mu)", font_size=26)
        group_a = VGroup(e11, e12, e13).arrange(DOWN, buff=0.4, aligned_edge=LEFT).move_to(UP * 1.6)

        self.play(FadeIn(header), FadeIn(group_a))
        self.next_slide(
            notes="""
            These are independent modeling closures, not a chain where each
            line is derived from the last -- accumulated on screen together
            rather than replacing one another.

            J_s decomposes into two named pieces (Eq. 11): J_sc, the
            shear-induced migration flux (Eq. 12), and J_sμ, the flux from
            spatial viscosity variation (Eq. 13).
            """
        )

        # --- Real step: add sedimentation to get the hindered-settling
        #     form. group_a fades since it's now folded into this. ---
        e14 = VGroup(
            MathTex(
                r"\frac{\mathbf{J}_s}{\rho_s} = "
                r"-\left[\Phi D_\Phi \nabla(\dot{\gamma}\Phi) + \Phi^2 D_\mu \dot{\gamma}\nabla(\ln \mu)\right]",
                font_size=28,
            ),
            MathTex(r"- f_h \mathbf{u}_{st}\Phi", font_size=28, color=ORANGE),
        ).arrange(RIGHT, buff=0.1).move_to(UP * 1.6)
        self.play(FadeOut(group_a), FadeIn(e14))
        self.next_slide(
            notes="""
            Eq. 14 is Eqs. 12-13's bracketed terms (renamed D_Phi, D_mu, and
            divided through by rho_s) with one new physical effect added --
            the orange sedimentation term, -f_h*u_st*Phi -- that isn't in
            Eq. 11's decomposition at all. This is the hindered-settling
            closure the rest of the derivation uses.
            """
        )

        # --- The definitions Eq. 14 uses, all at once, kept alongside it. ---
        e1516 = MathTex(r"D_\Phi = 0.41 a^2 \qquad D_\mu = 0.62 a^2", font_size=28)
        e17 = MathTex(r"\mathbf{u}_{st} = \frac{2a^2(\rho_s-\rho_f)}{9\mu}\,\mathbf{g}", font_size=28)
        e18 = MathTex(r"f_h = \frac{\mu_f(1-\Phi_{avg})}{\mu}", font_size=28)
        group_b = VGroup(e1516, e17, e18).arrange(DOWN, buff=0.5, aligned_edge=LEFT).next_to(e14, DOWN, buff=0.9)

        self.play(FadeIn(group_b))
        self.next_slide(
            notes="""
            The empirical prefactors (Eq. 15-16), the Stokes settling
            velocity (Eq. 17, from balancing drag against buoyancy for a
            single sphere), and the hindered-settling function (Eq. 18,
            correcting Stokes' law for a crowd of particles rather than one
            isolated sphere) -- three independent definitions Eq. 14 relies
            on, accumulated together and kept alongside it rather than each
            replacing the last.
            """
        )
        self.play(FadeOut(header), FadeOut(e14), FadeOut(group_b))

    def chapter_2d_shear_rate(self):
        header = self._header("Modeling. Shear rate.")
        e_main = self._start_eq(eq(r"\dot{\boldsymbol{\gamma}} = \nabla\mathbf{u} + \nabla\mathbf{u}^{T}"))
        self.play(FadeIn(header), Write(e_main))
        self.next_slide()

        self._set_eq(
            eq(r"\dot{\gamma} = \left[\tfrac{1}{2}\left(\dot{\boldsymbol{\gamma}}\cdot\dot{\boldsymbol{\gamma}}\right)\right]^{1/2}")
        )
        self.next_slide()

        self._set_eq(
            eq(
                r"\dot{\gamma} = \left[\tfrac{1}{2}\left(4u_x^2 + 2(u_y+v_x)^2 + 4v_y^2\right)\right]^{1/2}"
            )
        )
        self.next_slide(
            notes="""
            The shear-rate tensor (Eq. 19) contracted with itself and
            square-rooted gives its scalar magnitude -- the general
            double-dot-product form first, then written out in components
            for this model's 2D velocity field (u, v) as Eq. 20. Two visible
            steps: the general contraction, then the component expansion --
            not one jump straight to the component form.
            """
        )
        self.play(FadeOut(header), FadeOut(self.eq))

    def chapter_2e_assemble(self):
        header = self._header("Modeling. Assembling the master Φ-equation.")

        # --- Show the two collected inputs, stacked (no claim yet that one
        #     morphs into the other) ---
        inputs = VGroup(
            MathTex(r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi = \kappa\,\nabla\cdot\mathbf{J}_s", font_size=28),
            MathTex(r"\frac{\mathbf{J}_s}{\rho_s} = -\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right] - f_h\mathbf{u}_{st}\Phi", font_size=28),
        ).arrange(DOWN, buff=0.5)
        self.play(FadeIn(header), Write(inputs))
        self.next_slide(
            notes="""
            The two pieces going into this assembly: Eq. 10 (the master
            Phi-transport equation, with kappa left as a symbol) and Eq. 14
            (the hindered-settling flux closure that kappa*div(J_s) is about
            to absorb).
            """
        )
        self.play(FadeOut(inputs))

        # --- Real chain: substitute J_s into Eq. 10's RHS term by term ---
        hero = VGroup(
            MathTex(r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi =", font_size=30),
            MathTex(r"\kappa\,\nabla\cdot\mathbf{J}_s", font_size=30),
        ).arrange(RIGHT, buff=0.15).move_to(UP * 1.5)
        self.play(Write(hero))
        self.next_slide()

        self.play(hero[1].animate.set_color(ORANGE))
        step1 = MathTex(
            r"\kappa\,\rho_s\,\nabla\cdot\left\{-\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right] - f_h\mathbf{u}_{st}\Phi\right\}",
            font_size=26, color=ORANGE,
        ).move_to(hero[1], aligned_edge=LEFT)
        self.play(FadeOut(hero[1]), FadeIn(step1))
        self._hard_settle([hero[1]], [step1])
        hero.submobjects[1] = step1
        # Re-center unconditionally: hero[0] is a fixed-position left
        # anchor, so a wider right-hand side pushes the group's bounding
        # box off-center (and past the frame edge) even when its total
        # WIDTH is still under MAX_EQ_WIDTH -- checking width alone missed
        # this, confirmed by measuring get_left()/get_right() directly.
        hero.generate_target()
        if hero.target.width > MAX_EQ_WIDTH:
            hero.target.scale_to_fit_width(MAX_EQ_WIDTH)
        hero.target.move_to(UP * 1.5)
        self.play(MoveToTarget(hero))
        self.next_slide(
            notes="""
            J_s (divided by rho_s in Eq. 14) becomes rho_s times that same
            bracket once multiplied back through -- substituting it into
            kappa*div(J_s) is what starts turning Eq. 10 into Eq. 21.
            """
        )

        # --- Simplify kappa * rho_s -> a single coefficient ---
        kappa_calc = MathTex(
            r"\kappa\,\rho_s^\circ = \frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}\,\rho_s^\circ"
            r"= \frac{\rho_f^\circ-\rho_s^\circ}{\rho_f^\circ}",
            font_size=26, color=ORANGE,
        ).next_to(hero, DOWN, buff=0.8)
        self.play(FadeIn(kappa_calc))
        self.next_slide(
            notes="""
            kappa = (rho_s - rho_f)/(rho_s*rho_f), so kappa*rho_s simplifies
            to (rho_f - rho_s)/rho_f -- the rho_s cancels. Eq. 21 as printed
            in the paper keeps this uncancelled, writing
            (rho_f-rho_s)/(rho_s*rho_f) * div(rho_s{...}) instead -- the same
            quantity, just not algebraically simplified. Shown both ways so
            it's clear they match rather than presenting the paper's more
            roundabout form as if it were the only way to write it.
            """
        )
        self.play(FadeOut(kappa_calc))

        # --- Substitute the Stokes-velocity / hindered-settling closures ---
        self.play(hero[1].animate.set_color(ORANGE))
        final_rhs = MathTex(
            r"\frac{\rho_f^\circ-\rho_s^\circ}{\rho_s^\circ\rho_f^\circ}\nabla\cdot \rho_s^\circ"
            r"\left\{"
            r"\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right]"
            r"- \Phi \frac{2\mu_f a^2(1-\Phi_{avg})(\rho_s-\rho_f)}{9\mu^2}\mathbf{g}"
            r"\right\}",
            font_size=24,
        ).move_to(hero[1], aligned_edge=LEFT)
        self.play(FadeOut(hero[1]), FadeIn(final_rhs))
        self._hard_settle([hero[1]], [final_rhs])
        hero.submobjects[1] = final_rhs
        hero.generate_target()
        if hero.target.width > MAX_EQ_WIDTH:
            hero.target.scale_to_fit_width(MAX_EQ_WIDTH)
        hero.target.move_to(UP * 1.5)
        self.play(MoveToTarget(hero))
        self.next_slide()

        note = Text(
            "This is the one equation that determines where the cells go.",
            font_size=26, color=YELLOW,
        ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(note))
        self.next_slide(
            notes="""
            Eq. 21: Stokes velocity (Eq. 17) and the hindered-settling
            function (Eq. 18) substituted into the settling term finishes
            the assembly. Every step from Eq. 10 to here was a concrete
            substitution or simplification, shown on the same line rather
            than skipped past -- this is the one equation that determines
            where the cells go, and now it's visible how it got built.
            """
        )
        self.play(FadeOut(header), FadeOut(hero), FadeOut(note))

    def chapter_2f_rest_of_model(self):
        header = self._header("Modeling. Rest of the model.")

        # --- Pair 1: boundary conditions ---
        e22 = MathTex(r"\tau_w = \frac{4\mu_f(\mathbf{u}-\mathbf{u}_w)}{L}", font_size=32)
        e23 = MathTex(r"\mathbf{u}_r = \omega (y,-x)", font_size=32)
        pair1 = VGroup(e22, e23).arrange(DOWN, buff=0.5)
        self.play(FadeIn(header), FadeIn(e22), FadeIn(e23))
        self.next_slide(
            notes="""
            Four independent relations round out the model -- none derived
            from each other, so they accumulate on screen in two related
            pairs rather than morphing one into the next. First pair: wall
            shear stress (Eq. 22) and the rotational wall velocity (Eq. 23)
            -- the two boundary conditions closing the momentum equation at
            the vessel wall. Independent of each other and of everything
            derived so far.
            """
        )
        self.play(FadeOut(pair1))

        # --- Pair 2: nutrient + growth ---
        e2425 = MathTex(
            r"\frac{dC}{dt} + \mathbf{u}\cdot\nabla C = D_f \nabla^2 C + r_c"
            r"\qquad r_c = -\mu_c \cdot d",
            font_size=30,
        )
        e26 = MathTex(r"\frac{\partial d}{\partial t} = k_c \cdot C \cdot d_0 \cdot e^{k_e t}", font_size=30)
        e28 = MathTex(r"\Phi = \frac{\pi}{6} d\, a^3", font_size=30)
        pair2 = VGroup(e2425, e26, e28).arrange(DOWN, buff=0.5)
        self.play(FadeIn(e2425), FadeIn(e26), FadeIn(e28))
        self.next_slide(
            notes="""
            Second pair: nutrient transport and consumption (Eq. 24-25),
            the cell-growth kinetics driven by that nutrient (Eq. 26), and
            the relation between cell density and volume fraction (Eq. 28)
            that feeds growth back into Phi. Three more independent
            relations, accumulated together rather than chained by fade.
            """
        )
        self.play(FadeOut(header), FadeOut(pair2))

    def chapter_2g_summary(self):
        title = Text("Every equation that defines the model", font_size=32, weight=BOLD).to_edge(UP)

        rows = [
            ("Momentum", r"\rho \dot{\mathbf{u}} + \rho(\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p + \nabla\cdot[\mu(\nabla\mathbf{u}+\nabla\mathbf{u}^T)] + \rho\mathbf{g}"),
            ("Mixture density / viscosity", r"\rho=(1-\Phi)\rho_f^\circ+\Phi\rho_s^\circ \quad \mu=\mu_f(1-\Phi/\Phi_{\max})^{-2.5\Phi_{\max}}"),
            ("Φ-transport (master eq.)", r"\dot{\Phi} + \mathbf{u}\cdot\nabla\Phi = \kappa\,\nabla\cdot\mathbf{J}_s"),
            ("Flux closure", r"\mathbf{J}_s/\rho_s = -[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)] - f_h\mathbf{u}_{st}\Phi"),
            ("Shear rate", r"\dot{\gamma} = [\tfrac{1}{2}(\dot{\boldsymbol{\gamma}}:\dot{\boldsymbol{\gamma}})]^{1/2}"),
            ("Nutrient", r"\dot{C} + \mathbf{u}\cdot\nabla C = D_f\nabla^2 C + r_c"),
            ("Growth", r"\dot{d} = k_c\, C\, d_0\, e^{k_e t} \qquad \Phi = \tfrac{\pi}{6} d\, a^3"),
        ]
        lines = VGroup()
        for label, tex in rows:
            lbl = Text(label + ":  ", font_size=20, color=BLUE_C)
            e = MathTex(tex, font_size=22)
            line = VGroup(lbl, e).arrange(RIGHT, buff=0.15)
            if line.width > 13.0:
                line.scale_to_fit_width(13.0)
            lines.add(line)
        lines.arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        lines.scale_to_fit_width(13.0)
        lines.next_to(title, DOWN, buff=0.5)

        self.play(FadeIn(title))
        self.play(LaggedStart(*[FadeIn(l) for l in lines], lag_ratio=0.15))
        self.next_slide(
            notes="""
            The complete model, all in one place: momentum, mixture
            density/viscosity, the master Phi-transport equation, the flux
            closure, shear rate, and the nutrient/growth pair. Every one of
            these was built on screen earlier in this section -- nothing
            here is new, this is just the full picture side by side.
            """
        )
        self.play(FadeOut(title), FadeOut(lines))

    # ------------------------------------------------------------------
    def chapter_3_judgment_calls(self):
        title = Text("Judgment Calls", font_size=40, weight=BOLD).to_edge(UP, buff=0.6)
        col_paper = Text("the paper", font_size=28, color=GRAY_B).shift(LEFT * 3 + UP * 0.5)
        col_port = Text("our port", font_size=28, color=GRAY_B).shift(RIGHT * 3 + UP * 0.5)
        divider = Line(UP * 1.2, DOWN * 1.8, color=GRAY_D, stroke_width=1.5)

        self.play(FadeIn(title))
        self.play(FadeIn(col_paper), FadeIn(col_port), Create(divider))
        self.next_slide(
            notes="""
            This is the credibility slide, and it's worth real time here
            because an audience like this will (rightly) ask "how do you know
            your implementation matches the paper" -- and the honest answer
            is: in a few places, it can't, because the paper doesn't fully
            agree with itself.

            The paper's own inconsistencies:
            - Eq. 12 and Eq. 14 disagree on the power of Φ in the J_sc
              shear-induced-migration term -- one is linear in Φ, the other
              quadratic. These aren't two different regimes, they're the same
              term written twice with different exponents. We had to pick one
              (we went with Eq. 14's form) -- this is disclosed in the
              tutorial notebook, not buried.
            - The equation numbering itself skips/mismatches around Eq. 27 in
              the manuscript -- minor, but it's the kind of thing that makes
              you check everything else twice.

            Our own explicit approximations, disclosed the same way:
            - Φ_avg (used in the hindered-settling correction) should, by the
              model's own logic, be recomputed as a domain integral every
              timestep -- the code currently hardcodes it as a constant.
              Settling never adapts to the evolving concentration field. This
              is a real simplification, not a bug we're hiding -- flagged
              directly in the tutorial notebook.
            - The paper uses two distinct symbols for the growth-rate
              constant and the nutrient-consumption constant; our code
              currently reuses one parameter (kc) for both.
            - Caught, not disclosed-as-a-choice: the momentum equation's
              buoyancy term used bare g instead of ρg (Eq. 1's literal form)
              for most of this project -- briefly rationalized as avoiding
              double-counting with the settling flux J_st, but that
              rationalization doesn't hold: momentum (bulk flow) and J_st
              (migration relative to the bulk) are different equations, each
              needing its own buoyancy term. A bare, Φ-independent g can
              always be fully absorbed into the pressure field with zero
              effect on velocity -- so this bug meant buoyancy could never
              actually drive any flow, for any particle distribution. Found
              by the physical-consistency test suite (an exact
              rigid-body-rotation steady-state check), confirmed against the
              paper, and fixed. The right story for this room isn't "we made
              a defensible call" -- it's "our own tests caught a real bug in
              a place hand-inspection had missed."

            None of this is "the model is wrong" -- it's "here is exactly
            where we had to exercise judgment, and why," which is a more
            useful thing to tell a room of experts than a claim of perfect
            fidelity.
            """
        )
        self.play(FadeOut(title), FadeOut(col_paper), FadeOut(col_port), FadeOut(divider))

    # ------------------------------------------------------------------
    def chapter_4_implementation(self):
        title = Text("Implementation", font_size=40, weight=BOLD).to_edge(UP, buff=0.6)
        headline = Text("Julia · Gridap.jl", font_size=36, color=BLUE_C)
        subtitle = Text(
            "monolithic finite-element solver, 5 fields, 1 nonlinear system",
            font_size=22, color=GRAY_B,
        ).next_to(headline, DOWN, buff=0.5)

        self.play(FadeIn(title))
        self.play(FadeIn(headline))
        self.play(FadeIn(subtitle))
        self.next_slide(
            notes="""
            Rewritten from scratch as a monolithic finite-element solver: all
            five fields, one coupled nonlinear system, solved together each
            timestep with Newton's method (BackTracking line search for
            stability) -- not a segregated/split scheme where you solve for
            flow, then transport, then update, and hope it's consistent.
            Monolithic is more expensive per step but avoids splitting error
            entirely.

            Time discretization: BDF1 (backward Euler) for the first step,
            BDF2 for every step after, for better-than-first-order accuracy
            without a multi-stage scheme.

            One implementation detail worth a sentence if there's time:
            Gridap can differentiate the residual automatically (autodiff) to
            get the Jacobian for Newton's method, but doing that for this
            particular 5-field coupled system is expensive to compile -- so we
            hand-derived the Jacobian analytically instead. That's a
            compile-time/engineering story, not a physics one; happy to go
            into it in discussion if anyone's curious, but the important claim
            for this room is the next slide: however we got the Jacobian, we
            checked it.
            """
        )
        self.play(FadeOut(title), FadeOut(headline), FadeOut(subtitle))

    # ------------------------------------------------------------------
    def chapter_5_verification(self):
        title = Text("Verification", font_size=40, weight=BOLD).to_edge(UP, buff=0.6)
        number = Text("< 1e-8", font_size=56, font="monospace", color=GREEN_C)
        caption = Text(
            "relative error, analytic vs. automatic-differentiation Jacobian",
            font_size=20, color=GRAY_B,
        ).next_to(number, DOWN, buff=0.5)

        self.play(FadeIn(title))
        self.play(FadeIn(number))
        self.play(FadeIn(caption))
        self.next_slide(
            notes="""
            Two independent checks, both load-bearing:

            1. The hand-derived analytic Jacobian is checked against Gridap's
               own automatic differentiation of the same residual -- to a
               relative Frobenius-norm error under 1e-8, i.e. machine
               precision for this problem, on both the BDF1 and BDF2
               branches. This is a regression test that runs in CI, not a
               one-off check -- if anyone changes a nonlinear term in the
               residual and forgets to update the analytic Jacobian to match,
               this test fails loudly.

            2. Separately -- because a correct Jacobian doesn't prove the
               discretized equations themselves are right -- the whole
               nonlinear system is checked against the Method of Manufactured
               Solutions: pick an arbitrary smooth function for every field,
               substitute it into the PDE to derive exactly the source term
               that makes it an exact solution, then confirm the solver
               actually converges to that manufactured solution to near
               machine precision. This tests the solver's correctness
               independent of whether the manufactured solution is
               physically realistic -- it's a math check, not a physics
               check.

            Together: we're not just trusting that the plots look plausible.
            Every term in the residual and Jacobian has been exercised
            against a ground truth with a known, exact answer.
            """
        )
        self.play(FadeOut(title), FadeOut(number), FadeOut(caption))

    # ------------------------------------------------------------------
    def chapter_6_results(self):
        # Zero-animation slide: the entire content is the external video
        # (which already carries its own on-screen captions) -- no separate
        # bare-title card in front of it.
        self.next_slide(
            src=RESULTS_VIDEO,
            notes="""
            Same simulation, same timestamps, two views side by side -- the
            flow driving the migration (right) next to the concentration
            field it's redistributing (left).

            This is a deliberately adversarial initial condition, not a
            "nice" one: cells are placed in the upper half of the disk at
            t=0 -- which, since these cells are less dense than the
            surrounding medium (buoyant), is exactly the configuration
            buoyancy alone would want anyway. If buoyancy were the only thing
            going on, the concentration field would just... sit there.

            What to watch for: does the concentration field visibly
            redistribute away from that buoyancy-favored configuration as the
            simulation runs, and does that redistribution track where the
            flow field is most active? If yes, that's shear-induced migration
            actively fighting the passive buoyant equilibrium, which is the
            qualitative claim the whole paper is built on -- that
            shear-induced migration is a real, non-negligible transport
            mechanism in this geometry, not a small correction to buoyancy.

            Two caveats to state plainly, both on-screen as a compact note,
            not buried:
            1. The timestep here (dt=0.015s) was chosen specifically to
               resolve the Hele-Shaw drag relaxation time (tau ~ 0.04s) -- the
               one fast physical process in this model. An earlier attempt
               used a timestep ~60x too coarse for that timescale and the
               flow field never actually developed; this run's real
               transient is honestly resolved, not aliased past.
            2. Buoyancy is artificially scaled up by ~10^6 for this clip only
               (the note on-screen says so). The real Stokes settling
               velocity for these particles is nanometers/second --
               physically real, but it would take months to visibly cross
               the domain, useless for an illustrative video. Scaling it up
               makes buoyancy's pull visible on the same timescale as
               shear-induced migration, so the audience can watch the two
               effects compete directly. The momentum equation's own gravity
               term is untouched -- only the settling flux J_st is scaled,
               and only in this script.

            The simulated window is 30s -- about 3.75 vessel rotations and
            ~2.7 buoyancy-crossing times under the artificial scaling above --
            chosen so the field has room to settle into a repeating pattern
            rather than show a single partial transient. Otherwise:
            coarse-for-a-slide mesh, frames interpolated between real solves
            for smooth playback -- not a converged production result. That
            distinction matters to this audience and I'd rather say it than
            have someone ask.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_7_takeaways(self):
        title = Text("Takeaways", font_size=40, weight=BOLD).to_edge(UP, buff=0.6)
        points = BulletedList(
            "The paper's physics holds up -- but wasn't internally consistent everywhere",
            "Every judgment call we made is disclosed, not buried",
            "The solver is verified against exact, known solutions -- not just \"it looks right\"",
            font_size=26,
        )

        self.play(FadeIn(title))
        for i in range(len(points)):
            self.play(FadeIn(points[i]))
        self.next_slide(
            notes="""
            Discussion prompts, pick whichever lands with this room:

            - Is the 2D depth-averaged approximation (with a Hele-Shaw drag
              term standing in for the out-of-plane wall friction) actually
              defensible for this specific gap-to-radius geometry, or does it
              need a fully 3D treatment to trust quantitatively?
            - Given the paper's own ambiguity in the shear-induced migration
              term (linear vs. quadratic in Φ), how much does that choice
              actually change the qualitative picture we just watched? That's
              an open question we haven't run down yet.
            - More generally: how much should a reader trust a single-paper
              model when the paper itself has internal inconsistencies in its
              own core equations? What's the right level of skepticism vs.
              charitable interpretation when re-implementing someone else's
              model, exactly this situation?

            Close by inviting the room into whichever of these they want to
            pull on.
            """
        )
