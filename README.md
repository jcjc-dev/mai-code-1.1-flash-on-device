# MAI Code 1.1 Flash On-Device Downloader and Benchmark

`llama-server` performance results for **AMD Strix Halo** and **NVIDIA DGX
Spark (GB10)**, measured on October 19-20, 2026, plus a standalone model
downloader.

**Model variant:** All downloads and benchmarks here target Microsoft's
**MAI-Code-1.1-Flash-On-Device**, Azure ML version **2**, supplied as
`MAI-Code-1.1-Flash-Q2-XS.gguf`. This is the **quantized on-device GGUF
variant**, not the full-precision MAI Code 1.1 Flash checkpoint.

## Performance

All rates are **tokens per second**, calculated from server-side timings
rather than startup or network time.

| Size | Strix Halo PP | DGX Spark PP | Strix Halo TG | DGX Spark TG |
|---|---:|---:|---:|---:|
| 2,048 (2K) | 1160.581 | 1980.403 | 124.339 | 60.182 |
| 32,768 (32K) | 894.554 | 1982.820 | 45.427 | 49.201 |
| 65,536 (64K) | 711.913 | 1820.364 | 40.859 | 41.956 |

Medians are shown; warmups are excluded.

- **PP:** two warmups followed by five measured requests per run. DGX 2K
  uses the median of three run medians (15 measured requests); the other
  PP entries each use five measured requests from a run.
- **TG at 2K/32K:** dedicated tests with two warmups followed by five
  measured requests per run.
  Strix uses five measurements per size; DGX uses the median of three run
  medians, totaling 15 measured requests per size.
- **TG at 64K:** context-ramp measurements, with **1 measurement for Strix**
  and the median of **3 DGX measurements from 3 runs**. There were no
  dedicated warmups for these measurements. The prompt is 65,280 tokens
  plus 256 output tokens, making 65,536 total context tokens.

PP sizes and the 2K/32K TG sizes refer to prompt tokens; the 64K TG size
refers to total context as described above.

DFlash2 is **off**, concurrency is **one**, PP requests generate one output
token, and TG requests generate 256 output tokens.

| Hardware | Backend | OS / architecture | PP batch / ubatch | TG batch / ubatch |
|---|---|---|---|---|
| AMD Strix Halo | Vulkan / RADV | Fedora 43 / x86_64 | 2048 / 2048 | 2048 / 2048 |
| NVIDIA DGX Spark (GB10) | CUDA | Ubuntu 24.04 / aarch64 | 2048 / 512 at 2K; 2048 / 2048 at 32K/64K | 2048 / 512 |

These are separate runs on the listed configurations. Exact llama.cpp
revisions were not recorded. This repository does not include a benchmark
launcher or machine-setup framework.

## Model and llama.cpp configuration

The on-device main model is `MAI-Code-1.1-Flash-Q2-XS.gguf`; its optional
DFlash drafter is `dflash-v3-lc1.gguf`. The publisher describes the on-device
weights as mixed-precision quantized; see the model details below.

- [Model and drafter filenames, SHA-256 values and basic llama.cpp commands](docs/model-and-runtime.md)
- [Publisher's llama configuration](configs/llama-config.json)
- [Manual downloads without the Python script](docs/manual-download.md)

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
partial files using strict ETag, `If-Match`, byte-range and length checks.
Existing completed files are checked rather than overwritten. Interrupted
transfers and expired download URLs receive at most three attempts per file,
refreshing catalog metadata before retries. Temporary signed URLs are kept
in memory: they are not printed or written to receipts, partial-file metadata
or logs.

**Integrity boundary:** the catalog currently supplies no per-file checksum.
The GGUF reference checksums were observed in prior runs; the small config's
reference checksum was obtained from the publisher endpoint on October 22,
2026. These are not represented as publisher-signed checksums.
`download-manifest.json` records the actual SHA-256 and verification level
for every completed file.

Partial files with a changed identity/ETag or a bad checksum are retained and
rejected, never silently mixed or installed. To restart such a file, remove
only its `<filename>.part` and `<filename>.part.json` after confirming no
downloader is running. A directory lock prevents two script instances from
writing together; after a force-killed process, remove `.download.lock` only
once you have confirmed the previous process is gone.

Live catalog discovery, Blob listing and HEAD checks have been exercised;
the 504-byte publisher configuration has also been checked.
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

## License and model terms

This repository's original downloader, tests and benchmark documentation
are licensed under the [MIT License](LICENSE).

The model weights, drafter weights and publisher-supplied configuration are
third-party assets made available through Azure Machine Learning (Azure ML).
**They are not licensed or relicensed by this repository's MIT license.**
Their use, modification and redistribution remain subject to the model
publisher's applicable licenses, required notices, restrictions and
download/use terms. You are responsible for reviewing and complying with
those terms; this repository's MIT license does not override them or grant
additional rights in those assets.

Model and drafter weights are not included in this repository.
`configs/llama-config.json` is a reference copy of the publisher's
configuration and retains its upstream licensing. See
[third-party assets and notices](THIRD_PARTY_NOTICES.md) for the source and
links to the publisher's licensing information.

## Downloader tests

The tests use Python's standard library and tiny local HTTP fixtures. They
do not download model files or require a GPU, SSH access or internet access:

```powershell
python -m unittest discover -s tests -v
```

**Licensing:** [MIT](LICENSE) covers this repository's original code and
documentation, not third-party model assets. See
[license and model terms](#license-and-model-terms).
