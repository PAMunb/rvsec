"""The `-NOBS-` channel, separated from the accusations (gh109 task 8.7, INV-INS-158).

    INV-INS-158   a report line whose code marks an unobserved predicate is never
                  aggregated as conformance nor as violation; the separation is keyed on
                  the `site_kind` column of `codes.csv`, because `ErrorType` cannot
                  separate them -- `-NOBS-` and `-CONSTR-` share `UnsatisfiedConstraint`
                  by construction

Two halves are asserted here. The first is the classification itself, over fixtures, and
it holds in any checkout: a NOBS code lands in neither of the summable channels, an
unknown code lands in neither either, and a catalogue that contradicts itself raises
rather than picking a side. The second reads the real `jca_android/codes.csv` and asserts
the premise the invariant rests on -- that the two families really are indistinguishable
by `ErrorType` -- so that if a future set ever gave NOBS an `ErrorType` of its own, the
reason this module exists would be re-examined rather than inherited.

The second half needs the sibling Java reactor and skips without it.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"

sys.path.insert(0, str(SCRIPTS))

from gh109_nobs_channel import (  # noqa: E402
    CHANNEL_ACCUSATION,
    CHANNEL_NOT_OBSERVED,
    CHANNEL_UNCLASSIFIED,
    NOT_OBSERVED_KIND,
    InconsistentCatalogue,
    channel,
    code_of,
    load_site_kinds,
    tally,
)

SUCCESSOR = "rvsec/rvsec-mop/src/main/resources/jca_android"

HEADER = "spec,code,error_type,site_kind,event,file_line\n"


def _codes_csv(tmp_path: Path, rows: str) -> Path:
    path = tmp_path / "codes.csv"
    path.write_text(HEADER + rows, encoding="utf-8")
    return path


def _report(code: str) -> str:
    """One raw logcat line carrying `code`, in the seven-field form both eras write."""
    envelope = f"v=1 code={code} ev=i1 obj=Cipher val='' exp='a key' msg='no producer observed'"
    return (
        "08-28 10:00:00.000  1000  1000 E RVSEC   : "
        f"CipherSpec,br.unb.App,App,onCreate,App.java:10,UnsatisfiedConstraint,{envelope}\n"
    )


def _set_dir() -> Path:
    home = os.environ.get("RVSEC_HOME")
    if not home:
        pytest.skip(
            "RVSEC_HOME is unset; the specification set is in the sibling reactor"
        )
    set_dir = Path(home) / SUCCESSOR
    if not set_dir.is_dir():
        pytest.skip(f"the successor set is absent: {set_dir}")
    return set_dir


class TestClassification:
    """What channel a code lands in, and what the answer rests on."""

    def test_the_column_and_not_the_code_string_decides(self, tmp_path):
        """`site_kind` is the authority.

        The code string spells its family too, and the two agree in every committed
        catalogue -- but the column is the declaration, so this test fixes which of the
        two a reader may rename without changing what is summed.
        """
        codes = _codes_csv(
            tmp_path,
            "CipherSpec,CIPHER-NOBS-00,UnsatisfiedConstraint,NOBS,i1,CipherSpec.mop:1\n"
            "CipherSpec,CIPHER-CONSTR-00,UnsatisfiedConstraint,CONSTR,i1,CipherSpec.mop:2\n",
        )
        kinds = load_site_kinds(codes)

        assert channel("CIPHER-NOBS-00", kinds) == CHANNEL_NOT_OBSERVED
        assert channel("CIPHER-CONSTR-00", kinds) == CHANNEL_ACCUSATION

    def test_an_unobserved_line_is_summed_as_neither(self, tmp_path):
        """The invariant itself: NOBS is not conformance and not violation."""
        codes = _codes_csv(
            tmp_path,
            "CipherSpec,CIPHER-NOBS-00,UnsatisfiedConstraint,NOBS,i1,CipherSpec.mop:1\n"
            "CipherSpec,CIPHER-CONSTR-00,UnsatisfiedConstraint,CONSTR,i1,CipherSpec.mop:2\n",
        )
        kinds = load_site_kinds(codes)
        lines = [_report("CIPHER-NOBS-00")] * 3 + [_report("CIPHER-CONSTR-00")]

        by_channel, by_code = tally(lines, kinds)

        assert by_channel[CHANNEL_NOT_OBSERVED] == 3
        assert by_channel[CHANNEL_ACCUSATION] == 1
        assert by_code["CIPHER-NOBS-00"] == 3

    def test_a_code_the_catalogue_does_not_know_is_named_not_folded(self, tmp_path):
        """A pre-gh104 corpus, or another set, is counted apart.

        Folding it into either summable channel is the same defect the module exists to
        remove, one catalogue further out.
        """
        codes = _codes_csv(
            tmp_path,
            "CipherSpec,CIPHER-NOBS-00,UnsatisfiedConstraint,NOBS,i1,CipherSpec.mop:1\n",
        )
        kinds = load_site_kinds(codes)
        legacy = (
            "08-28 10:00:00.000  1000  1000 E RVSEC   : "
            "CipherSpec,br.unb.App,App,onCreate,App.java:10,UnsatisfiedConstraint,unknown\n"
        )

        by_channel, _ = tally([legacy, _report("OTHERSET-CONSTR-00")], kinds)

        assert by_channel[CHANNEL_UNCLASSIFIED] == 2
        assert by_channel[CHANNEL_NOT_OBSERVED] == 0
        assert by_channel[CHANNEL_ACCUSATION] == 0

    def test_a_catalogue_that_contradicts_itself_raises(self, tmp_path):
        """No side is picked when the column and the code string disagree.

        Resolving it either way would assign a channel by guess, which is what the
        invariant forbids.
        """
        codes = _codes_csv(
            tmp_path,
            "CipherSpec,CIPHER-NOBS-00,UnsatisfiedConstraint,CONSTR,i1,CipherSpec.mop:1\n",
        )

        with pytest.raises(InconsistentCatalogue):
            load_site_kinds(codes)

    def test_coverage_lines_carry_no_report(self):
        """`RVSEC-COV:` is the coverage channel and must not enter any of the three."""
        assert (
            code_of("08-28 10:00:00.000 E RVSEC-COV: br.unb.App: void onCreate()")
            is None
        )


class TestAgainstTheLiveSet:
    """The premise the invariant rests on, read from the set under measurement."""

    def test_error_type_does_not_separate_the_two_families(self):
        """`-NOBS-` and `-CONSTR-` share one `ErrorType`, so the column is the only key.

        This is the whole reason the module exists. If a future set ever gave the
        unobserved family an `ErrorType` of its own, this assertion fails and the design
        gets re-read instead of inherited.
        """
        rows = list(csv.DictReader((_set_dir() / "codes.csv").open(encoding="utf-8")))
        types = {
            row["site_kind"]: row["error_type"]
            for row in rows
            if row["site_kind"] in {NOT_OBSERVED_KIND, "CONSTR"}
        }

        assert types[NOT_OBSERVED_KIND] == types["CONSTR"] == "UnsatisfiedConstraint"

    def test_the_live_catalogue_is_internally_consistent(self):
        """Every code of the set spells the family its own row declares."""
        kinds = load_site_kinds(_set_dir() / "codes.csv")

        assert kinds, "the catalogue is empty"
        assert NOT_OBSERVED_KIND in set(
            kinds.values()
        ), "no unobserved family to separate"
