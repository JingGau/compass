from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from compass_core.intake import intake_problem
from compass_core.kb import default_roots, search_markdown
from compass_core.report import load_state, render_markdown_report
from compass_core.runtime import (
    CompassRuntimeError,
    add_hypothesis,
    add_scene_fact,
    complete_action,
    conclude_session,
    confirm_session,
    decide_strategy_review,
    next_step,
    plan_action,
    record_action_result,
    reopen_session,
    start_session,
)
from compass_core.state import read_or_init_state


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    return args.handler(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="compass", description="Local-first Compass investigation harness")
    subparsers = parser.add_subparsers(dest="command")

    setup = subparsers.add_parser("setup-check", help="check local configuration and adapter readiness")
    setup.add_argument("--json", action="store_true", dest="json_output")
    setup.set_defaults(handler=handle_setup_check)

    start = subparsers.add_parser("start", help="start a controlled investigation session")
    start.add_argument("text")
    start.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    start.add_argument("--json", action="store_true", dest="json_output")
    start.set_defaults(handler=handle_start)

    confirm = subparsers.add_parser("confirm", help="confirm execution mode and unlock actions")
    confirm.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    confirm.add_argument("--mode", choices=("auto", "manual"), default="auto")
    confirm.add_argument("--json", action="store_true", dest="json_output")
    confirm.set_defaults(handler=handle_confirm)

    next_cmd = subparsers.add_parser("next", help="show the next allowed investigation step")
    next_cmd.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    next_cmd.add_argument("--json", action="store_true", dest="json_output")
    next_cmd.set_defaults(handler=handle_next)

    action = subparsers.add_parser("action", help="record controlled investigation actions")
    action_sub = action.add_subparsers(dest="action_command", required=True)
    action_plan = action_sub.add_parser("plan", help="plan an action before execution")
    action_plan.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    action_plan.add_argument("--action-id", required=True)
    action_plan.add_argument("--track", default="manual")
    action_plan.add_argument("--source", required=True)
    action_plan.add_argument("--objective", required=True)
    action_plan.add_argument("--success-criteria", required=True)
    action_plan.add_argument("--input", action="append", default=[])
    action_plan.add_argument("--gate", action="append", default=[])
    action_plan.add_argument("--json", action="store_true", dest="json_output")
    action_plan.set_defaults(handler=handle_action_plan)

    action_complete = action_sub.add_parser("complete", help="complete a planned action and create evidence")
    action_complete.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    action_complete.add_argument("--action-id", required=True)
    action_complete.add_argument("--summary", required=True)
    action_complete.add_argument("--elapsed-ms", type=int, default=0)
    action_complete.add_argument("--finding", action="append", default=[])
    action_complete.add_argument("--lead", action="append", default=[])
    action_complete.add_argument("--supports")
    action_complete.add_argument("--kind")
    action_complete.add_argument("--strength", default="medium")
    action_complete.add_argument("--raw-ref")
    action_complete.add_argument("--json", action="store_true", dest="json_output")
    action_complete.set_defaults(handler=handle_action_complete)

    action_record = action_sub.add_parser("record", help="record an executed action as evidence")
    action_record.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    action_record.add_argument("--action-id", required=True)
    action_record.add_argument("--track", default="manual")
    action_record.add_argument("--source", required=True)
    action_record.add_argument("--summary", required=True)
    action_record.add_argument("--input", action="append", default=[])
    action_record.add_argument("--gate", action="append", default=[])
    action_record.add_argument("--elapsed-ms", type=int, default=0)
    action_record.add_argument("--finding", action="append", default=[])
    action_record.add_argument("--lead", action="append", default=[])
    action_record.add_argument("--supports")
    action_record.add_argument("--kind")
    action_record.add_argument("--strength", default="medium")
    action_record.add_argument("--raw-ref")
    action_record.add_argument("--json", action="store_true", dest="json_output")
    action_record.set_defaults(handler=handle_action_record)

    evidence = subparsers.add_parser("evidence", help="manage evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_sub.add_parser("add", help="add manual evidence")
    evidence_add.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    evidence_add.add_argument("--source", required=True)
    evidence_add.add_argument("--summary", required=True)
    evidence_add.add_argument("--supports")
    evidence_add.add_argument("--kind", default="manual")
    evidence_add.add_argument("--strength", default="medium")
    evidence_add.add_argument("--raw-ref")
    evidence_add.add_argument("--json", action="store_true", dest="json_output")
    evidence_add.set_defaults(handler=handle_evidence_add)

    scene = subparsers.add_parser("scene", help="record evidence-first scene facts")
    scene_sub = scene.add_subparsers(dest="scene_command", required=True)
    scene_fact = scene_sub.add_parser("fact", help="record a scene fact before deriving hypotheses")
    scene_fact.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    scene_fact.add_argument("--category", required=True)
    scene_fact.add_argument("--name", required=True)
    scene_fact.add_argument("--value", required=True)
    scene_fact.add_argument("--source", required=True)
    scene_fact.add_argument("--evidence", action="append", default=[])
    scene_fact.add_argument("--json", action="store_true", dest="json_output")
    scene_fact.set_defaults(handler=handle_scene_fact)

    hypothesis = subparsers.add_parser("hypothesis", help="manage hypotheses derived from evidence and scene facts")
    hypothesis_sub = hypothesis.add_subparsers(dest="hypothesis_command", required=True)
    hypothesis_add = hypothesis_sub.add_parser("add", help="add or update a hypothesis with source facts/evidence")
    hypothesis_add.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    hypothesis_add.add_argument("--id", required=True, dest="hypothesis_id")
    hypothesis_add.add_argument("--statement", required=True)
    hypothesis_add.add_argument("--source-fact", action="append", default=[])
    hypothesis_add.add_argument("--source-evidence", action="append", default=[])
    hypothesis_add.add_argument("--json", action="store_true", dest="json_output")
    hypothesis_add.set_defaults(handler=handle_hypothesis_add)

    conclude = subparsers.add_parser("conclude", help="write a conclusion with evidence references")
    conclude.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    conclude.add_argument("--conclusion", required=True)
    conclude.add_argument("--evidence", action="append", default=[])
    conclude.add_argument("--confidence", choices=("low", "medium", "high"), default="medium")
    conclude.add_argument("--what", help="What happened")
    conclude.add_argument("--where", help="Where in the component/call chain")
    conclude.add_argument("--when", help="When it happened")
    conclude.add_argument("--why-technical", help="Technical root cause")
    conclude.add_argument("--why-business", help="Business trigger")
    conclude.add_argument("--blast-radius", help="Quantified blast radius")
    conclude.add_argument("--how", help="Propagation chain")
    conclude.add_argument("--inference-chain", help="One continuous evidence-backed causal chain")
    conclude.add_argument("--next-action", action="append", default=[])
    conclude.add_argument("--json", action="store_true", dest="json_output")
    conclude.set_defaults(handler=handle_conclude)

    reopen = subparsers.add_parser("reopen", help="reopen a concluded session and archive the previous conclusion")
    reopen.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    reopen.add_argument("--reason", required=True)
    reopen.add_argument("--json", action="store_true", dest="json_output")
    reopen.set_defaults(handler=handle_reopen)

    strategy = subparsers.add_parser("strategy", help="confirm whether to keep the final investigation strategy")
    strategy_sub = strategy.add_subparsers(dest="strategy_command", required=True)
    strategy_keep = strategy_sub.add_parser("keep", help="keep this session's final query strategy")
    strategy_keep.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    strategy_keep.add_argument("--memory-file", default=str(PROJECT_ROOT / "memory" / "strategy-playbooks.json"))
    strategy_keep.add_argument("--title")
    strategy_keep.add_argument("--note", default="")
    strategy_keep.add_argument("--json", action="store_true", dest="json_output")
    strategy_keep.set_defaults(handler=handle_strategy_keep)

    strategy_discard = strategy_sub.add_parser("discard", help="discard this session's final query strategy")
    strategy_discard.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    strategy_discard.add_argument("--note", default="")
    strategy_discard.add_argument("--json", action="store_true", dest="json_output")
    strategy_discard.set_defaults(handler=handle_strategy_discard)

    intake = subparsers.add_parser("intake", help="structure a natural-language incident description")
    intake.add_argument("text")
    intake.add_argument("--json", action="store_true", dest="json_output")
    intake.set_defaults(handler=handle_intake)

    kb = subparsers.add_parser("kb", help="search local markdown knowledge roots")
    kb_sub = kb.add_subparsers(dest="kb_command", required=True)
    kb_search = kb_sub.add_parser("search", help="search markdown files, including Obsidian vaults")
    kb_search.add_argument("query")
    kb_search.add_argument("--root", action="append", default=[])
    kb_search.add_argument("--limit", type=int, default=10)
    kb_search.add_argument("--json", action="store_true", dest="json_output")
    kb_search.set_defaults(handler=handle_kb_search)

    state = subparsers.add_parser("state", help="read or initialize investigation state")
    state_sub = state.add_subparsers(dest="state_command", required=True)
    state_show = state_sub.add_parser("show", help="show current investigation state")
    state_show.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    state_show.add_argument("--json", action="store_true", dest="json_output")
    state_show.set_defaults(handler=handle_state_show)

    report = subparsers.add_parser("report", help="render investigation report from state")
    report.add_argument("--state-file", default=str(PROJECT_ROOT / "memory" / "session-state.yaml"))
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--audience", choices=("technical", "business", "review"), default="technical")
    report.set_defaults(handler=handle_report)

    return parser


def handle_setup_check(args: argparse.Namespace) -> int:
    from tools.setup_check import inspect_setup, render_setup_report

    report = inspect_setup(PROJECT_ROOT)
    if args.json_output:
        print_json({"ok": True, "setup": to_plain(report)})
    else:
        print(render_setup_report(report))
    return 0


def handle_start(args: argparse.Namespace) -> int:
    state = start_session(args.state_file, args.text)
    payload = {"ok": True, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已创建排查会话：{state['session_id']}")
        print(f"阶段：{state['flow']['phase']}")
        print(f"标准化问题：{state['problem']['standard']}")
        print("下一步：运行 compass confirm --mode auto")
    return 0


def handle_confirm(args: argparse.Namespace) -> int:
    try:
        state = confirm_session(args.state_file, args.mode)
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已确认执行模式：{state['flow']['execution_mode']}")
        print(f"阶段：{state['flow']['phase']}")
    return 0


def handle_next(args: argparse.Namespace) -> int:
    payload = {"ok": True, "next": next_step(args.state_file)}
    if args.json_output:
        print_json(payload)
    else:
        print(payload["next"]["message"])
        for item in payload["next"].get("next_actions", []):
            print(f"- {item}")
    return 0


def handle_action_plan(args: argparse.Namespace) -> int:
    try:
        state, action = plan_action(
            args.state_file,
            action_id=args.action_id,
            track=args.track,
            source=args.source,
            objective=args.objective,
            success_criteria=args.success_criteria,
            action_input=parse_pairs(args.input),
            gate=parse_pairs(args.gate),
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "action": action, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已规划 action {action['action_id']}：{action['objective']}")
    return 0


def handle_action_complete(args: argparse.Namespace) -> int:
    try:
        state, evidence = complete_action(
            args.state_file,
            action_id=args.action_id,
            summary=args.summary,
            elapsed_ms=args.elapsed_ms,
            findings=args.finding,
            leads=parse_leads(args.lead),
            supports=args.supports,
            kind=args.kind,
            strength=args.strength,
            raw_ref=args.raw_ref,
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "evidence": evidence, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已完成 action {args.action_id}，生成证据 {evidence['id']}：{evidence['summary']}")
    return 0


def handle_action_record(args: argparse.Namespace) -> int:
    try:
        state, evidence = record_action_result(
            args.state_file,
            action_id=args.action_id,
            source=args.source,
            summary=args.summary,
            track=args.track,
            action_input=parse_pairs(args.input),
            gate=parse_pairs(args.gate),
            elapsed_ms=args.elapsed_ms,
            findings=args.finding,
            leads=parse_leads(args.lead),
            supports=args.supports,
            kind=args.kind,
            strength=args.strength,
            raw_ref=args.raw_ref,
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "evidence": evidence, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已记录证据 {evidence['id']}：{evidence['summary']}")
    return 0


def handle_evidence_add(args: argparse.Namespace) -> int:
    from compass_core.runtime import add_evidence

    try:
        state, evidence = add_evidence(
            args.state_file,
            source=args.source,
            summary=args.summary,
            supports=args.supports,
            kind=args.kind,
            strength=args.strength,
            raw_ref=args.raw_ref,
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "evidence": evidence, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已记录证据 {evidence['id']}：{evidence['summary']}")
    return 0


def handle_scene_fact(args: argparse.Namespace) -> int:
    try:
        state = add_scene_fact(
            args.state_file,
            category=args.category,
            name=args.name,
            value=args.value,
            source=args.source,
            evidence_ids=args.evidence,
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已记录场景事实：{args.category}.{args.name}={args.value}")
    return 0


def handle_hypothesis_add(args: argparse.Namespace) -> int:
    try:
        state = add_hypothesis(
            args.state_file,
            hypothesis_id=args.hypothesis_id,
            statement=args.statement,
            source_facts=args.source_fact,
            source_evidence=args.source_evidence,
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已记录假设 {args.hypothesis_id}：{args.statement}")
    return 0


def handle_conclude(args: argparse.Namespace) -> int:
    try:
        state = conclude_session(
            args.state_file,
            conclusion=args.conclusion,
            evidence_ids=args.evidence,
            confidence=args.confidence,
            details={
                "what": args.what or "",
                "where": args.where or "",
                "when": args.when or "",
                "why_technical": args.why_technical or "",
                "why_business": args.why_business or "",
                "blast_radius": args.blast_radius or "",
                "how": args.how or "",
                "inference_chain": args.inference_chain or "",
            },
            next_actions=args.next_action,
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"结论：{state['conclusion']['summary']}")
        print(f"可信度：{state['conclusion']['confidence']}")
        print(f"证据：{', '.join(state['conclusion']['evidence'])}")
    return 0


def handle_reopen(args: argparse.Namespace) -> int:
    try:
        state = reopen_session(args.state_file, reason=args.reason)
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print(f"已重开排查：revision={state.get('revision')}")
        print(f"原因：{args.reason}")
    return 0


def handle_strategy_keep(args: argparse.Namespace) -> int:
    try:
        state, review = decide_strategy_review(
            args.state_file,
            keep=True,
            title=args.title,
            note=args.note,
            memory_path=args.memory_file,
        )
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "strategy_review": review, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print("已保留本次最终查询策略。")
        print(f"标题：{review.get('candidate', {}).get('title', '')}")
        print(f"策略库：{args.memory_file}")
    return 0


def handle_strategy_discard(args: argparse.Namespace) -> int:
    try:
        state, review = decide_strategy_review(args.state_file, keep=False, note=args.note)
    except CompassRuntimeError as exc:
        return print_error(exc)
    payload = {"ok": True, "strategy_review": review, "state": state}
    if args.json_output:
        print_json(payload)
    else:
        print("已标记不保留本次最终查询策略。")
    return 0


def handle_intake(args: argparse.Namespace) -> int:
    result = intake_problem(args.text)
    payload = result.to_dict()
    if args.json_output:
        print_json(payload)
    else:
        print(f"场景: {payload['scene']}")
        print(f"标准化问题: {payload['standard_problem']}")
        print("下一步:")
        for item in payload["next_actions"]:
            print(f"- {item}")
    return 0


def handle_kb_search(args: argparse.Namespace) -> int:
    roots = [Path(item) for item in args.root] or default_roots(PROJECT_ROOT)
    matches = search_markdown(args.query, roots=roots, limit=args.limit)
    payload = {
        "ok": True,
        "query": args.query,
        "roots": [str(root) for root in roots],
        "matches": [match.to_dict() for match in matches],
    }
    if args.json_output:
        print_json(payload)
    else:
        for match in matches:
            print(f"{match.path}:{match.line}: {match.snippet}")
    return 0


def handle_state_show(args: argparse.Namespace) -> int:
    state = read_or_init_state(args.state_file)
    if args.json_output:
        print_json({"ok": True, "state": state})
    else:
        print_json(state)
    return 0


def handle_report(args: argparse.Namespace) -> int:
    state = load_state(args.state_file)
    report = render_markdown_report(state, audience=args.audience)
    if args.format == "json":
        print_json({"ok": True, "audience": args.audience, "report": report, "state": state})
    else:
        print(report, end="")
    return 0


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def print_error(error: Exception) -> int:
    print_json({"ok": False, "error": str(error)})
    return 1


def parse_leads(items: list[str]) -> dict[str, list[str]]:
    leads: dict[str, list[str]] = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator:
            raise SystemExit(f"--lead must be KEY=VALUE, got: {item}")
        leads.setdefault(key, []).append(value)
    return leads


def parse_pairs(items: list[str]) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator:
            raise SystemExit(f"argument must be KEY=VALUE, got: {item}")
        pairs[key] = value
    return pairs


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
