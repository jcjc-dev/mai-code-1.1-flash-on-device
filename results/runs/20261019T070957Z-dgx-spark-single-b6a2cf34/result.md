# Benchmark result: dgx-spark-single

- **Run:** `20261019T070957Z-dgx-spark-single-b6a2cf34`
- **Status:** `succeeded`
- **Created (UTC):** 2026-10-19T07:09:57.623Z
- **Suite:** `mai-code-baseline-v1`
- **Classification:** `published`
- **Hardware:** NVIDIA DGX Spark (GB10) (aarch64)
- **RAM capacity:** 130663231488 bytes
- **OS:** Ubuntu 24.04.4
- **Backend:** `cuda`
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
| `pp-2k` | pp | 5 / 5 | 2048.000 | 1.000 | 2304.000 | 1980.403 +/- 19.579 | unavailable | unavailable |
| `tg-2k-dflash-off` | tg | 5 / 5 | 2048.000 | 256.000 | 4096.000 | unavailable | 60.852 +/- 0.601 | unavailable |

## Failed or safely stopped requests

| Workload | Kind | Status | Requested context | Actual context | Error code |
|---|---|---|---:|---:|---|
| None | - | - | - | - | - |

## Memory telemetry

| Metric | Phase | Source | Samples | Median interval | Peak / status |
|---|---|---|---:|---:|---:|
| unified_memory_used | baseline | linux_proc | 1 | unavailable | 3740827648.000 bytes |
| unified_memory_used | cleanup | linux_proc | 1 | unavailable | 3765276672.000 bytes |
| unified_memory_used | decode | linux_proc | 14 | 7251.000 ms | 69145911296.000 bytes |
| unified_memory_used | load | linux_proc | 1 | unavailable | 66732539904.000 bytes |
| unified_memory_used | peak | linux_proc | 1 | unavailable | 69149204480.000 bytes |
| unified_memory_used | prefill | linux_proc | 14 | 3642.000 ms | 68818092032.000 bytes |
| unified_memory_used | steady | linux_proc | 1 | unavailable | 69155885056.000 bytes |

## Evaluation

Largest actual context completed: unavailable tokens.
Compared with compatible run `20261019T070817Z-dgx-spark-single-30a2efde`.

| Workload | Metric | Previous tok/s | Current tok/s | Change |
|---|---|---:|---:|---:|
| `pp-2k` | PP | 1989.512 | 1980.403 | -0.46% |
| `tg-2k-dflash-off` | TG | 59.712 | 60.852 | +1.91% |
