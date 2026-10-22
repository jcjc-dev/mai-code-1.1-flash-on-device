# MAI Code 1.1 Flash: local llama.cpp measurements

Historical `llama-server` throughput measurements for **AMD Strix Halo** and
**one NVIDIA DGX Spark (GB10)**, collected on October 19-20, 2026. This is a
small evidence repository with a standalone model downloader, not a supported
benchmark runner or machine-setup framework. No new hardware runs are needed
to read or publish these results.

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
That means **five measured PP and five measured TG requests for Strix**, and
**15 measured requests per metric for DGX**, across three runs. Every workload
in every run first has two warmups, excluded from the results. These are not
cold-start rates or startup/load-time measurements. Individual request rates
and sample standard deviations are in each report.

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

## Scope

The experimental SSH/job runner, setup wrappers, Dockerfile, deployment
workflow, old planning documents and unverified optimizations are deliberately
not part of this version. They are not required to publish a static README
and historical source data.

## Model downloader

`scripts\download_model.py` uses Python 3.11+ and the standard library. No
Azure account, Azure CLI, packages or embedded credentials are required.
It uses the public Azure ML catalog's `GGUF` / `githubCopilotLocal: true`
metadata, then resolves this **pinned asset**, not an automatically changing
latest version:

```text
azureml://registries/azureml/models/MAI-Code-1.1-Flash-On-Device/versions/2
```

These commands fetch **metadata only**, never model or config file bodies.
Running the script with no arguments also defaults to metadata-only:

```powershell
python scripts\download_model.py --list-models
python scripts\download_model.py --dry-run
```

To actually download, explicitly opt in:

```powershell
python scripts\download_model.py --download --parallelism 4 --output .\models\MAI-Code-1.1-Flash-On-Device
```

| File | Bytes |
|---|---:|
| `MAI-Code-1.1-Flash-Q2-XS.gguf` | 56,307,620,832 |
| `dflash-v3-lc1.gguf` | 381,214,016 |
| `llama-config.json` | 504 |
| **Total** | **56,688,835,352** |

**Zero third-party dependencies:** everything, including parallel transfers,
uses Python's standard library. There is nothing to install with `pip`.

The downloader lists the Blob package and checks file headers before
transferring. By default, **four concurrent connections download separate
64 MiB ranges within each large GGUF**; it does not rely on downloading the
small companion files alongside one slow main-file stream. Each worker reads
at most 1 MiB per read and writes directly into its own offsets in the same
`.part` file. There is no second full-size copy or final concatenation step.
Completed ranges are journaled after flushing to disk; reruns reuse them and
retransfer only unfinished ranges. A full-file SHA-256 pass precedes
installation, so completing all ranges alone never counts as success.

`--parallelism` accepts **1 through 16**, default **4**. Four is a moderate
starting point, not a measured optimum for your connection; higher values
are not guaranteed to be faster. Use `--parallelism 1` for serial transfers.
The setting can change between attempts without losing completed ranges.
No production model download was performed to tune throughput.

The script requires sufficient remaining disk space and resumes its own
partial files using strict ETag, `If-Match`, byte-range and length checks. Existing
completed files are checked rather than overwritten; the tiny config is
compared with fresh remote bytes because it has no reference hash, and its
partial downloads are re-fetched rather than resumed. Interrupted transfers
and expired download URLs receive at most three attempts per file, refreshing
catalog metadata before retries. Temporary signed URLs are kept in memory:
they are not printed or written to receipts, partial-file metadata or logs.

**Integrity boundary:** the catalog currently supplies no per-file checksum.
Both GGUF SHA-256 values are pinned to observations in the retained benchmark
manifests, not represented as publisher-signed checksums. `llama-config.json`
has no reference digest; its checks are HTTPS transport, remote ETag/length
and JSON-object syntax. `download-manifest.json` records the actual SHA-256
and verification level for every completed file. It does not turn an observed
checksum into independent publisher authentication.

Partial files with a changed identity/ETag or a bad checksum are retained and
rejected, never silently mixed or installed. To restart such a file, remove
only its `<filename>.part` and `<filename>.part.json` after confirming no
downloader is running. A directory lock prevents two script instances from
writing together; after a force-killed process, remove `.download.lock` only
once you have confirmed the previous process is gone.

Live catalog discovery, Blob listing and HEAD checks have been exercised.
Transfer, actual bounded parallel requests, resume, retry and failure behavior
are tested against tiny local HTTP fixtures.
**The full production model has not been downloaded as validation
of this script.** The script does not install llama.cpp or launch inference.

This repository does not distribute weights. Consult the publisher's
[model card](https://github.com/Azure/azureml-assets/wiki/models-MAI-Code-1.1-Flash-On-Device)
and [VS Code on-device setup guide](https://code.visualstudio.com/docs/agent-customization/language-models#_use-ondevice-models)
for distribution and terms, and the
[catalog API guide](https://api.catalog.azureml.ms/asset-gallery/v1.0)
for the discovery contract. Those upstream instructions are not a
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
