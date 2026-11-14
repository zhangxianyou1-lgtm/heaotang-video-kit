"""Single-controller evidence ledger. Identities need actual host dispatch records.

Checks are trusted, predeclared argv lists, not sandboxed commands. A timeout
terminates the direct subprocess; it does not guarantee killing descendants.
Inputs are immutable sources from start through verification. Editable files
belong in owns; inputs must not overlap owns or ledger/log storage.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import tempfile
import uuid


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def file_hash(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def text(value, label):
    require(isinstance(value, str) and value.strip(), label + " must be nonempty text")
    return value.strip()


def relative(root, value):
    text(value, "path")
    windows = PureWindowsPath(value)
    require(not windows.drive and not windows.root and not Path(value).is_absolute(),
            "path must be relative: " + value)
    path = (root / value.replace("\\", "/")).resolve()
    require(path.is_relative_to(root) and path != root, "path outside root: " + value)
    # Case-fold comparisons intentionally follow Windows ownership semantics.
    return path.relative_to(root).as_posix()


def contains(parent, child):
    parent, child = parent.casefold(), child.casefold()
    return child == parent or child.startswith(parent + "/")


def overlap(first, second):
    return contains(first, second) or contains(second, first)


def snapshot(root, paths, missing=False):
    result = {}

    def visit(path, ancestors):
        name = relative(root, str(path.relative_to(root)))
        resolved = root / name
        require(resolved not in ancestors, "directory symlink cycle: " + name)
        if resolved.is_file():
            result[name] = file_hash(resolved)
        elif resolved.is_dir():
            result[name + "/"] = "directory"
            for child in sorted(resolved.iterdir()):
                visit(child, ancestors | {resolved})
        else:
            require(missing and not resolved.exists(), "missing/nonregular file: " + name)
            result[name] = "missing"

    for name in paths:
        visit(root / name, set())
    return result


def save(path, state, create=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as target:
            json.dump(state, target, ensure_ascii=False, indent=2)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        if create:
            # Atomic no-clobber publication; unlike replace, refuses existing state.
            if os.name == "nt":
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def event(state, action, task=None, **details):
    state["events"].append(dict(time=datetime.now(timezone.utc).isoformat(),
                                action=action, task=task, **details))


def initialize(args):
    require(not args.state.exists(), "state already exists")
    root = args.root.resolve(strict=True)
    require(root.is_dir(), "root must be a directory")
    spec_path = args.spec.resolve(strict=True)
    source = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    require(isinstance(source, dict), "spec must be an object")
    goal = text(source.get("goal"), "goal")
    require(isinstance(source.get("tasks"), list) and source["tasks"], "tasks must be nonempty")
    tasks = {}
    for raw in source["tasks"]:
        require(isinstance(raw, dict), "task must be an object")
        task = dict(raw)
        ident = text(task.get("id"), "task id")
        require(ident not in tasks, "duplicate task id: " + ident)
        task["id"] = ident
        task["title"] = text(task.get("title"), "title")
        acceptance = task.get("acceptance")
        require(isinstance(acceptance, list) and acceptance, "acceptance must be a nonempty list")
        task["acceptance"] = [text(item, "acceptance") for item in acceptance]
        for key in ("owns", "inputs", "depends", "checks"):
            require(isinstance(task.get(key), list), key + " must be a list")
        require(task["owns"], "owns must be nonempty")
        for key in ("owns", "inputs"):
            task[key] = [relative(root, item) for item in task[key]]
            require(len({item.casefold() for item in task[key]}) == len(task[key]),
                    "duplicate/alias paths in " + key)
        for key in ("owns", "inputs"):
            for path in task[key]:
                for reserved in (args.state, args.state.parent / (args.state.name + ".logs")):
                    require(not reserved.resolve().is_relative_to(root) or
                            not overlap(path, reserved.resolve().relative_to(root).as_posix()),
                            key + " overlaps ledger/log storage; use explicit source files, not the run directory")
        require(not any(overlap(own, source) for own in task["owns"] for source in task["inputs"]),
                "immutable inputs overlap owns; put editable files only in owns")
        task["depends"] = [text(item, "dependency") for item in task["depends"]]
        require(len(set(task["depends"])) == len(task["depends"]), "duplicate dependency")
        task.setdefault("validation", "commands")
        require(task["validation"] in ("commands", "inspection"), "unknown validation")
        require(task["checks"] or task["validation"] == "inspection", "commands validation needs checks")
        for argv in task["checks"]:
            require(isinstance(argv, list) and argv and
                    all(isinstance(arg, str) and "\0" not in arg for arg in argv) and argv[0].strip(),
                    "each check must be a nonempty argv list")
        task.setdefault("max_attempts", 3)
        require(type(task["max_attempts"]) is int and task["max_attempts"] > 0,
                "max_attempts must be a positive integer")
        task.setdefault("timeout", 120)
        require(type(task["timeout"]) in (int, float) and math.isfinite(task["timeout"]) and
                task["timeout"] > 0, "timeout must be finite and positive")
        tasks[ident] = dict(spec=task, status="pending", attempts=[])
    visited, active = set(), set()

    def visit(ident):
        require(ident in tasks, "unknown dependency: " + ident)
        require(ident not in active, "dependency cycle: " + ident)
        if ident not in visited:
            active.add(ident)
            for dependency in tasks[ident]["spec"]["depends"]:
                visit(dependency)
            active.remove(ident)
            visited.add(ident)

    for ident in tasks:
        visit(ident)
    state = dict(version=1, root=str(root), goal=goal, spec_path=str(spec_path),
                 spec_hash=file_hash(spec_path), tasks=tasks, events=[])
    event(state, "init")
    save(args.state, state, create=True)
    return dict(goal=goal, tasks=list(tasks))


def attempt(task):
    require(task["attempts"], "task has not started")
    return task["attempts"][-1]


def submission(task):
    submissions = attempt(task)["submissions"]
    require(submissions, "missing submission")
    return submissions[-1]


def source_evidence(state, ident):
    root = Path(state["root"])
    task = state["tasks"][ident]
    require(file_hash(Path(state["spec_path"])) == state["spec_hash"], "spec file changed")
    return dict(definition=digest(task["spec"]), spec_path=state["spec_path"], spec_hash=state["spec_hash"],
                inputs=snapshot(root, task["spec"]["inputs"]),
                dependencies={dep: verified_proof(state, dep) for dep in task["spec"]["depends"]})


def execution_baseline(state, ident):
    latest = attempt(state["tasks"][ident])
    require("baseline" in latest, "missing execution baseline; repair then start a new attempt")
    current_sources = source_evidence(state, ident)
    require(current_sources == latest["baseline"],
            "execution baseline changed since start; repair then start a new attempt")
    return current_sources


def fingerprint(state, ident):
    submitted = submission(state["tasks"][ident])
    return digest(dict(baseline=execution_baseline(state, ident),
                       artifacts=snapshot(Path(state["root"]), submitted["artifacts"])))


def current(state, ident):
    task = state["tasks"][ident]
    submitted = submission(task)
    require(fingerprint(state, ident) == submitted["fingerprint"], "stale task evidence: " + ident)
    return submitted


def evidence_files(state, task):
    latest = attempt(task)
    submitted = submission(task)
    if latest["check_runs"] and latest["check_runs"][-1]["submission"] == submitted["id"]:
        for result in latest["check_runs"][-1]["results"]:
            require(file_hash(Path(result["log"])) == result["log_hash"], "check log changed")
    if latest["reviews"] and latest["reviews"][-1]["submission"] == submitted["id"]:
        review = latest["reviews"][-1]
        report = Path(state["root"]) / relative(Path(state["root"]), review["report"])
        require(report.read_text(encoding="utf-8").strip() and file_hash(report) == review["report_hash"],
                "review report changed or empty")


def verified_proof(state, ident, require_verified=True):
    # ponytail: shared dependencies are rehashed; memoize per operation for large DAGs.
    task = state["tasks"][ident]
    if require_verified:
        require(task["status"] == "verified", "dependency is not verified: " + ident)
    submitted = current(state, ident)
    evidence_files(state, task)
    latest = attempt(task)
    if task["spec"]["checks"]:
        require(latest["check_runs"], "missing check execution")
        run = latest["check_runs"][-1]
        require(run["passed"] and run["submission"] == submitted["id"] and
                run["fingerprint"] == submitted["fingerprint"], "checks missing, failed or stale")
        require(len(run["results"]) == len(task["spec"]["checks"]), "incomplete checks")
        for result, argv in zip(run["results"], task["spec"]["checks"]):
            require(result["argv"] == argv and result["returncode"] == 0 and not result["timed_out"],
                    "check command changed or failed")
    require(latest["reviews"], "missing independent review")
    review = latest["reviews"][-1]
    require(review["verdict"] == "pass" and review["submission"] == submitted["id"] and
            review["fingerprint"] == submitted["fingerprint"], "review failed or stale")
    require(review["agent"].casefold() not in {item["agent"].casefold() for item in task["attempts"]},
            "executor cannot review own task")
    return digest(dict(submission=submitted, checks=latest["check_runs"], review=review,
                       attempt=latest["number"]))


def execute_checks(state, ident, state_path):
    task = state["tasks"][ident]
    submitted = current(state, ident)
    latest = attempt(task)
    root = Path(state["root"])
    before = snapshot(root, task["spec"]["owns"], missing=True)
    log_dir = state_path.parent / (state_path.name + ".logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    run = dict(id=uuid.uuid4().hex, submission=submitted["id"],
               fingerprint=submitted["fingerprint"], results=[], passed=False)
    for index, argv in enumerate(task["spec"]["checks"]):
        path = log_dir / (run["id"] + "-" + str(index) + ".log")
        result = dict(argv=argv, returncode=None, timed_out=False, log=str(path))
        with path.open("xb") as log:
            log.write((json.dumps(dict(argv=argv, cwd=str(root)), ensure_ascii=False) + "\n").encode("utf-8"))
            log.flush()
            try:
                with subprocess.Popen(argv, cwd=root, shell=False, stdout=log,
                                      stderr=subprocess.STDOUT) as process:
                    try:
                        result["returncode"] = process.wait(timeout=task["spec"]["timeout"])
                    except subprocess.TimeoutExpired:
                        process.kill()
                        result["returncode"] = process.wait()
                        result["timed_out"] = True
                        log.write(b"\nTIMEOUT: direct subprocess terminated\n")
            except OSError as error:
                result["error"] = str(error)
                log.write(("\nSPAWN ERROR: " + str(error) + "\n").encode("utf-8"))
        result["log_hash"] = file_hash(path)
        with path.open("rb") as log:
            log.seek(max(0, path.stat().st_size - 2000))
            result["summary"] = log.read().decode("utf-8", errors="replace")
        run["results"].append(result)
    try:
        run["unchanged"] = (before == snapshot(root, task["spec"]["owns"], missing=True) and
                              fingerprint(state, ident) == submitted["fingerprint"])
    except (Invalid, OSError, UnicodeError) as error:
        run["unchanged"] = False
        run["error"] = str(error)
    run["passed"] = run["unchanged"] and all(item["returncode"] == 0 and not item["timed_out"]
                                               for item in run["results"])
    run["validation"] = task["spec"]["validation"]
    run["commands_executed"] = len(run["results"])
    latest["check_runs"].append(run)
    if not run["passed"]:
        task["status"] = "repair"
    return run


def operate(args):
    if args.command == "init":
        return initialize(args), True
    state = json.loads(args.state.read_text(encoding="utf-8"))
    require(state.get("version") == 1, "unsupported state version")
    root = Path(state["root"]).resolve(strict=True)
    tasks = state["tasks"]
    task = None
    if hasattr(args, "task"):
        require(args.task in tasks, "unknown task: " + args.task)
        task = tasks[args.task]
    details, success = {}, True
    if args.command == "start":
        require(task["status"] in ("pending", "repair"), "start requires pending/repair")
        agent = text(args.agent, "agent")
        require(len(task["attempts"]) < task["spec"]["max_attempts"], "attempt budget exhausted")
        baseline = source_evidence(state, args.task)
        owns = [relative(root, path) for path in task["spec"]["owns"]]
        for other in tasks.values():
            if other is not task and other["status"] in ("running", "review", "waiting_external"):
                require(not any(overlap(a, relative(root, b)) for a in owns for b in other["spec"]["owns"]),
                        "parallel ownership conflict")
        task["attempts"].append(dict(number=len(task["attempts"]) + 1, agent=agent,
                                     baseline=baseline, submissions=[], check_runs=[], reviews=[]))
        task["status"] = "running"
        details = dict(agent=agent, attempt=len(task["attempts"]))
    elif args.command == "submit":
        require(task["status"] == "running", "submit requires running")
        execution_baseline(state, args.task)
        artifacts = [relative(root, path) for group in args.artifact for path in group]
        require(len(set(path.casefold() for path in artifacts)) == len(artifacts), "duplicate/alias artifacts")
        for path in artifacts:
            require((root / path).is_file(), "artifact must be an existing file: " + path)
            require(any(contains(relative(root, own), path) for own in task["spec"]["owns"]),
                    "artifact outside owns: " + path)
        submitted = dict(id=uuid.uuid4().hex, artifacts=artifacts)
        attempt(task)["submissions"].append(submitted)
        submitted["fingerprint"] = fingerprint(state, args.task)
        task["status"] = "review"
        details = dict(submission=submitted)
    elif args.command == "check":
        require(task["status"] == "review", "check requires review")
        details = execute_checks(state, args.task, args.state)
        success = details["passed"]
    elif args.command == "review":
        require(task["status"] == "review", "review requires review; failed reviews need a new attempt")
        submitted = current(state, args.task)
        agent = text(args.agent, "agent")
        require(agent.casefold() not in {item["agent"].casefold() for item in task["attempts"]},
                "executor cannot review own task")
        report = relative(root, args.report)
        report_path = root / report
        require(report_path.is_file() and report_path.read_text(encoding="utf-8").strip(),
                "report must be a nonempty UTF-8 file")
        details = dict(agent=agent, report=report, report_hash=file_hash(report_path),
                       report_text=report_path.read_text(encoding="utf-8"),
                       verdict=args.verdict, fingerprint=submitted["fingerprint"], submission=submitted["id"])
        attempt(task)["reviews"].append(details)
        if args.verdict == "fail":
            task["status"] = "repair"
    elif args.command == "verify":
        require(task["status"] in ("review", "verified"), "verify requires review/verified")
        details = dict(proof=verified_proof(state, args.task, require_verified=False),
                       validation=task["spec"]["validation"], commands_executed=len(task["spec"]["checks"]))
        task["status"] = "verified"
    elif args.command == "repair":
        require(task["status"] in ("running", "review", "verified", "repair"), "cannot repair this state")
        details = dict(reason=text(args.reason, "reason"))
        task["status"] = "repair"
    elif args.command == "wait":
        require(task["status"] in ("running", "review", "repair"), "cannot wait in this state")
        details = dict(reason=text(args.reason, "reason"), external_id=text(args.external_id, "external id"),
                       previous=task["status"])
        task["waiting"] = details
        task["status"] = "waiting_external"
    elif args.command == "resume":
        require(task["status"] == "waiting_external", "resume requires waiting_external")
        details = dict(resolution=text(args.resolution, "resolution"), waiting=task["waiting"])
        task["status"] = "repair" if task["waiting"]["previous"] == "repair" else "running"
        del task["waiting"]
    elif args.command == "status":
        details = dict(goal=state["goal"], tasks={})
        for ident, item in tasks.items():
            stale, reason = False, None
            if item["attempts"]:
                try:
                    execution_baseline(state, ident)
                    if item["status"] == "verified":
                        verified_proof(state, ident)
                    elif attempt(item)["submissions"]:
                        current(state, ident)
                        evidence_files(state, item)
                except (Invalid, OSError, UnicodeError) as error:
                    stale, reason = True, str(error)
            details["tasks"][ident] = dict(status=item["status"], attempts=len(item["attempts"]),
                                            max_attempts=item["spec"]["max_attempts"], stale=stale, reason=reason)
    elif args.command == "finish":
        require(tasks, "cannot finish empty tasks")
        details = dict(goal=state["goal"], proofs={ident: verified_proof(state, ident) for ident in tasks})
    event(state, args.command, getattr(args, "task", None), details=details)
    save(args.state, state)
    return details, success


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "start", "submit", "check", "review", "verify", "repair", "wait", "resume", "status", "finish"):
        command = commands.add_parser(name)
        command.add_argument("state", type=Path)
        if name not in ("init", "status", "finish"):
            command.add_argument("task")
        if name == "init":
            command.add_argument("--root", type=Path, required=True)
            command.add_argument("--spec", type=Path, required=True)
        if name in ("start", "review"):
            command.add_argument("--agent", required=True)
        if name == "submit":
            command.add_argument("--artifact", nargs="+", action="append", required=True)
        if name == "review":
            command.add_argument("--report", required=True)
            command.add_argument("--verdict", choices=("pass", "fail"), required=True)
        if name in ("repair", "wait"):
            command.add_argument("--reason", required=True)
        if name == "wait":
            command.add_argument("--external-id", required=True)
        if name == "resume":
            command.add_argument("--resolution", required=True)
    args = parser.parse_args(argv)
    args.state = args.state.resolve()
    try:
        result, success = operate(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if success else 1
    except (Invalid, OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print("workflow: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
