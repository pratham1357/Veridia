# Forensic Philosophy

VERIDIA provides **forensic indicators and supporting evidence**. It does not declare an image "authentic" or "fake."

1. **Indicators, not verdicts.** An analyzer reports what it observed, how, and with what parameters.
2. **Context matters.** Recompression, resizing or platform re-encoding can mimic tampering; absence of an indicator does not prove authenticity.
3. **Corroboration.** Conclusions should rest on multiple independent techniques where possible.
4. **Explainability.** Every finding must be traceable to the evidence (by SHA-256), the analyzer name and version, and its parameters.
5. **Reproducibility.** Re-running the same analyzer version on the same evidence should give the same result.
6. **Investigator judgement.** The system supports a human assessment; it does not replace it.
