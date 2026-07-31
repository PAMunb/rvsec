"""
Offline analysis utilities for recorded APE-RV runs.

Everything in this package is read-only over artifacts a run already produced:
no device, no emulator, no adb. None of it is imported by the execution path —
rv-platform never calls into here. The utilities live in the tool package rather
than in a per-campaign script directory because the real thesis experiment
consumes them, not only the calibration campaign (gh90 design D5).
"""
