import requests
from tqdm import tqdm  # For progress bar

def upload_file_with_progress(url, headers, files):
    """
    Upload a file to the given URL and display the progress of the upload.

    :param url: The API endpoint to upload the file.
    :param headers: The headers to include in the request.
    :param files: The files to upload.
    :return: The response from the server.
    """
    file_data = files['file'][1]  # Extract the file content
    file_name = files['file'][0]  # Extract the file name
    relative_path = files['relativePath'][1]  # Extract the relative path

    # Create a progress bar
    with tqdm(total=len(file_data), unit='B', unit_scale=True, desc=f"Uploading {file_name}") as progress_bar:
        def progress_callback(monitor):
            progress_bar.update(monitor.bytes_read - progress_bar.n)

        # Use a custom monitor to track upload progress
        from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
        encoder = MultipartEncoder(fields={
            'file': (file_name, file_data),
            'relativePath': (None, relative_path)
        })
        monitor = MultipartEncoderMonitor(encoder, progress_callback)

        # Send the request
        headers['Content-Type'] = monitor.content_type
        response = requests.post(url, headers=headers, data=monitor)

    return response