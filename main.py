from watchdog.observers import Observer
from watchdog.events    import FileSystemEventHandler
from os                 import getenv
from os.path            import basename
from os.path            import exists
from os                 import makedirs
from time               import sleep
from modules            import Logger
from modules            import upload_file_with_progress
from threading          import Thread

LOCAL_PATH =            getenv('FJS_SIMPLE_LOCAL_PATH')
REMOTE_PATH =           getenv('FJS_SIMPLE_REMOTE_PATH')
API_KEY =               getenv('FJS_SIMPLE_API_KEY')
API_BASE =              "https://app.filejump.com"

log = Logger('debug')

class EventHandler(FileSystemEventHandler):
    def wait_for_file(self, file_path):
        """Wait until the file is accessible"""
        while True:
            try:
                with open(file_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                sleep(2.5)
                continue

    def upload_file(self, file_path):
        """Handle the file upload in a separate thread"""
        log.info('Starting upload for: ' + file_path)
        content = self.wait_for_file(file_path)
        path = str(file_path).removeprefix(LOCAL_PATH)
        path = path.replace('\\', '/')
        files = {'file': (basename(file_path), content), 'relativePath': (None, REMOTE_PATH + "/" + path)}
        headers = {'Authorization': f'Bearer {API_KEY}'}
        response = upload_file_with_progress(url=API_BASE + "/api/v1/uploads", headers=headers, files=files)
        if response.status_code == 201:
            log.info('File Uploaded: ' + REMOTE_PATH + "/" + path)
        else:
            log.error('Upload Failed! Error code: ' + str(response.status_code))

    def on_created(self, event):
        if not event.is_directory:
            file_path = str(event.src_path).replace('\\', '/')
            log.info('Event Triggered by File Creation: ' + file_path)
            # Start a new thread for the upload
            upload_thread = Thread(target=self.upload_file, args=(file_path,))
            upload_thread.start()

    def on_modified(self, event):
        if not event.is_directory:
            file_path = str(event.src_path).replace('\\', '/')
            log.info('Event Triggered by File Modification: ' + file_path)
            # Start a new thread for the upload
            upload_thread = Thread(target=self.upload_file, args=(file_path,))
            upload_thread.start()

def main():
    makedirs(LOCAL_PATH, exist_ok=True)
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, LOCAL_PATH, recursive=True)
    observer.start()

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()