## 2026-09-16 - Fix Arbitrary File Read in sync-workflows.sh
**Vulnerability:** Symlink dereferencing via `cat "$file" > "$tmp_file"` allowed arbitrary file reads if a symlink was synced.
**Learning:** Trying to "preserve" symlinks using `cp -a` and `chmod` introduces a worse vulnerability, because `chmod` will dereference the copied symlink and change the target's permissions.
**Prevention:** The safest way to handle untrusted file syncing in shell scripts is to completely ignore symlinks using `if [ -L "$file" ]; then continue; fi`, eliminating both read and permission manipulation risks entirely.
