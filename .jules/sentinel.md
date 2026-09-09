## 2024-05-18 - JSON Injection in Bash Heredoc
**Vulnerability:** Bash command substitution inside a JSON here-doc (`cat << ENDJSON`) using `$(jq -n ...)` was susceptible to evaluation hangs and incorrect quoting when the input string contained unescaped quotes or backslashes.
**Learning:** Directly injecting command output into a JSON here-doc stream can lead to evaluation issues or JSON injection if the substituted variable is not securely escaped beforehand. `jq` processes variables safely but its evaluation inside a heredoc can cause race conditions or parsing errors.
**Prevention:** Always pre-escape dynamic shell variables using `jq -n --arg var "$VALUE" '$var'` *before* constructing the here-doc string, and inject the pre-escaped variable directly to prevent evaluation issues and ensure deterministic JSON syntax.

## 2024-05-18 - JSON Injection in sync-workflows.sh
**Vulnerability:** Filenames were being directly injected into a manually constructed JSON string (`printf '        "%s",\n'`) without escaping backslashes or double quotes, allowing potential JSON syntax breakage or injection.
**Learning:** When manually constructing JSON in Bash using `printf` or here-docs, all user-controlled data (like filenames) must have backslashes and double quotes explicitly escaped using parameter expansion (`${var//\\/\\\\}`, `${var//\"/\\\"}`) before inclusion.
**Prevention:** Always sanitize strings using Bash parameter expansion prior to injection into manually formatted JSON payloads.
