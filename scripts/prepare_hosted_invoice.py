"""Stage allowlisted invoice source and an optional verified Linux interpreter.

The Python bundle is an experiment for Engine's /app build layout, not a
supported platform image override. Never uploads or deploys by itself.
"""

import argparse
import hashlib
from pathlib import Path
import shutil
import tarfile


PYTHON_SHA256 = "7b03163a980c607ba8194709d4a4086735a7a9c488cc475b098157306927b36b"
# Noninteractive runtime profile. The executable is not linked to libpython;
# embedding, compiling C extensions, pip bootstrap and Tk are out of scope.
# No executable or extension binary is patched or recompressed.
COMPACT_OMISSIONS = (
    "python/share/terminfo", "python/include/", "python/lib/libpython",
    "python/lib/libtcl", "python/lib/tcl", "python/lib/tk", "python/lib/itcl",
    "python/lib/python3.15/site-packages/pip", "python/lib/python3.15/ensurepip/",
    "python/lib/python3.15/idlelib/", "python/lib/python3.15/tkinter/",
    "python/lib/python3.15/lib-dynload/_tkinter",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python-archive", type=Path)
    parser.add_argument("--compact-runtime", action="store_true")
    parser.add_argument("--profile", choices=("invoice", "journey"), default="invoice")
    args = parser.parse_args()
    # Never mix a new build with stale files, keys or caches in an old stage.
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[1] / "compatibility/openai_engine_adapter"
    files = [source / n for n in ("pyproject.toml", "uv.lock", "agent.yaml")]
    files += sorted((source / "src").rglob("*.py"))
    for file in files:
        target = args.output / file.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
    if args.profile == "journey":
        manifest = args.output / "agent.yaml"
        content = manifest.read_text()
        content = content.replace("Synthetic read-only OpenAI Runner compatibility proof",
                                  "Synthetic telecom supervisor and specialist journey")
        content = content.replace("openai_engine_adapter.invoice:app",
                                  "openai_engine_adapter.journey:app")
        content = content.replace("memory: false", "memory: true")
        content = content.replace("tools: [lookup_invoice]", "tools: [telco_read_invoice, "
            "telco_check_connection, telco_offer_plan, telco_simulate_plan_change]")
        manifest.write_text(content)
    if args.python_archive:
        with args.python_archive.open("rb") as archive_file:
            actual_hash = hashlib.file_digest(archive_file, "sha256").hexdigest()
        if actual_hash != PYTHON_SHA256:
            raise ValueError("Python artifact does not match published SHA-256")
        target = args.output / ".runtime-python"
        target.mkdir()
        with tarfile.open(args.python_archive) as archive:
            # terminfo aliases collide on case-insensitive macOS volumes;
            # the HTTP-only probe has no curses/terminal-database dependency.
            omissions = COMPACT_OMISSIONS if args.compact_runtime else ("python/share/terminfo",)
            members = [m for m in archive.getmembers() if not m.name.startswith(omissions)]
            archive.extractall(target, members=members, filter="data")
        (args.output / ".python-version").write_text("/app/.runtime-python/python/bin/python3.15\n")
    print(f"Staged {len(files)} source files; Linux Python bundle: {bool(args.python_archive)}")


if __name__ == "__main__":
    main()
