import os
import sys
import subprocess
import re
import time
from pathlib import Path

def find_video_files(directory):
    """Find all video files in the directory and subdirectories, sort by filename."""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.MP4', '.AVI', '.MOV', '.MKV')
    video_files = []
    
    # Walk through directory and subdirectories
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Skip hidden files and macOS metadata files
            if file.startswith('.') or file.startswith('._'):
                continue
            if file.endswith(video_extensions):
                # Store full path relative to base directory
                full_path = os.path.join(root, file)
                video_files.append(full_path)
    
    # Sort by filename only (not full path) for chronological order
    video_files.sort(key=lambda x: os.path.basename(x))
    return video_files

def create_concat_file(video_files, concat_file_path):
    """Create a text file listing all videos for ffmpeg concat."""
    with open(concat_file_path, 'w') as f:
        for video_path in video_files:
            # Use absolute paths and escape special characters
            video_path = os.path.abspath(video_path).replace('\\', '/')
            f.write(f"file '{video_path}'\n")

def get_total_size(video_files):
    """Calculate total size of all video files in MB."""
    total_bytes = 0
    for video_path in video_files:
        try:
            total_bytes += os.path.getsize(video_path)
        except:
            pass
    return total_bytes / (1024 * 1024)  # Convert to MB

def stitch_videos(directory, output_file, destination_dir=None):
    """Stitch all videos in the directory into one file."""
    directory = os.path.abspath(directory)
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return False
    
    # Handle destination directory
    if destination_dir:
        destination_dir = os.path.abspath(destination_dir)
        if not os.path.exists(destination_dir):
            print(f"Error: Destination directory '{destination_dir}' does not exist.")
            return False
    
    print(f"Scanning directory: {directory}")
    video_files = find_video_files(directory)
    
    if not video_files:
        print("No video files found in the directory or subdirectories.")
        return False
    
    # Group files by type for display
    driving_files = [f for f in video_files if 'Parking' not in f]
    parking_files = [f for f in video_files if 'Parking' in f]
    
    print(f"\nFound {len(video_files)} total video files:")
    print(f"  - {len(driving_files)} driving videos")
    print(f"  - {len(parking_files)} parking videos")
    
    print("\nFirst few files (chronologically):")
    for i, video in enumerate(video_files[:5], 1):
        filename = os.path.basename(video)
        folder = "Parking" if "Parking" in video else "Movie"
        print(f"  {i}. [{folder}] {filename}")
    if len(video_files) > 5:
        print(f"  ... and {len(video_files) - 5} more")
    
    # Calculate total size
    total_size_mb = get_total_size(video_files)
    print(f"\nTotal size: {total_size_mb:.1f} MB")
    
    # Create temporary concat file
    concat_file = os.path.join(directory, 'concat_list.txt')
    create_concat_file(video_files, concat_file)
    
    # Build output path
    if not output_file:
        output_file = 'stitched_output.mp4'
    
    # Apply destination directory if specified
    if destination_dir:
        output_file = os.path.join(destination_dir, os.path.basename(output_file))
    elif not os.path.isabs(output_file):
        # If no destination and output is relative, put it in source directory
        output_file = os.path.join(directory, output_file)
    
    print(f"\nStitching videos into: {output_file}")
    print("Processing...\n")
    
    # Run ffmpeg with file-by-file logging
    start_time = time.time()
    try:
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            '-fflags', '+genpts',
            '-movflags', '+faststart',
            '-v', 'info',
            output_file
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   universal_newlines=True, bufsize=1)
        
        file_count = 0
        for line in process.stderr:
            # Log when each file is being processed
            if "Opening '" in line and ".MP4'" in line:
                file_count += 1
                filename = line.split("'")[1].split('/')[-1].split('\\')[-1]
                print(f"[{file_count}/{len(video_files)}] Processing: {filename}")
        
        process.wait()
        
        # Clean up concat file
        os.remove(concat_file)
        
        if process.returncode == 0:
            elapsed = time.time() - start_time
            print(f"\n✓ Success! Completed in {int(elapsed)} seconds")
            print(f"✓ Processed {len(video_files)} files")
            print(f"✓ Total size: {total_size_mb:.1f} MB")
            print(f"✓ Output: {output_file}")
            return True
        else:
            print(f"\n✗ Error during stitching")
            return False
            
    except FileNotFoundError:
        print("\n✗ Error: ffmpeg not found. Please install ffmpeg first.")
        print("Download from: https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dashcam_stitcher.py <source_directory> [output_file] [--dest <destination_directory>]")
        print("\nExamples:")
        print("  python dashcam_stitcher.py E:\\DCIM")
        print("  python dashcam_stitcher.py E:\\DCIM my_trip.mp4")
        print("  python dashcam_stitcher.py E:\\DCIM --dest D:\\Videos")
        print("  python dashcam_stitcher.py E:\\DCIM my_trip.mp4 --dest D:\\Videos")
        sys.exit(1)
    
    directory = sys.argv[1]
    output_file = None
    destination_dir = None
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--dest' and i + 1 < len(sys.argv):
            destination_dir = sys.argv[i + 1]
            i += 2
        else:
            output_file = sys.argv[i]
            i += 1
    
    stitch_videos(directory, output_file, destination_dir)
