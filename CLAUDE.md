# ampart

## Overview
Python CLI tool that sets Apple Music (Music.app) playlist artwork using album art from each playlist's tracks. Creates a Spotify-style 2x2 grid from the first 4 unique albums, or falls back to the first track's artwork for smaller playlists.

## Architecture
- **`set_playlist_artwork.py`** — Single-file script, requires Pillow
- Uses JXA (JavaScript for Automation) for reading playlist metadata as JSON
- Uses AppleScript for artwork extraction and setting via `osascript` subprocess
- Uses Pillow for 2x2 grid compositing

## Key Design Decisions
- Artwork is extracted from tracks via AppleScript `raw data` → temp file → `read as «class PICT»`
- `set data of artwork 1 of playlist` throws "error type 1" but **actually works** — the error is ignored
- `make new artwork at playlist` does NOT work (-2710) despite the SDEF claiming it should
- Deduplicates by album name so the grid shows 4 distinct covers
- Playlists with <4 unique albums with artwork get the first track's art instead of a grid
- Filters out system/special playlists, empty playlists, and playlists where track 1 has no artwork
- `--dry-run` flag for previewing changes

## Running
```bash
python3 set_playlist_artwork.py           # update all playlists
python3 set_playlist_artwork.py --dry-run # preview only
```

## Precedence
Project-level instructions extend but do not override global `~/.claude/CLAUDE.md`.
