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

import numpy as np
from manim import *
from manim_slides import Slide

EQ_FONT = 40
MAX_EQ_WIDTH = 12.3

RESULTS_VIDEO = Path(__file__).parent / "results_combined.mp4"
# The paper's own Figures 7 and 10, cropped verbatim (no redrawing) from
# assets/Chao_Das_2015.pdf pages 25 and 28 -- used as-is, not schematics
# standing in for them.
PAPER_FIGURE_7 = Path(__file__).parent.parent.parent / "assets" / "Chao_Das_2015_figure7.png"
PAPER_FIGURE_10 = Path(__file__).parent.parent.parent / "assets" / "Chao_Das_2015_figure10.png"


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
        self.chapter_4_implementation()
        self.chapter_6_results()
        self.chapter_6a_paper_results()
        self.chapter_6b_paper_discussion()
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

    def _legend(self, *lines, font_size=18):
        # Small, gray, left-aligned term definitions. Callers position
        # this with .to_corner(DL, buff=0.4) -- flush to the bottom of the
        # frame, never mid-screen -- and fade it out after a couple of
        # slides once the symbols are established, not for the whole
        # chapter. Tex (not MathTex) so each line can mix $...$ symbols
        # with plain words.
        rows = VGroup(*[Tex(line, font_size=font_size, color=GRAY_B) for line in lines])
        rows.arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        return rows

    def _name(self, text, target):
        # A short name label shown above an equation the FIRST time it's
        # introduced -- e.g. "Momentum". Later derivations/substitutions
        # of that same equation inherit the name silently; they never get
        # a new label of their own.
        return Text(text, font_size=20, color=BLUE_C).next_to(target, UP, buff=0.2, aligned_edge=LEFT)

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
            "An open-source reimplementation of Chao & Das (2015), Chem. Eng. J.",
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
            MathTex(r"- \nabla\cdot\left[\rho c_s(1-c_s)\mathbf{u}_{slip}\mathbf{u}_{slip}\right]", font_size=30),
            MathTex(r"+ \nabla\cdot\left[", font_size=30),
            MathTex(r"\mu", font_size=30),
            MathTex(r"\left(\nabla\mathbf{u} + \nabla\mathbf{u}^{T}\right)\right]", font_size=30),
            MathTex(r"+", font_size=30),
            MathTex(r"\rho", font_size=30),
            MathTex(r"\mathbf{g}", font_size=30),
        ).arrange(RIGHT, buff=0.12)
        eq1.to_edge(LEFT, buff=1.0).shift(UP * 1.1)
        # The line only ever grows as mu/rho get substituted in later
        # (placeholders are narrower than what replaces them), so the
        # FINAL, fully-substituted state is the widest this equation will
        # ever be. Measure that final state up front (never added to the
        # scene) and derive one scale factor from it, applied to eq1 now
        # AND to the later rho_expr/mu_expr -- so every stage of the
        # substitution animation stays consistently sized and the fully
        # expanded equation still fits, instead of overflowing only once
        # both substitutions have landed.
        _final_preview = VGroup(
            MathTex(r"\rho \frac{\partial \mathbf{u}}{\partial t}", font_size=30),
            MathTex(r"+ \rho (\mathbf{u}\cdot\nabla)\mathbf{u}", font_size=30),
            MathTex(r"= -\nabla p", font_size=30),
            MathTex(r"- \nabla\cdot\left[\rho c_s(1-c_s)\mathbf{u}_{slip}\mathbf{u}_{slip}\right]", font_size=30),
            MathTex(r"+ \nabla\cdot\left[", font_size=30),
            MathTex(r"\mu_f\left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}", font_size=30),
            MathTex(r"\left(\nabla\mathbf{u} + \nabla\mathbf{u}^{T}\right)\right]", font_size=30),
            MathTex(r"+", font_size=30),
            MathTex(r"\left[(1-\Phi)\rho_f^\circ + \Phi \rho_s^\circ\right]", font_size=30),
            MathTex(r"\mathbf{g}", font_size=30),
        ).arrange(RIGHT, buff=0.12)
        eq1_scale = MAX_EQ_WIDTH / _final_preview.width if _final_preview.width > MAX_EQ_WIDTH else 1.0
        eq1.scale(eq1_scale)
        eq1.to_edge(LEFT, buff=1.0).shift(UP * 1.1)
        name1 = self._name("Momentum", eq1)

        eq2 = MathTex(r"\rho = (1-\Phi)\rho_f^\circ + \Phi \rho_s^\circ", font_size=26)
        eq3 = MathTex(r"\mu = \mu_f \left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}", font_size=26)
        closures = VGroup(eq2, eq3).arrange(DOWN, buff=0.4, aligned_edge=LEFT).next_to(eq1, DOWN, buff=0.9, aligned_edge=LEFT)
        name23 = self._name("Mixture density / viscosity", closures)

        legend = self._legend(
            r"$\rho$ -- mixture density \quad $\mathbf{u}$ -- velocity \quad $p$ -- pressure \quad $\mu$ -- mixture viscosity \quad $\mathbf{g}$ -- gravity",
            r"$\Phi$ -- particle volume fraction \quad $\rho_f^\circ,\ \rho_s^\circ$ -- fluid / particle density \quad $\mu_f$ -- fluid viscosity \quad $\Phi_{\max}$ -- max packing fraction",
            r"$c_s$ -- local mass fraction of solid \quad $\mathbf{u}_{slip}$ -- relative velocity between solid and fluid",
        ).to_corner(DL, buff=0.4)

        # Momentum and its two closures appear together -- they're all
        # needed to make Eq. 1 solvable, so the slide isn't one equation
        # sitting alone.
        self.play(FadeIn(header), FadeIn(name1), Write(eq1))
        self.play(FadeIn(name23), LaggedStartMap(FadeIn, closures, lag_ratio=0.3), FadeIn(legend))
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

            This is the paper's own Eq. 1 in full, including the
            slip-velocity stress term (third term) that earlier versions of
            this deck had silently dropped -- caught only when spot-checked
            against the printed page. It's quadratic in u_slip, which for
            this model is just the Stokes settling velocity (order
            nanometers/second), so it's many orders of magnitude smaller
            than the other terms here. We drop it for the rest of this
            derivation and in the actual solver -- a physically justified
            truncation, but one that needs to be said out loud rather than
            silently done, which is exactly what this note is doing.
            """
        )

        # Real substitution: highlight, then make room, then swap -- in
        # that order. Everything after the gravity term has to move out
        # of the way BEFORE the wider bracket appears, or the new content
        # would briefly overlap it.
        self.play(eq1[8].animate.set_color(ORANGE), eq2.animate.set_color(ORANGE), run_time=0.5)
        rho_expr = MathTex(
            r"\left[(1-\Phi)\rho_f^\circ + \Phi \rho_s^\circ\right]", font_size=30
        ).set_color(ORANGE)
        rho_expr.scale(eq1_scale)
        rho_expr.move_to(eq1[8], aligned_edge=LEFT)
        shift = rho_expr.width - eq1[8].width
        if shift > 1e-3:
            self.play(eq1[9].animate.shift(RIGHT * shift))
        self.play(FadeOut(eq1[8]), Write(rho_expr))
        self._hard_settle([eq1[8]], [rho_expr])
        eq1.submobjects[8] = rho_expr
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

        # Symmetric completion: Eq. 3 (the viscosity closure) gets plugged
        # in too, into the viscous-stress term -- both closures were shown
        # together, so both should end up used on screen, not just one.
        self.play(eq1[5].animate.set_color(ORANGE), eq3.animate.set_color(ORANGE), run_time=0.5)
        mu_expr = MathTex(
            r"\mu_f\left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}", font_size=30
        ).set_color(ORANGE)
        mu_expr.scale(eq1_scale)
        mu_expr.move_to(eq1[5], aligned_edge=LEFT)
        shift_mu = mu_expr.width - eq1[5].width
        if shift_mu > 1e-3:
            self.play(
                eq1[6].animate.shift(RIGHT * shift_mu), eq1[7].animate.shift(RIGHT * shift_mu),
                eq1[8].animate.shift(RIGHT * shift_mu), eq1[9].animate.shift(RIGHT * shift_mu),
            )
        self.play(FadeOut(eq1[5]), Write(mu_expr))
        self._hard_settle([eq1[5]], [mu_expr])
        eq1.submobjects[5] = mu_expr
        self.next_slide(
            notes="""
            Same for Eq. 3: the Krieger-Dougherty viscosity law plugged
            into the viscous-stress term. Both closures shown at the start
            of this slide are now actually used in the momentum balance,
            not just displayed alongside it.
            """
        )
        self.play(FadeOut(header), FadeOut(name1), FadeOut(eq1), FadeOut(name23), FadeOut(closures), FadeOut(legend))

    def chapter_2b_continuity_transport(self):
        header = self._header("Modeling. From two phases to one Φ-equation.")

        # --- Eq. 5, u_s isolated as its own addressable chunk. Named once
        #     here as "Phi-transport (master eq.)" -- every later step in
        #     this chapter is the SAME equation being rewritten, so it
        #     never gets a second name label. ---
        eq5 = VGroup(
            MathTex(r"\frac{\partial \Phi}{\partial t}", font_size=32),
            MathTex(r"+ \nabla\cdot(\Phi", font_size=32),
            MathTex(r"\mathbf{u}_s", font_size=32),
            MathTex(r") = 0", font_size=32),
        ).arrange(RIGHT, buff=0.1)
        eq5.to_edge(LEFT, buff=1.0).shift(UP * 1.9)
        name5 = self._name("Φ-transport (master eq.)", eq5)
        legend5 = self._legend(
            r"$\Phi$ -- particle volume fraction \quad $\mathbf{u}_s$ -- solid-phase velocity",
        ).to_corner(DL, buff=0.4)
        self.play(FadeIn(header), FadeIn(name5), Write(eq5), FadeIn(legend5))
        self.next_slide()

        # --- Real substitution -- only u_s changes. Highlight, reveal the
        #     definition, make room, THEN swap -- in that order, so the
        #     trailing ")=0" is already out of the way before the wider
        #     replacement appears. ---
        self.play(eq5[2].animate.set_color(ORANGE), run_time=0.5)
        definition = MathTex(
            r"\mathbf{u}_s = \mathbf{u} + (1-c_s)\mathbf{u}_{slip}", font_size=26
        ).set_color(ORANGE).next_to(eq5, DOWN, buff=0.6, aligned_edge=LEFT)
        # c_s appears in "definition" the moment it's shown, so the legend
        # has to define it right here too -- not one beat later, when it
        # would otherwise be sitting on screen undefined.
        new_legend5 = self._legend(
            r"$\Phi$ -- particle volume fraction \quad $c_s$ -- local solid fraction \quad $\mathbf{u}_{slip}$ -- slip velocity (solid $-$ fluid)",
        ).to_corner(DL, buff=0.4)
        self.play(FadeIn(definition), Transform(legend5, new_legend5))
        self.next_slide()

        replacement = MathTex(
            r"\left(\mathbf{u} + (1-c_s)\mathbf{u}_{slip}\right)", font_size=32
        ).set_color(ORANGE).move_to(eq5[2], aligned_edge=LEFT)
        # Same "+", not flipped to "-": this is a direct substitution of
        # u_s's own definition into Eq. 5, no rearrangement happens here,
        # so the sign can't change. Checked directly against the PDF page
        # image (not the OCR text or the markdown transcription, both of
        # which turned out to have this sign backwards) -- Eq. 6 keeps
        # Eq. 5's own "+".
        new_sign = MathTex(r"+ \nabla\cdot(\Phi", font_size=32).move_to(eq5[1], aligned_edge=LEFT)
        shift = replacement.width - eq5[2].width
        if abs(shift) > 1e-3:
            self.play(eq5[3].animate.shift(RIGHT * shift))
        self.play(
            FadeOut(definition), FadeOut(eq5[1]), FadeOut(eq5[2]),
            FadeIn(new_sign), FadeIn(replacement),
        )
        self._hard_settle([definition, eq5[1], eq5[2]], [new_sign, replacement])
        eq5.submobjects[1] = new_sign
        eq5.submobjects[2] = replacement
        # Name J_s explicitly, tied to the slip term that just landed.
        # It stays on screen -- not faded on the next beat -- until it's
        # actually exercised in the div(u) rearrangement several steps
        # below, so it never appears to vanish before being used.
        js_def = MathTex(
            r"\mathbf{J}_s := \rho_s^\circ\,\Phi\,(1-c_s)\,\mathbf{u}_{slip}", font_size=24
        ).set_color(ORANGE).next_to(legend5, UP, buff=0.25, aligned_edge=LEFT)
        self.play(FadeIn(js_def))
        self.next_slide(
            notes="""
            This is the derivation, live: a keystroke-triggered walkthrough of
            every numbered equation in the paper (Eq. 1-26, 28). On-screen
            content stays compact -- a persistent chapter header plus the
            equations, nothing that narrates itself. This spoken narration
            carries the why.

            Substituting u_s = u + (1-c_s) u_slip turns the solid-phase
            transport equation into Eq. 6. Only the u_s term changes -- the
            time-derivative and divergence wrapper are the same mobjects,
            untouched, same "+" sign as Eq. 5 (a direct substitution, not a
            rearrangement -- nothing here changes sign). Checked directly
            against the PDF page image for this one: this repo's earlier
            markdown transcription of the paper had this sign backwards,
            and the deck inherited that error until this pass.

            J_s is named right here, tied to the slip-velocity term that
            just appeared: rho_s times the (1-c_s)*u_slip piece. It stays
            up rather than fading immediately -- it isn't exercised until
            Eq. 4 gets rearranged in terms of it, a few steps from now.
            """
        )

        # --- Mixture continuity: an independent relation, named plainly
        #     (no claim about why it's separate -- just what it is). J_s's
        #     own definition stays up too: only the symbol legend's job is
        #     done here. A different, independent equation is now the
        #     focus, so the transport equation's just-substituted terms
        #     settle back to white -- orange should only ever mean "this
        #     is what's live right now." ---
        eq4 = VGroup(
            MathTex(r"(\rho_s^\circ-\rho_f^\circ)\left[\nabla\cdot\left(\Phi(1-c_s)\mathbf{u}_{slip}\right)\right]", font_size=26),
            MathTex(r"- \rho_f^\circ (\nabla\cdot\mathbf{u}) = 0", font_size=26),
        ).arrange(RIGHT, buff=0.1).next_to(eq5, DOWN, buff=1.2, aligned_edge=LEFT)
        eq4_label = self._name("Mixture continuity", eq4)
        self.play(
            FadeOut(legend5),
            FadeIn(eq4_label), FadeIn(eq4),
            eq5[1].animate.set_color(WHITE), eq5[2].animate.set_color(WHITE),
        )
        self.next_slide(
            notes="""
            Mixture continuity is not derived from Eq. 5/6 -- it's a
            separate statement (conservation of total mixture mass). Kept on
            screen alongside Eq. 6 because both feed into the combination
            two steps from now.
            """
        )

        # --- Eq. 4 -> Eq. 8, step 1 of 2: pure rearrangement. Move the
        #     rho_f*div(u) term across and divide through -- same symbols
        #     as Eq. 4, nothing renamed yet. That's the next step.
        #     Three persistent chunks from here through kappa's naming:
        #     eq8_lhs ("div(u) =") never changes again once written;
        #     eq8_frac (the fraction alone) changes twice -- gains a
        #     rho_s^o in the denominator below, then collapses to kappa a
        #     few beats later -- and only the fraction itself is
        #     redrawn each time, not the whole line; eq8_tail
        #     ("div(...)") changes once (the parenthetical becomes J_s
        #     below) and then never again, since eq8_named still ends in
        #     the identical "div(J_s)". ---
        self.play(eq4[0].animate.set_color(ORANGE), eq4[1].animate.set_color(ORANGE), run_time=0.5)
        eq8_lhs = MathTex(r"\nabla\cdot\mathbf{u} = ", font_size=28).set_color(ORANGE)
        eq8_frac = MathTex(r"\frac{\rho_s^\circ-\rho_f^\circ}{\rho_f^\circ}", font_size=28).set_color(ORANGE)
        eq8_tail = MathTex(r"\nabla\cdot\left(\Phi(1-c_s)\mathbf{u}_{slip}\right)", font_size=28).set_color(ORANGE)
        eq8_raw = VGroup(eq8_lhs, eq8_frac, eq8_tail).arrange(RIGHT, buff=0.08).move_to(eq4, aligned_edge=LEFT)
        self.play(FadeOut(eq4), FadeOut(eq4_label), Write(eq8_raw))
        self._hard_settle([eq4, eq4_label], [eq8_raw])
        self.next_slide(
            notes="""
            Step 1 of 2, pure algebra: move the rho_f*div(u) term to the
            other side and divide through by rho_f -- same symbols as
            Eq. 4, nothing renamed. Naming the bracket is the next,
            separate step.
            """
        )

        # --- Step 2 of 2: substitute, using J_s's definition -- still on
        #     screen, so its use here is visible rather than a symbol
        #     appearing from nowhere. Only the fraction (denominator
        #     picks up rho_s^o) and the tail (parenthetical -> J_s) are
        #     redrawn -- eq8_lhs is untouched, the same mobject as a beat
        #     ago. J_s stays up past this point too -- it's about to be
        #     reused again (Eq. 7's restated form below also ends in
        #     J_s), so its definition doesn't leave until that whole run
        #     of appearances is done. ---
        self.play(eq8_frac.animate.set_color(ORANGE), eq8_tail.animate.set_color(ORANGE), run_time=0.5)
        eq8_frac_v2 = MathTex(r"\frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}", font_size=28).set_color(ORANGE).move_to(eq8_frac, aligned_edge=LEFT)
        eq8_Js = MathTex(r"\nabla\cdot\mathbf{J}_s", font_size=28).set_color(ORANGE)
        shift_frac = eq8_frac_v2.width - eq8_frac.width
        if abs(shift_frac) > 1e-3:
            self.play(eq8_tail.animate.shift(RIGHT * shift_frac))
        eq8_Js.next_to(eq8_frac_v2, RIGHT, buff=0.08)
        self.play(FadeOut(eq8_frac), Write(eq8_frac_v2), FadeOut(eq8_tail), Write(eq8_Js))
        self._hard_settle([eq8_frac, eq8_tail], [eq8_frac_v2, eq8_Js])
        eq8_frac = eq8_frac_v2
        eq8_tail = eq8_Js
        eq8 = VGroup(eq8_lhs, eq8_frac, eq8_tail)
        self.next_slide(
            notes="""
            Step 2 of 2: the bracketed slip-flux term is exactly J_s/rho_s
            by the definition named a few steps ago -- substituted in
            here (the fraction's denominator picks up the matching
            rho_s^o). Landing on Eq. 8. J_s's own definition stays up a
            little longer: it reappears again shortly in Eq. 7's
            restated form below.
            """
        )

        # --- Name kappa here, as its own step -- not bundled with the
        #     substitution above, so this beat is "give this fraction a
        #     name" and nothing else. Only the fraction itself collapses
        #     to kappa -- eq8_lhs and eq8_tail (still "div(J_s)",
        #     unchanged) are untouched, just shift left to close the gap
        #     the shorter kappa leaves. Positioned below J_s's definition
        #     (still on screen) rather than the bare corner, so the two
        #     don't collide. ---
        kappa_def = MathTex(
            r"\kappa := \frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}", font_size=24
        ).set_color(ORANGE).next_to(js_def, DOWN, buff=0.2, aligned_edge=LEFT)
        self.play(eq8_frac.animate.set_color(ORANGE), run_time=0.5)
        eq8_kappa = MathTex(r"\kappa", font_size=28).set_color(ORANGE).move_to(eq8_frac, aligned_edge=LEFT)
        shift_kappa = eq8_kappa.width - eq8_frac.width
        self.play(FadeOut(eq8_frac), Write(eq8_kappa), eq8_tail.animate.shift(RIGHT * shift_kappa), FadeIn(kappa_def))
        self._hard_settle([eq8_frac], [eq8_kappa])
        eq8_frac = eq8_kappa
        eq8 = VGroup(eq8_lhs, eq8_frac, eq8_tail)
        self.next_slide(
            notes="""
            Naming (rho_s-rho_f)/(rho_s*rho_f) as kappa here, right when
            it first appears in a form worth naming. Kappa has units of
            inverse density -- worth a mental note but not a red flag,
            just this quantity's dimension.

            This equation (div(u) = kappa*div(J_s)) is independently
            re-derived from scratch and verified correct in
            scripts/verify_paper_equations.py -- not just carried over
            from the paper's own Eq. 8 on trust.
            """
        )

        # --- Eq. 6, step 1 of 2: distribute the divergence over the sum
        #     -- pure algebra (linearity of divergence), same sign
        #     convention as Eq. 6 itself, nothing renamed. The transport
        #     equation is the focus again, so its substituted terms come
        #     back to orange before being rewritten. eq5[0] (the time
        #     derivative) never changes across this whole chapter, so it
        #     stays put as a fixed anchor and the new pieces are built
        #     relative to it, instead of being refreshed for no reason. ---
        self.play(eq5[1].animate.set_color(ORANGE), eq5[2].animate.set_color(ORANGE), run_time=0.5)
        dist_a = MathTex(r"+ \nabla\cdot(\mathbf{u}\Phi)", font_size=32).set_color(ORANGE).next_to(eq5[0], RIGHT, buff=0.1)
        # dist_b is split into the term itself and the "=0" separately
        # (rather than one bundled chunk) so the next two steps can
        # animate them independently: rename the term in place first,
        # THEN move it across the equals sign as its own, later action.
        dist_b_term = MathTex(
            r"+ \nabla\cdot\left(\Phi(1-c_s)\mathbf{u}_{slip}\right)", font_size=32
        ).set_color(ORANGE).next_to(dist_a, RIGHT, buff=0.1)
        dist_b_rhs = MathTex(r"= 0", font_size=32).set_color(ORANGE).next_to(dist_b_term, RIGHT, buff=0.1)
        self.play(FadeOut(eq5[1]), FadeOut(eq5[2]), FadeOut(eq5[3]), Write(dist_a), Write(dist_b_term), Write(dist_b_rhs))
        self._hard_settle([eq5[1], eq5[2], eq5[3]], [dist_a, dist_b_term, dist_b_rhs])
        self.next_slide(
            notes="""
            Pure algebra, not the product rule (that's a later, separate
            step): distributing the divergence over the sum -- div(A+B) =
            div(A) + div(B) -- splits the u_s-substituted transport
            equation into a div(u*Phi) piece and a div(Phi*(1-c_s)*u_slip)
            piece, both still added on the left, "=0" on the right
            untouched. Nothing renamed yet, nothing moved yet -- that's
            the next two steps, kept separate on purpose.
            """
        )

        # --- Rename the second piece to J_s/rho_s^o, IN PLACE (still
        #     added, on the left, "=0" still on the right) -- the
        #     definition (js_def) is still fully visible while this
        #     rename happens, so the connection is never asserted off
        #     screen. Moving it across the equals sign is the NEXT,
        #     separate beat -- not bundled with the rename. ---
        self.play(
            dist_a.animate.set_color(WHITE), dist_b_term.animate.set_color(ORANGE),
            js_def.animate.set_color(ORANGE), run_time=0.5,
        )
        renamed_term = MathTex(r"+ \frac{\nabla\cdot\mathbf{J}_s}{\rho_s^\circ}", font_size=32).set_color(ORANGE).move_to(dist_b_term, aligned_edge=LEFT)
        shift_rename = renamed_term.width - dist_b_term.width
        if abs(shift_rename) > 1e-3:
            self.play(dist_b_rhs.animate.shift(RIGHT * shift_rename))
        self.play(FadeOut(dist_b_term), Write(renamed_term))
        self._hard_settle([dist_b_term], [renamed_term])
        self.next_slide(
            notes="""
            Renaming div(Phi*(1-c_s)*u_slip) to div(J_s)/rho_s^o, using
            the definition still visible below -- a rename, nothing more:
            still added, still on the left, "=0" still on the right,
            untouched.
            """
        )

        # --- NOW move it across the equals sign -- a real "term crosses,
        #     sign flips" action, its own beat. Eq. 6's sign is correct
        #     (fixed earlier this pass), so this is a genuine, verified
        #     term-by-term derivation, not a citation-based reformulation
        #     papering over a discrepancy. Verified independently in
        #     scripts/verify_paper_equations.py (Block 1, equation B). ---
        self.play(renamed_term.animate.set_color(ORANGE), dist_b_rhs.animate.set_color(ORANGE), run_time=0.5)
        piece1 = dist_a
        piece2 = MathTex(r"= -\frac{\nabla\cdot\mathbf{J}_s}{\rho_s^\circ}", font_size=32).next_to(piece1, RIGHT, buff=0.1)
        self.play(FadeOut(renamed_term), FadeOut(dist_b_rhs), Write(piece2), FadeOut(js_def))
        self._hard_settle([renamed_term, dist_b_rhs, js_def], [piece2])
        eq7 = VGroup(eq5[0], piece1, piece2)
        self.next_slide(
            notes="""
            The renamed term crosses the equals sign, picking up the
            minus sign that always comes with crossing -- landing on
            Eq. 7 exactly: div(u*Phi) stays on the left, div(J_s)/rho_s^o
            on the right with a minus. Independently re-derived and
            checked in scripts/verify_paper_equations.py -- this
            reproduces the paper's own Eq. 7 exactly.

            J_s's definition has now been visible through every one of
            its appearances in this run (Eq. 8, kappa, and here, right up
            through the rename that used it) and can finally leave.
            """
        )

        # --- Expand div(u*Phi) via the product rule: highlight it, shift
        #     the RHS out of the way to make room, THEN swap it for
        #     u.grad(Phi) and fade in the new Phi*div(u) term alongside --
        #     a genuine term-isolated insertion, not a whole-line fade.
        #     Eq. 8 (still on screen) is what substitutes into the new
        #     term next, so it stays visible through this step instead of
        #     fading before it's used. ---
        self.play(piece1.animate.set_color(ORANGE), piece2.animate.set_color(WHITE), run_time=0.5)
        u_dot_grad = MathTex(r"+\mathbf{u}\cdot\nabla\Phi", font_size=30).set_color(ORANGE).next_to(eq5[0], RIGHT, buff=0.1)
        new_term = MathTex(r"+ \Phi(\nabla\cdot\mathbf{u})", font_size=30).set_color(ORANGE).next_to(u_dot_grad, RIGHT, buff=0.12)
        added_width = u_dot_grad.width + 0.12 + new_term.width - piece1.width
        if abs(added_width) > 1e-3:
            self.play(piece2.animate.shift(RIGHT * added_width))
        self.play(FadeOut(piece1), Write(u_dot_grad), Write(new_term))
        self._hard_settle([piece1], [u_dot_grad, new_term])
        expanded = VGroup(eq5[0], u_dot_grad, new_term, piece2)
        self.next_slide(
            notes="""
            Product rule: div(u*Phi) = u.grad(Phi) + Phi*div(u) -- the
            first piece replaces div(u*Phi) in place, the second is a
            genuinely new term. Eq. 8 stays on screen below: it's exactly
            what substitutes into that new term next.
            """
        )

        # --- Substitute Eq. 8 (already named with kappa) into the new
        #     term -- a single rename, kappa already established, nothing
        #     new introduced here. Eq. 8 is finally exercised, so it
        #     fades along with it. ---
        self.play(new_term.animate.set_color(ORANGE), eq8.animate.set_color(ORANGE), run_time=0.5)
        kappa_term = MathTex(
            r"+ \Phi\,\kappa\,\nabla\cdot\mathbf{J}_s", font_size=30
        ).set_color(ORANGE).move_to(new_term, aligned_edge=LEFT)
        shift2 = kappa_term.width - new_term.width
        if abs(shift2) > 1e-3:
            self.play(expanded[3].animate.shift(RIGHT * shift2))
        self.play(FadeOut(new_term), Write(kappa_term), FadeOut(eq8))
        self._hard_settle([new_term, eq8], [kappa_term])
        expanded.submobjects[2] = kappa_term
        self.next_slide(
            notes="""
            div(u) = kappa*div(J_s), by Eq. 8, named a few steps ago --
            substituted here using that already-established name, so this
            step is a single rename, not a rename-and-define at once.
            Eq. 8 has now done its job and leaves the screen.
            """
        )

        # --- Real simplification, shown in four separate, genuine algebra
        #     steps -- nothing skipped, nothing asserted without the work
        #     shown. Verified end to end in
        #     scripts/verify_paper_equations.py (Block 1). ---

        # Step 1: cross the equals sign (sign flip), same pattern as the
        #     rename-then-move used a few beats ago for J_s itself.
        self.play(kappa_term.animate.set_color(ORANGE), run_time=0.5)
        rhs_term2 = MathTex(r"- \Phi\,\kappa\,\nabla\cdot\mathbf{J}_s", font_size=28).set_color(ORANGE).next_to(piece2, RIGHT, buff=0.1)
        self.play(FadeOut(kappa_term), Write(rhs_term2))
        self._hard_settle([kappa_term], [rhs_term2])
        self.next_slide(
            notes="""
            Step 1 of 5: Phi*kappa*div(J_s) crosses the equals sign, sign
            flipping to a minus, same as any term moving sides -- landing
            next to the -div(J_s)/rho_s^o already there. Nothing combined
            yet, that's the next step.
            """
        )

        # Step 2: expand kappa's own definition inline, in place, within
        #     this newly-moved term only.
        self.play(rhs_term2.animate.set_color(ORANGE), run_time=0.5)
        kappa_expanded_term = MathTex(
            r"- \Phi\,\frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s", font_size=24
        ).set_color(ORANGE).move_to(rhs_term2, aligned_edge=LEFT)
        self.play(FadeOut(rhs_term2), Write(kappa_expanded_term))
        self._hard_settle([rhs_term2], [kappa_expanded_term])
        self.next_slide(
            notes="""
            Step 2 of 5: expanding kappa back into (rho_s^o-rho_f^o)/
            (rho_s^o*rho_f^o), the name given a few chapters back -- a
            substitution, not a new definition. Still its own separate
            term, not yet combined with -div(J_s)/rho_s^o.
            """
        )

        # Step 3: put piece2 over the SAME common denominator FIRST,
        #     on its own, before combining anything -- -1/rho_s^o
        #     becomes -rho_f^o/(rho_s^o*rho_f^o) (multiply top and
        #     bottom by rho_f^o). Only once both terms visibly share one
        #     denominator does merging them into a single fraction next
        #     become a justified step rather than a jump.
        self.play(piece2.animate.set_color(ORANGE), run_time=0.5)
        piece2_common = MathTex(
            r"= -\frac{\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s", font_size=26
        ).set_color(ORANGE).move_to(piece2, aligned_edge=LEFT)
        shift_common = piece2_common.width - piece2.width
        if abs(shift_common) > 1e-3:
            self.play(kappa_expanded_term.animate.shift(RIGHT * shift_common))
        self.play(FadeOut(piece2), Write(piece2_common))
        self._hard_settle([piece2], [piece2_common])
        piece2 = piece2_common
        self.next_slide(
            notes="""
            Step 3 of 5: -1/rho_s^o, rewritten over the SAME denominator
            rho_s^o*rho_f^o that kappa_expanded_term already uses --
            multiply top and bottom by rho_f^o to get
            -rho_f^o/(rho_s^o*rho_f^o). Nothing combined yet: this is
            just putting the two terms on equal footing so the next step
            (adding numerators) is a real, followable action instead of
            an unexplained merge.
            """
        )

        # Step 4: NOW both terms share one visible denominator -- combine
        #     into a single fraction by adding numerators, div(J_s)
        #     factored out.
        self.play(piece2.animate.set_color(ORANGE), kappa_expanded_term.animate.set_color(ORANGE), run_time=0.5)
        combined_frac = MathTex(
            r"= -\frac{\rho_f^\circ + \Phi(\rho_s^\circ-\rho_f^\circ)}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s",
            font_size=26,
        ).set_color(ORANGE).move_to(piece2, aligned_edge=LEFT)
        self.play(FadeOut(piece2), FadeOut(kappa_expanded_term), Write(combined_frac))
        self._hard_settle([piece2, kappa_expanded_term], [combined_frac])
        self.next_slide(
            notes="""
            Step 4 of 5: both terms now share the same denominator
            rho_s^o*rho_f^o (the previous step's whole point) -- so
            adding their numerators, rho_f^o + Phi*(rho_s^o-rho_f^o),
            over that one shared denominator is a real combination, not
            an unexplained merge. div(J_s) factored out since both
            terms carry it.
            """
        )

        # Step 5: recognize the numerator as exactly Eq. 2's rho -- the
        #     payoff step, landing on the final, correct master equation.
        combined_rhs = MathTex(
            r"= -\frac{\rho}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s", font_size=30
        ).set_color(ORANGE).next_to(u_dot_grad, RIGHT, buff=0.1)
        self.play(FadeOut(combined_frac), Write(combined_rhs))
        self._hard_settle([combined_frac], [combined_rhs])
        master = VGroup(eq5[0], u_dot_grad, combined_rhs)
        self.next_slide(
            notes="""
            Step 5 of 5: rho_f^o + Phi*(rho_s^o-rho_f^o) expands to
            rho_f^o - Phi*rho_f^o + Phi*rho_s^o, exactly (1-Phi)*rho_f^o +
            Phi*rho_s^o -- Eq. 2's own rho, not a new quantity.
            Recognizing that lands on the correct master Phi-transport
            equation: -[rho/(rho_s^o*rho_f^o)]*div(J_s), re-derived from
            Eq. 5 with nothing borrowed from the paper's own Eq. 10.
            Every one of these four steps is machine-verified in
            scripts/verify_paper_equations.py.
            """
        )

        # --- Term-level comparison against the paper's own printed Eq.
        #     10, in red -- the term itself (what the paper calls this
        #     same coefficient), not a sentence about it. The label
        #     naming what's being compared is plain text; only the
        #     paper's actual term is colored. ---
        paper_label = Text("Paper's Eq. 10 instead:", font_size=18, color=GRAY_B)
        paper_kappa_term = MathTex(r"\kappa\,\nabla\cdot\mathbf{J}_s", font_size=24).set_color(RED)
        paper_tag = VGroup(paper_label, paper_kappa_term).arrange(RIGHT, buff=0.15).next_to(master, DOWN, buff=0.5, aligned_edge=LEFT)
        self.play(FadeIn(paper_tag))
        self.next_slide(
            notes="""
            The paper's own Eq. 10 uses kappa here instead of rho/
            (rho_s^o*rho_f^o) -- shown in red as the actual conflicting
            term, not narrated as a sentence on screen.

            Worth saying out loud: their own Eq. 10 states BOTH forms
            (kappa*div(J_s) and rho/(rho_s^o*rho_f^o)*div(J_s)) and
            claims they're equal. They aren't, in general -- confirmed
            symbolically and numerically about 20x apart at their own
            Table 1 densities, in scripts/verify_paper_equations.py.
            Separately, Eq. 21 (claimed to be Eq. 10 with the flux
            closure substituted in) prints yet a third, sign-flipped
            version of this same coefficient, with no algebraic step
            that should flip a sign. Our own re-derived coefficient here
            matches the paper's rho/(rho_s^o*rho_f^o) form in magnitude
            but not sign, and doesn't match kappa at all -- kappa isn't
            even Phi-dependent, so it can't be right for a coefficient
            that genuinely varies with Phi through rho.

            This is what "the paper as a starting point, not ground
            truth" means in practice: re-derive it, don't transcribe it.
            """
        )
        self.play(
            FadeOut(header), FadeOut(name5), FadeOut(kappa_def),
            FadeOut(master), FadeOut(paper_tag),
        )

    def chapter_2c_flux_closure(self):
        header = self._header("Modeling. Closing the flux J_s.")

        # --- The flux decomposition and its two named pieces, all at once:
        #     independent closures, not a chain derived line-by-line. A
        #     sentence of physics, not just symbols: what each flux IS. ---
        e11 = MathTex(r"\mathbf{J}_s = \mathbf{J}_{s\mu} + \mathbf{J}_{sc}", font_size=32)
        e12 = MathTex(r"\mathbf{J}_{sc} = -a^2\Phi^2 k_{sc}\nabla(\dot{\gamma}\Phi)", font_size=26)
        e13 = MathTex(r"\mathbf{J}_{s\mu} = -a^2\Phi^2 k_\mu \nabla(\ln \mu)", font_size=26)
        group_a = VGroup(e11, e12, e13).arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        group_a.to_edge(LEFT, buff=1.0).shift(UP * 1.6)
        name_a = self._name("Flux decomposition", group_a)
        physics_a = Text(
            "Particles migrate two ways: pushed from high-shear regions toward low-shear\n"
            "ones (J_sc), and pushed toward locally less-viscous fluid (J_sμ).",
            font_size=20, color=GRAY_B,
        ).next_to(group_a, DOWN, buff=0.5, aligned_edge=LEFT)
        legend_c = self._legend(
            r"$\mathbf{J}_{sc}$ -- shear-induced migration flux \quad $\mathbf{J}_{s\mu}$ -- viscosity-gradient flux \quad $a$ -- particle radius",
            r"$\dot{\gamma}$ -- shear-rate magnitude (derived next) \quad $k_{sc}, k_\mu$ -- empirical coefficients",
        ).to_corner(DL, buff=0.4)

        self.play(
            FadeIn(header), FadeIn(name_a), LaggedStartMap(FadeIn, group_a, lag_ratio=0.2),
            FadeIn(physics_a), FadeIn(legend_c),
        )
        self.next_slide(
            notes="""
            These are independent modeling closures, not a chain where each
            line is derived from the last -- accumulated on screen together
            rather than replacing one another.

            J_s decomposes into two named pieces (Eq. 11): J_sc, the
            shear-induced migration flux (Eq. 12), and J_sμ, the flux from
            spatial viscosity variation (Eq. 13).

            The physical picture in one sentence: particles get pushed out
            of high-shear regions toward low-shear ones (J_sc -- this is
            THE effect this whole talk is about, the one that can fight
            buoyancy), and separately pushed toward locally less-viscous
            fluid (J_sμ, a much smaller secondary effect in this geometry).

            If asked for the source of this flux split: it's not derived
            in this paper, it's cited. Eqs. 11-13 come from Leighton &
            Acrivos (J. Fluid Mech., 1987) for the shear-induced migration
            mechanism, and Phillips, Armstrong, Brown, Graham & Abbott
            (1992) for the constitutive form combining it with the
            viscosity-gradient flux -- both in this paper's own reference
            list.
            """
        )
        self.play(FadeOut(legend_c))

        # --- Real step: add sedimentation to get the hindered-settling
        #     form. group_a and its prose fade since folded into this.
        #     The two terms that don't match Eq. 12/13 above are colored
        #     red IN PLACE, within the equation itself -- not a separate
        #     sentence -- per an explicit request for red terms, not red
        #     prose. Verified in scripts/verify_paper_equations.py
        #     (Block 2). ---
        e14_a = MathTex(r"\frac{\mathbf{J}_s}{\rho_s} = -\Big[", font_size=28)
        e14_phi1 = MathTex(r"\Phi", font_size=28).set_color(RED)
        e14_b = MathTex(r"D_\Phi \nabla(\dot{\gamma}\Phi) + \Phi^2 D_\mu\,", font_size=28)
        e14_gammadot = MathTex(r"\dot{\gamma}", font_size=28).set_color(RED)
        e14_c = MathTex(r"\nabla(\ln \mu)\Big]", font_size=28)
        e14_sediment = MathTex(r"+ f_h \mathbf{u}_{st}\Phi", font_size=28).set_color(ORANGE)
        e14 = VGroup(e14_a, e14_phi1, e14_b, e14_gammadot, e14_c, e14_sediment).arrange(RIGHT, buff=0.05)
        e14.to_edge(LEFT, buff=1.0).shift(UP * 1.6)
        name_14 = self._name("Flux closure", e14)
        physics_14 = Text(
            "Adds a third effect on top of Eq. 11's two: buoyant settling, slowed down\n"
            "by how crowded the suspension locally is (the hindered-settling factor f_h).",
            font_size=20, color=GRAY_B,
        ).next_to(e14, DOWN, buff=0.5, aligned_edge=LEFT)
        legend_c2 = self._legend(
            r"$D_\Phi, D_\mu$ -- empirical prefactors (below) \quad $f_h$ -- hindered-settling factor \quad $\mathbf{u}_{st}$ -- Stokes settling velocity",
        ).to_corner(DL, buff=0.4)
        self.play(
            FadeOut(group_a), FadeOut(name_a), FadeOut(physics_a),
            FadeIn(name_14), FadeIn(e14), FadeIn(physics_14), FadeIn(legend_c2),
        )
        self.next_slide(
            notes="""
            Eq. 14 is Eqs. 12-13's bracketed terms (renamed D_Phi, D_mu, and
            divided through by rho_s) with one new physical effect added --
            the orange sedimentation term, +f_h*u_st*Phi (printed as a
            plus in the paper, checked directly against the PDF page
            image) -- that isn't in Eq. 11's decomposition at all. This is
            the hindered-settling closure the rest of the derivation uses.

            The two red terms are a genuine, self-contained inconsistency
            in the paper's own printed equations, not an interpretation on
            our part: Eq. 12 says J_sc scales as Phi^2; the Phi shown in
            red here (the term Eq. 14 claims is that same J_sc -- its own
            text says Eq. 14 comes from "combining equations 11-13") is
            only Phi^1. Separately, the gammadot shown in red is an extra
            factor on the viscosity-gradient term that Eq. 13's own J_smu
            simply doesn't have. Both confirmed by directly comparing the
            printed powers/factors -- see
            scripts/verify_paper_equations.py, Block 2.
            """
        )

        # --- The definitions Eq. 14 uses, all at once, kept alongside it. ---
        e1516 = MathTex(r"D_\Phi = 0.41 a^2 \qquad D_\mu = 0.62 a^2", font_size=28)
        e17 = MathTex(r"\mathbf{u}_{st} = \frac{2a^2(\rho_s-\rho_f)}{9\mu}\,\mathbf{g}", font_size=28)
        e18 = MathTex(r"f_h = \frac{\mu_f(1-\Phi_{avg})}{\mu}", font_size=28)
        group_b = VGroup(e1516, e17, e18).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
        group_b.next_to(physics_14, DOWN, buff=0.5, aligned_edge=LEFT)
        legend_c3 = self._legend(
            r"$D_\Phi, D_\mu$ -- empirical prefactors \quad $f_h$ -- hindered-settling factor \quad $\mathbf{u}_{st}$ -- Stokes settling velocity",
            r"$\Phi_{avg}$ -- domain-average particle volume fraction",
        ).to_corner(DL, buff=0.4)

        self.play(FadeIn(group_b), Transform(legend_c2, legend_c3))
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
        self.play(FadeOut(header), FadeOut(name_14), FadeOut(e14), FadeOut(physics_14), FadeOut(group_b), FadeOut(legend_c2))

    def chapter_2d_shear_rate(self):
        # Condensed to one slide: all three equivalent forms of the same
        # quantity shown together, rather than paced one at a time.
        header = self._header("Modeling. Shear rate.")
        e1 = eq(r"\dot{\boldsymbol{\gamma}} = \nabla\mathbf{u} + \nabla\mathbf{u}^{T}", font_size=32)
        e2 = eq(r"\dot{\gamma} = \left[\tfrac{1}{2}\left(\dot{\boldsymbol{\gamma}}\cdot\dot{\boldsymbol{\gamma}}\right)\right]^{1/2}", font_size=32)
        e3 = eq(r"\dot{\gamma} = \left[\tfrac{1}{2}\left(4u_x^2 + 2(u_y+v_x)^2 + 4v_y^2\right)\right]^{1/2}", font_size=32)
        group = VGroup(e1, e2, e3).arrange(DOWN, buff=0.5, aligned_edge=LEFT).to_edge(LEFT, buff=1.0)
        name_d = self._name("Shear rate", group)
        physics_d = Text(
            "This scalar is what drives migration and viscosity throughout the model --\n"
            "not the velocity field directly, just how fast it's shearing, locally.",
            font_size=20, color=GRAY_B,
        ).next_to(group, DOWN, buff=0.5, aligned_edge=LEFT)
        legend_d = self._legend(
            r"$\dot{\boldsymbol{\gamma}}$ -- shear-rate tensor \quad $\mathbf{u}$ -- velocity field",
            r"$u,v$ -- velocity components (x, y) \quad subscripts -- partial derivatives, e.g. $u_x=\partial u/\partial x$",
        ).to_corner(DL, buff=0.4)

        self.play(FadeIn(header), FadeIn(name_d))
        self.play(LaggedStart(Write(e1), Write(e2), Write(e3), lag_ratio=0.4), FadeIn(physics_d), FadeIn(legend_d))
        self.next_slide(
            notes="""
            The shear-rate tensor (Eq. 19) contracted with itself and
            square-rooted gives its scalar magnitude -- the general
            double-dot-product form -- then written out in components for
            this model's 2D velocity field (u, v) as Eq. 20. All three
            forms of the same quantity, together rather than paced one at
            a time: the tensor, its contraction, and the component form.

            The point of this scalar: it's what actually feeds into the
            flux closures (J_sc, J_sμ) and the viscosity law -- migration
            responds to how fast the fluid is shearing, not to velocity
            itself.
            """
        )
        self.play(FadeOut(header), FadeOut(name_d), FadeOut(group), FadeOut(physics_d), FadeOut(legend_d))

    def chapter_2e_assemble(self):
        header = self._header("Modeling. Assembling the master Φ-equation.")

        # --- Show the two collected inputs, stacked (no claim yet that one
        #     morphs into the other). The closure (inputs[1]) is about to
        #     be substituted in below, so only inputs[0] is retired here --
        #     the closure stays on screen until it's actually exercised.
        #     inputs0's RHS is OUR verified master equation from the
        #     previous chapter (-rho/(rho_s*rho_f)*div(J_s)), not the
        #     paper's own kappa*div(J_s) -- see chapter_2b_continuity_
        #     transport and scripts/verify_paper_equations.py. ---
        inputs0 = VGroup(
            MathTex(r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi =", font_size=28),
            MathTex(r"-\frac{\rho}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s", font_size=28),
        ).arrange(RIGHT, buff=0.1)
        inputs1 = MathTex(
            r"\frac{\mathbf{J}_s}{\rho_s} = -\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right] + f_h\mathbf{u}_{st}\Phi",
            font_size=28,
        )
        inputs = VGroup(inputs0, inputs1).arrange(DOWN, buff=0.5, aligned_edge=LEFT).to_edge(LEFT, buff=1.0)
        self.play(FadeIn(header), Write(inputs))
        self.next_slide(
            notes="""
            The two pieces going into this assembly: our own verified
            Phi-transport equation from the previous chapter (with
            -rho/(rho_s*rho_f) left as the coefficient, not the paper's
            kappa) and Eq. 14 (the hindered-settling flux closure that
            div(J_s) is about to absorb). Eq. 14 stays on screen through
            the substitution just below -- it isn't exercised yet.
            """
        )

        # --- Real chain: substitute J_s into the RHS term by term.
        #     inputs0 IS the working "hero" line from here on -- moved
        #     into place, not deleted and rewritten as identical-looking
        #     new content. Pre-chunked into 2 pieces above so hero[1] is
        #     addressable for the highlight-then-swap step below. ---
        #     No pause between the move and the first real substitution --
        #     a slide where nothing but repositioning happens isn't worth
        #     its own beat. ---
        hero = inputs0
        closure = inputs1
        hero_target = hero.copy().to_edge(LEFT, buff=1.0).shift(UP * 1.5)
        closure_target = closure.copy().next_to(hero_target, DOWN, buff=0.8, aligned_edge=LEFT)
        self.play(hero.animate.become(hero_target), closure.animate.become(closure_target))

        self.play(hero[1].animate.set_color(ORANGE), closure.animate.set_color(ORANGE), run_time=0.5)
        chunk0 = MathTex(r"-\frac{\rho}{\rho_s^\circ\rho_f^\circ}\,\rho_s^\circ\,\nabla\cdot\Big\{", font_size=26).set_color(ORANGE)
        chunk1 = MathTex(
            r"-\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right]",
            font_size=26,
        ).set_color(ORANGE)
        chunk2 = MathTex(r"+ f_h\mathbf{u}_{st}\Phi\Big\}", font_size=26).set_color(ORANGE)
        step1 = VGroup(chunk0, chunk1, chunk2).arrange(RIGHT, buff=0.05).move_to(hero[1], aligned_edge=LEFT)
        self.play(FadeOut(hero[1]), Write(step1), FadeOut(closure))
        self._hard_settle([hero[1], closure], [chunk0, chunk1, chunk2])
        hero.submobjects[1] = step1
        # hero[0] is a fixed left anchor and every swap above preserves it
        # (aligned_edge=LEFT), so the group's LEFT edge never needs to
        # move -- only scale down, about that same left edge, if a wider
        # right-hand side would overflow the frame.
        if hero.width > MAX_EQ_WIDTH:
            hero.generate_target()
            hero.target.scale_to_fit_width(MAX_EQ_WIDTH, about_edge=LEFT)
            self.play(MoveToTarget(hero))
        self.next_slide(
            notes="""
            J_s (divided by rho_s in Eq. 14) becomes rho_s times that same
            bracket once multiplied back through. Eq. 14 has now been
            exercised, so it leaves the screen. The rho_s^o just
            introduced obviously cancels against the rho_s^o already in
            the denominator -- that cancellation is the next, separate
            step, not bundled in here.
            """
        )

        # --- Cancel rho_s^o -- a single, genuinely clean simplification
        #     (unlike the paper's own Eq. 21, which keeps the equivalent
        #     rho_s^o uncancelled). chunk1/chunk2 settle to white since
        #     they aren't the focus of this beat. ---
        self.play(chunk1.animate.set_color(WHITE), chunk2.animate.set_color(WHITE), run_time=0.5)
        coeff_simplified = MathTex(
            r"-\frac{\rho}{\rho_f^\circ}\,\nabla\cdot\Big\{",
            font_size=26,
        ).set_color(ORANGE).move_to(chunk0, aligned_edge=LEFT)
        # coeff_simplified is NARROWER than chunk0 (rho_s^o cancels away),
        # so shift3 is negative here -- this is the one spot in the deck
        # where the replacement shrinks rather than grows. The guard
        # below must fire in both directions (previously only handled
        # shift3 > 0, silently skipping the leftward close-up and
        # stranding chunk1/chunk2 with a large gap after the brace).
        shift3 = coeff_simplified.width - chunk0.width
        if abs(shift3) > 1e-3:
            self.play(chunk1.animate.shift(RIGHT * shift3), chunk2.animate.shift(RIGHT * shift3))
        self.play(FadeOut(chunk0), Write(coeff_simplified))
        self._hard_settle([chunk0], [coeff_simplified])
        step1.submobjects[0] = coeff_simplified
        if hero.width > MAX_EQ_WIDTH:
            hero.generate_target()
            hero.target.scale_to_fit_width(MAX_EQ_WIDTH, about_edge=LEFT)
            self.play(MoveToTarget(hero))
        self.next_slide(
            notes="""
            rho_s^o cancels cleanly, top and bottom -- leaving
            -rho/rho_f^o as the whole coefficient. This is the payoff of
            re-deriving the Phi-transport equation correctly instead of
            copying the paper's own Eq. 10/21: our version cancels to
            something genuinely simpler than what the paper prints for
            its own Eq. 21, which keeps the equivalent term uncancelled
            AND, per the previous chapter's finding, carries a sign error
            relative to its own Eq. 10.
            """
        )

        # --- Substitute the Stokes-velocity / hindered-settling closures
        #     into the sedimentation term -- the other, independent
        #     substitution, kept separate from the cancellation above.
        #     Recall those two closures briefly, alongside the term
        #     they're about to replace, rather than reaching for them from
        #     memory several chapters back. ---
        recall = VGroup(
            MathTex(r"\mathbf{u}_{st} = \frac{2a^2(\rho_s-\rho_f)}{9\mu}\,\mathbf{g}", font_size=22).set_color(GRAY_B),
            MathTex(r"f_h = \frac{\mu_f(1-\Phi_{avg})}{\mu}", font_size=22).set_color(GRAY_B),
        ).arrange(RIGHT, buff=0.6).to_corner(DL, buff=0.4)
        self.play(chunk2.animate.set_color(ORANGE), FadeIn(recall))
        sediment_sub = MathTex(
            r"+ \Phi\frac{2\mu_f a^2(1-\Phi_{avg})(\rho_s-\rho_f)}{9\mu^2}\mathbf{g}\Big\}",
            font_size=24,
        ).set_color(ORANGE).move_to(chunk2, aligned_edge=LEFT)
        # chunk2 is the last piece on the line, so no trailing content
        # needs to be displaced to make room for it.
        self.play(FadeOut(chunk2), Write(sediment_sub), FadeOut(recall))
        self._hard_settle([chunk2], [sediment_sub])
        step1.submobjects[2] = sediment_sub
        if hero.width > MAX_EQ_WIDTH:
            hero.generate_target()
            hero.target.scale_to_fit_width(MAX_EQ_WIDTH, about_edge=LEFT)
            self.play(MoveToTarget(hero))
        self.next_slide(
            notes="""
            Stokes velocity (Eq. 17) and the hindered-settling function
            (Eq. 18), recalled here from the flux-closure chapter,
            substituted into the sedimentation term (kept as a plus,
            matching Eq. 14's own printed sign, fixed earlier this pass)
            -- the other half of finishing the assembly, kept as its own
            step. Every step from the master equation to here was a
            concrete substitution or simplification, shown on the same
            line rather than skipped past -- this is the one equation
            that determines where the cells go, and now it's visible how
            it got built, correctly.
            """
        )

        # --- Term-level comparison against the paper's own printed Eq.
        #     21 -- the term itself (their printed leading coefficient),
        #     in red, not a sentence about it. Verified in
        #     scripts/verify_paper_equations.py, Block 1. ---
        paper21_label = Text("Paper's Eq. 21 instead:", font_size=18, color=GRAY_B)
        paper21_term = MathTex(r"\frac{\rho_f^\circ-\rho_s^\circ}{\rho_s^\circ\rho_f^\circ}", font_size=24).set_color(RED)
        paper_eq21 = VGroup(paper21_label, paper21_term).arrange(RIGHT, buff=0.15).next_to(hero, DOWN, buff=0.6, aligned_edge=LEFT)
        self.play(FadeIn(paper_eq21))
        self.next_slide(
            notes="""
            Flagged in red because this is another paper-side error we
            caught, continuing directly from the previous chapter's
            finding: the paper's own text says Eq. 21 is just Eq. 10 with
            Eq. 14's closure substituted in -- a pure substitution should
            never flip an overall sign. But Eq. 21's printed coefficient,
            (rho_f-rho_s)/(rho_s*rho_f), is exactly the negative of
            Eq. 10's own kappa, (rho_s-rho_f)/(rho_s*rho_f). No algebraic
            step in their own derivation explains that flip. Verified
            symbolically in scripts/verify_paper_equations.py, Block 1.

            Our own version, built by re-deriving from Eq. 5 rather than
            copying Eq. 10 or Eq. 21, sidesteps the whole problem: there's
            only one coefficient, -rho/rho_f^o, and it's shown exactly how
            it was obtained -- not a print-time inconsistency to explain
            away.
            """
        )

        note = Text(
            "This is the coupled Φ-transport equation.",
            font_size=26, color=YELLOW,
        ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(note), run_time=1.3)
        self.next_slide()
        self.play(FadeOut(header), FadeOut(hero), FadeOut(note), FadeOut(paper_eq21))

    def chapter_2f_rest_of_model(self):
        header = self._header("Modeling. Rest of the model.")

        # --- Boundary conditions: its own slide, with a plain-language
        #     sentence -- these aren't standard Navier-Stokes wall
        #     conditions, so a bare equation reads as "trust me." ---
        e22 = MathTex(r"\tau_w = \frac{4\mu_f(\mathbf{u}-\mathbf{u}_w)}{L}", font_size=30)
        e23 = MathTex(r"\mathbf{u}_r = \omega (y,-x)", font_size=30)
        pair1 = VGroup(e22, e23).arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        pair1.to_edge(LEFT, buff=1.0).shift(UP * 1.6)
        name1 = self._name("Boundary conditions", pair1)
        physics_bc = Text(
            "The wall drags the fluid toward the wall's own velocity (a linear shear-\n"
            "stress law), and the wall itself moves by solid-body rotation.",
            font_size=20, color=GRAY_B,
        ).next_to(pair1, DOWN, buff=0.5, aligned_edge=LEFT)
        legend_bc = self._legend(
            r"$\tau_w$ -- wall shear stress \quad $\mathbf{u}_w$ -- wall velocity \quad $L$ -- gap half-width \quad $\omega$ -- vessel angular velocity",
        ).to_corner(DL, buff=0.4)

        self.play(
            FadeIn(header), FadeIn(name1), LaggedStart(FadeIn(e22), FadeIn(e23), lag_ratio=0.4),
            FadeIn(physics_bc), FadeIn(legend_bc),
        )
        self.next_slide(
            notes="""
            Two boundary conditions close the momentum equation at the
            vessel wall: wall shear stress (a linear drag law toward the
            wall's own velocity) and the rotational wall velocity itself,
            solid-body rotation at angular speed omega.
            """
        )
        self.play(
            FadeOut(header), FadeOut(name1), FadeOut(pair1),
            FadeOut(physics_bc), FadeOut(legend_bc),
        )

        # --- Nutrient + growth: its own slide too, same reasoning -- cell
        #     growth kinetics aren't standard fluid mechanics either. ---
        header2 = self._header("Modeling. Nutrient and growth.")
        e2425 = MathTex(
            r"\frac{dC}{dt} + \mathbf{u}\cdot\nabla C = D_f \nabla^2 C + r_c"
            r"\qquad r_c = -\mu_c \cdot d",
            font_size=28,
        )
        e2425.to_edge(LEFT, buff=1.0).shift(UP * 1.6)
        name_nutrient = self._name("Nutrient", e2425)
        physics_nutrient = Text(
            "Nutrient is carried and diffused like any dissolved species, then consumed\n"
            "locally by the cells -- consumption rate scales with cell diameter.",
            font_size=20, color=GRAY_B,
        ).next_to(e2425, DOWN, buff=0.5, aligned_edge=LEFT)

        e26 = MathTex(r"\frac{\partial d}{\partial t} = k_c \cdot C \cdot d_0 \cdot e^{k_e t}", font_size=28)
        e28 = MathTex(r"\Phi = \frac{\pi}{6} d\, a^3", font_size=28)
        growth = VGroup(e26, e28).arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        growth.next_to(physics_nutrient, DOWN, buff=0.6, aligned_edge=LEFT)
        name_growth = self._name("Growth", growth)
        physics_growth = Text(
            "Cells grow with available nutrient (exponentially in time), and that growth\n"
            "in diameter is exactly what raises the particle volume fraction Φ.",
            font_size=20, color=GRAY_B,
        ).next_to(growth, DOWN, buff=0.5, aligned_edge=LEFT)

        legend2 = self._legend(
            r"$C$ -- nutrient concentration \quad $D_f$ -- nutrient diffusivity \quad $r_c$ -- consumption rate \quad $d$ -- cell diameter \quad $\mu_c$ -- consumption-rate constant",
            r"$k_c, k_e$ -- growth-rate constants \quad $d_0$ -- initial cell diameter",
        ).to_corner(DL, buff=0.4)

        self.play(FadeIn(header2), FadeIn(name_nutrient), FadeIn(e2425), FadeIn(physics_nutrient))
        self.play(
            FadeIn(name_growth), LaggedStart(FadeIn(e26), FadeIn(e28), lag_ratio=0.3),
            FadeIn(physics_growth), FadeIn(legend2),
        )
        self.next_slide(
            notes="""
            Nutrient: transport and consumption, standard advection-
            diffusion with a sink term. Growth: the cell-growth kinetics
            driven by that nutrient, and the relation between cell
            diameter and volume fraction that feeds growth back into Phi
            -- this is how consuming nutrient eventually raises the local
            particle concentration the rest of the model tracks.
            """
        )
        self.play(
            FadeOut(header2), FadeOut(name_nutrient), FadeOut(e2425), FadeOut(physics_nutrient),
            FadeOut(name_growth), FadeOut(growth), FadeOut(physics_growth), FadeOut(legend2),
        )

    def chapter_2g_summary(self):
        title = Text("Every equation that defines the model", font_size=32, weight=BOLD).to_edge(UP)

        rows = [
            ("Momentum", r"\rho \dot{\mathbf{u}} + \rho(\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p + \nabla\cdot[\mu(\nabla\mathbf{u}+\nabla\mathbf{u}^T)] + \rho\mathbf{g}"),
            ("Mixture density / viscosity", r"\rho=(1-\Phi)\rho_f^\circ+\Phi\rho_s^\circ \quad \mu=\mu_f(1-\Phi/\Phi_{\max})^{-2.5\Phi_{\max}}"),
            ("Φ-transport (master eq.)", r"\dot{\Phi} + \mathbf{u}\cdot\nabla\Phi = -\frac{\rho}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s"),
            ("Flux closure", r"\mathbf{J}_s/\rho_s = -[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)] + f_h\mathbf{u}_{st}\Phi"),
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

            [Judgment calls -- spoken here, no separate slide for just two
            column headers with everything else in notes anyway. This is
            the credibility moment for the room: how do you know your
            implementation matches the paper? Honest answer: in a few
            places it can't, because the paper doesn't fully agree with
            itself.]

            The paper's own inconsistencies -- all machine-verified in
            scripts/verify_paper_equations.py, not just asserted:
            - Eq. 10 states its own right-hand side two different ways
              (kappa*div(J_s) and rho/(rho_s*rho_f)*div(J_s)) and claims
              they're equal. They aren't, in general -- confirmed
              symbolically, and numerically ~20x apart at the paper's own
              Table 1 densities. Eq. 21 then prints a THIRD version of
              this same coefficient, sign-flipped from Eq. 10's own kappa,
              with no algebraic step that should flip it. We re-derived
              the correct Phi-transport equation from Eq. 5 directly
              (shown on screen during the derivation, flagged in red both
              times against the paper's printed forms) -- it's
              -rho/(rho_s*rho_f)*div(J_s), matching the magnitude of the
              paper's second form but not its sign, and not matching
              their first form (kappa) at all.
            - Eq. 12 and Eq. 14 disagree on the power of Φ in the J_sc
              shear-induced-migration term -- one is linear in Φ, the other
              quadratic. Eq. 14's viscosity-gradient term also carries a
              shear-rate factor Eq. 13's own version of that term doesn't
              have. These aren't two different regimes, they're the same
              term written inconsistently. We had to pick one (we went
              with Eq. 14's form) -- flagged on screen in red, and
              disclosed in the tutorial notebook, not buried.
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
            - Eq. 1's momentum balance carries a slip-velocity stress term
              (rho*c_s*(1-c_s)*u_slip⊗u_slip) that this deck used to drop
              silently -- caught only when spot-checked against the printed
              page. It's quadratic in u_slip (here, the Stokes settling
              velocity, order nanometers/second), so it's genuinely
              negligible next to the other terms -- but that's a
              justification, not a license to skip disclosing it. Now shown
              in full on the momentum slide, then dropped for the rest of
              the derivation and in the actual solver, same as it always
              was; the difference is saying so.
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
        self.play(FadeOut(title), FadeOut(lines))

    # ------------------------------------------------------------------
    def _fem_mesh_graphic(self, n=10, radius=1.15):
        # The actual mesh src/examples.jl's build_harv_2d_case builds: an
        # n x n Cartesian grid of straight-sided quadrilaterals on a
        # reference square (n=10 is that function's own default
        # partition), warped onto the disk by harv_square_to_disk() --
        # ported here verbatim, not re-derived -- rather than a
        # stand-in schematic grid. No diagonals: Gridap's
        # CartesianDiscreteModel keeps quad cells here, it's never
        # simplexified into triangles.
        def warp(x, y):
            X, Y = x / radius, y / radius
            x_new = X * (1.0 - Y ** 2 / 2.0) ** 0.5
            y_new = Y * (1.0 - X ** 2 / 2.0) ** 0.5
            return np.array([x_new * radius, y_new * radius, 0.0])

        coords = [-radius + 2 * radius * k / n for k in range(n + 1)]
        nodes = [[warp(x, y) for y in coords] for x in coords]

        lines = VGroup()
        for i in range(n + 1):
            for j in range(n):
                lines.add(Line(nodes[i][j], nodes[i][j + 1], stroke_width=1, color=GRAY_B))
        for j in range(n + 1):
            for i in range(n):
                lines.add(Line(nodes[i][j], nodes[i + 1][j], stroke_width=1, color=GRAY_B))
        return lines

    def chapter_4_implementation(self):
        title = Text("Monolithic finite-element solver", font_size=34, weight=BOLD).to_edge(UP, buff=0.6)
        headline = Text("Julia · Gridap.jl", font_size=30, color=BLUE_C).to_edge(LEFT, buff=1.0).shift(UP * 1.6)

        mesh = self._fem_mesh_graphic().next_to(headline, DOWN, buff=0.6, aligned_edge=LEFT)

        # Bigger than _legend()'s small-corner default (18pt) on purpose --
        # these five primal variables are this slide's main content, not
        # a footnote, so they need to actually be readable.
        fields = VGroup(
            Tex(r"$\mathbf{u}$ -- fluid velocity", font_size=30),
            Tex(r"$p$ -- pressure", font_size=30),
            Tex(r"$\Phi$ -- particle volume fraction", font_size=30),
            Tex(r"$C$ -- nutrient concentration", font_size=30),
            Tex(r"$\Gamma$ -- shear rate, lifted into its own field", font_size=30),
            Tex(r"(only to keep $\nabla\Gamma$ smooth -- not a 6th unknown)", font_size=24, color=GRAY_B),
        ).arrange(DOWN, buff=0.22, aligned_edge=LEFT).next_to(headline, RIGHT, buff=1.0, aligned_edge=UP)

        self.play(FadeIn(title), FadeIn(headline))
        self.play(Create(mesh))
        self.play(FadeIn(fields))
        self.next_slide(
            notes="""
            Rewritten from scratch as a monolithic finite-element solver: all
            five fields (u, p, Φ, C, Γ) in one coupled nonlinear system,
            solved together each timestep with Newton's method
            (BackTracking line search for stability) -- not a
            segregated/split scheme where you solve for flow, then
            transport, then update, and hope it's consistent. Monolithic is
            more expensive per step but avoids splitting error entirely.

            Gamma is worth a sentence of its own: it's not a sixth physical
            unknown, it's the shear rate lifted into its own FE field purely
            so its gradient (needed in the migration flux) can be computed
            from a smooth projection instead of differentiating the
            non-smooth sqrt() of a quadratic form directly, which is
            singular at zero shear. A numerical trick, not new physics.

            Time discretization: BDF1 (backward Euler) for the first step,
            BDF2 for every step after, for better-than-first-order accuracy
            without a multi-stage scheme.

            One implementation detail worth a sentence if there's time:
            Gridap can differentiate the residual automatically (autodiff) to
            get the Jacobian for Newton's method, but doing that for this
            particular 5-field coupled system is expensive to compile -- so we
            hand-derived the Jacobian analytically instead. That's a
            compile-time/engineering story, not a physics one; happy to go
            into it in discussion if anyone's curious.

            Two independent checks back this solver, both load-bearing, worth
            saying out loud even without a dedicated slide for them:

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
        self.play(FadeOut(title), FadeOut(headline), FadeOut(mesh), FadeOut(fields))
        # Close this slide out on its own -- otherwise this fade-out has no
        # next_slide() of its own and gets swept into the results chapter's
        # zero-animation src= slide below, which needs two keystrokes (one
        # to finish this fade, a second to actually reveal the external
        # video). This used to be handled by chapter_5_verification's own
        # trailing next_slide() before that chapter was removed.
        self.next_slide()

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
    def chapter_6a_paper_results(self):
        title = Text("What the paper itself found", font_size=36, weight=BOLD).to_edge(UP, buff=0.6)

        # The paper's own Figure 7, verbatim -- cropped straight from the
        # PDF page, not redrawn or reinterpreted. Never present a
        # schematic as if it were the paper's actual result.
        density = ImageMobject(str(PAPER_FIGURE_7)).scale_to_fit_width(4.6).to_edge(LEFT, buff=1.0).shift(DOWN * 0.1)
        density_caption = Text(
            "Fig. 7, Chao & Das (2015) -- cell density at t = 1, 3, 5, 7 days",
            font_size=16, color=GRAY_B,
        ).next_to(density, DOWN, buff=0.3, aligned_edge=LEFT)
        if density_caption.get_left()[0] < -6.9:
            density_caption.to_edge(LEFT, buff=0.4)

        points = BulletedList(
            "Cells settle into concentric rings, densest at mid-radius",
            "Nutrient stays fairly uniform, with a mild outer-to-inner decrease",
            "Checked against two independent experiments (Pollack et al.; Altamirano et al.)",
            font_size=24,
        ).scale_to_fit_width(6.2).next_to(density, RIGHT, buff=1.0)

        self.play(FadeIn(title))
        self.play(FadeIn(density), FadeIn(density_caption))
        self.play(LaggedStart(*[FadeIn(p) for p in points], lag_ratio=0.4))
        self.next_slide(
            notes="""
            This is the paper's own §3, in its own words -- separate from
            anything we built or verified ourselves.

            Validation against Pollack et al.'s experiments: they match the
            HARV geometry and rotation speed (10 rpm) to that prior
            experimental study, then check whether the model reproduces the
            observed swirling/sedimentation pattern -- not a quantitative
            fit, a qualitative shape check. Denser-than-medium cells migrate
            toward the outer wall; lighter-than-medium cells (this paper's
            own "floating cells" case, with cells started at the top of the
            vessel) migrate inward and mix first at the outer radius before
            slowly filling toward the center -- both match Pollack et al.'s
            reported behavior. That "floating cells" case is exactly the
            adversarial initial condition used in this talk's own results
            video a moment ago -- the paper picked the same stress test we
            did.

            §3.2: at higher, growing cell density (their CHO-culture runs,
            not the constant-population Pollack comparison), cells settle
            into concentric rings with density peaking at mid-radius. They
            note this differs in detail from Pollack et al.'s own 24-hour
            distribution experiment (which showed aggregation right at the
            center) and offer two candidate explanations: cell size (drag
            effects are stronger on smaller cells) and a smaller
            fluid/cell density mismatch weakening buoyancy's role -- offered
            as plausible, not confirmed.

            §3.3: nutrient (glucose) concentration is fairly uniform overall,
            but decreases mildly from the outer radius toward the inner
            radius, most noticeably right where cell density peaks --
            consistent with local consumption tracking local cell density.

            §3.4: comparing simulated vs. Altamirano et al.'s experimental
            CHO growth data, doubling time and overall growth trend line up
            well, including the rotating bioreactor outperforming a batch
            reactor -- attributed to sustaining higher local cell density.
            One discrepancy, carried to the next slide: real cultures kept
            growing 20-30 hours after nutrient was fully consumed; the
            simulation does not capture that.
            """
        )
        self.play(FadeOut(title), FadeOut(points), FadeOut(density), FadeOut(density_caption))

    # ------------------------------------------------------------------
    def chapter_6b_paper_discussion(self):
        title = Text("What the paper concludes", font_size=36, weight=BOLD).to_edge(UP, buff=0.6)

        # The paper's own Figure 10, verbatim -- cropped straight from the
        # PDF page, not redrawn. Note this is ONLY the simulated curve:
        # the paper's own caption says it is "not compared directly to
        # experimental measurements" -- so no real-vs-simulated
        # comparison curve is drawn here either; that comparison isn't in
        # the paper's own figure, only in its prose (the bullet at right).
        growth = ImageMobject(str(PAPER_FIGURE_10)).scale_to_fit_width(4.6).to_edge(LEFT, buff=1.0).shift(DOWN * 0.1)
        growth_caption = Text(
            "Fig. 10, Chao & Das (2015) -- simulated only, per their own caption",
            font_size=16, color=GRAY_B,
        ).next_to(growth, DOWN, buff=0.3, aligned_edge=LEFT)
        if growth_caption.get_left()[0] < -6.9:
            growth_caption.to_edge(LEFT, buff=0.4)

        points = BulletedList(
            "Growth-kinetics gap: simulated cells die off after nutrient depletion, real cultures kept growing 20-30h longer",
            "Framed as a design-exploration tool, not a finished predictive model",
            "Their own words: several parameters are assumption-based -- further studies are needed",
            font_size=22,
        ).scale_to_fit_width(6.2).next_to(growth, RIGHT, buff=1.0)

        self.play(FadeIn(title))
        self.play(FadeIn(growth), FadeIn(growth_caption))
        self.play(LaggedStart(*[FadeIn(p) for p in points], lag_ratio=0.4))
        self.next_slide(
            notes="""
            The paper is upfront about where its own model falls short --
            worth holding up next to our own judgment-calls disclosure a few
            slides back, since this is the paper doing the same thing for
            itself.

            The growth-kinetics gap (§3.4): Altamirano et al.'s real CHO
            cultures kept growing for 20-30 hours after nutrient was fully
            consumed; this model's cells die off/degenerate immediately once
            nutrient runs out. The paper's own explanation is a lack of
            precise experimental data for HARV specifically to calibrate
            against -- not a claim that the mechanism is fully understood and
            just mis-tuned. This is exactly the sort of gap a design-tool
            framing can tolerate but a predictive-fit claim couldn't.

            Conclusion (§4), the paper's own framing of what it built: a tool
            to explore bioreactor design choices -- rotation speed, scaffold
            density, geometry, cell type -- by letting you vary parameters
            and see the qualitative consequence, rather than a validated
            quantitative predictor you'd trust for a specific culture without
            further calibration. They state plainly that several parameters
            were fixed by assumption because the necessary data didn't exist
            at the time, and that "further studies are needed" to pin those
            down -- their words, not a caveat we're adding on their behalf.

            Point for discussion: this is a second, independent instance of
            the same theme as our own judgment-calls slide -- an honest model
            author disclosing where the model doesn't yet have solid ground
            to stand on, rather than presenting it as finished. Worth naming
            explicitly for the room.
            """
        )
        self.play(FadeOut(title), FadeOut(points), FadeOut(growth), FadeOut(growth_caption))

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
        self.play(LaggedStart(*[FadeIn(p) for p in points], lag_ratio=0.4))
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
