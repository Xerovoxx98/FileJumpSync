# INFO
There is a PR currently pending for adding support for FileJump to RClone made by: [@masrlinu](https://github.com/masrlinu)
PR: https://github.com/rclone/rclone/pull/8693

I do not currently have time to continue building this, if you are looking for an option for syncing to files to FileJump, I would recommend waiting for this.


# FileJumpSync
A folder Sync client for FileJump https://filejump.com/ to run in a Docker container.

# Current Features
One Way Synchronization.
  - File Watching and Uploading.
  - On device encryption and chunking (to get around the 50mb API limit)
  - Simple Uploader script to upload an entire folder.

# Known Issues
  - FileJump REST API Cannot handle files > 50mb
