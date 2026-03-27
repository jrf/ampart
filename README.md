# ampart

Set Apple Music playlist artwork automatically — Spotify-style 2x2 grid from album art, or single cover for smaller playlists.

![Example](vgm.png)

## Requirements

- macOS with Music.app
- Python 3.10+
- Pillow (`pip install -r requirements.txt`)

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
2. For each playlist with 4+ unique albums: creates a 2x2 grid collage
3. For playlists with fewer: uses the first track's album art
4. Sets the result as the playlist artwork

## Notes

- Duplicate playlist names: if two playlists share a name, only the first is updated
- The `set data of artwork 1` command reports an error but actually works — this is expected
- Albums are deduplicated so the grid shows 4 distinct covers
