"""Re-read the CSVs this component emits with the readers already committed under scripts/.

The component and the manual pipeline coexist for a while, and during that window whatever the
emitters produce has to be consumable by what already exists -- otherwise "the component
substitutes the manual tables" is a claim about columns and nothing else. So the check is made
against the four readers themselves, not against a reimplementation of them here.

Run it after `mvn -pl rvsec-crysl-core test`, which writes the fixture under target/emitted-csv:

    cd rv-android && uv run python <path to this file>
"""

import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
)
sys.path.insert(0, str(REPO / "scripts"))

EMITTED = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/"
    "rvsec/rvsec-crysl/rvsec-crysl-core/target/emitted-csv"
)

from gh104_gates import read_constraint_table, read_records  # noqa: E402
from gh105_order_gate import read_map  # noqa: E402
from gh105_predicate_graph import read_graph  # noqa: E402

graph = read_graph(EMITTED / "predicate_graph.csv")
table = read_constraint_table(EMITTED / "constraint_table.csv")
mapping = read_map(EMITTED / "order_alphabet_map.csv")
# read_records resolves <repo>/data/<set>/, so the fixture is staged in that layout.
with tempfile.TemporaryDirectory() as staging:
    (Path(staging) / "data" / "emitted").mkdir(parents=True)
    shutil.copy(EMITTED / "divergence_record.csv", Path(staging) / "data" / "emitted")
    records = read_records("emitted", Path(staging))

assert len(graph) == 2, graph
assert graph[0]["file"] == "CipherSpec.mop" and graph[0]["predicate"] == "GENERATED_KEY"
assert graph[0]["verdict"] == "read:body" and graph[0]["fidelity"] == "CONFLADO"
assert graph[0]["origin"] == "derived" and graph[1]["origin"] == "inherited"
assert graph[0]["mop_commit"] == "39b000ce" and graph[0]["oracle_commit"] == "a1b2c3d4"

assert table is not None and len(table) == 1, table
assert table[0]["spec"] == "CipherInputStreamSpec"
assert table[0]["cryptsl_line"] == "CipherInputStream.crysl:26"

assert list(mapping) == ["CipherSpec"], mapping
assert mapping["CipherSpec"][0].order_symbol == "Inits"
assert mapping["CipherSpec"][0].disposition == "mapped"

assert list(records) == ["KeyPairGeneratorSpec"], records
assert len(records["KeyPairGeneratorSpec"]) == 1, records
assert records["KeyPairGeneratorSpec"][0]["kind"] == "api30-omits", records

print("read_graph            ->", len(graph), "rows")
print("read_constraint_table ->", len(table), "rows")
print(
    "read_map              ->",
    sum(len(v) for v in mapping.values()),
    "rows,",
    len(mapping),
    "specs",
)
print("read_records          ->", sum(len(v) for v in records.values()), "rows")
print("OK: all four emitted CSVs parse with the committed readers")
