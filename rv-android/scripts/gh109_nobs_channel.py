#!/usr/bin/env python3
"""The `-NOBS-` channel, separated from the accusations, for every consumer of a run
(INV-INS-158).

A report line whose code carries the `NOBS` family says *no producer of this object was
ever observed*. That is a reach limit of the instrument, not a claim about the program:
the monitor never saw the half of the run that would settle the clause. An accusation --
`CONSTR`, `ORDER`, `ALG`, `KEYSIZE`, `KSTYPE`, `PROTO`, `FORB` -- says the opposite, that
what the program did is what the rule forbids.

Nothing in the pipeline told them apart. `ErrorType` cannot: the 64 `-NOBS-` codes and the
86 `-CONSTR-` codes of `jca_android` all carry `UnsatisfiedConstraint`, by construction and
not by accident, because a predicate read has no `ErrorType` of its own. So a run that
answered "I never saw the key generator" was summed beside a run that used a forbidden
cipher, and the sum was reported as violations found. Measured before this module existed:
zero consumers under `modules/` or `scripts/` filtered on the substring.

The separation is keyed on the **`site_kind` column of `codes.csv`**, not on the KIND
letters of the code string. The two agree today and the loader below refuses a file where
they do not, but the column is the declaration and the string is a spelling of it: a code
renamed without its row would silently change channel if the string were the authority.
This is the opposite reading from `gh104_gates.py`, deliberately -- that gate derives KIND
from the code so an inconsistent catalogue shows up as an unknown code instead of passing
through a side door. Here inconsistency is louder still: `load_site_kinds` raises.

**What this module does not do.** It does not measure the NOBS rate -- that is gh109 task
7.3, over the APK corpus, and it is the first reading of this channel; no earlier count is
comparable to it, because before this module a `-NOBS-` line was summed indistinguishably
from a `-CONSTR-` one. It does not decide whether any producer should `negate` when it
accuses, which is a design question that belongs after the measurement. And it changes
nothing on the device: the same `addError` calls fire, carrying the same codes.

The campaign consolidators (`experimento-gh104/scripts/consolidate.py` and its `analise.py`)
are deliberately **not** wired to this module. Both declare themselves byte-copies of the
`comp162` campaign's, and their `mop_total` is what pairs the two campaigns; re-defining it
here would be a second difference between them where the design admits one, the spec set.
A consumer that wants the channels asks for them by calling `tally`.

Usage:
    gh109_nobs_channel.py <logcat|errors.csv> [...]   # tally the channels
    gh109_nobs_channel.py --codes-csv <path> <file...>
    gh109_nobs_channel.py --by-code <file...>          # ... and per code
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import re
import sys
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REACTOR = REPO.parent
DEFAULT_CODES_CSV = REACTOR / "rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv"

#: The `codes.csv` columns this module reads. `site_kind` is the authority on the channel;
#: `code` is the key a report line carries.
CODE_COLUMN = "code"
SITE_KIND_COLUMN = "site_kind"

#: The one family that is neither conformance nor violation.
NOT_OBSERVED_KIND = "NOBS"

#: The three channels a report line can fall into. `unclassified` is not an error state:
#: a corpus predating gh104 carries no envelope at all, and a set other than the one whose
#: `codes.csv` was loaded carries codes this catalogue does not know. Both are counted and
#: named rather than folded into either of the other two, because folding them is the very
#: defect this module exists to remove.
CHANNEL_NOT_OBSERVED = "not-observed"
CHANNEL_ACCUSATION = "accusation"
CHANNEL_UNCLASSIFIED = "unclassified"
CHANNELS = (CHANNEL_NOT_OBSERVED, CHANNEL_ACCUSATION, CHANNEL_UNCLASSIFIED)

#: `RVSEC: <Spec>,<class>,<simpleClass>,<method>,<source>,<ErrorType>,<message>` -- the
#: logcat form both spec eras write. Same expression as `msg_diff.py`'s `VIOL`, and the
#: coverage lines (`RVSEC-COV`) do not match it.
RVSEC_LINE = re.compile(r"\bRVSEC\s*:\s*([A-Za-z0-9_$]+Spec,.+)$")

#: The message is the seventh field, and it is the only one that may itself hold commas.
PAYLOAD_SPLITS = 6

#: `v=1 code=<SPEC>-<KIND>-<NN> ev=... obj=... val='...' exp='...' msg='...'`. Only the
#: code is read here; the rest of the envelope is the message's business.
ENVELOPE_CODE = re.compile(r"^v=1 code=(\S+) ")

#: The KIND letters of a well-formed code, used only to cross-check `site_kind`.
CODE_RE = re.compile(r"^(?P<spec>[A-Z0-9]+)-(?P<kind>[A-Z]+)-(?P<nn>\d{2})$")


class InconsistentCatalogue(Exception):
    """A `codes.csv` whose `site_kind` column and code strings disagree.

    Raised rather than resolved, because either answer would be a guess about which of the
    two the author meant, and a channel assigned by guess is exactly what INV-INS-158
    forbids.
    """


def load_site_kinds(path: Path = DEFAULT_CODES_CSV) -> dict[str, str]:
    """Read `codes.csv` into `{code: site_kind}`.

    Args:
        path: the `codes.csv` of the specification set under measurement.

    Returns:
        Every row's code mapped to the family its `site_kind` column declares.

    Raises:
        InconsistentCatalogue: when a code's `site_kind` cell is empty, when its KIND
            letters and that cell name different families, or when a code appears twice
            with different cells. The channel is keyed on the column, so a disagreement --
            or a silence, which `channel` would otherwise file as an accusation because an
            empty cell is not `NOBS` -- means the file cannot say what channel one of its
            own codes is in.
    """
    kinds: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            code = (row.get(CODE_COLUMN) or "").strip()
            declared = (row.get(SITE_KIND_COLUMN) or "").strip()
            if not code:
                continue
            if not declared:
                raise InconsistentCatalogue(
                    f"{path}: `{code}` declares no {SITE_KIND_COLUMN}, so the file cannot "
                    f"say what channel its own code is in"
                )
            match = CODE_RE.match(code)
            if match and match.group("kind") != declared:
                raise InconsistentCatalogue(
                    f"{path}: `{code}` spells its family `{match.group('kind')}` and its "
                    f"{SITE_KIND_COLUMN} cell says `{declared or 'nothing'}`"
                )
            if kinds.get(code, declared) != declared:
                raise InconsistentCatalogue(
                    f"{path}: `{code}` appears twice, filed as `{kinds[code]}` and as "
                    f"`{declared}`"
                )
            kinds[code] = declared
    return kinds


def channel(code: str, site_kinds: dict[str, str]) -> str:
    """The channel one report line's code belongs to.

    Args:
        code: the `code=` field of the line's envelope.
        site_kinds: the catalogue `load_site_kinds` returned.

    Returns:
        `CHANNEL_NOT_OBSERVED` when the catalogue files the code as `NOBS`,
        `CHANNEL_ACCUSATION` when it files it as anything else, and
        `CHANNEL_UNCLASSIFIED` when the catalogue does not know the code -- a line with no
        envelope, or a line from a different specification set.
    """
    declared = site_kinds.get(code)
    if declared is None:
        return CHANNEL_UNCLASSIFIED
    return CHANNEL_NOT_OBSERVED if declared == NOT_OBSERVED_KIND else CHANNEL_ACCUSATION


def code_of(line: str) -> str | None:
    """The code of one raw logcat line, or `None` when the line carries no report.

    A `RVSEC-COV:` line, a line of some other tag, and a truncated payload all return
    `None`; a report whose message predates the envelope returns the empty string, which
    `channel` files as unclassified.
    """
    if "RVSEC" not in line or "RVSEC-COV" in line:
        return None
    match = RVSEC_LINE.search(line.rstrip("\n"))
    if not match:
        return None
    fields = match.group(1).split(",", PAYLOAD_SPLITS)
    if len(fields) <= PAYLOAD_SPLITS:
        return None
    envelope = ENVELOPE_CODE.match(fields[PAYLOAD_SPLITS].strip())
    return envelope.group(1) if envelope else ""


def tally(
    lines: Iterable[str], site_kinds: dict[str, str]
) -> tuple[collections.Counter, collections.Counter]:
    """Count an iterable of raw report lines into the three channels.

    Args:
        lines: any iterable of logcat lines.
        site_kinds: the catalogue `load_site_kinds` returned.

    Returns:
        `(by_channel, by_code)` -- the first keyed on the three channels, the second on the
        code, so a caller measuring one site's rate (task 7.3) does not have to re-parse.
    """
    by_channel: collections.Counter = collections.Counter(
        {name: 0 for name in CHANNELS}
    )
    by_code: collections.Counter = collections.Counter()
    for line in lines:
        code = code_of(line)
        if code is None:
            continue
        by_channel[channel(code, site_kinds)] += 1
        by_code[code] += 1
    return by_channel, by_code


def _open_text(path: Path):
    """Open a report file, transparent to gzip.

    Archived runs are sometimes compressed in place keeping the `.logcat` suffix, so the
    discriminator is the magic number and not the name -- the same reading as `msg_diff.py`.
    """
    with path.open("rb") as probe:
        compressed = probe.read(2) == b"\x1f\x8b"
    if compressed:
        return gzip.open(path, "rt", errors="ignore")
    return path.open("r", errors="ignore")


def main() -> int:
    """Tally the channels over the files named on the command line.

    Returns:
        0 always when the catalogue loads and every file opens: this is a measurement, not
        a gate, and there is no threshold it could fail. A missing file or an inconsistent
        catalogue returns 1, because a silently short count would read as a low NOBS rate.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--codes-csv", type=Path, default=DEFAULT_CODES_CSV)
    parser.add_argument(
        "--by-code",
        action="store_true",
        help="also print one line per code, descending (gh109 task 7.3)",
    )
    args = parser.parse_args()

    try:
        site_kinds = load_site_kinds(args.codes_csv)
    except (OSError, InconsistentCatalogue) as failure:
        print(failure, file=sys.stderr)
        return 1

    by_channel: collections.Counter = collections.Counter(
        {name: 0 for name in CHANNELS}
    )
    by_code: collections.Counter = collections.Counter()
    for path in args.files:
        try:
            with _open_text(path) as handle:
                channels, codes = tally(handle, site_kinds)
        except OSError as failure:
            print(failure, file=sys.stderr)
            return 1
        by_channel.update(channels)
        by_code.update(codes)

    total = sum(by_channel.values())
    print(f"{len(site_kinds)} code(s) in {args.codes_csv}")
    for name in CHANNELS:
        share = f"{100 * by_channel[name] / total:.1f} %" if total else "-"
        print(f"{name:>14s}  {by_channel[name]:8d}  {share:>7s}")
    print(f"{'total':>14s}  {total:8d}")
    if args.by_code:
        for code, count in by_code.most_common():
            print(
                f"{count:8d}  {channel(code, site_kinds):>14s}  {code or '(no envelope)'}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
