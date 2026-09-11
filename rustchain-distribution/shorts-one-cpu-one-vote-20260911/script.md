# Script — One CPU, One Vote

**Target runtime:** 45–55 seconds

> What if blockchain consensus rewarded the *machine* instead of whoever bought the most hashpower?
>
> RustChain calls this **one CPU, one vote**. A verified physical machine gets one participation slot per epoch, so throwing more cores or threads at the network does not buy extra votes.
>
> Rewards are then weighted by hardware antiquity. The current public table lists a PowerPC G4 at **2.5×**, while modern x86_64 sits at **0.8×**.
>
> And no, a VM cannot just rename itself “G4.” RustChain uses six hardware-fingerprint checks, including clock drift, cache timing, SIMD identity, thermal entropy, instruction jitter, and anti-emulation detection.
>
> The result is a network designed to reward real, diverse hardware — especially machines that are still alive decades later.
>
> Search **RustChain Proof of Antiquity** to see the source and miner docs.