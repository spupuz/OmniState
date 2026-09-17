## 2024-05-24 - Symlink Traversal via chmod
**Vulnerability:** When copying a file with `cp -a` to a temporary location and then attempting to preserve its permissions using `chmod --reference` or similar commands (e.g. `chmod` and `chown`), if the original file is a symlink, `chmod` / `chown` dereference the symlink and modify the permissions of the symlink's target, leading to arbitrary permission manipulation.
**Learning:** Tools like `cp -a` copy the symlink itself, but subsequent operations like `chmod` on the copy may inadvertently act on the symlink target.
**Prevention:** Explicitly ignore symlinks using `if [ -L "$file" ]; then continue; fi` or `return` when performing syncing or copying of untrusted files that might involve permission modifications.
