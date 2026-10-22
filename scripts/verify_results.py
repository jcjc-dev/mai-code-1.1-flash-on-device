"""Verify selected historical archives and the README throughput table, offline."""

import hashlib
import json
import math
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
BASELINES = {
    "Strix Halo": ("20261019T051400Z-strix-halo-874446e8",),
    "DGX Spark": (
        "20261019T070817Z-dgx-spark-single-30a2efde",
        "20261019T070957Z-dgx-spark-single-b6a2cf34",
        "20261019T071132Z-dgx-spark-single-c9ded3ab",
    ),
}
EXPLORATORY = {
    "Strix Halo": "20261019T181827Z-strix-halo-9b033a20",
    "DGX Spark": "20261020T041247Z-dgx-spark-single-32745efc",
}
RAW_FILES = {"manifest.json", "samples.jsonl", "host-metrics.jsonl"}
TABLE_START = "<!-- verified-results:start -->"
TABLE_END = "<!-- verified-results:end -->"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_rates(root, run_id, classification):
    directory = root / "results" / "runs" / run_id
    ledger = json.loads((directory / "raw-hashes.json").read_text(encoding="utf-8"))
    require(ledger["schema_version"] == "raw-hashes-v1", f"{run_id}: ledger version")
    require(set(ledger["files"]) == RAW_FILES, f"{run_id}: raw-file allowlist")
    for name, expected in ledger["files"].items():
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        require(actual == expected, f"{run_id}: {name} SHA-256 mismatch")

    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["run_id"] == run_id, f"{run_id}: run identity")
    require(manifest["status"] == "succeeded", f"{run_id}: incomplete run")
    require(manifest["runtime"]["engine"] == "llama-server", f"{run_id}: engine")
    require(manifest["runtime"]["timing_source"] == "server_response", f"{run_id}: timings")
    require(not manifest["dflash2"]["enabled"], f"{run_id}: DFlash2 must be off")
    protocol = manifest["protocol"]
    require(protocol["classification"] == classification, f"{run_id}: classification")
    require(protocol["warmups"] == 2 and protocol["measured_repetitions"] == 5,
            f"{run_id}: repetition protocol")
    require(protocol["concurrency"] == 1, f"{run_id}: concurrency")
    samples = [
        json.loads(line)
        for line in (directory / "samples.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    workloads = {workload["id"]: workload for workload in manifest["workloads"]}
    require(len(samples) == 7 * len(workloads), f"{run_id}: sample count")
    require(len({sample["sample_id"] for sample in samples}) == len(samples),
            f"{run_id}: duplicate samples")
    require(all(sample["workload_id"] in workloads for sample in samples),
            f"{run_id}: unknown workload")
    rates = {}
    for workload_id, workload in workloads.items():
        selected = [sample for sample in samples if sample["workload_id"] == workload_id]
        require(sum(sample["phase"] == "warmup" for sample in selected) == 2
                and sum(sample["phase"] == "measurement" for sample in selected) == 5,
                f"{run_id}/{workload_id}: warmup/measurement counts")
        measured = []
        for sample in selected:
            require(sample["status"] == "succeeded", f"{run_id}/{workload_id}: failed sample")
            require(sample["prompt_tokens"] == workload["prompt_tokens"]
                    and sample["output_tokens"] == workload["output_tokens"],
                    f"{run_id}/{workload_id}: token-count mismatch")
            timing = sample["prompt_eval_ms" if workload["kind"] == "pp" else "generation_ms"]
            require(isinstance(timing, (int, float)) and math.isfinite(timing) and timing > 0,
                    f"{run_id}/{workload_id}: invalid timing")
            if sample["phase"] == "measurement":
                tokens = sample["prompt_tokens" if workload["kind"] == "pp" else "output_tokens"]
                measured.append(tokens * 1000 / timing)
        rates[workload_id] = statistics.median(measured)
    return manifest, rates


def result_table(root):
    rows = [
        "| Hardware | Workload | tok/s | Evidence |",
        "|---|---|---:|---|",
    ]
    models = set()
    for hardware, run_ids in BASELINES.items():
        runs = [load_rates(root, run_id, "published") for run_id in run_ids]
        models.update(run[0]["model"]["sha256"] for run in runs)
        for workload, label in (("pp-2k", "PP 2K"), ("tg-2k-dflash-off", "TG 2K")):
            median = statistics.median(run[1][workload] for run in runs)
            evidence = "5 measured requests" if len(runs) == 1 else "median of 3 run medians"
            rows.append(f"| {hardware} | {label} | {median:.3f} | {evidence} |")
    for hardware, run_id in EXPLORATORY.items():
        manifest, rates = load_rates(root, run_id, "exploratory")
        models.add(manifest["model"]["sha256"])
        for workload, label in (("pp-32k", "PP 32K"), ("pp-64k", "PP 64K")):
            rows.append(f"| {hardware} | {label} | {rates[workload]:.3f} | exploratory |")
    require(len(models) == 1, "Selected runs do not share a model SHA-256")
    return "\n".join(rows)


def verify(root=ROOT):
    table = result_table(root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    require(readme.count(TABLE_START) == 1 and readme.count(TABLE_END) == 1,
            "README result-table markers are missing or duplicated")
    recorded = readme.split(TABLE_START, 1)[1].split(TABLE_END, 1)[0].strip()
    require(recorded == table, "README throughput table differs from archived measurements")
    return table


if __name__ == "__main__":
    try:
        print(verify())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Result verification failed: {error}", file=sys.stderr)
        sys.exit(1)
