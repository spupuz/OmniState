## 2024-09-09 - Caching multiple file metrics simultaneously
**Learning:** In Python scripts, performing multiple passes over the same set of files to extract different metrics (e.g. word count and chunk label) causes redundant O(N) disk I/O overhead.
**Action:** Extract all necessary metrics in a single pass during the first read and cache them in a dictionary to prevent redundant I/O operations later in the script.
