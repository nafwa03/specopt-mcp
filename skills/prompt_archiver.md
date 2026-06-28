---
name: prompt_archiver
inputs:
  - source_dir: str
  - archive_name: str
outputs:
  - archive_path: str
model: any
temperature: 0.0
---

## Purpose
Archives prompt files from a source directory into a timestamped zip archive for version tracking and rollback.

## Behavior
1. Scans source_dir for all .md files.
2. Creates a timestamped zip archive with the given archive_name.
3. Returns the path to the created archive.
4. Preserves original files in place.

## Example
```python
skill = PromptArchiverSkill()
path = skill.execute(source_dir="./agents", archive_name="prompt_backup")
```
