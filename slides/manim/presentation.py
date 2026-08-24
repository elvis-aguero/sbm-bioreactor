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

CAPTION_FONT = 30
EQ_FONT = 40
MAX_EQ_WIDTH = 12.3

RESULTS_VIDEO = Path(__file__).parent / "results_combined.mp4"


def eq(tex, font_size=EQ_FONT):
    m = MathTex(tex, font_size=font_size)
    if m.width > MAX_EQ_WIDTH:
        m.scale_to_fit_width(MAX_EQ_WIDTH)
    return m


def tag(text):
    return Text(text, font_size=CAPTION_FONT, weight=BOLD).to_edge(UP, buff=0.5)


def eqnum(n):
    return Text(f"Eq. {n}", font_size=22, color=GRAY).to_corner(DR, buff=0.4)


class Presentation(Slide):
    def construct(self):
        self.chapter_0_title()
        self.chapter_1_system()
        self.chapter_2_model()
        self.chapter_3_judgment_calls()
        self.chapter_4_implementation()
        self.chapter_5_verification()
        self.chapter_6_results()
        self.chapter_7_takeaways()

    # ------------------------------------------------------------------
    def chapter_title(self, text, notes=""):
        title = Text(text, font_size=44, weight=BOLD)
        self.play(FadeIn(title, shift=UP * 0.3))
        self.next_slide(notes=notes)
        self.play(FadeOut(title))

    # --- tracked-slot helpers: always transform FROM the live mobject ---
    def _start_cap(self, text):
        self.cap = tag(text)
        return self.cap

    def _set_cap(self, text):
        self.play(Transform(self.cap, tag(text)))

    def _start_num(self, n):
        self.num = eqnum(n)
        return self.num

    def _set_num(self, n):
        self.play(Transform(self.num, eqnum(n)))

    def _start_eq(self, mobj):
        self.eq = mobj
        return self.eq

    def _set_eq(self, new_mobj, anim=TransformMatchingTex):
        self.play(anim(self.eq, new_mobj))
        self.eq = new_mobj

    def _end_group(self, *extra):
        self.play(FadeOut(self.cap), FadeOut(self.num), FadeOut(self.eq), *[FadeOut(m) for m in extra])

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
        self.chapter_title(
            "The Model -- 1. Momentum",
            notes="""
            This is the derivation, live: a keystroke-triggered walkthrough of
            every numbered equation in the paper (Eq. 1-26, 28). Kept
            deliberately compact and non-verbose on-screen -- a caption of a
            few words per step, the equation itself doing the explaining via
            the Transform, not a paragraph of on-screen prose. This spoken
            narration carries the why; the animation carries the how.
            """
        )

        cap = self._start_cap("Momentum balance")
        e1 = self._start_eq(
            eq(
                r"\rho \frac{\partial \mathbf{u}}{\partial t}"
                r"+ \rho (\mathbf{u}\cdot\nabla)\mathbf{u}"
                r"= -\nabla p"
                r"+ \nabla\cdot\left[\mu\left(\nabla\mathbf{u} + \nabla\mathbf{u}^{T}\right)\right]"
                r"+ \rho \mathbf{g}"
            )
        )
        num = self._start_num("1")
        self.play(FadeIn(cap), Write(e1), FadeIn(num))
        self.next_slide()

        self._set_cap("closure: mixture density")
        self._set_eq(
            eq(
                r"\rho \frac{\partial \mathbf{u}}{\partial t}"
                r"+ \rho (\mathbf{u}\cdot\nabla)\mathbf{u}"
                r"= -\nabla p"
                r"+ \nabla\cdot\left[\mu\left(\nabla\mathbf{u} + \nabla\mathbf{u}^{T}\right)\right]"
                r"+ \left[(1-\Phi)\rho_f^\circ + \Phi \rho_s^\circ\right] \mathbf{g}"
            )
        )
        self._set_num("1, 2")
        self.next_slide()

        self._set_cap("closure: Krieger-Dougherty viscosity")
        self._set_eq(
            eq(r"\mu = \mu_f \left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}"),
            anim=FadeTransform,
        )
        self._set_num("3")
        self.next_slide()
        self._end_group()

    def chapter_2b_continuity_transport(self):
        self.chapter_title("2. From two phases to one Φ-equation")

        cap = self._start_cap("solid-phase transport")
        e_main = self._start_eq(
            eq(r"\frac{\partial \Phi}{\partial t} + \nabla\cdot(\Phi \mathbf{u}_s) = 0")
        )
        num = self._start_num("5")
        self.play(FadeIn(cap), Write(e_main), FadeIn(num))
        self.next_slide()

        self._set_cap("substitute: u_s = u + slip velocity")
        self._set_eq(
            eq(
                r"\frac{\partial \Phi}{\partial t}"
                r"- \nabla\cdot\left[\Phi\left(\mathbf{u} + (1-c_s)\mathbf{u}_{slip}\right)\right] = 0"
            )
        )
        self._set_num("5, 6")
        self.next_slide()

        self._set_cap("define the migration flux J_s")
        self._set_eq(
            eq(
                r"\frac{\partial \Phi}{\partial t} + \nabla\cdot(\mathbf{u}\Phi)"
                r"= -\frac{\nabla\cdot\mathbf{J}_s}{\rho_s^\circ}"
            )
        )
        self._set_num("7")
        self.next_slide()

        self._set_cap("meanwhile, mixture continuity")
        self._set_num("4")
        self._set_eq(
            eq(
                r"(\rho_s^\circ-\rho_f^\circ)\left[\nabla\cdot\left(\Phi(1-c_s)\mathbf{u}_{slip}\right)\right]"
                r"- \rho_f^\circ (\nabla\cdot\mathbf{u}) = 0"
            ),
            anim=FadeTransform,
        )
        self.next_slide()

        self._set_cap("rearrange: continuity in terms of ∇·J_s")
        self._set_eq(
            eq(
                r"\nabla\cdot\mathbf{u} = "
                r"\frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s"
            )
        )
        self._set_num("8")
        self.next_slide()

        self._set_cap("combine with Eq. 7: the master Φ-transport equation")
        self._set_eq(
            eq(
                r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi"
                r"= \underbrace{\frac{\rho_s^\circ-\rho_f^\circ}{\rho_s^\circ\rho_f^\circ}}_{\kappa}"
                r"\,\nabla\cdot\mathbf{J}_s"
            )
        )
        self._set_num("10")
        note = Text(
            "κ has units of inverse density -- a dimensional slip here is\n"
            "exactly the bug our own test suite caught this session.",
            font_size=22, color=YELLOW,
        ).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(note))
        self.next_slide(
            notes="""
            From two phases to one Φ-equation: solid-phase transport (Eq. 5) ->
            substitute the slip velocity (Eq. 6) -> define the migration flux
            J_s (Eq. 7) -> bring in mixture continuity (Eq. 4) -> rearrange it
            in terms of div(J_s) (Eq. 8) -> combine with Eq. 7 into the master
            Φ-transport equation (Eq. 10).

            The κ coefficient that falls out here is exactly where this
            session's dimensional bug lived -- flagged on-screen, not just in
            the repo. κ has units of inverse density; a dimensional slip here
            is a real, caught bug, not a hand-wave.
            """
        )
        self._end_group(note)

    def chapter_2c_flux_closure(self):
        self.chapter_title(
            "3. Closing the flux J_s",
            notes="""
            Closing the flux: decompose J_s (Eq. 11) into J_sc (Eq. 12) and
            J_sμ (Eq. 13), add sedimentation with hindered settling (Eq. 14),
            then unpack the empirical prefactors (Eq. 15-16), Stokes settling
            velocity (Eq. 17), and hindered-settling function (Eq. 18).
            """
        )

        cap = self._start_cap("decompose J_s")
        e_main = self._start_eq(eq(r"\mathbf{J}_s = \mathbf{J}_{s\mu} + \mathbf{J}_{sc}"))
        num = self._start_num("11")
        self.play(FadeIn(cap), Write(e_main), FadeIn(num))
        self.next_slide()

        self._set_cap("shear-induced migration flux")
        self._set_eq(eq(r"\mathbf{J}_{sc} = -a^2\Phi^2 k_{sc}\nabla(\dot{\gamma}\Phi)"))
        self._set_num("12")
        self.next_slide()

        self._set_cap("viscosity-gradient flux")
        self._set_eq(eq(r"\mathbf{J}_{s\mu} = -a^2\Phi^2 k_\mu \nabla(\ln \mu)"))
        self._set_num("13")
        self.next_slide()

        self._set_cap("add sedimentation, divide by ρ_s: hindered settling")
        self._set_eq(
            eq(
                r"\frac{\mathbf{J}_s}{\rho_s} = "
                r"-\left[\Phi D_\Phi \nabla(\dot{\gamma}\Phi) + \Phi^2 D_\mu \dot{\gamma}\nabla(\ln \mu)\right]"
                r"- f_h \mathbf{u}_{st}\Phi"
            )
        )
        self._set_num("14")
        self.next_slide()

        self._set_cap("empirical prefactors")
        self._set_eq(eq(r"D_\Phi = 0.41 a^2 \qquad D_\mu = 0.62 a^2"), anim=FadeTransform)
        self._set_num("15, 16")
        self.next_slide()

        self._set_cap("Stokes settling velocity")
        self._set_eq(eq(r"\mathbf{u}_{st} = \frac{2a^2(\rho_s-\rho_f)}{9\mu}\,\mathbf{g}"))
        self._set_num("17")
        self.next_slide()

        self._set_cap("hindered-settling function")
        self._set_eq(eq(r"f_h = \frac{\mu_f(1-\Phi_{avg})}{\mu}"))
        self._set_num("18")
        self.next_slide()
        self._end_group()

    def chapter_2d_shear_rate(self):
        self.chapter_title("4. Shear rate")

        cap = self._start_cap("shear-rate tensor")
        e_main = self._start_eq(eq(r"\dot{\boldsymbol{\gamma}} = \nabla\mathbf{u} + \nabla\mathbf{u}^{T}"))
        num = self._start_num("19")
        self.play(FadeIn(cap), Write(e_main), FadeIn(num))
        self.next_slide()

        self._set_cap("its scalar magnitude")
        self._set_eq(
            eq(
                r"\dot{\gamma} = \left[\tfrac{1}{2}\left(\dot{\boldsymbol{\gamma}}\cdot\dot{\boldsymbol{\gamma}}\right)\right]^{1/2}"
                r"= \left[\tfrac{1}{2}\left(4u_x^2 + 2(u_y+v_x)^2 + 4v_y^2\right)\right]^{1/2}"
            )
        )
        self._set_num("20")
        self.next_slide()
        self._end_group()

    def chapter_2e_assemble(self):
        self.chapter_title("5. Assemble: the master Φ-equation")

        cap = self._start_cap("Eq. 10 + Eq. 14-18 + Eq. 19-20, combined")
        e_main = self._start_eq(
            VGroup(
                eq(r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi = \kappa\,\nabla\cdot\mathbf{J}_s", font_size=28),
                eq(r"\frac{\mathbf{J}_s}{\rho_s} = -\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right] - f_h\mathbf{u}_{st}\Phi", font_size=28),
            ).arrange(DOWN, buff=0.5)
        )
        num = self._start_num("10, 14-18")
        self.play(FadeIn(cap), Write(e_main), FadeIn(num))
        self.next_slide()

        self._set_eq(
            eq(
                r"\frac{\partial \Phi}{\partial t} + \mathbf{u}\cdot\nabla\Phi ="
                r"\frac{\rho_f^\circ-\rho_s^\circ}{\rho_s^\circ\rho_f^\circ}"
                r"\nabla\cdot \rho_s^\circ"
                r"\left\{"
                r"\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right]"
                r"- \Phi \frac{2\mu_f a^2(1-\Phi_{avg})(\rho_s-\rho_f)}{9\mu^2}\mathbf{g}"
                r"\right\}",
                font_size=30,
            ),
            anim=FadeTransform,
        )
        self._set_num("21")
        self.next_slide()
        note = Text(
            "This is the one equation that determines where the cells go.",
            font_size=26, color=YELLOW,
        ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(note))
        self.next_slide(
            notes="""
            Eq. 10 + Eq. 14-18 + Eq. 19-20 fold into the one equation (Eq. 21)
            that actually determines where the cells go -- the payoff of the
            whole derivation so far.
            """
        )
        self._end_group(note)

    def chapter_2f_rest_of_model(self):
        self.chapter_title("6. Rest of the model")

        cap = self._start_cap("wall shear & rotational boundary")
        e_main = self._start_eq(
            eq(
                r"\tau_w = \frac{4\mu_f(\mathbf{u}-\mathbf{u}_w)}{L} \qquad "
                r"\mathbf{u}_r = \omega (y,-x)"
            )
        )
        num = self._start_num("22, 23")
        self.play(FadeIn(cap), Write(e_main), FadeIn(num))
        self.next_slide()

        self._set_cap("nutrient transport & consumption")
        self._set_eq(
            eq(
                r"\frac{dC}{dt} + \mathbf{u}\cdot\nabla C = D_f \nabla^2 C + r_c"
                r"\qquad r_c = -\mu_c \cdot d"
            ),
            anim=FadeTransform,
        )
        self._set_num("24, 25")
        self.next_slide()

        self._set_cap("growth kinetics")
        self._set_eq(eq(r"\frac{\partial d}{\partial t} = k_c \cdot C \cdot d_0 \cdot e^{k_e t}"))
        self._set_num("26")
        self.next_slide()

        self._set_cap("Φ ↔ cell density")
        self._set_eq(eq(r"\Phi = \frac{\pi}{6} d\, a^3"))
        self._set_num("28")
        self.next_slide(
            notes="""
            The rest of the model: wall shear/rotation (Eq. 22-23), nutrient
            transport (Eq. 24-25), growth kinetics (Eq. 26), and the
            Φ-density relation (Eq. 28).
            """
        )
        self._end_group()

    def chapter_2g_summary(self):
        self.chapter_title("The complete model")

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
        self.next_slide()
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
        title = Text("Results", font_size=40, weight=BOLD).to_edge(UP, buff=0.6)
        self.play(FadeIn(title))
        self.next_slide()
        self.play(FadeOut(title))

        # Zero-animation slide: the entire content is the external video.
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
