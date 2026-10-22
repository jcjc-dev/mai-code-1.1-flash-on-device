# Benchmark result: dgx-spark-single

- **Run:** `20261020T041247Z-dgx-spark-single-32745efc`
- **Status:** `succeeded`
- **Created (UTC):** 2026-10-20T04:12:47.838Z
- **Suite:** `mai-code-baseline-v2`
- **Classification:** `exploratory`
- **Hardware:** NVIDIA DGX Spark (GB10) (aarch64)
- **RAM capacity:** 130663231488 bytes
- **OS:** Ubuntu 24.04
- **Backend:** `cuda`
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
| `pp-32k` | pp | 5 / 5 | 32768.000 | 1.000 | 33024.000 | 1982.820 +/- 3.965 | unavailable | unavailable |
| `pp-64k` | pp | 5 / 5 | 65536.000 | 1.000 | 65792.000 | 1820.364 +/- 1.954 | unavailable | unavailable |

## Failed or safely stopped requests

| Workload | Kind | Status | Requested context | Actual context | Error code |
|---|---|---|---:|---:|---|
| None | - | - | - | - | - |

## Memory telemetry

| Metric | Phase | Source | Samples | Median interval | Peak / status |
|---|---|---|---:|---:|---:|
| device_memory_used | baseline | unknown | 1 | unavailable | unavailable (not_exposed) |
| device_memory_used | cleanup | unknown | 17 | 249.000 ms | unavailable (not_exposed) |
| device_memory_used | decode | unknown | 14 | 41687.000 ms | unavailable (not_exposed) |
| device_memory_used | load | unknown | 27 | 249.000 ms | unavailable (not_exposed) |
| device_memory_used | peak | unknown | 1 | unavailable | unavailable (not_exposed) |
| device_memory_used | prefill | unknown | 1529 | 249.000 ms | unavailable (not_exposed) |
| device_memory_used | steady | unknown | 289 | 248.000 ms | unavailable (not_exposed) |
| memory_pressure | baseline | unknown | 1 | unavailable | unavailable (not_exposed) |
| memory_pressure | cleanup | unknown | 17 | 249.000 ms | unavailable (not_exposed) |
| memory_pressure | decode | unknown | 14 | 41687.000 ms | unavailable (not_exposed) |
| memory_pressure | load | unknown | 27 | 249.000 ms | unavailable (not_exposed) |
| memory_pressure | peak | unknown | 1 | unavailable | unavailable (not_exposed) |
| memory_pressure | prefill | unknown | 1529 | 249.000 ms | unavailable (not_exposed) |
| memory_pressure | steady | unknown | 289 | 248.000 ms | unavailable (not_exposed) |
| process_memory_used | baseline | linux_proc | 1 | unavailable | unavailable (not_exposed) |
| process_memory_used | cleanup | linux_proc | 17 | 249.000 ms | unavailable (not_exposed) |
| process_memory_used | decode | unknown | 14 | 41687.000 ms | unavailable (not_exposed) |
| process_memory_used | load | linux_proc | 27 | 249.000 ms | unavailable (not_exposed) |
| process_memory_used | peak | linux_proc | 1 | unavailable | unavailable (not_exposed) |
| process_memory_used | prefill | linux_proc | 1529 | 249.000 ms | unavailable (not_exposed) |
| process_memory_used | steady | linux_proc | 289 | 248.000 ms | unavailable (not_exposed) |
| system_memory_used | baseline | linux_proc | 1 | unavailable | unavailable (not_exposed) |
| system_memory_used | cleanup | linux_proc | 17 | 249.000 ms | unavailable (not_exposed) |
| system_memory_used | decode | unknown | 14 | 41687.000 ms | unavailable (not_exposed) |
| system_memory_used | load | linux_proc | 27 | 249.000 ms | unavailable (not_exposed) |
| system_memory_used | peak | linux_proc | 1 | unavailable | unavailable (not_exposed) |
| system_memory_used | prefill | linux_proc | 1529 | 249.000 ms | unavailable (not_exposed) |
| system_memory_used | steady | linux_proc | 289 | 248.000 ms | unavailable (not_exposed) |
| temperature | baseline | unknown | 1 | unavailable | unavailable (not_exposed) |
| temperature | cleanup | unknown | 17 | 249.000 ms | unavailable (not_exposed) |
| temperature | decode | unknown | 14 | 41687.000 ms | unavailable (not_exposed) |
| temperature | load | unknown | 27 | 249.000 ms | unavailable (not_exposed) |
| temperature | peak | unknown | 1 | unavailable | unavailable (not_exposed) |
| temperature | prefill | unknown | 1529 | 249.000 ms | unavailable (not_exposed) |
| temperature | steady | unknown | 289 | 248.000 ms | unavailable (not_exposed) |
| unified_memory_used | baseline | linux_proc | 1 | unavailable | unavailable (not_exposed) |
| unified_memory_used | cleanup | linux_proc | 16 | 249.000 ms | 77249495040.000 bytes |
| unified_memory_used | cleanup | linux_proc | 1 | unavailable | unavailable (collector_failed) |
| unified_memory_used | decode | unknown | 14 | 41687.000 ms | unavailable (not_exposed) |
| unified_memory_used | load | linux_proc | 25 | 248.500 ms | 67370995712.000 bytes |
| unified_memory_used | load | linux_proc | 2 | 253.000 ms | unavailable (not_exposed) |
| unified_memory_used | peak | linux_proc | 1 | unavailable | 76992286720.000 bytes |
| unified_memory_used | prefill | linux_proc | 1529 | 249.000 ms | 76992286720.000 bytes |
| unified_memory_used | steady | linux_proc | 289 | 248.000 ms | 76992286720.000 bytes |

## Evaluation

Largest actual context completed: unavailable tokens.
Exploratory run: excluded from published historical comparisons.
