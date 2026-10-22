# Benchmark result: strix-halo

- **Run:** `20261019T051400Z-strix-halo-874446e8`
- **Status:** `succeeded`
- **Created (UTC):** 2026-10-19T05:14:00.002Z
- **Suite:** `mai-code-baseline-v1`
- **Classification:** `published`
- **Hardware:** AMD Strix Halo (x86_64)
- **RAM capacity:** 133617983488 bytes
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
- **Drafter SHA-256:** `7052df547898b46fab3ff23f8c1085547003116899506099467f948debb75b15`

## Timing results

Rates use normalized server-side timing fields; only measured successful samples are summarized.

| Workload | Kind | Successful / measured | Prompt tokens | Output tokens | Requested n_ctx | PP tok/s (median +/- SD) | TG tok/s (median +/- SD) | Largest actual context tested |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `pp-2k` | pp | 5 / 5 | 2048.000 | 1.000 | 2304.000 | 1160.581 +/- 4.464 | unavailable | unavailable |
| `tg-2k-dflash-off` | tg | 5 / 5 | 2048.000 | 256.000 | 4096.000 | unavailable | 124.339 +/- 0.428 | unavailable |

## Failed or safely stopped requests

| Workload | Kind | Status | Requested context | Actual context | Error code |
|---|---|---|---:|---:|---|
| None | - | - | - | - | - |

## Memory telemetry

| Metric | Phase | Source | Samples | Median interval | Peak / status |
|---|---|---|---:|---:|---:|
| unified_memory_used | baseline | linux_proc | 1 | unavailable | 7913623552.000 bytes |
| unified_memory_used | cleanup | linux_proc | 1 | unavailable | 7863463936.000 bytes |
| unified_memory_used | decode | linux_proc | 14 | 22018.000 ms | 77713043456.000 bytes |
| unified_memory_used | load | linux_proc | 1 | unavailable | 74036064256.000 bytes |
| unified_memory_used | peak | linux_proc | 1 | unavailable | 77732585472.000 bytes |
| unified_memory_used | prefill | linux_proc | 14 | 22059.000 ms | 77503676416.000 bytes |
| unified_memory_used | steady | linux_proc | 1 | unavailable | 77741568000.000 bytes |

## Evaluation

Largest actual context completed: unavailable tokens.
No earlier compatible published run exists; this run establishes the baseline.
