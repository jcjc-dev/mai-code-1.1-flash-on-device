# MAI Code 1.1 Flash: local llama.cpp measurements

`llama-server` performance results for **AMD Strix Halo** and **one NVIDIA DGX
Spark (GB10)**, measured on October 19-20, 2026, plus a standalone model
downloader.

## Performance

PP is prompt processing; TG is token generation. All rates are **tokens per
second**, calculated from server-side timings rather than startup or network
time.

| Prompt tokens | Strix Halo PP | DGX Spark PP | Strix Halo TG | DGX Spark TG |
|---|---:|---:|---:|---:|
| 2,048 (2K) | 1160.581 | 1980.403 | 124.339 | 60.182 |
| 32,768 (32K) | 894.554 | 1982.820 | - | - |
| 65,536 (64K) | 711.913 | 1820.364 | - | - |

Each workload uses **two warmups followed by five measured requests**;
warmups are excluded and the median is shown. The DGX 2K values are the
median of three run medians, totaling 15 measured requests per metric.
Strix 2K and both machines' 32K/64K values each use one run of five measured
requests per metric. `-` means TG was not measured in these runs, not zero.

DFlash2 is **off**, concurrency is **one**, PP requests generate one output
token, and TG requests generate 256 output tokens.

| Hardware | Backend | OS / architecture | 2K batch / ubatch | 32K/64K batch / ubatch |
|---|---|---|---|---|
| AMD Strix Halo | Vulkan / RADV | Fedora 43 / x86_64 | 2048 / 2048 | 2048 / 2048 |
| NVIDIA DGX Spark (GB10) | CUDA | Ubuntu 24.04 / aarch64 | 2048 / 512 | 2048 / 2048 |

These are separate runs on the listed configurations. Exact llama.cpp
revisions were not recorded. This repository does not include a benchmark
launcher or machine-setup framework.

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
Both GGUF SHA-256 values are reference checksums observed in prior runs,
not represented as publisher-signed checksums. `llama-config.json`
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

## Downloader tests

The tests use Python's standard library and tiny local HTTP fixtures. They
do not download model files or require a GPU, SSH access or internet access:

```powershell
python -m unittest discover -s tests -v
```
