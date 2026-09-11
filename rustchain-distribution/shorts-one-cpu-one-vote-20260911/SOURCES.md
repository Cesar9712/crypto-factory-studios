# Sources and fact map

Primary source: RustChain public README  
https://github.com/Scottcjn/Rustchain/blob/main/README.md

## Claim mapping

### “One CPU, one vote” / one participation slot per verified machine
The RustChain README’s Proof-of-Antiquity explanation states that each unique hardware device gets one consensus participation slot per epoch and contrasts this with hashpower-based voting.

### PowerPC G4 = 2.5×; modern x86_64 = 0.8×
The current hardware multiplier table in the RustChain README lists PowerPC G4 (2003) at 2.5× and modern x86_64 at 0.8×.

### Six hardware fingerprint checks
The current README enumerates:
1. Clock-skew & oscillator drift
2. Cache timing fingerprint
3. SIMD unit identity
4. Thermal drift entropy
5. Instruction path jitter
6. Anti-emulation detection

### VM / emulator framing
The README describes the six-check fingerprint system and explicitly says a SheepShaver VM pretending to be a G4 will fail. This package uses narrower language — “uses six checks to distinguish real hardware from VMs/emulators” — and avoids claiming perfect or mathematically absolute spoof resistance.

### No profitability claim
This package intentionally does not convert multipliers into money, expected return, token price, or ROI. The numbers are presented only as the project’s published reward-weight multipliers.