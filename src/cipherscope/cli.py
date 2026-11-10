"""Headless scripting interface for vault, hashes, and S-box metrics."""
import argparse
import getpass
import json
from pathlib import Path

from cipherscope.core import analysis, sbox, vault


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cipherscope-cli", description="CipherScope lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("encrypt", "decrypt"):
        p = sub.add_parser(command)
        p.add_argument("source", type=Path)
        p.add_argument("destination", type=Path)
    h = sub.add_parser("hash")
    h.add_argument("source", type=Path)
    h.add_argument("--algorithm", choices=["SHA-256", "SHA3-256", "BLAKE2b-256"],
                   default="SHA-256")
    a = sub.add_parser("analyze")
    a.add_argument("source", type=Path)
    s = sub.add_parser("sbox")
    s.add_argument("--kind", choices=["aes", "random", "triadic"], default="aes")
    s.add_argument("--seed", type=int, default=2026)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in ("encrypt", "decrypt"):
        password = getpass.getpass("Password: ")
        if args.command == "encrypt":
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise SystemExit("Passwords do not match.")
            result = vault.encrypt_file(args.source, args.destination, password)
        else:
            result = vault.decrypt_file(args.source, args.destination, password)
        print(f"Saved: {result}")
    elif args.command == "hash":
        # File hash via streaming, rather than holding arbitrary files in memory.
        import hashlib
        ctor = {"SHA-256": hashlib.sha256, "SHA3-256": hashlib.sha3_256,
                "BLAKE2b-256": lambda: hashlib.blake2b(digest_size=32)}[args.algorithm]
        hasher = ctor()
        with args.source.open("rb") as file:
            while block := file.read(1024 * 1024):
                hasher.update(block)
        print(hasher.hexdigest())
    elif args.command == "analyze":
        # Deliberately bounded; the GUI also limits in-memory sample sizes.
        with args.source.open("rb") as file:
            blob = file.read(8 * 1024 * 1024)
        report = analysis.byte_stats(blob).to_dict()
        report.pop("histogram")
        print(json.dumps(report, indent=2))
    else:
        table = {"aes": sbox.aes_sbox, "random": lambda: sbox.random_sbox(args.seed),
                 "triadic": lambda: sbox.triadic_sbox(args.seed)}[args.kind]()
        report = sbox.evaluate(table, args.kind).to_dict()
        report.pop("table")
        report.pop("sac")
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
