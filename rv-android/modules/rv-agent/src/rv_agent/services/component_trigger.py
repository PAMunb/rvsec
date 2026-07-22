"""
Component triggering as a stagnation escape (INV-AGT-48).

When exploration plateaus, the UI-driven strategy can no longer reach monitored
operations that live behind non-activity components (services started
programmatically, receivers fired by broadcasts). This service escapes the
plateau by dispatching those MOP-reaching components directly through the device
``am`` interface, bypassing the UI:

- services  → ``am start-service``
- receivers → ``am broadcast``

Activities are deliberately EXCLUDED from the trigger catalog — they are covered
by the launcher (E-mín MOP-first ordering in ``RVAgentStrategy``). Mixing them in
would double-drive activities and blur the launcher/trigger boundary (gh11
correction, design Decision #5).

Scope note (design Open Question "E-ext"): the trigger catalog is the
MOP-reaching non-activity components only (``reaches_target=True``). Exported
non-MOP components (E-ext) are NOT dispatched here — the spec (INV-AGT-48,
scenario "Activities Excluded from Triggering") scopes triggering to MOP-reaching
components, and widening to all exported components is left out until there is a
spec requirement for it.

Firing is gated three ways: it happens only on a plateau signal, only up to the
``component_percentage`` cadence (a deterministic 1-in-N period, so it is
seed-neutral), and never for a component whose dispatch previously failed (the
denylist prevents repeated waste). At most one component is dispatched per
invocation.
"""

import logging
from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    from rv_agent.agent.device_interface import DeviceInterface
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_android_core.domain.components import Components, ComponentInfo


logger = logging.getLogger(__name__)


class ComponentTriggerService:
    """
    Plateau-gated dispatcher of MOP-reaching services and receivers (INV-AGT-48).

    Holds the MOP-reaching non-activity catalog, a round-robin cursor over it, and
    a denylist of components whose dispatch failed. ``maybe_trigger`` is the single
    entry point; it dispatches at most one component per call and only when all of
    the gates (enabled, plateau, cadence, non-denylisted) allow.
    """

    def __init__(
        self,
        package_name: str,
        components: Optional["Components"],
        device: "DeviceInterface",
        config: "RVAgentConfig",
    ):
        """
        Initialize the component-trigger service.

        Args:
            package_name: Target application package, used to build ``pkg/class``
                component names for ``am``.
            components: Static component catalog, or None. When None (no static
                data), the trigger catalog is empty and the service never fires.
            device: Device interface providing ``start_service`` / ``send_broadcast``.
            config: Agent configuration (``component_trigger_enabled``,
                ``component_percentage``).

        State:
            self._candidates: MOP-reaching non-activity trigger catalog. Built
                once here; empty when components is None (service never fires).
            self._denylist: Class names whose dispatch failed. Grows in
                ``maybe_trigger``; excludes those components from future firing.
            self._cursor: Round-robin position into the catalog. Advances one
                slot per successful selection so triggers spread across components.
            self._opportunities: Count of plateau opportunities seen. Increments
                on every gated call; drives the deterministic cadence period.
        """
        self._package = package_name
        self._device = device
        # getattr-with-default so an incomplete test double (a bare
        # MagicMock(spec=RVAgentConfig) without the gh77 fields seeded) reads as
        # disabled rather than raising — a real RVAgentConfig always has them.
        self._enabled = getattr(config, "component_trigger_enabled", False)
        self._cadence = getattr(config, "component_percentage", 0.0)
        self._candidates: List["ComponentInfo"] = self._build_candidates(components)
        self._denylist: Set[str] = set()
        self._cursor = 0
        self._opportunities = 0

        logger.info(
            "ComponentTriggerService initialized: enabled=%s candidates=%d cadence=%.3f",
            self._enabled,
            len(self._candidates),
            self._cadence,
        )

    @staticmethod
    def _build_candidates(
        components: Optional["Components"],
    ) -> List["ComponentInfo"]:
        """
        Build the MOP-reaching non-activity trigger catalog (services + receivers).

        Activities are excluded (launcher territory); providers are not dispatched
        via ``am start-service``/``broadcast``. Only ``reaches_target=True`` entries
        are kept — a plateau escape targets monitored operations, not arbitrary
        components.

        Args:
            components: Static component catalog, or None when no static data is
                available.

        Returns:
            The MOP-reaching services and receivers with a resolvable
            ``class_name``, or an empty list when components is None.
        """
        if components is None:
            return []
        catalog: List["ComponentInfo"] = []
        for comp in list(components.services) + list(components.receivers):
            if comp.reaches_target and comp.class_name:
                catalog.append(comp)
        return catalog

    def maybe_trigger(self, plateau: bool) -> Optional[str]:
        """
        Dispatch at most one MOP-reaching component when the plateau gate allows.

        The dispatch fires only when the feature is enabled, the caller reports a
        plateau, the cadence period is reached, and a non-denylisted candidate
        exists. A failed dispatch is contained: the component is denylisted, the
        run continues, and None is returned (scenario "Dispatch Failure Is
        Contained").

        Args:
            plateau: True when the plateau detector signals stagnation.

        Returns:
            The dispatched component's ``class_name`` on success (for
            ``decision_source`` attribution), or None when nothing was dispatched.
        """
        if not self._enabled or not plateau:
            return None
        if not self._candidates:
            return None

        # Cadence gate: count every plateau opportunity, fire on the period.
        self._opportunities += 1
        if not self._cadence_allows():
            return None

        candidate = self._next_candidate()
        if candidate is None:
            return None  # every candidate is denylisted

        if self._dispatch(candidate):
            logger.info(
                "[RV-ARCH] component_trigger dispatched %s (%s)",
                candidate.class_name,
                candidate.component_type,
            )
            return candidate.class_name

        # Dispatch failure is contained: denylist and continue.
        self._denylist.add(candidate.class_name)
        logger.warning(
            "component_trigger dispatch failed for %s; added to denylist",
            candidate.class_name,
        )
        return None

    def _cadence_allows(self) -> bool:
        """
        Report whether the current opportunity falls on the cadence period.

        ``component_percentage`` is the fraction of opportunities that dispatch;
        it maps to a deterministic period ``round(1 / percentage)`` so firing is
        periodic in plateau opportunities and independent of any RNG (seed-neutral).
        A non-positive percentage disables firing entirely.
        """
        if self._cadence <= 0:
            return False
        period = max(1, round(1 / self._cadence))
        return self._opportunities % period == 0

    def _next_candidate(self) -> Optional["ComponentInfo"]:
        """
        Return the next non-denylisted candidate via round-robin, or None.

        Walks the catalog once from the persisted cursor so repeated triggers
        spread across the MOP components rather than hammering the first one.
        """
        n = len(self._candidates)
        for i in range(n):
            idx = (self._cursor + i) % n
            candidate = self._candidates[idx]
            if candidate.class_name not in self._denylist:
                self._cursor = (idx + 1) % n
                return candidate
        return None

    def _dispatch(self, component: "ComponentInfo") -> bool:
        """Dispatch one component via the matching ``am`` verb and report success."""
        name = f"{self._package}/{component.class_name}"
        if component.component_type == "service":
            return self._device.start_service(name)
        if component.component_type == "receiver":
            return self._device.send_broadcast(name)
        # The catalog is built from services + receivers only; any other type is a
        # programming error rather than a runtime condition.
        logger.warning(
            "component_trigger skipped unsupported component type: %s",
            component.component_type,
        )
        return False
