"""dexnorm: an off body and an on body that differ only where the stamp writes
normalise equal; a body with one more instruction does not."""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "dexnorm", Path(__file__).resolve().parent.parent / "scripts" / "dexnorm.py"
)
dexnorm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dexnorm)

HEADER = """Processing '/work/off-1.dex'...
Opened '/work/off-1.dex', DEX version '035'
Class #0            -
  Class descriptor  : 'Lcom/example/Main;'
  Direct methods    -
    #0              : (in Lcom/example/Main;)
      name          : 'bind'
      type          : '(Landroid/widget/Button;Landroid/view/View$OnClickListener;)V'
      registers     : 3
      ins           : 2
      outs          : 2
"""

OFF = HEADER + """      insns size    : 8 16-bit code units
000310:                                        |[000310] com.example.Main.bind:(Landroid/widget/Button;Landroid/view/View$OnClickListener;)V
000320: 3801 0500                              |0000: if-eqz v1, 0005 // +0005
000324: 6e20 1200 1000                         |0002: invoke-virtual {v0, v1}, Landroid/widget/Button;.setOnClickListener:(Landroid/view/View$OnClickListener;)V // method@0012
00032a: 0e00                                   |0005: return-void
      catches       : (none)
      positions     :
        0x0002 line=12
"""

# The same body after the stamp: the setter is routed to the helper (other pool
# indices, other file offsets) and nothing else changes.
ON_SETTER = HEADER.replace("off-1", "on-1") + """      insns size    : 8 16-bit code units
000410:                                        |[000410] com.example.Main.bind:(Landroid/widget/Button;Landroid/view/View$OnClickListener;)V
000420: 3801 0500                              |0000: if-eqz v1, 0005 // +0005
000424: 7120 3000 1000                         |0002: invoke-static {v0, v1}, Lmop/RvsecStamp;.setOnClickListener:(Landroid/view/View;Landroid/view/View$OnClickListener;)V // method@0030
00042a: 0e00                                   |0005: return-void
      catches       : (none)
      positions     :
        0x0002 line=12
"""

EXTRA = HEADER + """      insns size    : 9 16-bit code units
000310:                                        |[000310] com.example.Main.bind:(Landroid/widget/Button;Landroid/view/View$OnClickListener;)V
000320: 3801 0600                              |0000: if-eqz v1, 0006 // +0006
000324: 6e20 1200 1000                         |0002: invoke-virtual {v0, v1}, Landroid/widget/Button;.setOnClickListener:(Landroid/view/View$OnClickListener;)V // method@0012
00032a: 0000                                   |0005: nop
00032c: 0e00                                   |0006: return-void
      catches       : (none)
      positions     :
        0x0002 line=12
"""


def _norm(text):
    return dexnorm.normalise(text.splitlines(keepends=True))


def test_off_and_on_differing_only_at_a_setter_site_normalise_equal():
    off_digest, off_counts = _norm(OFF)
    on_digest, on_counts = _norm(ON_SETTER)

    assert off_digest == on_digest
    assert off_counts["setter_virtual"] == 1 and off_counts["stamp_static"] == 0
    assert on_counts["setter_virtual"] == 0 and on_counts["stamp_static"] == 1


def test_a_body_with_an_extra_instruction_does_not_normalise_equal():
    off_digest, off_counts = _norm(OFF)
    extra_digest, extra_counts = _norm(EXTRA)

    assert off_digest != extra_digest
    assert extra_counts["insns_lines"] == off_counts["insns_lines"] + 1


def test_a_compose_node_insertion_is_dropped_and_counted():
    on_compose = OFF.replace(
        "00032a: 0e00                                   |0005: return-void\n",
        "00032a: 7120 4000 2100                         |0005: invoke-static {v1, v2}, Lmop/RvsecStamp;.composeNode:(Ljava/lang/Object;Ljava/lang/Object;)V // method@0040\n"
        "000330: 0e00                                   |0008: return-void\n",
    )
    digest, counts = _norm(on_compose)

    assert digest == _norm(OFF)[0]
    assert counts["compose_inserted"] == 1
