"""CivicBrain | ai-service/training/download_models.py - downloads all-MiniLM-L6-v2 once (Step 12 duplicates)

    ai-service\\.venv\\Scripts\\python ai-service\\training\\download_models.py            # download + check
    ai-service\\.venv\\Scripts\\python ai-service\\training\\download_models.py --revision <commit>   # pin a commit

Downloads only the files sentence-transformers needs (no ONNX/OpenVINO/TF copies) into
ai-service/models/all-MiniLM-L6-v2/, records the Hugging Face commit and the SHA-256 of every file in
ai-service/models/MANIFEST.json, then loads the model on CPU and encodes two sentences (384 dimensions).
After this the worker runs with HF_HUB_OFFLINE=1 (no internet needed). Licence: Apache-2.0.
The agent may run it (prompt P09). Exit codes: 0 ok, 1 check failed, 2 download failed.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "0"                 # this one script must go online, whatever .env says
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_manifest import MODELS_DIR, now_iso, sha256_file, upsert_entry  # noqa: E402

REPO_ID = "sentence-transformers/all-MiniLM-L6-v2"
FOLDER = "all-MiniLM-L6-v2"
ALLOW = ["config.json", "config_sentence_transformers.json", "modules.json", "sentence_bert_config.json",
         "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt", "model.safetensors",
         "1_Pooling/config.json", "README.md"]


def file_entries(folder: Path) -> list[dict]:
    files = []
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if p.is_file() and not rel.startswith(".cache/"):
            files.append({"path": rel, "sha256": sha256_file(p), "bytes": p.stat().st_size})
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    ap.add_argument("--revision", default="main", help="Hugging Face commit or branch (default main; the commit is recorded)")
    ap.add_argument("--no-check", action="store_true")
    args = ap.parse_args(argv)

    target = args.models_dir / FOLDER
    try:
        from huggingface_hub import HfApi, snapshot_download

        commit = HfApi().model_info(REPO_ID, revision=args.revision).sha
        snapshot_download(repo_id=REPO_ID, revision=commit, local_dir=str(target), allow_patterns=ALLOW)
    except Exception as e:  # noqa: BLE001 - network/auth problems are reported plainly
        print(f"ERROR: download failed: {e}", file=sys.stderr)
        return 2

    missing = [f for f in ALLOW if f != "README.md" and not (target / f).is_file()]
    if missing:
        print(f"ERROR: files missing after download: {missing}", file=sys.stderr)
        return 2

    entry = {"path": f"{FOLDER}/", "kind": "sentence-transformers folder (one SHA-256 per file)", "repo": REPO_ID,
             "revision": commit, "files": file_entries(target), "licence": "Apache-2.0", "installed_at": now_iso()}
    manifest = upsert_entry(entry, args.models_dir)

    if not args.no_check:
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(str(target), device="cpu")
            emb = model.encode(["Large pothole near the bus stand", "Big pothole close to the bus stop"], normalize_embeddings=True)
            if emb.shape != (2, 384):
                raise ValueError(f"unexpected embedding shape {emb.shape}")
            sim = float(emb[0] @ emb[1])
            print(f"CHECK ok: 384 dimensions, similarity of two pothole sentences = {sim:.3f}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: model check failed: {e}", file=sys.stderr)
            return 1

    print(f"INSTALLED {target} (commit {commit[:12]}, {len(entry['files'])} files)")
    print(f"MANIFEST  {manifest}")
    print("Set TEXT_EMBEDDING_MODEL_DIR to this folder in .env (new-env.ps1 already does) and keep HF_HUB_OFFLINE=1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
