# Model, drafter and llama.cpp settings

## Model variant

This repository downloads and benchmarks the **quantized on-device variant**,
not the full-precision MAI Code 1.1 Flash checkpoint.

| Property | Value |
|---|---|
| Azure ML model name | `MAI-Code-1.1-Flash-On-Device` |
| Publisher | Microsoft |
| Azure ML version | 2 |
| Intended deployment | Local / on-device inference |
| File format | GGUF |
| Main-file quantization label | `Q2-XS` |
| Publisher-reported total / active parameters | 137.9B / 6.8B |

The catalog resolver identifies the model as `MAI-Code-1.1-Flash-On-Device`
with `modelFlavor: GGUF` and `githubCopilotLocal: true`. `Q2-XS` is the label
in the package's main filename; the resolver does not expose a separate
quantization field.

The [publisher's model card](https://github.com/Azure/azureml-assets/wiki/models-MAI-Code-1.1-Flash-On-Device)
describes mixed-precision weight quantization averaging approximately
**3.3 bits per weight**. Do not interpret the filename as a claim that every
weight uses exactly two bits. "On-device" identifies this quantized variant,
not an incomplete download or a file containing only the active parameters.
The README's measurements apply to this package, not other MAI Code variants.

## Model files

The package is the public Azure ML asset:

```text
azureml://registries/azureml/models/MAI-Code-1.1-Flash-On-Device/versions/2
```

The files are publisher-provided assets distributed through Azure ML, not
relicensed under this project's MIT license. See
[third-party assets and license scope](../THIRD_PARTY_NOTICES.md).

| Role | Filename | Bytes |
|---|---|---:|
| Main model, Q2-XS GGUF | `MAI-Code-1.1-Flash-Q2-XS.gguf` | 56,307,620,832 |
| Optional DFlash drafter | `dflash-v3-lc1.gguf` | 381,214,016 |
| Publisher runtime configuration | `llama-config.json` | 504 |

Reference SHA-256 values:

```text
MAI-Code-1.1-Flash-Q2-XS.gguf
048788de4848e92c7a543feb1c5e0c9144515ac8a3fec1508d5857d25b0e556e

dflash-v3-lc1.gguf
7052df547898b46fab3ff23f8c1085547003116899506099467f948debb75b15

llama-config.json
afcfce372a09bfa79f8b655f048eadd12b2551a4d656d8bd8e6b662e2598fa96
```

The GGUF checksums were observed in prior runs. The configuration checksum
was observed from the publisher endpoint on October 22, 2026. The catalog
does not supply these as independent publisher-signed checksums. Both the
Python downloader and the [manual download guide](manual-download.md) use
these same filenames and reference values.

## Publisher configuration

[`configs/llama-config.json`](../configs/llama-config.json) contains the
configuration supplied with the model package:

| Setting | Value |
|---|---|
| Main model | `MAI-Code-1.1-Flash-Q2-XS.gguf` |
| Drafter | `dflash-v3-lc1.gguf` |
| Context | 262144 |
| Parallel sequences | 1 |
| GPU layers | 999 |
| Speculation type | `draft-dflash` |
| Maximum draft tokens | 3 |
| Minimum draft probability | 0.2 |
| Draft GPU layers | `all` |
| Flash attention | `on` |
| Batch / ubatch | 2048 / 2048 |
| Fit | `off` |
| Context checkpoints | 0 |
| Host buffer | `--no-host` |

This JSON is package metadata, not a native `llama-server --config` file.
Its filenames refer to files in the downloaded model directory. The
publisher's 262144 context setting is not a claim that the README measured
that context or that it fits every machine.

## Basic llama-server command

Use a llama.cpp build that supports this MAI model architecture and your
GPU backend: Vulkan/RADV for the Strix configuration or CUDA for DGX Spark.
Run from the directory containing the downloaded model files, with
`llama-server` on your PATH:

```text
llama-server --model MAI-Code-1.1-Flash-Q2-XS.gguf --ctx-size 131072 --parallel 1 --n-gpu-layers 999 --flash-attn on --batch-size 2048 --ubatch-size 2048 --fit off --ctx-checkpoints 0 --load-mode none --no-host --host 127.0.0.1 --port 8080
```

This is the no-drafter configuration corresponding to the mode shown in the
README. It uses a 131072 context limit rather than the larger publisher
default. DGX 2K PP and all displayed DGX TG measurements used
`--ubatch-size 512`; DGX 32K/64K PP and the Strix measurements used 2048.

For optional DFlash decoding, add:

```text
--model-draft dflash-v3-lc1.gguf --spec-type draft-dflash --spec-draft-n-max 3 --spec-draft-p-min 0.2 --spec-draft-ngl all
```

These are the publisher's drafter settings. The README numbers have DFlash2
off; adding the drafter does not reproduce those runs or guarantee faster
decoding.

Exact llama.cpp revisions for the measurements were not recorded. The
commands document the basic settings, not a newly tested build or a
machine-setup procedure. Check `llama-server --help` for the build you use.

Sources: [publisher model card](https://github.com/Azure/azureml-assets/wiki/models-MAI-Code-1.1-Flash-On-Device)
and [llama.cpp server options](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).
