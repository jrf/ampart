# Playlist Generator

## Overview
Python CLI tool that sets Apple Music (Music.app) playlist artwork using the album art from each playlist's first track.

## Architecture
- **`set_playlist_artwork.py`** — Single-file script, no external dependencies
- Uses JXA (JavaScript for Automation) for reading playlist metadata as JSON
- Uses AppleScript for artwork extraction and setting via `osascript` subprocess

## Key Design Decisions
- Artwork is extracted from track 1 via AppleScript `raw data` → temp file → `read as «class PICT»`
- `set data of artwork 1 of playlist` throws "error type 1" but **actually works** — the error is ignored
- `make new artwork at playlist` does NOT work (-2710) despite the SDEF claiming it should
- Filters out system/special playlists, empty playlists, and playlists where track 1 has no artwork
- `--dry-run` flag for previewing changes

## Running
```bash
python3 set_playlist_artwork.py           # update all playlists
python3 set_playlist_artwork.py --dry-run # preview only
```

## Precedence
Project-level instructions extend but do not override global `~/.claude/CLAUDE.md`.
