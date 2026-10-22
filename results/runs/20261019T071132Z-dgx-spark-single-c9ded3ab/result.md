# Benchmark result: dgx-spark-single

- **Run:** `20261019T071132Z-dgx-spark-single-c9ded3ab`
- **Status:** `succeeded`
- **Created (UTC):** 2026-10-19T07:11:32.869Z
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
| `pp-2k` | pp | 5 / 5 | 2048.000 | 1.000 | 2304.000 | 1976.775 +/- 21.571 | unavailable | unavailable |
| `tg-2k-dflash-off` | tg | 5 / 5 | 2048.000 | 256.000 | 4096.000 | unavailable | 60.182 +/- 0.190 | unavailable |

## Failed or safely stopped requests

| Workload | Kind | Status | Requested context | Actual context | Error code |
|---|---|---|---:|---:|---|
| None | - | - | - | - | - |

## Memory telemetry

| Metric | Phase | Source | Samples | Median interval | Peak / status |
|---|---|---|---:|---:|---:|
| unified_memory_used | baseline | linux_proc | 1 | unavailable | 3767390208.000 bytes |
| unified_memory_used | cleanup | linux_proc | 1 | unavailable | 3791794176.000 bytes |
| unified_memory_used | decode | linux_proc | 14 | 7505.000 ms | 69105795072.000 bytes |
| unified_memory_used | load | linux_proc | 1 | unavailable | 66710581248.000 bytes |
| unified_memory_used | peak | linux_proc | 1 | unavailable | 69109678080.000 bytes |
| unified_memory_used | prefill | linux_proc | 14 | 3567.000 ms | 68812447744.000 bytes |
| unified_memory_used | steady | linux_proc | 1 | unavailable | 69112537088.000 bytes |

## Evaluation

Largest actual context completed: unavailable tokens.
Compared with compatible run `20261019T070957Z-dgx-spark-single-b6a2cf34`.

| Workload | Metric | Previous tok/s | Current tok/s | Change |
|---|---|---:|---:|---:|
| `pp-2k` | PP | 1980.403 | 1976.775 | -0.18% |
| `tg-2k-dflash-off` | TG | 60.852 | 60.182 | -1.10% |
