# Dashcam Video Stitcher

Automatically stitch multiple dashcam video files into one continuous video.

## Requirements

- Python 3.6+
- ffmpeg (must be installed and in your PATH)

### Installing ffmpeg

**Windows:** Download from https://ffmpeg.org/download.html or use `winget install ffmpeg`

## Usage

```bash
python dashcam_stitcher.py <source_directory> [output_file] [--dest <destination_directory>]
```

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
```

## How it works

1. Recursively scans the directory for video files (.mp4, .avi, .mov, .mkv)
2. Finds videos in both main folder and Parking subfolder
3. Sorts them all chronologically by filename timestamp
4. Uses ffmpeg to concatenate them without re-encoding (fast!)
5. Creates one continuous video file

## Notes

- The script uses `-c copy` which means no re-encoding, so it's very fast
- All videos should have the same codec/resolution for best results
- Original files are not modified
- Works with DCIM/Movie structure (includes Parking subfolder)
