#!/usr/bin/env python3
"""
Set Music.app playlist artwork from each playlist's tracks.

For playlists with 4+ tracks that have artwork, creates a 2x2 grid
collage (like Spotify). For playlists with fewer, uses the first
track's album art.

Uses AppleScript's "set data of artwork 1" which throws an error but
actually works.
"""

import json
import os
import subprocess
import sys
import tempfile

from PIL import Image


def run_osascript(script: str, timeout: int = 30) -> str:
    """Run an AppleScript via osascript, return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip()}")
    return result.stdout.strip()


def run_jxa(script: str, timeout: int = 30) -> str:
    """Run a JXA script via osascript, return stdout."""
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"JXA failed: {result.stderr.strip()}")
    return result.stdout.strip()


def get_playlists() -> list[dict]:
    """Get all user playlists with metadata via JXA (returns clean JSON)."""
    script = """
    var music = Application("Music");
    var playlists = music.userPlaylists();
    var result = [];
    for (var i = 0; i < playlists.length; i++) {
        var p = playlists[i];
        var trackCount = 0;
        var hasArtwork = false;
        try {
            trackCount = p.tracks.length;
            if (trackCount > 0) {
                hasArtwork = p.tracks[0].artworks.length > 0;
            }
        } catch (e) {}
        result.push({
            name: p.name(),
            trackCount: trackCount,
            firstTrackHasArtwork: hasArtwork,
            specialKind: p.specialKind()
        });
    }
    JSON.stringify(result);
    """
    return json.loads(run_jxa(script))


def extract_track_artwork(playlist_name: str, track_index: int, tmp_path: str) -> bool:
    """Extract a specific track's artwork from a playlist to a temp file."""
    safe_name = playlist_name.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
    tell application "Music"
        set p to first user playlist whose name is "{safe_name}"
        set t to track {track_index + 1} of p
        set artList to artworks of t
        if (count of artList) > 0 then
            set artData to raw data of first artwork of t
        else
            return "no_artwork"
        end if
    end tell

    set outFile to POSIX file "{tmp_path}"
    try
        set fRef to open for access outFile with write permission
        set eof fRef to 0
        write artData to fRef
        close access fRef
        return "ok"
    on error errMsg
        try
            close access outFile
        end try
        return "error: " & errMsg
    end try
    '''
    result = run_osascript(script)
    return result == "ok"


def get_unique_album_indices(playlist_name: str, max_count: int = 4) -> list[int]:
    """Get track indices for up to max_count unique albums/artists in a playlist.

    Deduplicates by both album and artist so the grid shows distinct covers.
    """
    safe_name = playlist_name.replace("\\", "\\\\").replace("'", "\\'")
    script = f"""
    var music = Application("Music");
    var p = music.userPlaylists.byName('{safe_name}');
    var tracks = p.tracks();
    var seenAlbums = {{}};
    var seenArtists = {{}};
    var indices = [];
    for (var i = 0; i < tracks.length && indices.length < {max_count}; i++) {{
        try {{
            if (tracks[i].artworks.length === 0) continue;
            var album = tracks[i].album();
            var artist = tracks[i].artist();
            if (!seenAlbums[album] && !seenArtists[artist]) {{
                seenAlbums[album] = true;
                seenArtists[artist] = true;
                indices.push(i);
            }}
        }} catch(e) {{}}
    }}
    JSON.stringify(indices);
    """
    return json.loads(run_jxa(script))


def make_grid(image_paths: list[str], output_path: str, size: int = 600):
    """Create a 2x2 grid image from 4 images."""
    half = size // 2
    grid = Image.new("RGB", (size, size))
    for i, path in enumerate(image_paths):
        img = Image.open(path)
        img = img.resize((half, half), Image.LANCZOS)
        x = (i % 2) * half
        y = (i // 2) * half
        grid.paste(img, (x, y))
    grid.save(output_path, "JPEG", quality=90)


def apply_artwork(playlist_name: str, image_path: str):
    """Set artwork on a playlist. Throws error type 1 but works."""
    safe_name = playlist_name.replace("\\", "\\\\").replace('"', '\\"')
    set_script = f'''
    set imgData to read (POSIX file "{image_path}") as «class PICT»
    tell application "Music"
        set p to first user playlist whose name is "{safe_name}"
        set data of artwork 1 of p to imgData
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", set_script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "error of type 1" not in stderr.lower():
            raise RuntimeError(f"osascript failed: {stderr}")


def set_playlist_artwork(playlist_name: str, tmp_dir: str) -> bool:
    """Build artwork for a playlist and apply it.

    Uses a 2x2 grid if 4+ unique albums have artwork, otherwise
    uses the first track's artwork.
    """
    indices = get_unique_album_indices(playlist_name, max_count=4)
    if not indices:
        return False

    if len(indices) >= 4:
        # Extract 4 artworks and make a grid
        art_paths = []
        for i, track_idx in enumerate(indices[:4]):
            path = os.path.join(tmp_dir, f"art_{i}.jpg")
            if extract_track_artwork(playlist_name, track_idx, path):
                art_paths.append(path)

        if len(art_paths) == 4:
            grid_path = os.path.join(tmp_dir, "grid.jpg")
            make_grid(art_paths, grid_path)
            apply_artwork(playlist_name, grid_path)
            return True

    # Fall back to first track's artwork
    path = os.path.join(tmp_dir, "art_0.jpg")
    if extract_track_artwork(playlist_name, indices[0], path):
        apply_artwork(playlist_name, path)
        return True

    return False


def main():
    dry_run = "--dry-run" in sys.argv

    print("Fetching playlists from Music.app...")
    playlists = get_playlists()

    processable = [
        p
        for p in playlists
        if p["specialKind"] == "none"
        and p["trackCount"] > 0
        and p["firstTrackHasArtwork"]
    ]

    skipped_empty = [p for p in playlists if p["trackCount"] == 0]
    skipped_no_art = [
        p
        for p in playlists
        if p["trackCount"] > 0
        and not p["firstTrackHasArtwork"]
        and p["specialKind"] == "none"
    ]
    skipped_special = [p for p in playlists if p["specialKind"] != "none"]

    print(f"Found {len(playlists)} user playlists:")
    print(f"  {len(processable)} to update")
    if skipped_empty:
        print(f"  {len(skipped_empty)} skipped (empty)")
    if skipped_no_art:
        print(f"  {len(skipped_no_art)} skipped (first track has no artwork)")
    if skipped_special:
        print(f"  {len(skipped_special)} skipped (system/special playlists)")

    if dry_run:
        print("\n--dry-run: playlists that would be updated:")
        for p in processable:
            print(f"  - {p['name']} ({p['trackCount']} tracks)")
        return

    if not processable:
        print("Nothing to update.")
        return

    success_count = 0
    fail_count = 0

    for i, p in enumerate(processable, 1):
        name = p["name"]
        print(f"[{i}/{len(processable)}] {name}...", end=" ", flush=True)

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                if set_playlist_artwork(name, tmp_dir):
                    print("OK")
                    success_count += 1
                else:
                    print("SKIP (no artwork)")
                    fail_count += 1

        except Exception as e:
            print(f"ERROR ({e})")
            fail_count += 1

    print(f"\nDone. {success_count} updated, {fail_count} failed/skipped.")


if __name__ == "__main__":
    main()
