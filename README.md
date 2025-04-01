# FileJumpSync
A folder Sync client for FileJump https://filejump.com/ to run in a Docker container.

# Current Features
One Way Synchronization.
  - File Watching and Uploading.
  - On device encryption and chunking (to get around the 50mb API limit)
  - Simple Uploader script to upload an entire folder.

# Known Issues
  - FileJump REST API Cannot handle files > 50mb
