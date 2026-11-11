## 2026-11-11 - Fix shell injection in entrypoint.sh su -c exec
**Vulnerability:** entrypoint.sh used `exec $*` (unquoted) inside `su omnistate -c "..."`, allowing word splitting and glob expansion of container CMD arguments. A CMD with spaces or shell metacharacters could inject commands. The non-root path correctly used `exec "$@"` (quoted), but the root path did not.
**Learning:** Always quote variable expansions in shell scripts, especially when passing user-controlled input to `su -c` or `eval`. POSIX sh has no `printf %q`, so use single-quote escaping: wrap each arg in single quotes and replace embedded single quotes with `'''`.
**Prevention:** Use single-quote escaping loop for POSIX sh compatibility. Both root and non-root paths must use the same quoting discipline.
