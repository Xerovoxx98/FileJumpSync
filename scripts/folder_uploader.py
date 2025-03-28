#!/usr/bin/env -S python3 -u
from requests_toolbelt      import MultipartEncoder
import requests
import argparse
import os


def upload_file(file_path, file_name, remote_path, api_key):
    try:
        with open(file_path, 'rb') as f:
            # Create a MultipartEncoder to stream the file
            encoder = MultipartEncoder(fields={
                'file': (file_name, f, 'application/octet-stream'),
                'relativePath': (None, remote_path + file_name)
            })

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': encoder.content_type  # Set the content type to multipart
            }

            # Perform the POST request with the encoder, which streams the file
            response = requests.post(
                'https://app.filejump.com/api/v1/uploads',
                headers=headers,
                data=encoder,
                timeout=600  # Timeout set to 10 minutes
            )

            if response.status_code == 201:
                print(f'Uploaded: {file_name}')
            else:
                print(f'Failed to upload {file_name}. Status Code: {response.status_code}')
    except Exception as e:
        print(f'Error uploading {file_name}: {str(e)}')

def main(local_path, remote_path, api_key):
    print('Script Starting.')

    # Loop through files in the specified backup directory
    for file in os.listdir(local_path):
        file_path = os.path.join(local_path, file)
        print(f'Uploading: {file_path}')
        upload_file(file_path, file, remote_path, api_key)

    print('Script Finished.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple upload script for FileJump")
    parser.add_argument('-l', '--local_path', help="Local path of the files to upload")
    parser.add_argument('-r', '--remote_path', help="Remote path in FileJump cloud")
    parser.add_argument('-a', '--api_key', help='FileJump API Key')
    args = parser.parse_args()
    main(args.local_path, args.remote_path, args.api_key)