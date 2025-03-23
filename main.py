from watchdog.observers import Observer
from watchdog.events    import FileSystemEventHandler
from os                 import getenv
from os.path            import basename
from os                 import makedirs
from time               import sleep
import niquests         as nq

LOCAL_PATH =            getenv('FJS_SIMPLE_LOCAL_PATH')
REMOTE_PATH =           getenv('FJS_SIMPLE_REMOTE_PATH')
API_KEY =               getenv('FJS_SIMPLE_API_KEY')
API_BASE =              "https://app.filejump.com"

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

    def on_created(self, event):
        content = self.wait_for_file(event.src_path)
        files = {'file': (basename(event.src_path), content),'relativePath': (None,REMOTE_PATH)}
        headers = {'Authorization': f'Bearer {API_KEY}'} 
        response = nq.post(url=API_BASE + "/api/v1/uploads",headers=headers,files=files)
        print('File Uploaded: ' + event.src_path)
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