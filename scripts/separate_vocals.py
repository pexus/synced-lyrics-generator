#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import sys


def ensure_demucs_installed():
    try:
        import demucs  # noqa: F401
    except ImportError:
        print("Demucs is not installed. Install it with: pip install demucs", file=sys.stderr)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Separate vocals from an audio file using Demucs (CPU by default)."
    )
    parser.add_argument("input", help="Path to input audio file (wav/mp3).")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="data/vocal_stems",
        help="Output directory for separated stems.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="htdemucs",
        help="Demucs model name (e.g., htdemucs, mdx_extra_q).",
    )
    parser.add_argument(
        "-d",
        "--device",
        default="cpu",
        help="Device to use (cpu or cuda).",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    if not ensure_demucs_installed():
        return 1

    os.makedirs(args.output_dir, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "-n",
        args.model,
        "--two-stems",
        "vocals",
        "-d",
        args.device,
        "-o",
        args.output_dir,
        str(input_path),
    ]

    result = os.spawnvp(os.P_WAIT, cmd[0], cmd)
    if result != 0:
        print("Demucs failed to separate vocals.", file=sys.stderr)
        return result

    output_root = Path(args.output_dir) / args.model / input_path.stem
    vocals_path = output_root / "vocals.wav"
    other_path = output_root / "other.wav"

    print(f"Vocals output: {vocals_path}")
    print(f"Instrumental output: {other_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
