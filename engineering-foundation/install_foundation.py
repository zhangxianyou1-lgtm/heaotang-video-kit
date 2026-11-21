"""Verify and install the Three-Masters Engineering Foundation (Matt Pocock + Ponytail + Poteto pstack).

Stdlib-only (Python 3.11+). Supports --check, --dry-run, and --target {all,codex,antigravity}.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import sys

ALLOWED_AGY_PLUGIN_KEYS = {
    "name",
    "displayName",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "suggestedPrompts",
    "logo",
    "disabled",
}

FOUNDATION_DIR = Path(__file__).resolve().parent
BUNDLES = ("mattpocock-skills", "ponytail", "pstack-poteto")
REPLACED_H1_PREFIXES = (
    "# 用户级任务流程",
    "# 用户级协作与验收底线",
    "# 三剑客工程底座",
)


def parse_frontmatter(md_text: str) -> dict:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", md_text, re.DOTALL)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def check_foundation() -> dict:
    errors = []
    upstream_path = FOUNDATION_DIR / "UPSTREAM.json"
    if not upstream_path.is_file():
        errors.append("Missing UPSTREAM.json")
    else:
        json.loads(upstream_path.read_text(encoding="utf-8"))

    global_agents = FOUNDATION_DIR / "global-AGENTS.md"
    if not global_agents.is_file() or not global_agents.read_text(encoding="utf-8").strip():
        errors.append("Missing or empty global-AGENTS.md")

    seen_skills = {}
    bundle_counts = {}
    for bname in BUNDLES:
        bdir = FOUNDATION_DIR / bname
        if not bdir.is_dir():
            errors.append(f"Missing bundle directory: {bname}")
            continue

        agy_pj = bdir / "plugin.json"
        if not agy_pj.is_file():
            errors.append(f"{bname}: missing plugin.json")
        else:
            pdata = json.loads(agy_pj.read_text(encoding="utf-8"))
            extra = set(pdata.keys()) - ALLOWED_AGY_PLUGIN_KEYS
            if extra:
                errors.append(f"{bname}: invalid top-level keys in plugin.json: {sorted(extra)}")

        codex_pj = bdir / ".codex-plugin" / "plugin.json"
        if not codex_pj.is_file():
            errors.append(f"{bname}: missing .codex-plugin/plugin.json")
        else:
            cdata = json.loads(codex_pj.read_text(encoding="utf-8"))
            if not cdata.get("name") or not cdata.get("skills"):
                errors.append(f"{bname}: .codex-plugin/plugin.json missing name or skills")

        sroot = bdir / "skills"
        count = 0
        for sdir in sorted(sroot.iterdir()) if sroot.is_dir() else []:
            if not sdir.is_dir():
                continue
            smd = sdir / "SKILL.md"
            oyaml = sdir / "agents" / "openai.yaml"
            if not smd.is_file():
                errors.append(f"{bname}/{sdir.name}: missing SKILL.md")
                continue
            text = smd.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            if fm.get("name") != sdir.name:
                errors.append(f"{bname}/{sdir.name}: frontmatter name={fm.get('name')!r} != dir name")
            if not fm.get("description"):
                errors.append(f"{bname}/{sdir.name}: empty description in frontmatter")
            if not oyaml.is_file():
                errors.append(f"{bname}/{sdir.name}: missing agents/openai.yaml")
            if bname == "pstack-poteto":
                for forbidden in ("claude-fable-", "pstack-models.mdc"):
                    if forbidden in text:
                        errors.append(f"{bname}/{sdir.name}: unadapted Cursor string {forbidden!r}")
            if sdir.name in seen_skills:
                errors.append(f"Duplicate skill name {sdir.name!r} in {bname} and {seen_skills[sdir.name]}")
            seen_skills[sdir.name] = bname
            count += 1
        bundle_counts[bname] = count

    if errors:
        raise ValueError("Foundation check failed:\n- " + "\n- ".join(errors))
    return {
        "status": "PASS",
        "bundles": bundle_counts,
        "total_unique_skills": len(seen_skills),
    }


def merge_codex_agents_md(existing_text: str, new_header_section: str) -> str:
    sections = re.split(r"(?=^# )", existing_text.strip(), flags=re.MULTILINE) if existing_text.strip() else []
    preserved = []
    for sec in sections:
        sec_stripped = sec.strip()
        if not sec_stripped:
            continue
        if any(sec_stripped.startswith(prefix) for prefix in REPLACED_H1_PREFIXES):
            continue
        preserved.append(sec_stripped)
    parts = [new_header_section.strip()] + preserved
    return "\n\n".join(parts) + "\n"


def ensure_codex_plugin_enabled(config_text: str, plugin_key: str, after_key: str | None = None) -> str:
    header = f'[plugins."{plugin_key}"]'
    if header in config_text:
        return re.sub(
            rf'(\[plugins\."{re.escape(plugin_key)}"\]\r?\n)enabled\s*=\s*false',
            r"\1enabled = true",
            config_text,
        )
    block = f'{header}\nenabled = true\n'
    if after_key:
        anchor = f'[plugins."{after_key}"]\nenabled = true'
        if anchor in config_text:
            return config_text.replace(anchor, f"{anchor}\n\n{block.strip()}", 1)
    return config_text.rstrip() + f"\n\n{block}"


def copy_tree_clean(src: Path, dst: Path, dry_run: bool, actions: list[str]):
    actions.append(f"sync {src.name} -> {dst}")
    if dry_run:
        return
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def install(home: Path, target: str, dry_run: bool) -> dict:
    check_report = check_foundation()
    actions = []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = home / ".agents" / f"foundation_backup_{stamp}"

    if target in ("all", "codex"):
        codex_dir = home / ".codex"
        if codex_dir.is_dir():
            mp_personal = codex_dir / "marketplaces" / "migration-personal"
            mp_ponytail = codex_dir / "marketplaces" / "migration-ponytail"
            cfg_path = codex_dir / "config.toml"
            agents_path = codex_dir / "AGENTS.md"

            if not dry_run:
                backup_dir.mkdir(parents=True, exist_ok=True)
                for fpath, bname in (
                    (cfg_path, "config.toml.bak"),
                    (agents_path, "codex_AGENTS.md.bak"),
                    (mp_personal / "marketplace.json", "personal_marketplace.json.bak"),
                ):
                    if fpath.is_file():
                        shutil.copy2(fpath, backup_dir / bname)
                actions.append(f"backup existing Codex configs -> {backup_dir}")
            else:
                actions.append(f"would backup existing Codex configs -> {backup_dir}")

            # 1. Sync Matt Pocock (v1.3.2) & Poteto pstack into migration-personal
            copy_tree_clean(
                FOUNDATION_DIR / "mattpocock-skills",
                mp_personal / "plugins" / "matt-pocock-skills-local",
                dry_run,
                actions,
            )
            copy_tree_clean(
                FOUNDATION_DIR / "pstack-poteto",
                mp_personal / "plugins" / "pstack-poteto-local",
                dry_run,
                actions,
            )

            # Update migration-personal marketplace manifests
            codex_mp_json = {
                "name": "personal",
                "plugins": [
                    {
                        "name": "matt-pocock-skills-local",
                        "source": {"source": "local", "path": "./plugins/matt-pocock-skills-local"},
                        "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                    },
                    {
                        "name": "pstack-poteto-local",
                        "source": {"source": "local", "path": "./plugins/pstack-poteto-local"},
                        "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                    },
                ],
            }
            claude_mp_json = {
                "name": "personal",
                "plugins": [
                    {
                        "name": "matt-pocock-skills-local",
                        "source": "./plugins/matt-pocock-skills-local",
                        "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                    },
                    {
                        "name": "pstack-poteto-local",
                        "source": "./plugins/pstack-poteto-local",
                        "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                    },
                ],
                "owner": {"name": "Three-Masters Engineering Foundation"},
            }
            actions.append(f"update {mp_personal / 'marketplace.json'} (matt-pocock-skills-local + pstack-poteto-local)")
            if not dry_run:
                (mp_personal / ".claude-plugin").mkdir(parents=True, exist_ok=True)
                (mp_personal / "marketplace.json").write_text(json.dumps(codex_mp_json, indent=2) + "\n", encoding="utf-8", newline="\n")
                (mp_personal / ".claude-plugin" / "marketplace.json").write_text(
                    json.dumps(claude_mp_json, indent=2) + "\n", encoding="utf-8", newline="\n"
                )

            # Preserve existing migration-ponytail if already present (keeps hook trusted_hash valid!)
            if (mp_ponytail / "plugins" / "ponytail").is_dir():
                actions.append(f"preserve existing {mp_ponytail / 'plugins' / 'ponytail'} (retaining hook trusted_hash)")
            else:
                copy_tree_clean(FOUNDATION_DIR / "ponytail", mp_ponytail / "plugins" / "ponytail", dry_run, actions)
                if not dry_run:
                    (mp_ponytail / "marketplace.json").write_text(
                        json.dumps(
                            {
                                "name": "ponytail",
                                "plugins": [
                                    {
                                        "name": "ponytail",
                                        "source": {"source": "local", "path": "./plugins/ponytail"},
                                        "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                                    }
                                ],
                            },
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )

            # Enable plugins in config.toml
            if cfg_path.is_file():
                orig_cfg = cfg_path.read_text(encoding="utf-8")
                new_cfg = ensure_codex_plugin_enabled(orig_cfg, "matt-pocock-skills-local@personal")
                new_cfg = ensure_codex_plugin_enabled(
                    new_cfg, "pstack-poteto-local@personal", after_key="matt-pocock-skills-local@personal"
                )
                new_cfg = ensure_codex_plugin_enabled(new_cfg, "ponytail@ponytail")
                actions.append(f"ensure plugins enabled in {cfg_path}")
                if not dry_run and new_cfg != orig_cfg:
                    cfg_path.write_text(new_cfg, encoding="utf-8", newline="\n")

            # Merge global AGENTS.md (preserving custom H1 sections such as browser recovery)
            existing_agents = agents_path.read_text(encoding="utf-8") if agents_path.is_file() else ""
            new_header = (FOUNDATION_DIR / "global-AGENTS.md").read_text(encoding="utf-8")
            merged_agents = merge_codex_agents_md(existing_agents, new_header)
            actions.append(f"update {agents_path} (preserving non-workflow user H1 sections)")
            if not dry_run:
                agents_path.write_text(merged_agents, encoding="utf-8", newline="\n")

    if target in ("all", "antigravity"):
        agy_plugins_dir = home / ".gemini" / "config" / "plugins"
        if (home / ".gemini").is_dir():
            for bname in BUNDLES:
                copy_tree_clean(FOUNDATION_DIR / bname, agy_plugins_dir / bname, dry_run, actions)

    return {
        "status": "DRY_RUN" if dry_run else "INSTALLED",
        "check": check_report,
        "actions": actions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate bundle manifests, frontmatter, and zero collisions.")
    parser.add_argument("--dry-run", action="store_true", help="Preview installation actions without writing files.")
    parser.add_argument("--target", choices=("all", "codex", "antigravity"), default="all", help="Target host(s) to install into.")
    parser.add_argument("--home", type=Path, default=Path.home(), help="User home directory (default: current user).")
    args = parser.parse_args(argv)

    if args.check:
        report = check_foundation()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    report = install(args.home.resolve(), args.target, args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
