# Benchmark result: strix-halo

- **Run:** `20261019T181827Z-strix-halo-9b033a20`
- **Status:** `succeeded`
- **Created (UTC):** 2026-10-19T18:18:27.832Z
- **Suite:** `mai-code-baseline-v2`
- **Classification:** `exploratory`
- **Hardware:** AMD Strix Halo (x86_64)
- **RAM capacity:** unavailable
- **OS:** Fedora 43
- **Backend:** `vulkan-radv`
- **llama.cpp revision:** `unrecorded`
- **Timing source:** `server_response`
- **Prompt-cache policy:** `unique_prefix_per_repetition`
- **Memory sampling interval:** 250 ms
- **DFlash2 pair:** `unpaired` (unpaired, position 0)
- **Model:** `microsoft/MAI-Code-1.1-Flash-On-Device` (56307620832 bytes)
- **Model SHA-256:** `048788de4848e92c7a543feb1c5e0c9144515ac8a3fec1508d5857d25b0e556e`
- **DFlash2:** `off`
- **Drafter SHA-256:** `pending/not used`

## Timing results

Rates use normalized server-side timing fields; only measured successful samples are summarized.

| Workload | Kind | Successful / measured | Prompt tokens | Output tokens | Requested n_ctx | PP tok/s (median +/- SD) | TG tok/s (median +/- SD) | Largest actual context tested |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `pp-32k` | pp | 5 / 5 | 32768.000 | 1.000 | 33024.000 | 894.554 +/- 5.921 | unavailable | unavailable |
| `pp-64k` | pp | 5 / 5 | 65536.000 | 1.000 | 65792.000 | 711.913 +/- 1.726 | unavailable | unavailable |

## Failed or safely stopped requests

| Workload | Kind | Status | Requested context | Actual context | Error code |
|---|---|---|---:|---:|---|
| None | - | - | - | - | - |

## Memory telemetry

| Metric | Phase | Source | Samples | Median interval | Peak / status |
|---|---|---|---:|---:|---:|
| unified_memory_used | baseline | linux_proc | 1 | unavailable | 7869898752.000 bytes |
| unified_memory_used | cleanup | unknown | 1 | unavailable | unavailable (collector_failed) |
| unified_memory_used | decode | linux_proc | 14 | 107205.000 ms | 85816037376.000 bytes |
| unified_memory_used | load | linux_proc | 1 | unavailable | 74951196672.000 bytes |
| unified_memory_used | peak | linux_proc | 1 | unavailable | 85815996416.000 bytes |
| unified_memory_used | prefill | linux_proc | 14 | 51531.000 ms | 85570990080.000 bytes |
| unified_memory_used | steady | linux_proc | 1 | unavailable | 85806383104.000 bytes |

## Evaluation

Largest actual context completed: unavailable tokens.
Exploratory run: excluded from published historical comparisons.
