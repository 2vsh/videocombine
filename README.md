# Dashcam Video Stitcher

Automatically stitch multiple dashcam video files into one continuous video.

## Requirements

- Python 3.6+
- ffmpeg (must be installed and in your PATH)

### Installing ffmpeg

**Windows:** Download from https://ffmpeg.org/download.html or use `winget install ffmpeg`

## Usage

```bash
python dashcam_stitcher.py <source_directory> [output_file] [--dest <destination_directory>] [--force]
```

Run `python dashcam_stitcher.py --help` for the full option list.

### Examples

```bash
# Stitch all videos (creates stitched_output.mp4 in source folder)
python dashcam_stitcher.py E:\DCIM

# Specify custom output filename
python dashcam_stitcher.py E:\DCIM my_trip.mp4

# Save to a different destination folder
python dashcam_stitcher.py E:\DCIM --dest D:\Videos

# Custom filename AND destination
python dashcam_stitcher.py E:\DCIM my_trip.mp4 --dest D:\Videos

# Overwrite an existing output without being asked
python dashcam_stitcher.py E:\DCIM my_trip.mp4 --force
```

## How it works

1. If the folder you point at contains a `Movie` subfolder, the script descends into it,
   so both `E:\DCIM` and `E:\DCIM\Movie` work as the starting point
2. Scans that folder for video files (`.mp4`, `.avi`, `.mov`, `.mkv`, any capitalisation),
   plus its `Parking` subfolder — one level only, it does not recurse into other subfolders
3. Merges both sets and sorts them by filename, comparing digit runs numerically so
   `REC_2` comes before `REC_10`
4. Uses ffmpeg to concatenate them without re-encoding (fast!)
5. Creates one continuous video file

## Notes

- The script uses `-c copy` which means no re-encoding, so it's very fast
- All videos should have the same codec/resolution for best results
- Original files are not modified
- Works with DCIM/Movie structure (includes Parking subfolder)
- The output file is excluded from the scan, so re-running over the same folder
  will not fold a previous result back into the new one
- If the output already exists you are asked before it is replaced; use `--force`
  to skip the prompt. When not running interactively the script refuses rather than
  overwriting silently
- The ffmpeg file list is written to a temporary directory, never to the source
  volume, so a full or write-protected SD card is not a problem
- Exit status is `0` on success and non-zero on failure, so the script can be used
  from batch files and scheduled tasks
