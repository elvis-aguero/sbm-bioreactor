"""
manim-slides presentation: "Where Do the Cells Go? -- High-Level Overview".

A SEPARATE, shorter deck from presentation.py. Where presentation.py builds
every equation on screen step by step (full algebra, red-flagged paper
discrepancies inline), this deck skips the derivation entirely: one final
equation per slide (Name / Equation / Physical meaning / Undefined terms),
then the same summary table and implementation slides as the main deck
(reused verbatim), followed by a results section (test-case setup /
video / paper's own takeaways / cross-field relevance) aimed at a
general audience, not just fluids specialists. Built mechanically per
an explicit request
-- this file intentionally duplicates a few small helpers from
presentation.py rather than importing from it, so the two decks can keep
evolving independently.

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

RESULTS_VIDEO = Path(__file__).parent / "results_combined.mp4"


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
        self.chapter_1_momentum()
        self.chapter_2_density_viscosity()
        self.chapter_3_transport()
        self.chapter_4_flux_closure()
        self.chapter_5_shear_rate()
        self.chapter_6_nutrient()
        self.chapter_7_growth()
        self.chapter_8_summary()
        self.chapter_9_implementation()
        self.chapter_10_results_setup()
        self.chapter_11_results_video()
        self.chapter_12_paper_takeaways()
        self.chapter_13_broader_relevance()

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
        title = Text(name, font_size=36, weight=BOLD).to_edge(UP, buff=0.6)

        equation = eq(tex, font_size=eq_font_size).next_to(title, DOWN, buff=0.55)

        meaning_header = Text("Physical meaning", font_size=22, color=BLUE_C)
        meaning = BulletedList(*meaning_lines, font_size=24)
        meaning_block = VGroup(meaning_header, meaning).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        meaning_block.next_to(equation, DOWN, buff=0.55)
        if meaning_block.width > 12.0:
            meaning_block.scale_to_fit_width(12.0)

        term_group = VGroup()
        if term_lines:
            terms_header = Text("Terms", font_size=18, color=GRAY_B)
            terms = self._legend(*term_lines, font_size=18)
            term_group = VGroup(terms_header, terms).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            term_group.to_corner(DL, buff=0.4)

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
        title = Text("Where Do the Cells Go?", font_size=52, weight=BOLD)
        subtitle = Text(
            "High-level overview -- Chao & Das (2015), Chem. Eng. J.", font_size=26, color=GRAY_B
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
    def chapter_1_momentum(self):
        self._equation_slide(
            name="Momentum balance",
            tex=r"\rho \dot{\mathbf{u}} + \rho(\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p + \nabla\cdot[\mu(\nabla\mathbf{u}+\nabla\mathbf{u}^T)] + \rho\mathbf{g}",
            meaning_lines=[
                "Mixture momentum balance -- fluid and suspended cells treated as one continuum",
                "Ordinary variable-density, variable-viscosity Navier--Stokes",
                "Buoyancy enters through $\\rho\\mathbf{g}$",
            ],
            term_lines=[
                r"$\rho$ -- mixture density",
                r"$\mathbf{u}$ -- mixture velocity",
                r"$p$ -- pressure",
                r"$\mu$ -- mixture viscosity",
                r"$\mathbf{g}$ -- gravity",
            ],
            notes="""
            This is the only momentum equation in the model -- fluid and
            suspended cells move together as one mixture, no separate
            momentum balance for the solid phase. Density and viscosity
            both depend on the local particle volume fraction Phi, defined
            next slide -- that coupling is what makes this system nonlinear
            and is where the suspension physics actually enters.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_2_density_viscosity(self):
        self._equation_slide(
            name="Mixture density & viscosity",
            tex=r"\rho=(1-\Phi)\rho_f^\circ+\Phi\rho_s^\circ \qquad \mu=\mu_f\left(1-\frac{\Phi}{\Phi_{\max}}\right)^{-2.5\Phi_{\max}}",
            meaning_lines=[
                "Density: volume-weighted average of the pure fluid and pure solid densities",
                "Viscosity: Krieger--Dougherty closure -- the suspension thickens sharply as $\\Phi\\to\\Phi_{\\max}$ (jamming)",
            ],
            term_lines=[
                r"$\Phi$ -- particle volume fraction (0 to $\Phi_{\max}$)",
                r"$\rho_f^\circ,\ \rho_s^\circ$ -- pure fluid / solid phase densities",
                r"$\mu_f$ -- pure fluid viscosity",
                r"$\Phi_{\max}$ -- maximum packing fraction",
            ],
            notes="""
            Both closures are algebraic -- no new PDEs, they just define
            rho and mu as functions of Phi so the momentum equation above
            can be solved. The Krieger-Dougherty viscosity is an empirical
            closure from the suspension-rheology literature, not derived in
            this paper -- cited, not original to it.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_3_transport(self):
        self._equation_slide(
            name="Particle transport (master equation)",
            tex=r"\dot{\Phi} + \mathbf{u}\cdot\nabla\Phi = -\frac{\rho}{\rho_s^\circ\rho_f^\circ}\,\nabla\cdot\mathbf{J}_s",
            meaning_lines=[
                "$\\Phi$ is carried along by the bulk flow $\\mathbf{u}$ (advection, left-hand side)",
                "...plus a correction from any relative motion between the phases, via $\\nabla\\cdot\\mathbf{J}_s$",
                "This is the equation that actually says where the cells end up",
            ],
            term_lines=[
                r"$\mathbf{J}_s$ -- particle migration flux (defined next slide)",
            ],
            notes="""
            This is our own re-derivation of the paper's Phi-transport
            equation, verified from first principles with sympy
            (scripts/verify_paper_equations.py) -- the paper's own printed
            Eq. 10 states two different forms of this coefficient and
            claims they're equal; they aren't, about 20x apart at the
            paper's own Table 1 densities. This slide shows the
            mathematically correct form. Full derivation and the paper
            comparison are in the other deck / the verification script, not
            here.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_4_flux_closure(self):
        self._equation_slide(
            name="Flux closure -- shear-induced migration",
            tex=r"\mathbf{J}_s/\rho_s^\circ = -\left[0.41a^2\Phi\nabla(\dot{\gamma}\Phi) + 0.62a^2\Phi^2\dot{\gamma}\nabla(\ln\mu)\right] + f_h\mathbf{u}_{st}\Phi",
            meaning_lines=[
                "Shear-rate gradients push cells toward low-shear regions",
                "Viscosity gradients reinforce that same migration",
                "Hindered settling adds a buoyancy/gravity contribution",
                "This is the term that actually couples flow gradients to particle transport",
            ],
            term_lines=[
                r"$a$ -- cell radius",
                r"$\dot{\gamma}$ -- shear rate (defined next slide)",
                r"$f_h$ -- hindered-settling function",
                r"$\mathbf{u}_{st}$ -- Stokes settling velocity",
            ],
            notes="""
            Three competing migration mechanisms in one flux. Worth noting
            for anyone who wants the detail: the paper's own printed
            equations 12-14 aren't fully self-consistent about the power of
            Phi in the shear-migration term (linear in one place, quadratic
            in another) -- we picked the form shown here (matching their
            Eq. 14) and disclose that choice; not re-litigating it on this
            slide.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_5_shear_rate(self):
        self._equation_slide(
            name="Shear rate (auxiliary field)",
            tex=r"\dot{\gamma} = \left[\tfrac{1}{2}(\dot{\boldsymbol{\gamma}}:\dot{\boldsymbol{\gamma}})\right]^{1/2}, \qquad \dot{\boldsymbol{\gamma}}=\nabla\mathbf{u}+\nabla\mathbf{u}^T",
            meaning_lines=[
                "Scalar magnitude of the local strain-rate tensor",
                "Carried as its own field ($\\Gamma$) in the solver purely so $\\nabla\\dot\\gamma$ stays smooth near $\\dot\\gamma=0$ -- a numerical trick, not new physics",
            ],
            term_lines=[],
            notes="""
            No new physical unknowns here -- gamma-dot is fully determined
            by u, which is already in the system. It's lifted into its own
            finite-element field in the implementation only because
            differentiating sqrt() of a quadratic form directly is singular
            at zero shear; more on that in the implementation slide.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_6_nutrient(self):
        self._equation_slide(
            name="Nutrient transport",
            tex=r"\dot{C} + \mathbf{u}\cdot\nabla C = D_f\nabla^2 C + r_c",
            meaning_lines=[
                "Standard advection--diffusion--reaction for dissolved nutrient concentration",
                "$r_c$ is a sink -- nutrient is consumed by the cells",
            ],
            term_lines=[
                r"$C$ -- nutrient concentration",
                r"$D_f$ -- nutrient diffusivity",
                r"$r_c$ -- consumption rate",
            ],
            notes="""
            The second transport equation in the system, coupled to the
            flow the same way Phi is -- advected by u, plus its own
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
                r"$d$ -- cell number density",
                r"$k_c$ -- growth-rate constant",
                r"$d_0$ -- initial cell density",
                r"$k_e$ -- growth-rate exponent",
            ],
            notes="""
            Closes the loop: nutrient concentration C drives cell-density
            growth d, which converts to volume fraction Phi, which feeds
            back into density/viscosity and the migration flux. Worth
            flagging in discussion if it comes up: the paper uses two
            distinct symbols for the growth-rate and nutrient-consumption
            constants; our code currently reuses one parameter (kc) for
            both -- a disclosed simplification, not a bug.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_8_summary(self):
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
            The complete model, all seven pieces side by side -- exactly
            what was shown one slide at a time on the previous seven
            slides, just gathered here for reference before moving on to
            the implementation.
            """
        )
        self.play(FadeOut(title), FadeOut(lines))

    # ------------------------------------------------------------------
    def _fem_mesh_graphic(self, n=10, radius=1.15):
        # Ported verbatim from presentation.py -- the actual mesh
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
        title = Text("Monolithic finite-element solver", font_size=34, weight=BOLD).to_edge(UP, buff=0.6)
        headline = Text("Julia · Gridap.jl", font_size=30, color=BLUE_C).to_edge(LEFT, buff=1.0).shift(UP * 1.6)

        mesh = self._fem_mesh_graphic().next_to(headline, DOWN, buff=0.6, aligned_edge=LEFT)

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
            All five fields (u, p, Phi, C, Gamma) in one coupled nonlinear
            system, solved together each timestep with Newton's method --
            not a segregated/split scheme. Monolithic is more expensive per
            step but avoids splitting error entirely.

            Verified two independent ways: the hand-derived analytic
            Jacobian matches Gridap's own automatic differentiation of the
            same residual to under 1e-8 relative error (a CI regression
            test); separately, the full nonlinear system is checked against
            the Method of Manufactured Solutions, confirming the solver
            converges to a known exact solution to near machine precision.
            Not just "the plots look plausible."
            """
        )
        self.play(FadeOut(title), FadeOut(headline), FadeOut(mesh), FadeOut(fields))
        self.next_slide()

    # ------------------------------------------------------------------
    def chapter_10_results_setup(self):
        title = Text("Putting it to the test", font_size=36, weight=BOLD).to_edge(UP, buff=0.6)

        setup = BulletedList(
            "Adversarial initial condition: cells start exactly where\\\\buoyancy alone would already want to hold them",
            "Question: does shear-induced migration visibly compete\\\\with that passive, buoyancy-favored equilibrium?",
            font_size=28,
        ).next_to(title, DOWN, buff=0.8)

        self.play(FadeIn(title))
        self.play(LaggedStart(*[FadeIn(b) for b in setup], lag_ratio=0.4))
        self.next_slide(
            notes="""
            Cells here are less dense than the surrounding medium
            (buoyant), and are placed in the upper half of the disk at
            t=0 -- exactly the configuration buoyancy alone would want
            anyway. If buoyancy were the only thing going on, the
            concentration field would just sit there.

            What follows is the same simulation shown two ways side by
            side: the flow field driving migration, next to the
            concentration field it's redistributing. Watch whether Phi
            visibly moves away from that buoyancy-favored starting point,
            tracking where the flow is most active -- that's
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
            ~10^6x for this clip only, so its effect is visible on the same
            timescale as shear-induced migration -- the momentum equation's
            own gravity term is untouched, only the settling flux is
            scaled, and only in this script.

            This is a qualitative, illustrative result on a coarse mesh
            with interpolated frames for smooth playback -- not a
            converged production run.
            """,
        )

    # ------------------------------------------------------------------
    def chapter_12_paper_takeaways(self):
        title = Text("What the paper found", font_size=36, weight=BOLD).to_edge(UP, buff=0.6)

        points = BulletedList(
            "Shear-induced migration is not a small correction to buoyancy\\\\-- it measurably redistributes cells even in a \"low-shear\" vessel",
            "A 2D, depth-averaged model (with a Hele-Shaw drag term standing\\\\in for the 3rd dimension) is enough to capture that competition",
            "Standard suspension-rheology closures (Krieger--Dougherty\\\\viscosity, shear/viscosity-gradient migration) transfer directly\\\\onto a biological particle -- no cell-specific physics required",
            font_size=26,
        ).next_to(title, DOWN, buff=0.7)

        self.play(FadeIn(title))
        self.play(LaggedStart(*[FadeIn(p) for p in points], lag_ratio=0.4))
        self.next_slide(
            notes="""
            The paper's central point, stripped of the equations: a
            rotating vessel designed specifically to minimize shear still
            has enough shear structure to move cells around in a way
            buoyancy alone would not predict. "Low shear" is a design
            goal, not a statement that transport stops.

            The closures themselves (Krieger-Dougherty viscosity,
            shear-induced migration flux) come from decades of suspension
            rheology on inert particles -- sand, glass beads, emulsions.
            The paper's contribution is showing they carry over to a
            living, growing particle population with almost no
            modification.
            """
        )
        self.play(FadeOut(title), FadeOut(points))

    # ------------------------------------------------------------------
    def chapter_13_broader_relevance(self):
        title = Text("Why it matters, across fields", font_size=34, weight=BOLD).to_edge(UP, buff=0.6)

        rows = [
            ("Experimentalists", "predicts where cells will concentrate before you run the culture -- informs probe placement and vessel design"),
            ("Biologists", "gives a mechanistic reason \"low shear'' isn't \"no transport'' -- local flow sets the local growth environment"),
            ("Chemists / rheologists", "the same closures generalize to any concentrated suspension -- slurries, colloids, blood analogs, not just cells"),
            ("Applied mathematicians", "a coupled 5-field nonlinear PDE system with a documented, reusable verification path (MMS + Jacobian check)"),
        ]
        lines = VGroup()
        for label, desc in rows:
            lbl = Text(label + ":  ", font_size=24, color=BLUE_C, weight=BOLD)
            txt = Tex(desc, font_size=24)
            line = VGroup(lbl, txt).arrange(RIGHT, buff=0.15, aligned_edge=UP)
            if line.width > 12.0:
                line.scale_to_fit_width(12.0)
            lines.add(line)
        lines.arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        lines.next_to(title, DOWN, buff=0.7)

        self.play(FadeIn(title))
        self.play(LaggedStart(*[FadeIn(l) for l in lines], lag_ratio=0.25))
        self.next_slide(
            notes="""
            The point of this slide: an SBM isn't just "the Chao & Das
            paper" -- it's a reusable modeling pattern any of these
            audiences can pick up.

            - Experimentalists get a predictive tool instead of pure
              trial-and-error vessel design -- run the model before you
              run the bioreactor.
            - Biologists get a physical explanation for spatial
              heterogeneity in culture outcomes that's otherwise easy to
              misattribute to biological variability.
            - Chemists/rheologists already have this toolkit for inert
              particles -- this is a demonstration it survives contact
              with a living, growing, consuming particle phase.
            - Applied mathematicians get a concrete, moderately-sized
              coupled nonlinear system with a worked verification
              story (MMS + analytic-vs-AD Jacobian) that generalizes to
              validating other multiphysics couplings.

            Now open for discussion.
            """
        )
        self.play(FadeOut(title), FadeOut(lines))
