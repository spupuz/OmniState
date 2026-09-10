## 2024-09-10 - Symlink Traversal Bypass with cp -a
**Vulnerability:** Using `cp -a` to copy a file defeats the `mktemp` mitigation by preserving symlinks or overwriting file descriptors, allowing symlink traversal attacks.
**Learning:** `cp -a` or standard `cp` should never be used to copy contents into a secure temporary file created by `mktemp`.
**Prevention:** Use `cat "$original_file" > "$tmp_file"` to copy only the file contents without preserving symlinks or affecting file descriptors.
