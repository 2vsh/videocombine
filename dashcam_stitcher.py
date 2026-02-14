import os
import sys
import subprocess
import re
import time
from pathlib import Path

def find_video_files(directory):
    """Find all video files in the directory and sort them by filename."""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.MP4', '.AVI', '.MOV', '.MKV')
    video_files = []
    
    for file in os.listdir(directory):
        # Skip hidden files and macOS metadata files
        if file.startswith('.') or file.startswith('._'):
            continue
        if file.endswith(video_extensions):
            video_files.append(file)
    
    # Sort by filename (chronological order based on timestamp)
    video_files.sort()
    return video_files

def create_concat_file(video_files, directory, concat_file_path):
    """Create a text file listing all videos for ffmpeg concat."""
    with open(concat_file_path, 'w') as f:
        for video in video_files:
            # Use absolute paths and escape special characters
            video_path = os.path.join(directory, video)
            video_path = video_path.replace('\\', '/')
            f.write(f"file '{video_path}'\n")

def get_total_size(directory, video_files):
    """Calculate total size of all video files in MB."""
    total_bytes = 0
    for video in video_files:
        video_path = os.path.join(directory, video)
        try:
            total_bytes += os.path.getsize(video_path)
        except:
            pass
    return total_bytes / (1024 * 1024)  # Convert to MB

def stitch_videos(directory, output_file, destination_folder=None):
    """Stitch all videos in the directory into one file."""
    directory = os.path.abspath(directory)
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return False
    
    # Validate destination folder if provided
    if destination_folder:
        destination_folder = os.path.abspath(destination_folder)
        if not os.path.exists(destination_folder):
            print(f"Creating destination folder: {destination_folder}")
            os.makedirs(destination_folder, exist_ok=True)
    
    print(f"Scanning directory: {directory}")
    video_files = find_video_files(directory)
    
    if not video_files:
        print("No video files found in the directory.")
        return False
    
    print(f"Found {len(video_files)} video files:")
    for i, video in enumerate(video_files[:5], 1):
        print(f"  {i}. {video}")
    if len(video_files) > 5:
        print(f"  ... and {len(video_files) - 5} more")
    
    # Calculate total size
    total_size_mb = get_total_size(directory, video_files)
    print(f"\nTotal size: {total_size_mb:.1f} MB")
    
    # Create temporary concat file
    concat_file = os.path.join(directory, 'concat_list.txt')
    create_concat_file(video_files, directory, concat_file)
    
    # Build output path
    if not output_file:
        output_file = 'stitched_output.mp4'
    
    # If output_file is just a filename (no path), use destination folder or source directory
    if not os.path.dirname(output_file):
        if destination_folder:
            output_file = os.path.join(destination_folder, output_file)
        else:
            output_file = os.path.join(directory, output_file)
    # If output_file has a path but destination_folder is specified, warn user
    elif destination_folder:
        print(f"Warning: Output file has a path specified. Ignoring destination folder.")
    
    output_file = os.path.abspath(output_file)
    
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
        print("Usage: python dashcam_stitcher.py <directory> [output_file] [--dest <destination_folder>]")
        print("\nExamples:")
        print("  python dashcam_stitcher.py C:\\DashcamFootage")
        print("  python dashcam_stitcher.py C:\\DashcamFootage output.mp4")
        print("  python dashcam_stitcher.py C:\\DashcamFootage --dest C:\\ProcessedVideos")
        print("  python dashcam_stitcher.py C:\\DashcamFootage output.mp4 --dest C:\\ProcessedVideos")
        sys.exit(1)
    
    directory = sys.argv[1]
    output_file = None
    destination_folder = None
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--dest' and i + 1 < len(sys.argv):
            destination_folder = sys.argv[i + 1]
            i += 2
        else:
            output_file = sys.argv[i]
            i += 1
    
    stitch_videos(directory, output_file, destination_folder)