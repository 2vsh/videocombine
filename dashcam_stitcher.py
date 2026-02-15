import os
import sys
import subprocess
import re
import time
from pathlib import Path

def detect_dcim_structure(directory):
    """Detect if directory is DCIM root and return Movie folder path."""
    # Check if this is DCIM folder with Movie subfolder
    movie_path = os.path.join(directory, 'Movie')
    if os.path.exists(movie_path) and os.path.isdir(movie_path):
        print(f"✓ Detected DCIM structure at: {directory}")
        return movie_path
    return None

def find_video_files(directory):
    """Find all video files including from Parking subfolder and sort chronologically."""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.MP4', '.AVI', '.MOV', '.MKV')
    video_files = []
    
    # Check if we're pointing to DCIM folder
    movie_folder = detect_dcim_structure(directory)
    if movie_folder:
        directory = movie_folder
        print(f"✓ Processing Movie folder: {directory}")
    
    # Collect driving footage from main Movie folder
    print(f"Scanning for driving footage in: {directory}")
    driving_count = 0
    for file in os.listdir(directory):
        # Skip hidden files, macOS metadata files, and directories
        if file.startswith('.') or file.startswith('._'):
            continue
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and file.endswith(video_extensions):
            video_files.append(('driving', file_path))
            driving_count += 1
    print(f"✓ Found {driving_count} driving footage files")
    
    # Collect parking footage from Parking subfolder
    parking_folder = os.path.join(directory, 'Parking')
    parking_count = 0
    if os.path.exists(parking_folder) and os.path.isdir(parking_folder):
        print(f"Scanning for parking footage in: {parking_folder}")
        for file in os.listdir(parking_folder):
            if file.startswith('.') or file.startswith('._'):
                continue
            file_path = os.path.join(parking_folder, file)
            if os.path.isfile(file_path) and file.endswith(video_extensions):
                video_files.append(('parking', file_path))
                parking_count += 1
        print(f"✓ Found {parking_count} parking footage files")
    else:
        print(f"⚠ Warning: No Parking subfolder found at {parking_folder}")
    
    # Sort by filename (chronological order based on timestamp in filename)
    # Extract just the filename for sorting, not the full path
    video_files.sort(key=lambda x: os.path.basename(x[1]))
    
    return video_files

def create_concat_file(video_files, concat_file_path):
    """Create a text file listing all videos for ffmpeg concat."""
    with open(concat_file_path, 'w') as f:
        for video_type, video_path in video_files:
            # Use absolute paths and escape special characters
            video_path = os.path.abspath(video_path)
            video_path = video_path.replace('\\', '/')
            f.write(f"file '{video_path}'\n")

def get_total_size(video_files):
    """Calculate total size of all video files in MB."""
    total_bytes = 0
    for video_type, video_path in video_files:
        try:
            total_bytes += os.path.getsize(video_path)
        except Exception as e:
            print(f"⚠ Warning: Could not get size of {os.path.basename(video_path)}: {e}")
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
    
    print(f"Scanning directory: {directory}\n")
    video_files = find_video_files(directory)
    
    if not video_files:
        print("✗ Error: No video files found in the directory.")
        return False
    
    print(f"\n✓ Found {len(video_files)} total video files")
    print(f"First 5 files in chronological order:")
    for i, (video_type, video_path) in enumerate(video_files[:5], 1):
        filename = os.path.basename(video_path)
        print(f"  {i}. [{video_type.upper()}] {filename}")
    if len(video_files) > 5:
        print(f"  ... and {len(video_files) - 5} more")
    
    # Calculate total size
    total_size_mb = get_total_size(video_files)
    print(f"\nTotal size: {total_size_mb:.1f} MB")
    
    # Create temporary concat file in the source directory
    source_dir = os.path.dirname(video_files[0][1])
    concat_file = os.path.join(source_dir, 'concat_list.txt')
    create_concat_file(video_files, concat_file)
    
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
            '-v', 'warning',
            '-stats',
            output_file
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   universal_newlines=True, bufsize=1)
        
        file_count = 0
        stderr_output = []
        for line in process.stderr:
            stderr_output.append(line)
            # Log when each file is being processed (works for any video extension)
            if "Opening '" in line and any(ext in line for ext in ['.mp4', '.MP4', '.avi', '.AVI', '.mov', '.MOV', '.mkv', '.MKV']):
                file_count += 1
                filename = line.split("'")[1].split('/')[-1].split('\\')[-1]
                # Determine if it's parking or driving based on filename
                file_type = 'PARKING' if 'PF.' in filename else 'DRIVING'
                print(f"[{file_count}/{len(video_files)}] Processing [{file_type}]: {filename}")
            # Show warnings and errors
            elif 'warning' in line.lower() or 'error' in line.lower():
                print(f"⚠ {line.strip()}")
        
        process.wait()
        
        # Clean up concat file
        try:
            os.remove(concat_file)
        except Exception as e:
            print(f"⚠ Warning: Could not remove concat file: {e}")
        
        if process.returncode == 0:
            elapsed = time.time() - start_time
            print(f"\n✓ Success! Completed in {int(elapsed)} seconds")
            print(f"✓ Processed {len(video_files)} files")
            print(f"✓ Total size: {total_size_mb:.1f} MB")
            print(f"✓ Output: {output_file}")
            return True
        else:
            print(f"\n✗ Error during stitching (exit code: {process.returncode})")
            print("FFmpeg error output:")
            for line in stderr_output:
                print(f"  {line.rstrip()}")
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