## 2024-09-13 - Batching jq string escaping
**Learning:** Using multiple `jq -n --arg` calls sequentially to escape bash variables into JSON strings introduces significant N+1 process spawning overhead, which is particularly bad in cold-path bash scripts.
**Action:** Batch string escaping into a single `jq` execution by passing multiple `--arg` parameters and outputting a stream of escaped strings (e.g., `jq -n --arg a "$A" --arg b "$B" '$a, $b'`) and reading them simultaneously using `mapfile -t`.
