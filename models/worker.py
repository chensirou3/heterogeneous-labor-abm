"""
Worker agent for Models B and C.
Each worker has a state (E/U/N) and behavioral parameters.
"""
import numpy as np
from models.config import EMPLOYED, UNEMPLOYED, NILF


class Worker:
    __slots__ = [
        "state", "reservation_wage", "base_reservation_wage",
        "offer_arrival_belief",
        "search_intensity", "participation_propensity",
        "worker_type", "age_group", "edu_group", "sex",
        "months_in_state",
    ]

    def __init__(
        self,
        state: int,
        reservation_wage: float,
        offer_arrival_belief: float,
        search_intensity: float,
        participation_propensity: float,
        worker_type: int = 2,
        age_group: int = 1,
        edu_group: int = 0,
        sex: int = 0,
    ):
        self.state = state
        self.reservation_wage = reservation_wage
        self.base_reservation_wage = reservation_wage  # original (undecayed) value
        self.offer_arrival_belief = offer_arrival_belief
        self.search_intensity = search_intensity
        self.participation_propensity = participation_propensity
        self.worker_type = worker_type
        self.age_group = age_group
        self.edu_group = edu_group
        self.sex = sex
        self.months_in_state = 0

    def step(
        self,
        vacancy_rate: float,
        layoff_rate: float,
        mean_log_offer_wage: float,
        sd_log_offer_wage: float,
        rng: np.random.RandomState,
        offer_received: bool = False,
        use_type_behavior: bool = True,
        use_declining_rw: bool = True,
    ) -> int:
        """
        Execute one monthly transition. Returns new state.

        Parameters
        ----------
        offer_received : bool
            If True, skip independent offer draw (matching market assigned).
        use_type_behavior : bool
            If False, all type multipliers = 1.0 (ablation).
        use_declining_rw : bool
            If False, no reservation wage decay (ablation).
        """
        old_state = self.state
        pp = self.participation_propensity
        si = self.search_intensity
        oab = self.offer_arrival_belief
        wt = self.worker_type

        # ── Type-specific behavioral modifiers ──
        if use_type_behavior:
            type_layoff_mult = {0: 0.85, 1: 1.0, 2: 1.15}.get(wt, 1.0)
            type_exit_mult = {0: 0.5, 1: 0.7, 2: 1.3}.get(wt, 1.0)
            type_reentry_mult = {0: 1.3, 1: 1.2, 2: 0.6}.get(wt, 1.0)
        else:
            type_layoff_mult = type_exit_mult = type_reentry_mult = 1.0

        # ── Declining reservation wage during unemployment ──
        if old_state == UNEMPLOYED and use_declining_rw:
            decay = max(0.70, 1.0 - 0.03 * self.months_in_state)
            effective_rw = self.base_reservation_wage * decay
        else:
            effective_rw = self.base_reservation_wage
            if old_state == EMPLOYED:
                self.reservation_wage = self.base_reservation_wage

        if old_state == EMPLOYED:
            # ── E → U (layoff) ──
            adj_layoff = layoff_rate * type_layoff_mult
            if rng.random() < adj_layoff:
                self.state = UNEMPLOYED
            # ── E → N (voluntary exit) ──
            else:
                p_en = min(0.04, (1.0 - pp) * 0.035 + 0.005) * type_exit_mult
                if rng.random() < p_en:
                    self.state = NILF

        elif old_state == UNEMPLOYED:
            # ── U → E (find job) ──
            got_offer = offer_received  # from matching market (Model C)
            if not got_offer:
                # Independent offer arrival (Models A & B)
                effective_si = max(si, 0.5)
                p_offer = _offer_prob(effective_si, oab, vacancy_rate)
                got_offer = rng.random() < p_offer

            if got_offer:
                offer_w = np.exp(rng.normal(mean_log_offer_wage, sd_log_offer_wage))
                if offer_w >= effective_rw:
                    self.state = EMPLOYED

            # ── U → N (discouraged) ──
            if self.state == UNEMPLOYED:
                p_un = min(0.25, (1.0 - pp) * 0.30 + 0.02) * type_exit_mult
                if self.months_in_state > 6:
                    p_un = min(0.30, p_un * 1.15)
                if rng.random() < p_un:
                    self.state = NILF

        else:  # NILF
            # ── N → U (re-enter as searcher) ──
            p_nu = pp * 0.04 * type_reentry_mult
            if rng.random() < p_nu:
                self.state = UNEMPLOYED
            # ── N → E (direct entry) ──
            else:
                p_ne = pp * 0.06 * type_reentry_mult
                if rng.random() < p_ne:
                    got_offer = offer_received
                    if not got_offer:
                        p_offer = _offer_prob(0.4, oab, vacancy_rate)
                        got_offer = rng.random() < p_offer
                    if got_offer:
                        offer_w = np.exp(rng.normal(mean_log_offer_wage, sd_log_offer_wage))
                        if offer_w >= effective_rw:
                            self.state = EMPLOYED

        # Track duration
        if self.state == old_state:
            self.months_in_state += 1
        else:
            self.months_in_state = 0
            self.reservation_wage = effective_rw

        return self.state


def _offer_prob(si: float, oab: float, vacancy_rate: float,
                baseline_vacancy: float = 4.0) -> float:
    """P(offer) = si × oab × (V / V_baseline), clamped to [0, 0.95]."""
    p = si * oab * (vacancy_rate / baseline_vacancy)
    return min(max(p, 0.0), 0.95)
