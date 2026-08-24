"""
manim-slides derivation of the Chao & Das (2015) Suspension Balance Model.

Keystroke-triggered walkthrough of every numbered equation in the paper (Eq.
1-26, 28), showing how the momentum balance, mixture continuity, and
solid-phase transport equations combine into the master particle-transport
equation (Eq. 21), then closing out with nutrient transport, growth kinetics,
and a one-screen summary of the complete model.

Render:
    manim-slides render chao_das_derivation.py ChaoDasDerivation
Present (keystroke-driven, arrow keys / space to advance):
    manim-slides present ChaoDasDerivation
Export to a self-contained HTML player (for embedding in Slidev via iframe):
    manim-slides convert ChaoDasDerivation ../public/chao_das_derivation.html

Implementation note: Transform(A, B) and TransformMatchingTex(A, B) mutate A
in place to look like B -- A is what remains "live" in the scene afterward;
B is only ever a template and is never itself added. Every step below
therefore transforms FROM the one tracked live mobject per slot (caption,
equation, eq-number), via the _start_*/_set_* helpers, and never introduces a
second on-screen equation that the main chain would need to continue from --
that "stack two, transform only one" choreography was tried first and is
exactly what caused a real bug (duplicated, never-removed text piling up in
a corner), caught by rendering and inspecting frames before trusting it.
"""
from manim import *
from manim_slides import Slide

# Keep captions compact -- one short line, not an explanation. The verbal
# narration during the actual talk carries the "why"; on-screen text only
# orients the viewer to which piece of the model is on screen.
CAPTION_FONT = 30
EQ_FONT = 40
MAX_EQ_WIDTH = 12.3


def eq(tex, font_size=EQ_FONT):
    m = MathTex(tex, font_size=font_size)
    if m.width > MAX_EQ_WIDTH:
        m.scale_to_fit_width(MAX_EQ_WIDTH)
    return m


def tag(text):
    return Text(text, font_size=CAPTION_FONT, weight=BOLD).to_edge(UP, buff=0.5)


def eqnum(n):
    return Text(f"Eq. {n}", font_size=22, color=GRAY).to_corner(DR, buff=0.4)


class ChaoDasDerivation(Slide):
    def construct(self):
        self.chapter_1_momentum()
        self.chapter_2_continuity_transport()
        self.chapter_3_flux_closure()
        self.chapter_4_shear_rate()
        self.chapter_5_assemble()
        self.chapter_6_rest_of_model()
        self.chapter_7_summary()

    # ------------------------------------------------------------------
    def chapter_title(self, text):
        title = Text(text, font_size=44, weight=BOLD)
        self.play(FadeIn(title, shift=UP * 0.3))
        self.next_slide()
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
        # Unlike plain Transform (which mutates its first argument in place, so
        # self.num/self.cap stay correct across repeated _set_num/_set_cap calls
        # with no reassignment needed -- confirmed by rendering), TransformMatchingTex
        # and FadeTransform do NOT leave the first argument as the scene's live
        # object -- confirmed by a render where every prior equation piled up
        # on screen because self.eq kept pointing at a stale, already-orphaned
        # mobject. Explicitly reassigning after every call, regardless of which
        # animation class was used, avoids depending on that per-class contract.
        self.play(anim(self.eq, new_mobj))
        self.eq = new_mobj

    def _end_group(self, *extra):
        self.play(FadeOut(self.cap), FadeOut(self.num), FadeOut(self.eq), *[FadeOut(m) for m in extra])

    # ------------------------------------------------------------------
    def chapter_1_momentum(self):
        self.chapter_title("1. Momentum")

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

    # ------------------------------------------------------------------
    def chapter_2_continuity_transport(self):
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
        self.next_slide()
        self._end_group(note)

    # ------------------------------------------------------------------
    def chapter_3_flux_closure(self):
        self.chapter_title("3. Closing the flux J_s")

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

    # ------------------------------------------------------------------
    def chapter_4_shear_rate(self):
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

    # ------------------------------------------------------------------
    def chapter_5_assemble(self):
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
        self.next_slide()
        self._end_group(note)

    # ------------------------------------------------------------------
    def chapter_6_rest_of_model(self):
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
        self.next_slide()
        self._end_group()

    # ------------------------------------------------------------------
    def chapter_7_summary(self):
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
