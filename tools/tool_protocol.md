# Tool Protocol (v3)

## 每轮标准顺序

1. `session_state.read_state()`
2. `sensors.sense_flow_deviation()`
3. `context_injector.get_context()`

## 每次查询后

4. `sensors.sense_query_result()`
5. `session_state.mark_checkpoint()`

## 进入下一步前

6. （日志轨）`sensors.sense_log_track_progress()`
7. `session_state.assert_step_complete()`
8. `sensors.sense_context_size()`
9. （需要时）`compressor.compress()`
10. `session_state.advance_step()`

## 关键约束

- `assert_step_complete().ok == false` 时严禁推进。
- `sense_query_result.signal == RETRY_LIMIT` 时必须暂停并等待用户决策。
- `sense_context_size.action == COMPRESS` 时必须先压缩再继续。
