# Tool Protocol (v3)

## 每轮标准顺序

1. `session_state.read_state()`
2. `sensors.sense_flow_deviation()`
3. `context_injector.get_context()`

## 每个动作前

4. 构造 `action_cards.InvestigationAction`
5. 输出 `action_cards.render_before_card(action)`
6. 执行并输出对应 Safety Gate
   - SQL: `sql_gate.assess_sql_explain()` 后输出 `action_cards.render_safety_gate_card()`
   - SLS/Redis/ES/外部库: 按对应 guard 输出 Safety Gate
7. 若 Safety Gate 返回 `requires_confirmation == true`
   - 调用 `action_cards.build_pending_confirmation()`
   - 写入 `session_state.pending_confirmations`
   - 暂停，等待用户明确回复「确认执行」

未经以上步骤，禁止调用 adapter、禁止读取生产数据、禁止把查询过程事后补写。

## 每次查询后

8. 构造 `action_cards.ActionResult`
9. 输出 `action_cards.render_after_card(action, result)`
10. 将 `ActionResult.leads` 写入 `evidence_graph.EvidenceGraph`
11. `sensors.sense_query_result()`
12. `session_state.mark_checkpoint()`

## 进入下一步前

13. （日志轨）`sensors.sense_log_track_progress()`
14. `session_state.assert_step_complete()`
15. `sensors.sense_context_size()`
16. （需要时）`compressor.compress()`
17. `session_state.advance_step()`

## 关键约束

- `assert_step_complete().ok == false` 时严禁推进。
- `sense_query_result.signal == RETRY_LIMIT` 时必须暂停并等待用户决策。
- `sense_context_size.action == COMPRESS` 时必须先压缩再继续。
- `SafetyGateResult.requires_confirmation == true` 时必须暂停，用户明确确认前严禁执行。
