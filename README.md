# MAI Code 1.1 Flash: local llama.cpp measurements

Historical `llama-server` throughput measurements for **AMD Strix Halo** and
**one NVIDIA DGX Spark (GB10)**, collected on October 19-20, 2026. This is a
small evidence repository, not a supported benchmark runner or machine-setup
framework. No new hardware runs are needed to read or publish these results.

## Measured throughput

PP is prompt processing; TG is token generation. Rates are tokens/second from
the archived server-response timings, not network or client wall-clock time.
All rows have DFlash2 **off**, concurrency one, two warmups and five measured
requests per workload per run. PP requests generate one output token; TG
requests generate 256.

<!-- verified-results:start -->
| Hardware | Workload | tok/s | Evidence |
|---|---|---:|---|
| Strix Halo | PP 2K | 1160.581 | 5 measured requests |
| Strix Halo | TG 2K | 124.339 | 5 measured requests |
| DGX Spark | PP 2K | 1980.403 | median of 3 run medians |
| DGX Spark | TG 2K | 60.182 | median of 3 run medians |
| Strix Halo | PP 32K | 894.554 | exploratory |
| Strix Halo | PP 64K | 711.913 | exploratory |
| DGX Spark | PP 32K | 1982.820 | exploratory |
| DGX Spark | PP 64K | 1820.364 | exploratory |
<!-- verified-results:end -->

**These are configuration-specific observations, not a controlled hardware
ranking.** The 2K Strix run uses Vulkan/RADV on Fedora x86_64 with
batch/ubatch 2048/2048; the DGX runs use CUDA on Ubuntu aarch64 with
2048/512. Prompt-token hashes also differ across profiles. DGX's headline
2K rates are medians of three run medians, not pooled request medians.
Individual request rates and sample standard deviations are in each report.

Both long-prompt archives remain **exploratory**, including the accepted
single-DGX measurement; neither is upgraded to a matched cross-profile result.
Both record batch/ubatch 2048/2048, but the Strix archive's runtime digest
differs from its 2K baseline and was not established as the later intended
runtime. The later matched Strix attempts did not produce accepted archives.
There is no completed matched PP comparison here.

## Source archives

Each folder retains the original manifest, request samples, host metrics,
SHA-256 ledger, and Markdown report byte-for-byte.

| Source | Report |
|---|---|
| Strix 2K baseline | [20261019T051400Z-strix-halo-874446e8](results/runs/20261019T051400Z-strix-halo-874446e8/result.md) |
| DGX 2K replication 1 | [20261019T070817Z-dgx-spark-single-30a2efde](results/runs/20261019T070817Z-dgx-spark-single-30a2efde/result.md) |
| DGX 2K replication 2 | [20261019T070957Z-dgx-spark-single-b6a2cf34](results/runs/20261019T070957Z-dgx-spark-single-b6a2cf34/result.md) |
| DGX 2K replication 3 | [20261019T071132Z-dgx-spark-single-c9ded3ab](results/runs/20261019T071132Z-dgx-spark-single-c9ded3ab/result.md) |
| Strix exploratory PP 32K/64K | [20261019T181827Z-strix-halo-9b033a20](results/runs/20261019T181827Z-strix-halo-9b033a20/result.md) |
| DGX exploratory PP 32K/64K | [20261020T041247Z-dgx-spark-single-32745efc](results/runs/20261020T041247Z-dgx-spark-single-32745efc/result.md) |

All six manifests record the same 56,307,620,832-byte model with SHA-256
`048788de4848e92c7a543feb1c5e0c9144515ac8a3fec1508d5857d25b0e556e`.
Exact llama.cpp revisions, driver versions and KV-cache types were not
recorded; do not infer them from a current image tag. Container digests are
retained as historical provenance, not promises of current availability.

**Memory caveat:** older reports' "250 ms" value is the configured target,
not achieved continuous sampling. The Strix long-prompt archive has sparse
phase snapshots, so its memory figures do not establish a continuous peak.
The newer DGX long-prompt archive contains continuous host telemetry; missing
fields still mean unavailable, not zero. No cross-hardware memory ranking,
coding-quality score, dual-Spark result or maximum-context claim is made.

## Scope and downloads

The experimental SSH/job runner, setup wrappers, Dockerfile, deployment
workflow, old planning documents and unverified optimizations are deliberately
not part of this version. They are not required to publish a static README
and historical source data.

No completed downloader was present in the original project: the
model-artifact helper checks files already on disk, and its expected hashes
were unset. It is not included here as a download script. This repository
does not distribute weights or claim that a full model download was validated.
Consult the publisher's
[model card](https://github.com/Azure/azureml-assets/wiki/models-MAI-Code-1.1-Flash-On-Device)
and [VS Code on-device setup guide](https://code.visualstudio.com/docs/agent-customization/language-models#_use-ondevice-models)
for distribution and terms. Those upstream instructions are not a
validated Strix/DGX setup recipe.

## Offline verification

Python 3.11+ and its standard library are sufficient; no package installation,
GPU, SSH access or network connection is needed:

```powershell
python scripts\verify_results.py
python -m unittest discover -s tests -v
```

The verifier checks every retained raw-file SHA-256, completed request counts,
token counts, timing validity, classification and the README table. It fails
if the recorded numbers no longer reproduce. Hashes establish consistency
with these archived inputs, not independent proof of how a measurement was
originally collected. Reports are historical artifacts; this version does
not regenerate them or launch inference.
