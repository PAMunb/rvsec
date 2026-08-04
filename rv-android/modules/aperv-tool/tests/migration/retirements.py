"""The 21 retired arm names, each with the kind of retirement it is and why.

The list exists so that a name leaving `get_variants()` is a *decision on the record* rather
than an absence. The regeneration diff reads it: a baseline arm that is gone and listed here
is reported as a documented retirement, and a baseline arm that is gone and NOT listed here
fails the check. Without that, deleting an arm by accident and retiring one on purpose would
produce the same green test.

The three kinds are kept apart because merging them would misreport what the migration did:

- **never distinct** — the name carried no configuration of its own. Nothing is lost, because
  there was nothing there that another name does not already have.
- **name consolidated** — the configuration survives, under the name given by `survivor`. The
  diff proves that claim rather than repeating it: the survivor must regenerate the retired
  name's baseline entry exactly.
- **finished campaign** — the configuration is real and is being retired anyway, because the
  campaign it served has concluded. Recorded results are frozen artifacts and are unaffected;
  what ends is the ability to launch new runs under the name.
"""

from dataclasses import dataclass
from typing import Dict

KIND_NEVER_DISTINCT = "never distinct"
KIND_NAME_CONSOLIDATED = "name consolidated"
KIND_FINISHED_CAMPAIGN = "finished campaign"


@dataclass(frozen=True)
class Retirement:
    """One retired arm name: what kind of retirement, why, and what survives it."""

    kind: str
    reason: str
    survivor: str | None = None


RETIREMENTS: Dict[str, Retirement] = {
    "ape_pure": Retirement(
        KIND_NEVER_DISTINCT,
        "enumerated every RV flag at its off value because the jar exposed no kill switch. "
        "After stage 2 purity is structural — ape.apePureMode is a retired key whose abort "
        "message reads 'purity is structural: a feature absent from the plan does not "
        "exist' — and owner decision D3 descopes the stock-APE mode. The comparison with "
        "original APE stays anchored on the frozen phase-2 data",
    ),
    "bfs": Retirement(
        KIND_NEVER_DISTINCT,
        "never an agent type: ApeAgent.createAgent accepts only sata, random and replay, and "
        "every other value fell through to SataAgent, so this arm always carried sata's "
        "effective configuration under a name that promised something else",
    ),
    "sata_mop_widget": Retirement(
        KIND_NEVER_DISTINCT,
        "one object under two names — get_variants() bound it and sata_mop to the same dict. "
        "sata_mop is the surviving name because it is the one the frozen corpus carries",
        survivor="sata_mop",
    ),
    "sata_mop_act_frontier": Retirement(
        KIND_NAME_CONSOLIDATED,
        "byte-identical to mop_on_llm_off — the ANC2 anchor under two names. The "
        "configuration that won the cmpma multi-arm comparison survives under the name the "
        "E3 decisive run recorded",
        survivor="mop_on_llm_off",
    ),
    "sata_mop_activity": Retirement(
        KIND_FINISHED_CAMPAIGN,
        "an intermediate step of the reach decomposition (widget → +A′ → +B+E-min), "
        "superseded by the reach package the decisive run's arms carry",
    ),
    "random": Retirement(
        KIND_FINISHED_CAMPAIGN,
        "a baseline whose strategy is not retired with it: 'random' stays in the configure() "
        "whitelist and remains reachable as aperv:sata@strategy=random. What ends is the "
        "named arm",
    ),
}

# The six gh43 prompt-ablation arms: identical but for llm_prompt_variant, which is what the
# ablation varied. The campaign concluded and its results are frozen artifacts.
for _variant in (
    "ape_current",
    "ape_reasoning",
    "compact_v1",
    "v13",
    "v17",
    "visual_only",
):
    RETIREMENTS[f"sata_mop_llm_{_variant}"] = Retirement(
        KIND_FINISHED_CAMPAIGN,
        f"gh43 prompt ablation, arm '{_variant}'. The ablation concluded; the six arms "
        "differed only in llm_prompt_variant and their recorded results are unaffected",
    )

# The nine Phase-A calibration arms. The campaign ended with VERIFY ADMISSIBLE on 2026-07-24,
# and phases B and C were superseded by the decisive run's pre-registration freeze of
# 2026-08-01, so no further run is launched under these names.
for _index in range(1, 10):
    RETIREMENTS[f"cal_a{_index}"] = Retirement(
        KIND_FINISHED_CAMPAIGN,
        f"gh88 Phase-A LLM calibration, arm A{_index}. The campaign concluded (VERIFY "
        "ADMISSIBLE, 2026-07-24) and phases B and C were superseded by the decisive run's "
        "FREEZE-PREREGISTRO of 2026-08-01",
    )
