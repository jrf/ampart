# Playlist Generator

Set Apple Music playlist artwork using the album art from each playlist's first track.

## Requirements

- macOS with Music.app
- Python 3.10+
- No external dependencies

## Usage

Preview what would be updated:

```bash
python3 set_playlist_artwork.py --dry-run
```

Update all playlists:

```bash
python3 set_playlist_artwork.py
```

## What It Does

1. Fetches all user playlists from Music.app
2. Skips empty playlists, system playlists, and playlists where the first track has no artwork
3. For each remaining playlist: extracts the first track's album art and sets it as the playlist artwork

## Notes

- Duplicate playlist names: if two playlists share a name, only the first is updated
- The `set data of artwork 1` command reports an error but actually works — this is expected
