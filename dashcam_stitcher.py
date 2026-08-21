#!/usr/bin/env python3
"""Stitch dashcam clips (driving + parking) into one continuous video with ffmpeg."""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import deque

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv')
DEFAULT_OUTPUT = 'stitched_output.mp4'
STDERR_TAIL_LINES = 200


def enable_unicode_output():
    """Keep the ✓/⚠ glyphs working when stdout is redirected on a non-UTF-8 locale."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except (ValueError, OSError):
                pass


def find_subfolder(directory, name):
    """Return the path to a subfolder, matching case-insensitively."""
    target = name.lower()
    try:
        entries = os.listdir(directory)
    except OSError:
        return None
    for entry in entries:
        if entry.lower() == target:
            path = os.path.join(directory, entry)
            if os.path.isdir(path):
                return path
    return None


def natural_key(filename):
    """Sort key that orders REC_2 before REC_10 instead of after it.

    Digit runs compare numerically and everything else compares as lowercased
    text, so both zero-padded timestamps (2024_0101_120000_F.MP4) and bare
    sequence numbers (REC_2.MP4) end up in the order the camera recorded them.
    """
    parts = re.split(r'(\d+)', filename)
    return [(0, int(part), '') if part.isdigit() else (1, 0, part.lower())
            for part in parts]


def detect_dcim_structure(directory):
    """Detect if directory is DCIM root and return Movie folder path."""
    movie_path = find_subfolder(directory, 'Movie')
    if movie_path:
        print(f"✓ Detected DCIM structure at: {directory}")
    return movie_path


def collect_videos(folder, tag, exclude):
    """Return (tag, path) pairs for video files directly inside folder."""
    found = []
    try:
        entries = os.listdir(folder)
    except OSError as exc:
        print(f"⚠ Warning: could not read {folder}: {exc}")
        return found
    for entry in entries:
        # Skip hidden files (this also covers macOS ._ metadata files)
        if entry.startswith('.'):
            continue
        path = os.path.join(folder, entry)
        if not entry.lower().endswith(VIDEO_EXTENSIONS):
            continue
        if not os.path.isfile(path):
            continue
        if os.path.realpath(path) in exclude:
            print(f"  (skipping {entry} — it is this run's output file)")
            continue
        found.append((tag, path))
    return found


def find_video_files(directory, exclude=frozenset()):
    """Find videos in the Movie folder and its Parking subfolder, oldest first."""
    movie_folder = detect_dcim_structure(directory)
    if movie_folder:
        directory = movie_folder
        print(f"✓ Processing Movie folder: {directory}")

    print(f"Scanning for driving footage in: {directory}")
    video_files = collect_videos(directory, 'driving', exclude)
    print(f"✓ Found {len(video_files)} driving footage files")

    parking_folder = find_subfolder(directory, 'Parking')
    if parking_folder:
        print(f"Scanning for parking footage in: {parking_folder}")
        parking = collect_videos(parking_folder, 'parking', exclude)
        print(f"✓ Found {len(parking)} parking footage files")
        video_files.extend(parking)
    else:
        print(f"⚠ Warning: No Parking subfolder found in {directory}")

    video_files.sort(key=lambda item: natural_key(os.path.basename(item[1])))
    return video_files


def create_concat_file(video_files, concat_file_path):
    """Write the ffmpeg concat manifest listing all videos."""
    with open(concat_file_path, 'w', encoding='utf-8') as handle:
        for _video_type, video_path in video_files:
            path = os.path.abspath(video_path)
            # The concat demuxer ends a quoted filename at the first bare
            # apostrophe, so a path like "Dan's Drive" must escape it.
            path = path.replace("'", r"'\''")
            handle.write(f"file '{path}'\n")


def get_total_size(video_files):
    """Calculate total size of all video files in MB."""
    total_bytes = 0
    for _video_type, video_path in video_files:
        try:
            total_bytes += os.path.getsize(video_path)
        except OSError as exc:
            print(f"⚠ Warning: Could not get size of {os.path.basename(video_path)}: {exc}")
    return total_bytes / (1024 * 1024)


def resolve_output_path(directory, output_file, destination_folder):
    """Work out the final output path before any scanning happens."""
    if not output_file:
        output_file = DEFAULT_OUTPUT
    if os.path.dirname(output_file):
        if destination_folder:
            print("⚠ Warning: output file already includes a path. Ignoring --dest.")
        return os.path.abspath(output_file)
    base = destination_folder or directory
    return os.path.abspath(os.path.join(base, output_file))


def confirm_overwrite(output_file, force):
    """Ask before replacing an existing output file."""
    if force or not os.path.exists(output_file):
        return True
    if not sys.stdin.isatty():
        print(f"✗ Error: '{output_file}' already exists. Re-run with --force to overwrite.")
        return False
    try:
        answer = input(f"⚠ '{output_file}' already exists. Overwrite? [y/N] ")
    except EOFError:
        answer = ''
    if answer.strip().lower() in ('y', 'yes'):
        return True
    print("Not overwriting - exiting.")
    return False


def run_ffmpeg(concat_file, output_file):
    """Run ffmpeg, echoing its progress. Returns the exit code, or None if missing."""
    cmd = [
        'ffmpeg',
        '-hide_banner',
        '-nostdin',
        '-y',
        # genpts is a demuxer flag: it only takes effect before -i.
        '-fflags', '+genpts',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        '-movflags', '+faststart',
        '-v', 'warning',
        '-stats',
        output_file,
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
        )
    except FileNotFoundError:
        return None

    tail = deque(maxlen=STDERR_TAIL_LINES)
    stats_pending = False
    for line in process.stderr:
        tail.append(line)
        text = line.rstrip('\r\n')
        if not text:
            continue
        if text.startswith(('frame=', 'size=')):
            # Progress updates overwrite in place rather than scrolling.
            print(f"  {text}", end='\r', file=sys.stderr, flush=True)
            stats_pending = True
        else:
            if stats_pending:
                print(file=sys.stderr)
                stats_pending = False
            print(f"⚠ {text}", file=sys.stderr)
    if stats_pending:
        print(file=sys.stderr)

    process.wait()
    return process.returncode, list(tail)


def stitch_videos(directory, output_file=None, destination_folder=None, force=False):
    """Stitch all videos in the directory into one file."""
    directory = os.path.abspath(directory)

    if not os.path.isdir(directory):
        if os.path.exists(directory):
            print(f"Error: '{directory}' is a file, not a directory.")
        else:
            print(f"Error: Directory '{directory}' does not exist.")
        return False

    if destination_folder:
        destination_folder = os.path.abspath(destination_folder)
        if not os.path.isdir(destination_folder):
            print(f"Creating destination folder: {destination_folder}")
            try:
                os.makedirs(destination_folder, exist_ok=True)
            except OSError as exc:
                print(f"✗ Error: could not create destination folder: {exc}")
                return False

    output_file = resolve_output_path(directory, output_file, destination_folder)

    print(f"Scanning directory: {directory}\n")
    # Exclude the output so a second run never swallows the first run's file.
    video_files = find_video_files(directory, exclude={os.path.realpath(output_file)})

    if not video_files:
        print("✗ Error: No video files found in the directory.")
        return False

    print(f"\n✓ Found {len(video_files)} total video files")
    print("First 5 files in chronological order:")
    for index, (video_type, video_path) in enumerate(video_files[:5], 1):
        print(f"  {index}. [{video_type.upper()}] {os.path.basename(video_path)}")
    if len(video_files) > 5:
        print(f"  ... and {len(video_files) - 5} more")

    total_size_mb = get_total_size(video_files)
    print(f"\nTotal size: {total_size_mb:.1f} MB")

    if not confirm_overwrite(output_file, force):
        return False

    print(f"\nStitching videos into: {output_file}")
    print("Processing...\n")

    # Keep the manifest off the source volume — SD cards are often full or
    # write-protected — and remove it even when ffmpeg never starts.
    handle = tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', prefix='dashcam_concat_', delete=False, encoding='utf-8')
    handle.close()
    concat_file = handle.name

    start_time = time.time()
    try:
        create_concat_file(video_files, concat_file)
        result = run_ffmpeg(concat_file, output_file)
    except OSError as exc:
        print(f"\n✗ Error: {exc}")
        return False
    finally:
        try:
            os.remove(concat_file)
        except OSError as exc:
            print(f"⚠ Warning: Could not remove concat file: {exc}")

    if result is None:
        print("\n✗ Error: ffmpeg not found. Please install ffmpeg first.")
        print("Download from: https://ffmpeg.org/download.html")
        return False

    returncode, stderr_tail = result
    if returncode != 0:
        print(f"\n✗ Error during stitching (exit code: {returncode})")
        print("FFmpeg error output:")
        for line in stderr_tail:
            print(f"  {line.rstrip()}")
        return False

    elapsed = int(time.time() - start_time)
    print(f"\n✓ Success! Completed in {elapsed} seconds")
    print(f"✓ Processed {len(video_files)} files")
    print(f"✓ Total size: {total_size_mb:.1f} MB")
    print(f"✓ Output: {output_file}")
    return True


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog='dashcam_stitcher.py',
        description='Stitch dashcam videos into one continuous file.',
        epilog=(
            'Examples:\n'
            '  python dashcam_stitcher.py E:\\DCIM\n'
            '  python dashcam_stitcher.py E:\\DCIM my_trip.mp4\n'
            '  python dashcam_stitcher.py E:\\DCIM --dest D:\\Videos\n'
            '  python dashcam_stitcher.py E:\\DCIM my_trip.mp4 --dest D:\\Videos\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('directory', help='folder holding the footage (DCIM root or Movie folder)')
    parser.add_argument('output_file', nargs='?', default=None,
                        help=f'output filename (default: {DEFAULT_OUTPUT})')
    parser.add_argument('--dest', dest='destination_folder', metavar='FOLDER',
                        help='folder to write the output into')
    parser.add_argument('-f', '--force', action='store_true',
                        help='overwrite the output file without asking')
    return parser.parse_args(argv)


def main(argv=None):
    enable_unicode_output()
    args = parse_args(argv)
    ok = stitch_videos(args.directory, args.output_file,
                       args.destination_folder, args.force)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
