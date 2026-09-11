# Sources and fact check

All factual claims in this package were checked against public RustChain materials on 2026-09-10.

1. **Proof of Antiquity / one physical CPU gets one vote**
   - https://rustchain.org/
   - Homepage states “1 CPU = 1 Vote” and describes Proof of Antiquity consensus.

2. **PowerPC G4 base multiplier = 2.50×**
   - https://rustchain.org/
   - Tenure-grown multipliers table row: “PowerBook G4 / Power Mac G4 | PowerPC 7450 | 2.50x”.

3. **Modern x86_64 base multiplier = 0.80×**
   - https://rustchain.org/
   - Tenure-grown multipliers table row: “Modern x86_64 | Modern | 0.80x”.

4. **Relative base-weight calculation = 3.125×**
   - Arithmetic derived directly from the published table: `2.50 / 0.80 = 3.125`.

5. **Anti-emulation / VM penalty**
   - https://rustchain.org/
   - Anti-VM fingerprinting section states detected VMs earn `0.000000001x` rewards by design.

6. **Install command**
   - https://rustchain.org/
   - Published quick-start command: `pip install clawrtc`.

## Accuracy guardrails
The script does not claim that G4 hardware is faster than modern x86, that an individual fingerprint signal is unforgeable, or that mining returns are guaranteed. The comparison is only the published RustChain base weighting under its current Proof-of-Antiquity rules.
