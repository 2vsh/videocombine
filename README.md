# Dashcam Video Stitcher

Automatically stitch multiple dashcam video files into one continuous video.

## Requirements

- Python 3.6+
- ffmpeg (must be installed and in your PATH)

### Installing ffmpeg

**Windows:** Download from https://ffmpeg.org/download.html or use `winget install ffmpeg`

## Usage

```bash
python dashcam_stitcher.py <directory> [output_file]
```

### Examples

```bash
# Stitch all videos in a folder (creates stitched_output.mp4 in that folder)
python dashcam_stitcher.py C:\DashcamFootage

# Specify custom output file
python dashcam_stitcher.py C:\DashcamFootage my_trip.mp4
```

## How it works

1. Scans the directory for video files (.mp4, .avi, .mov, .mkv)
2. Sorts them alphabetically (your timestamp format ensures chronological order)
3. Uses ffmpeg to concatenate them without re-encoding (fast!)
4. Creates one continuous video file

## Notes

- The script uses `-c copy` which means no re-encoding, so it's very fast
- All videos should have the same codec/resolution for best results
- Original files are not modified
