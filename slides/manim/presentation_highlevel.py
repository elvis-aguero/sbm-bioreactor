"""
manim-slides presentation: "Where Do the Cells Go? (High-Level Overview)".

A SEPARATE, shorter deck from presentation.py. Where presentation.py builds
every equation on screen step by step (full algebra, red-flagged paper
discrepancies inline), this deck skips the derivation entirely: one final
equation per slide (Name / Equation / Physical meaning / Undefined terms),
then the same summary table and implementation slides as the main deck
(reused verbatim), followed by a results section (test-case setup / video /
a genuinely paper-grounded finding) aimed at a general audience, not just
fluids specialists. Built mechanically per an explicit request; this file
intentionally duplicates a few small helpers from presentation.py rather
than importing from it, so the two decks can keep evolving independently.

Render:
    manim-slides render -q h presentation_highlevel.py Presentation
Present (keystroke-driven, arrow keys / space to advance):
    manim-slides present Presentation
Export to a self-contained, offline HTML player:
    manim-slides convert Presentation ../public/presentation_highlevel.html --offline
"""
from pathlib import Path

import numpy as np
from manim import *
from manim_slides import Slide

EQ_FONT = 40
MAX_EQ_WIDTH = 12.0
LEFT_BUFF = 1.0

RESULTS_VIDEO = Path(__file__).parent / "results_combined.mp4"
# The paper's own Figure 7, cropped verbatim from assets/Chao_Das_2015.pdf
# (see presentation.py's header comment for the extraction method).
PAPER_FIGURE_7 = Path(__file__).parent.parent.parent / "assets" / "Chao_Das_2015_figure7.png"
PAPER_FIGURE_10 = Path(__file__).parent.parent.parent / "assets" / "Chao_Das_2015_figure10.png"


def eq(tex, font_size=EQ_FONT):
    m = MathTex(tex, font_size=font_size)
    if m.width > MAX_EQ_WIDTH:
        m.scale_to_fit_width(MAX_EQ_WIDTH)
    return m


class Presentation(Slide):
    def construct(self):
        self._slide_no = 1
        self._page = Text("1", font_size=20, color=GRAY).to_corner(DR, buff=0.4)
        self.add(self._page)

        self.chapter_0_title()
        self.chapter_0b_what_it_does()
        self.chapter_1_momentum()
        self.chapter_2_density_viscosity()
        self.chapter_3_transport()
        self.chapter_4_flux_closure()
        # self.chapter_5_shear_rate()  # commented out per feedback: not
        # worth its own slide. Shear rate now appears by name only (flux
        # closure's Terms, and the Implementation slide), not as a
        # separately-derived equation.
        self.chapter_6_nutrient()
        self.chapter_7_growth()
        self.chapter_8_summary()
        self.chapter_9_implementation()
        self.chapter_10_results_setup()
        self.chapter_11_results_video()
        self.chapter_12_ring_pattern()
        self.chapter_13_density_collapse()

    def next_slide(self, *args, **kwargs):
        result = super().next_slide(*args, **kwargs)
        self._slide_no += 1
        self._page.become(Text(str(self._slide_no), font_size=20, color=GRAY).to_corner(DR, buff=0.4))
        return result

    # ------------------------------------------------------------------
    def _legend(self, *lines, font_size=20):
        rows = VGroup(*[Tex(line, font_size=font_size, color=GRAY_B) for line in lines])
        rows.arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        return rows

    def _equation_slide(self, name, tex, meaning_lines, term_lines, notes, eq_font_size=EQ_FONT):
        title = Text(name, font_size=36, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        equation = eq(tex, font_size=eq_font_size).next_to(title, DOWN, buff=0.55, aligned_edge=LEFT)

        meaning_header = Text("Physical meaning", font_size=22, color=BLUE_C)
        meaning = BulletedList(*meaning_lines, font_size=24)
        meaning_block = VGroup(meaning_header, meaning).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        meaning_block.next_to(equation, DOWN, buff=0.55, aligned_edge=LEFT)
        if meaning_block.width > 11.0:
            meaning_block.scale(11.0 / meaning_block.width, about_edge=LEFT)

        term_group = VGroup()
        if term_lines:
            terms_header = Text("Terms", font_size=18, color=GRAY_B)
            terms = self._legend(*term_lines, font_size=18)
            term_group = VGroup(terms_header, terms).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            term_group.to_edge(DOWN, buff=0.4).align_to(title, LEFT)

        self.play(FadeIn(title))
        self.play(Write(equation))
        self.play(FadeIn(meaning_block))
        if term_group:
            self.play(FadeIn(term_group))
        self.next_slide(notes=notes)

        to_fade = [title, equation, meaning_block]
        if term_group:
            to_fade.append(term_group)
        self.play(*[FadeOut(m) for m in to_fade])

    # ------------------------------------------------------------------
    def chapter_0_title(self):
        title = Text("Numerical simulation of coupled cell motion \n and nutrient transport in NASA's rotating bioreactor",
                     font_size=52, weight=BOLD)
        subtitle = Text(
            "High-level overview: Chao & Das (2015), Chem. Eng. J.", font_size=26, color=GRAY_B
        ).next_to(title, DOWN, buff=0.5)

        self.play(FadeIn(title, shift=UP * 0.3))
        self.play(FadeIn(subtitle))
        self.next_slide(
            notes="""
            Short version of the deck: no derivation on screen, just the
            final equations that define the model, one per slide, then the
            implementation and a results video. Good for an audience that
            wants the shape of the model and the result, not the algebra.
            """
        )
        self.play(FadeOut(title), FadeOut(subtitle))

    # ------------------------------------------------------------------
    def chapter_0b_what_it_does(self):
        title = Text("What the model does", font_size=36, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        points = BulletedList(
            "Treats the fluid and the suspended cells as one continuous\\\\mixture, not as individually tracked particles",
            "Tracks a single field, the local particle volume fraction $\\Phi$,\\\\and couples it to the fluid flow",
            "Two mechanisms compete to move $\\Phi$ around: shear-induced\\\\migration, which pushes cells out of high-shear regions,\\\\against buoyancy, which settles or floats them by density difference",
            "Also tracks nutrient transport and cell growth, so the model\\\\predicts both where cells accumulate and how the population grows",
            font_size=28,
        ).next_to(title, DOWN, buff=0.7, aligned_edge=LEFT)

        self.play(FadeIn(title))
        self.play(LaggedStart(*[FadeIn(p) for p in points], lag_ratio=0.4))
        self.next_slide(
            notes="""
            This is the "SBM" in the paper's title: a continuum model, not
            a discrete-particle one. Instead of tracking millions of
            individual cells, it tracks one smooth field, Phi, the local
            fraction of the mixture's volume that's cells. That's what
            makes it computationally tractable for something the size of
            a bioreactor.

            The five equations on the next several slides are each one
            piece of this picture: momentum (how the mixture flows),
            density/viscosity (how Phi changes the fluid's own
            properties), the Phi-transport equation and its flux closure
            (the shear-vs-buoyancy competition this whole talk is about),
            and nutrient/growth (the biological side, coupled in through
            the same Phi field). Nothing on this slide is new physics;
            it's the map before the terrain.
            """
        )
        self.play(FadeOut(title), FadeOut(points))

    # ------------------------------------------------------------------
    def chapter_1_momentum(self):
        self._equation_slide(
            name="Momentum balance",
            tex=r"\rho \dot{\mathbf{u}} + \rho(\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p - \nabla\cdot[\rho c_s(1-c_s)\mathbf{u}_{slip}\mathbf{u}_{slip}] + \nabla\cdot[\mu(\nabla\mathbf{u}+\nabla\mathbf{u}^T)] + \rho\mathbf{g}",
            eq_font_size=32,
            meaning_lines=[
                "Mixture momentum balance: fluid and suspended cells move as one continuum",
                "Variable-density, variable-viscosity Navier-Stokes, plus a stress from slip between the two phases",
                "Buoyancy enters through $\\rho\\mathbf{g}$",
            ],
            term_lines=[
                r"$\rho,\ \mathbf{u},\ p,\ \mu,\ \mathbf{g}$: mixture density, velocity, pressure, viscosity, gravity",
                r"$c_s$: local mass fraction of solid",
                r"$\mathbf{u}_{slip}$: relative velocity between solid and fluid",
            ],
            notes="""
            This is the paper's own Eq. 1, shown in full. The middle term
            is a stress from slip between the phases; it's quadratic in
            u_slip, which for this model is just the Stokes settling
            velocity, on the order of nanometers per second. That makes
            the term many orders of magnitude smaller than the others,
            and it changes nothing numerically at these settling
            velocities. It is genuinely implemented in the solver now
            (src/physics.jl's slip_stress_coeff, wired into the momentum
            residual and its analytic Jacobian in src/solver.jl, verified
            against Gridap's automatic differentiation to machine
            precision).

            It had previously been omitted from both this deck and the
            code with no disclosure at all: caught in review, then
            actually fixed rather than just written up as a disclosed
            simplification. The summary slide's momentum row still shows
            this same complete form.

            This is the only momentum equation in the model. Fluid and
            suspended cells move together as one mixture; there is no
            separate momentum balance for the solid phase. Density and
            viscosity both depend on the local particle volume fraction
            Phi, defined on the next slide. That coupling is what makes
            this system nonlinear, and is where the suspension physics
            actually enters.
            """,
        )

    # ------------------------------------------------------------------
    def _viscosity_plot(self):
        # Krieger-Dougherty curve using this model's own parameters
        # (src/physics.jl: mu_f=0.5889, Phi_max=0.64), plotted as the
        # dimensionless ratio mu/mu_f so the fluid's own viscosity value
        # never needs to appear on screen.
        mu_f_ratio = lambda phi, phi_max=0.64: (1 - phi / phi_max) ** (-2.5 * phi_max)
        phi_max = 0.64

        axes = Axes(
            x_range=[0, 0.72, 0.16],
            y_range=[0, 20, 5],
            x_length=4.0,
            y_length=2.6,
            tips=False,
            axis_config={"font_size": 16, "stroke_color": GRAY_B, "include_numbers": True},
        )
        curve = axes.plot(mu_f_ratio, x_range=[0, 0.54], color=BLUE_C, stroke_width=3)
        asymptote = DashedLine(axes.c2p(phi_max, 0), axes.c2p(phi_max, 20), color=GRAY_B, stroke_width=2)
        x_label = Tex(r"$\Phi$", font_size=22).next_to(axes.x_axis.get_end(), RIGHT, buff=0.1)
        y_label = Tex(r"$\mu/\mu_f$", font_size=22).next_to(axes.y_axis.get_end(), UP, buff=0.1)
        phimax_label = Tex(r"$\Phi_{\max}$", font_size=18, color=GRAY_B).next_to(asymptote, UP, buff=0.08)
        return VGroup(axes, curve, asymptote, x_label, y_label, phimax_label)

    def chapter_2_density_viscosity(self):
        title = Text("Mixture density and viscosity", font_size=34, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        equation = eq(
            r"\rho=(1-\Phi)\rho_f^\circ+\Phi\rho_s^\circ \qquad \mu=\mu_f\left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}",
            font_size=30,
        ).next_to(title, DOWN, buff=0.5, aligned_edge=LEFT)
        if equation.width > 8.6:
            equation.scale(8.6 / equation.width, about_edge=LEFT)

        meaning_header = Text("Physical meaning", font_size=22, color=BLUE_C)
        meaning = BulletedList(
            "Density: a volume-weighted average of the pure fluid and solid densities",
            "Viscosity: the suspension thickens sharply as $\\Phi$ approaches $\\Phi_{\\max}$ (jamming)",
            font_size=22,
        )
        meaning_block = VGroup(meaning_header, meaning).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        meaning_block.next_to(equation, DOWN, buff=0.5, aligned_edge=LEFT)
        if meaning_block.width > 7.2:
            meaning_block.scale(7.2 / meaning_block.width, about_edge=LEFT)

        terms_header = Text("Terms", font_size=18, color=GRAY_B)
        terms = self._legend(
            r"$\Phi$: particle volume fraction (0 to $\Phi_{\max}$)",
            r"$\rho_f^\circ,\ \rho_s^\circ$: pure fluid and solid phase densities",
            r"$\mu_f$: pure fluid viscosity",
            r"$\Phi_{\max}$: maximum packing fraction",
            font_size=18,
        )
        term_group = VGroup(terms_header, terms).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        term_group.to_edge(DOWN, buff=0.4).align_to(title, LEFT)

        plot = self._viscosity_plot().to_edge(RIGHT, buff=0.6).shift(DOWN * 0.5)

        self.play(FadeIn(title))
        self.play(Write(equation))
        self.play(FadeIn(meaning_block))
        self.play(Create(plot))
        self.play(FadeIn(term_group))
        self.next_slide(
            notes="""
            Both closures are algebraic. No new PDEs; they just define rho
            and mu as functions of Phi so the momentum equation above can
            be solved. The Krieger-Dougherty viscosity is an empirical
            closure from the suspension-rheology literature, cited here,
            not derived in this paper.

            The plot is that Krieger-Dougherty curve itself, using this
            model's own parameters (Phi_max = 0.64, mu_f = 0.5889):
            viscosity stays close to the pure-fluid value at low Phi, then
            rises steeply and diverges as Phi approaches Phi_max, the
            random-close-packing limit where the suspension jams and stops
            behaving like a fluid at all.
            """
        )
        self.play(FadeOut(title), FadeOut(equation), FadeOut(meaning_block), FadeOut(term_group), FadeOut(plot))

    # ------------------------------------------------------------------
    def chapter_3_transport(self):
        self._equation_slide(
            name="Particle transport (master equation)",
            tex=r"\dot{\Phi} + \mathbf{u}\cdot\nabla\Phi = -\frac{\rho}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s",
            meaning_lines=[
                "$\\Phi$ is carried along by the bulk flow $\\mathbf{u}$ (advection, left-hand side)",
                "Plus a correction from any relative motion between the phases, via $\\nabla\\cdot\\mathbf{J}_s$",
                "This is the equation that actually says where the cells end up",
            ],
            term_lines=[
                r"$\mathbf{J}_s$: particle migration flux (defined next slide)",
            ],
            notes="""
            This is our own re-derivation of the paper's Phi-transport
            equation, verified from first principles with sympy
            (scripts/verify_paper_equations.py). The paper's own printed
            Eq. 10 states two different forms of this coefficient and
            claims they are equal; they are not, about 20x apart at the
            paper's own Table 1 densities. This slide shows the
            mathematically correct form. The full derivation and paper
            comparison live in the other deck and in the verification
            script, not here.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_4_flux_closure(self):
        title = Text("Flux closure: shear-induced migration", font_size=36, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        # Each additive piece of the equation is colored to match its own
        # explanation below, in place, instead of a free-floating bullet
        # list the reader has to map back onto the symbols by guesswork.
        eq_parts = VGroup(
            MathTex(r"\mathbf{J}_s/\rho_s^\circ = -\Big[", font_size=EQ_FONT),
            MathTex(r"0.41a^2\Phi\nabla(\dot{\gamma}\Phi)", font_size=EQ_FONT, color=BLUE_C),
            MathTex(r"+", font_size=EQ_FONT),
            MathTex(r"0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)", font_size=EQ_FONT, color=GREEN_C),
            MathTex(r"\Big]", font_size=EQ_FONT),
            MathTex(r"+", font_size=EQ_FONT),
            MathTex(r"f_h\mathbf{u}_{st}\Phi", font_size=EQ_FONT, color=ORANGE),
        ).arrange(RIGHT, buff=0.12)
        if eq_parts.width > MAX_EQ_WIDTH:
            eq_parts.scale_to_fit_width(MAX_EQ_WIDTH)
        eq_parts.next_to(title, DOWN, buff=0.55, aligned_edge=LEFT)

        meaning_header = Text("Physical meaning", font_size=22, color=BLUE_C).next_to(eq_parts, DOWN, buff=0.5, aligned_edge=LEFT)
        rows = [
            ("Shear term", "cells drift away from high-shear regions, toward calmer flow", BLUE_C),
            ("Viscosity term", "cells drift away from thick (viscous) regions, toward thinner ones", GREEN_C),
            ("Settling term", "gravity still pulls denser cells down, just slowed by the crowd around them", ORANGE),
        ]
        meaning_lines = VGroup()
        for label, desc, color in rows:
            lbl = Text(label + ": ", font_size=24, color=color, weight=BOLD)
            txt = Tex(desc, font_size=24)
            line = VGroup(lbl, txt).arrange(RIGHT, buff=0.12, aligned_edge=UP)
            if line.width > 11.0:
                line.scale(11.0 / line.width, about_edge=LEFT)
            meaning_lines.add(line)
        meaning_lines.arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        meaning_lines.next_to(meaning_header, DOWN, buff=0.3, aligned_edge=LEFT)

        terms_header = Text("Terms", font_size=18, color=GRAY_B)
        terms = self._legend(
            r"$a$: cell radius",
            r"$\dot{\gamma}$: shear rate (solved as its own field; see Implementation)",
            r"$f_h$: hindered-settling function",
            r"$\mathbf{u}_{st}$: Stokes settling velocity",
            font_size=18,
        )
        term_group = VGroup(terms_header, terms).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        term_group.to_edge(DOWN, buff=0.4).align_to(title, LEFT)

        self.play(FadeIn(title))
        self.play(Write(eq_parts))
        self.play(FadeIn(meaning_header), FadeIn(meaning_lines))
        self.play(FadeIn(term_group))
        self.next_slide(
            notes="""
            Three competing migration mechanisms in one flux, each term
            colored to match its own explanation so the mapping from
            symbol to meaning isn't left as an exercise for the audience.

            For anyone who wants the detail: the paper's own printed
            equations 12 through 14 are not fully self-consistent about
            the power of Phi in the shear-migration term (linear in one
            place, quadratic in another). We picked the form shown here
            (matching their Eq. 14) and disclose that choice rather than
            re-litigating it on this slide.
            """
        )
        self.play(FadeOut(title), FadeOut(eq_parts), FadeOut(meaning_header), FadeOut(meaning_lines), FadeOut(term_group))

    # ------------------------------------------------------------------
    def chapter_5_shear_rate(self):
        # Not called from construct() (see the comment there). Kept in
        # case a future version of this deck wants it back.
        self._equation_slide(
            name="Shear rate (auxiliary field)",
            tex=r"\dot{\gamma} = \left[\tfrac{1}{2}(\dot{\boldsymbol{\gamma}}:\dot{\boldsymbol{\gamma}})\right]^{1/2}, \qquad \dot{\boldsymbol{\gamma}}=\nabla\mathbf{u}+\nabla\mathbf{u}^T",
            meaning_lines=[
                "Scalar magnitude of the local strain-rate tensor",
                "Solved as its own field in the implementation, purely so $\\nabla\\dot\\gamma$ stays smooth near $\\dot\\gamma=0$: a numerical trick, not new physics",
            ],
            term_lines=[],
            notes="""
            No new physical unknowns here: gamma-dot is fully determined
            by u, which is already in the system. It is lifted into its
            own finite-element field in the implementation only because
            differentiating sqrt() of a quadratic form directly is
            singular at zero shear; more on that in the implementation
            slide.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_6_nutrient(self):
        self._equation_slide(
            name="Nutrient transport",
            tex=r"\dot{C} + \mathbf{u}\cdot\nabla C = D_f\nabla^2 C + r_c",
            meaning_lines=[
                "Standard advection, diffusion, and reaction for dissolved nutrient concentration",
                "$r_c$ is a sink: nutrient is consumed by the cells",
            ],
            term_lines=[
                r"$C$: nutrient concentration",
                r"$D_f$: nutrient diffusivity",
                r"$r_c$: consumption rate",
            ],
            notes="""
            The second transport equation in the system, coupled to the
            flow the same way Phi is: advected by u, plus its own
            diffusion and a sink term for consumption by the cells. Feeds
            into growth kinetics on the next slide.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_7_growth(self):
        self._equation_slide(
            name="Growth kinetics",
            tex=r"\dot{d} = k_c\, C\, d_0\, e^{k_e t}, \qquad \Phi = \tfrac{\pi}{6}\,d\,a^3",
            meaning_lines=[
                "Cell number density $d$ grows exponentially, nutrient-limited through $C$",
                "Converts back to a volume fraction $\\Phi$ through the (fixed) cell radius $a$",
            ],
            term_lines=[
                r"$d$: cell number density",
                r"$k_c$: growth-rate constant",
                r"$d_0$: initial cell density",
                r"$k_e$: growth-rate exponent",
            ],
            notes="""
            Closes the loop: nutrient concentration C drives cell-density
            growth d, which converts to volume fraction Phi, which feeds
            back into density/viscosity and the migration flux. Worth
            flagging in discussion if it comes up: the paper uses two
            distinct symbols for the growth-rate and nutrient-consumption
            constants; our code currently reuses one parameter (kc) for
            both. That is a disclosed simplification, not a bug.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_8_summary(self):
        title = Text("Every equation that defines the model", font_size=32, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        rows = [
            ("Momentum", r"\rho \dot{\mathbf{u}} + \rho(\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p - \nabla\cdot[\rho c_s(1-c_s)\mathbf{u}_{slip}\mathbf{u}_{slip}] + \nabla\cdot[\mu(\nabla\mathbf{u}+\nabla\mathbf{u}^T)] + \rho\mathbf{g}"),
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
        lines.scale_to_fit_width(12.0)
        lines.next_to(title, DOWN, buff=0.5, aligned_edge=LEFT)

        self.play(FadeIn(title))
        self.play(LaggedStart(*[FadeIn(l) for l in lines], lag_ratio=0.15))
        self.next_slide(
            notes="""
            The complete model, all seven pieces together: exactly what
            was shown one slide at a time on the previous seven slides,
            gathered here for reference before moving on to the
            implementation.
            """
        )
        self.play(FadeOut(title), FadeOut(lines))

    # ------------------------------------------------------------------
    def _fem_mesh_graphic(self, n=10, radius=1.15):
        # Ported verbatim from presentation.py: the actual mesh
        # src/examples.jl's build_harv_2d_case builds (n=10 default
        # partition warped onto the disk by harv_square_to_disk()), not a
        # stand-in schematic grid.
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

    def chapter_9_implementation(self):
        title = Text("Monolithic finite-element solver", font_size=34, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)
        subtitle = Text(
            "Solved as one weak (finite-element) system, all five fields together",
            font_size=22, color=GRAY_B,
        ).next_to(title, DOWN, buff=0.25, aligned_edge=LEFT)
        headline = Text("Julia · Gridap.jl", font_size=28, color=BLUE_C).next_to(subtitle, DOWN, buff=0.55, aligned_edge=LEFT)

        mesh = self._fem_mesh_graphic().next_to(headline, DOWN, buff=0.5, aligned_edge=LEFT)

        fields = VGroup(
            Tex(r"$\mathbf{u}$: fluid velocity", font_size=30),
            Tex(r"$p$: pressure", font_size=30),
            Tex(r"$\Phi$: particle volume fraction", font_size=30),
            Tex(r"$C$: nutrient concentration", font_size=30),
            Tex(r"$\dot{\gamma}$: shear rate, solved as its own field", font_size=30),
        ).arrange(DOWN, buff=0.22, aligned_edge=LEFT).next_to(headline, RIGHT, buff=1.0, aligned_edge=UP)

        self.play(FadeIn(title), FadeIn(subtitle))
        self.play(FadeIn(headline))
        self.play(Create(mesh))
        self.play(FadeIn(fields))
        self.next_slide(
            notes="""
            All five fields (u, p, Phi, C, gamma-dot) solved together,
            monolithically, each timestep, via Newton's method with a
            backtracking line search. Not a segregated or split scheme.

            Weak formulation, for anyone who wants the function spaces: u
            uses vector-valued, H1-conforming Lagrange elements of order
            2; p, Phi, C, and gamma-dot each use H1-conforming Lagrange
            elements of order 1. This velocity/pressure pairing (P2/P1,
            "Taylor-Hood") is the standard inf-sup stable choice for
            incompressible flow. Test spaces V, Q, W, Z, G and trial
            spaces U, P, Phi_space, C_space, Gamma_space are assembled
            into MultiFieldFESpaces Y and X respectively.

            Two math tricks were needed to make this solvable, beyond
            simply lifting shear rate into its own field:
            1. The shear rate itself is regularized: sqrt(|2 eps(u) dot
               eps(u)| + 1e-10), not a bare sqrt. Without that added
               constant, the derivative of sqrt(x) blows up as x
               approaches 0, which happens at rest (t=0) and at any point
               of locally rigid rotation, exactly the kind of state this
               problem starts in and passes through. That singular
               derivative would wreck Newton's Jacobian.
            2. The pressure space carries a zero-mean constraint. Velocity
               has a pure Dirichlet (no-slip, rotating-wall) boundary
               condition everywhere, so nothing else pins down an
               absolute pressure level. Without the zero-mean constraint,
               pressure would be determined only up to an arbitrary
               additive constant and the linear system would be singular.

            Verified two independent ways: the hand-derived analytic
            Jacobian matches Gridap's own automatic differentiation of the
            same residual to under 1e-8 relative error (a CI regression
            test); separately, the full nonlinear system is checked
            against the Method of Manufactured Solutions, confirming the
            solver converges to a known exact solution to near machine
            precision. Not just "the plots look plausible."
            """
        )
        self.play(FadeOut(title), FadeOut(subtitle), FadeOut(headline), FadeOut(mesh), FadeOut(fields))
        # No extra next_slide() here: chapter_10 has real animations of
        # its own, so this fade-out folds safely into its leading content
        # instead of needing a dedicated (and otherwise-blank) slide.

    # ------------------------------------------------------------------
    def chapter_10_results_setup(self):
        title = Text("Example simulation", font_size=36, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        setup = BulletedList(
            "Adversarial initial condition: cells start exactly where\\\\buoyancy alone would already want to hold them",
            "Question: does shear-induced migration visibly compete\\\\with that passive, buoyancy-favored equilibrium?",
            font_size=28,
        ).next_to(title, DOWN, buff=0.8, aligned_edge=LEFT)

        self.play(FadeIn(title))
        self.play(LaggedStart(*[FadeIn(b) for b in setup], lag_ratio=0.4))
        self.next_slide(
            notes="""
            Cells here are less dense than the surrounding medium
            (buoyant), and are placed in the upper half of the disk at
            t=0, exactly the configuration buoyancy alone would want
            anyway. If buoyancy were the only thing going on, the
            concentration field would just sit there.

            What follows is the same simulation shown two ways side by
            side: the flow field driving migration, next to the
            concentration field it's redistributing. Watch whether Phi
            visibly moves away from that buoyancy-favored starting point,
            tracking where the flow is most active. That is
            shear-induced migration actively fighting passive buoyant
            equilibrium, the qualitative claim the whole paper is built
            on.
            """
        )
        self.play(FadeOut(title), FadeOut(setup))

    # ------------------------------------------------------------------
    def chapter_11_results_video(self):
        # Zero-animation slide: the entire content is the external video
        # (which already carries its own on-screen captions).
        self.next_slide(
            src=RESULTS_VIDEO,
            notes="""
            Two caveats, stated plainly: (1) the timestep was chosen to
            resolve the Hele-Shaw drag relaxation time, the one fast
            process in this model; (2) buoyancy is artificially scaled up
            ~10^6x for this clip only, so its effect is visible on the
            same timescale as shear-induced migration. The momentum
            equation's own gravity term is untouched; only the settling
            flux is scaled, and only in this script.

            This is a qualitative, illustrative result on a coarse mesh
            with interpolated frames for smooth playback, not a converged
            production run.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_12_ring_pattern(self):
        title = Text("Cells pile up in a ring around mid-radius", font_size=30, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        fig = ImageMobject(str(PAPER_FIGURE_7)).scale_to_fit_width(6.0).next_to(title, DOWN, buff=0.4, aligned_edge=LEFT)
        fig_caption = Text(
            "Fig. 7, Chao & Das (2015): simulated cell density at t = 1, 3, 5, 7 days",
            font_size=16, color=GRAY_B,
        ).next_to(fig, DOWN, buff=0.15, aligned_edge=LEFT)

        meaning_header = Text("What the picture shows", font_size=20, color=BLUE_C)
        meaning = BulletedList(
            "Density concentrates in a thin, bright ring at roughly two-thirds\\\\of the disk's radius, in all four snapshots",
            "Just inside that ring, density is depleted: a visibly darker\\\\band sits between the ring and the center",
            "Shear-induced migration pushes cells out of the middle\\\\and out from the rim, and they pile up at that ring in between",
            font_size=22,
        )
        meaning_block = VGroup(meaning_header, meaning).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        if meaning_block.width > 6.0:
            meaning_block.scale(6.0 / meaning_block.width, about_edge=LEFT)
        meaning_block.next_to(fig, RIGHT, buff=0.8, aligned_edge=UP)

        self.play(FadeIn(title))
        self.play(FadeIn(fig), FadeIn(fig_caption))
        self.play(FadeIn(meaning_block))
        self.next_slide(
            notes="""
            This is the paper's own simulated result, read directly off
            the figure, not something we computed ourselves. Each panel's
            color scale is auto-ranged per panel, so at a glance the four
            snapshots look like the same static ring; the ring itself is
            the real content here.

            Physically: shear-induced migration pushes cells away from the
            highest-shear region (out near the rotating rim) and away from
            the very center (where the flow is calmest but so is the
            shear-migration driving force), so they accumulate at an
            intermediate radius instead of spreading out evenly. Four
            independent time snapshots all show the same ring, which is
            exactly what that competition between center and rim should
            produce.

            The next slide follows the same simulation's average density
            over time, which turns out to have its own, separate surprise.
            """
        )
        self.play(FadeOut(title), FadeOut(fig), FadeOut(fig_caption), FadeOut(meaning_block))

    # ------------------------------------------------------------------
    def chapter_13_density_collapse(self):
        title = Text("Cell density peaks, then collapses", font_size=32, weight=BOLD).to_edge(UP, buff=0.6).to_edge(LEFT, buff=LEFT_BUFF)

        fig = ImageMobject(str(PAPER_FIGURE_10)).scale_to_fit_width(6.0).next_to(title, DOWN, buff=0.4, aligned_edge=LEFT)
        fig_caption = Text(
            "Fig. 10, Chao & Das (2015): average cell density over the same run",
            font_size=16, color=GRAY_B,
        ).next_to(fig, DOWN, buff=0.15, aligned_edge=LEFT)

        meaning_header = Text("What the curve shows", font_size=20, color=BLUE_C)
        meaning = BulletedList(
            "Density roughly doubles over the first 4 days\\\\(about $3\\times10^{11}\\to 7\\times10^{11}$ cells/m$^3$)",
            "It plateaus around day 4-5, matching Fig. 7's own day-5 peak",
            "Then it collapses by nearly two-thirds by day 7,\\\\the same crash Fig. 7's color scale hinted at, now unmistakable",
            font_size=22,
        )
        meaning_block = VGroup(meaning_header, meaning).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        if meaning_block.width > 6.0:
            meaning_block.scale(6.0 / meaning_block.width, about_edge=LEFT)
        meaning_block.next_to(fig, RIGHT, buff=0.8, aligned_edge=UP)

        question = Text(
            "What happens after day 5?", font_size=24, color=BLUE_C, weight=BOLD
        )
        if question.width > 6.0:
            question.scale(6.0 / question.width)
        question.next_to(meaning_block, DOWN, buff=0.6, aligned_edge=LEFT)

        self.play(FadeIn(title))
        self.play(FadeIn(fig), FadeIn(fig_caption))
        self.play(FadeIn(meaning_block))
        self.play(FadeIn(question))
        self.next_slide(
            notes="""
            This is the same simulation as the previous slide, plotted as
            a continuous average over the whole disk instead of four
            discrete snapshots, and it confirms the previous slide's
            colorbar-peak observation with an actual trend line instead of
            four disconnected numbers: density rises for about four days,
            holds close to its peak for another day, then drops by nearly
            two-thirds over the next two days.

            We do not have the paper's own explanation for this on hand.
            A plausible read, given the model, is nutrient depletion
            catching up with growth (the growth term is directly
            proportional to local nutrient concentration C), but that is
            our inference, not a claim the paper defends explicitly.
            Ask the room: does anyone read this differently, or know
            whether the original paper discusses it?

            For anyone who wants the detail: the paper's own Nomenclature
            table defines this field's units ambiguously (cell density in
            mol/m^3, alongside a separately-defined phase density in
            kg/m^3 used elsewhere in the same model); we are reading the
            plotted values as printed, not resolving that ambiguity here.
            This figure's own caption also says it is "not compared
            directly to experimental measurements": a qualitative,
            simulated-only result, same as the ring pattern on the
            previous slide.

            Open for discussion.
            """
        )
