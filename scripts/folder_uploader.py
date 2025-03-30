#!/usr/bin/env -S python3 -u
from requests_toolbelt      import MultipartEncoder, MultipartEncoderMonitor
import requests
import argparse
import os
from rich import print
from json import dumps
import sys
from tqdm import tqdm

def report_progress(current, total):
    progress = (current / total) * 100 if total > 0 else 100
    print(progress / 100)
    progress = progress / 100
    print(dumps({"progress": round(progress, 2), "message": f"Processed {current}/{total} files"}))
    sys.stdout.flush()

def upload_file(file_path, file_name, remote_path, api_key):
    try:
        print(f'[blue]Starting to upload {file_name}[/blue]')
        file_size = os.path.getsize(file_path)  # Get file size for progress tracking
        
        with open(file_path, 'rb') as f:
            progress = tqdm(total=file_size, unit='B', unit_scale=True, desc=file_name, leave=True, dynamic_ncols=True)

            last_bytes_read = 0  # Track the last read byte count
            
            def callback(monitor):
                nonlocal last_bytes_read
                new_bytes = monitor.bytes_read - last_bytes_read
                if new_bytes > 0:
                    progress.update(new_bytes)
                    last_bytes_read = monitor.bytes_read

            encoder = MultipartEncoder(fields={
                'file': (file_name, f, 'application/octet-stream'),
                'relativePath': (None, remote_path + file_name)
            })

            monitor = MultipartEncoderMonitor(encoder, callback)

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': monitor.content_type
            }

            response = requests.post(
                'https://app.filejump.com/api/v1/uploads',
                headers=headers,
                data=monitor,
                timeout=600
            )

            progress.n = file_size  # Ensure progress reaches 100%
            progress.close()  # Properly close progress bar

            if response.status_code == 201:
                print(f'[green]Uploaded: {file_name}[/green]')
                return True
            else:
                print(f'[red]Failed to upload {file_name}. Status Code: {response.status_code}[/red]')
                return False
    except Exception as e:
        print(f'Error uploading {file_name}: {str(e)}')
        return False


def main(local_path, remote_path, api_key):
    print('Script Starting.')

    files = os.listdir(local_path)
    total_files = len(files)

    if total_files == 0:
        report_progress(100, 100)  # No files to process, complete instantly
        print('No files found. Exiting.')
        return

    for idx, file in enumerate(files, start=1):
        file_path = os.path.join(local_path, file)
        upload_file(file_path, file, remote_path, api_key)
        report_progress(idx, total_files)

    print('Script Finished.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple upload script for FileJump")
    parser.add_argument('-l', '--local_path', help="Local path of the files to upload")
    parser.add_argument('-r', '--remote_path', help="Remote path in FileJump cloud")
    parser.add_argument('-a', '--api_key', help='FileJump API Key')
    args = parser.parse_args()
    main(args.local_path, args.remote_path, args.api_key)