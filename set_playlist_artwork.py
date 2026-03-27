#!/usr/bin/env python3
"""
Set Music.app playlist artwork from each playlist's first track.

Iterates all user playlists in Music.app. For each playlist that has
at least one track with artwork, extracts the artwork from the first
track and sets it as the playlist's artwork.

Uses AppleScript's "set data of artwork 1" which throws an error but
actually works.
"""

import json
import os
import subprocess
import sys
import tempfile


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


def set_playlist_artwork(playlist_name: str, tmp_path: str) -> bool:
    """Extract first track's artwork and set it on the playlist.

    The "set data of artwork 1" command throws "error type 1" but
    actually works — we catch and ignore that specific error.
    """
    safe_name = playlist_name.replace("\\", "\\\\").replace('"', '\\"')

    # Step 1: Extract artwork from first track to temp file
    extract_script = f'''
    tell application "Music"
        set p to first user playlist whose name is "{safe_name}"
        set t to first track of p
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
    result = run_osascript(extract_script)
    if result != "ok":
        return False

    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
        return False

    # Step 2: Set artwork on playlist (throws error type 1 but works)
    set_script = f'''
    set imgData to read (POSIX file "{tmp_path}") as «class PICT»
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
    # Error type 1 is expected — the command works despite the error
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "error of type 1" not in stderr.lower() and "error: an error of type 1" not in stderr.lower():
            raise RuntimeError(f"osascript failed: {stderr}")

    return True


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

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name

            if set_playlist_artwork(name, tmp_path):
                print("OK")
                success_count += 1
            else:
                print("SKIP (no artwork on first track)")
                fail_count += 1

        except Exception as e:
            print(f"ERROR ({e})")
            fail_count += 1

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    print(f"\nDone. {success_count} updated, {fail_count} failed/skipped.")


if __name__ == "__main__":
    main()
