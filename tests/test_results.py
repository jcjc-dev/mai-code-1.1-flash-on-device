import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import verify_results


class ResultsTests(unittest.TestCase):
    def test_actual_archives_reproduce_readme(self):
        verify_results.verify()

    def test_changed_raw_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_id = verify_results.BASELINES["Strix Halo"][0]
            source = verify_results.ROOT / "results" / "runs" / run_id
            destination = root / "results" / "runs" / run_id
            shutil.copytree(source, destination)
            with (destination / "samples.jsonl").open("a", encoding="utf-8") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_results.load_rates(root, run_id, "published")

    def test_incomplete_or_invalid_requests_are_rejected_even_with_updated_hashes(self):
        for change in ("missing", "wrong_tokens", "zero_timing"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_id = verify_results.BASELINES["Strix Halo"][0]
                source = verify_results.ROOT / "results" / "runs" / run_id
                destination = root / "results" / "runs" / run_id
                shutil.copytree(source, destination)
                path = destination / "samples.jsonl"
                samples = [json.loads(line) for line in path.read_text().splitlines()]
                if change == "missing":
                    samples.pop()
                elif change == "wrong_tokens":
                    samples[2]["prompt_tokens"] -= 1
                else:
                    samples[2]["prompt_eval_ms"] = 0
                path.write_text(
                    "\n".join(json.dumps(sample) for sample in samples) + "\n",
                    encoding="utf-8",
                )
                ledger_path = destination / "raw-hashes.json"
                ledger = json.loads(ledger_path.read_text())
                ledger["files"]["samples.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
                ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
                with self.assertRaises(ValueError):
                    verify_results.load_rates(root, run_id, "published")

    def test_incorrect_readme_number_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(verify_results.ROOT / "results", root / "results")
            readme = (verify_results.ROOT / "README.md").read_text(encoding="utf-8")
            (root / "README.md").write_text(readme.replace("1160.581", "9999.999"),
                                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from archived measurements"):
                verify_results.verify(root)


if __name__ == "__main__":
    unittest.main()
