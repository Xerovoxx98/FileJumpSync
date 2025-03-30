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
    print(progress / 10)
    progress = progress / 10
    print(dumps({"progress": round(progress, 2), "message": f"Processed {current}/{total} files"}))
    sys.stdout.flush()

def upload_file(file_path, file_name, remote_path, api_key):
    try:
        file_size = os.path.getsize(file_path)  # Get file size for progress tracking
        
        with open(file_path, 'rb') as f:
            # Wrap the file with tqdm to track progress
            progress = tqdm(total=file_size, unit='B', unit_scale=True, desc=file_name)
            
            def callback(monitor):
                progress.update(monitor.bytes_read - progress.n)  # Update progress bar
            
            # Create MultipartEncoder
            encoder = MultipartEncoder(fields={
                'file': (file_name, f, 'application/octet-stream'),
                'relativePath': (None, remote_path + file_name)
            })

            # Wrap encoder with MultipartEncoderMonitor to track progress
            monitor = MultipartEncoderMonitor(encoder, callback)

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': monitor.content_type
            }

            # Perform the POST request
            response = requests.post(
                'https://app.filejump.com/api/v1/uploads',
                headers=headers,
                data=monitor,
                timeout=600
            )

            progress.close()  # Close progress bar

            if response.status_code == 201:
                print(f'Uploaded: {file_name}')
                return True
            else:
                print(f'Failed to upload {file_name}. Status Code: {response.status_code}')
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