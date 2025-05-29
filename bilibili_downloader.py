import subprocess
import os
# import argparse # No longer needed for command-line arguments

# --- Configuration Start ---
# Set your Bilibili video URL here
VIDEO_URL_TO_DOWNLOAD = "https://www.bilibili.com/video/BV1ghGZzhE4z/"
# Set your desired output directory here
DEFAULT_OUTPUT_DIRECTORY = "downloads"
# --- Configuration End ---

def download_bilibili_video(video_url, output_dir="downloads"):
    """
    Downloads a video from a Bilibili URL using yt-dlp.

    Args:
        video_url (str): The URL of the Bilibili video.
        output_dir (str): The directory where the video should be saved.
                          Defaults to "downloads".
    """
    if video_url == "YOUR_BILIBILI_VIDEO_URL_HERE" or not video_url:
        print("Please set the VIDEO_URL_TO_DOWNLOAD variable in the script before running.")
        return

    print(f"Attempting to download video from: {video_url}")
    print(f"Output directory: {output_dir}")

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # yt-dlp command:
    # -o specifies the output template. 
    #   %(title)s will be the video title, %(ext)s will be the file extension.
    #   We place it inside the output_dir.
    # --paths specifies the root directory for output, ensuring files go into output_dir
    # --no-warnings to suppress common warnings unless there's an error
    # --progress to show progress bar
    # You can add more yt-dlp options here if needed (e.g., for specific formats)
    command = [
        "yt-dlp",
        "--paths", output_dir,
        "-o", "%(title)s.%(ext)s",
        "--no-warnings",
        "--no-mtime",
        "--progress",
        video_url
    ]

    print(f"Executing command: {' '.join(command)}")

    try:
        # Using subprocess.run to execute the command
        # capture_output=True would capture stdout/stderr, but yt-dlp's progress bar works best directly in console
        # check=True will raise a CalledProcessError if yt-dlp returns a non-zero exit code
        process = subprocess.run(command, check=True, text=True)
        print(f"Video downloaded successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error during download: yt-dlp exited with code {e.returncode}")
        if e.stdout:
            print(f"yt-dlp stdout:\n{e.stdout}")
        if e.stderr:
            print(f"yt-dlp stderr:\n{e.stderr}")
    except FileNotFoundError:
        print("Error: yt-dlp command not found. Please ensure yt-dlp is installed and in your system's PATH.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="Download videos from Bilibili using yt-dlp.")
    # parser.add_argument("url", help="The Bilibili video URL to download.")
    # parser.add_argument("-o", "--output", default="downloads", 
    #                     help="Output directory for the downloaded video. Defaults to './downloads'.")
    # 
    # args = parser.parse_args()

    # download_bilibili_video(args.url, args.output) 
    
    # Call the download function with the configured variables
    download_bilibili_video(VIDEO_URL_TO_DOWNLOAD, DEFAULT_OUTPUT_DIRECTORY) 