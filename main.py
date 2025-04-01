from watchdog.observers     import Observer
from watchdog.events        import FileSystemEventHandler
from os                     import getenv
from os.path                import basename
from os                     import remove
from os                     import path
from os                     import walk
from os.path                import getmtime
from time                   import sleep
from modules                import Logger
from sqlalchemy             import create_engine
from sqlalchemy.orm         import sessionmaker
from sqlalchemy.orm         import declarative_base
from sqlalchemy             import Column
from sqlalchemy             import Integer
from sqlalchemy             import String
from datetime               import datetime as dt
from base64                 import urlsafe_b64encode
from cryptography.fernet    import Fernet
from tqdm                   import tqdm
from requests_toolbelt      import MultipartEncoder
from requests_toolbelt      import MultipartEncoderMonitor
from requests               import get
from requests               import post
from concurrent.futures     import ThreadPoolExecutor
from concurrent.futures     import as_completed
from os                     import makedirs
from sqlalchemy             import Boolean
from pandas                 import DataFrame
from rich                   import print
from os                     import _exit

if __name__ == "__main__":
    log = Logger('debug')

IGNORE_PREFIXES         = ['.~lock']
LOCAL_PATH              = getenv('FJS_SIMPLE_LOCAL_PATH')
REMOTE_PATH             = getenv('FJS_SIMPLE_REMOTE_PATH')
API_KEY                 = getenv('FJS_SIMPLE_API_KEY')
API_BASE                = "https://app.filejump.com"
TEMP_FOLDER             = getenv("FJS_TEMP_FOLDER")
MAX_UPLOAD_THREADS      = 8
REMOTE_BASE             = basename(REMOTE_PATH)
FILE_ENTRIES_URL        = '/api/v1/drive/file-entries'
MAX_ENTRIES_PER_PAGE    = 50

class ApiHandler:
    def __init__(self, base_url: str, remote_path: str, api_key: str):
        self.base_url    = base_url
        self.remote_path = remote_path
        self.api_key     = api_key       

    def remote_index(self):
        log.info("Starting Remote Index...")
        folders, files = [], []
        headers        = {'Authorization': f'Bearer {API_KEY}','Content-Type':'application/json'}
        params         = {'type': 'folder', 'query': REMOTE_BASE}
        response       = get(API_BASE + FILE_ENTRIES_URL, headers=headers, params=params)
        if len(response.json()['data']) > 1:
            raise Exception('Too many results for sync folder! Name should be unique!')
        base_id = response.json()['data'][0]['id']
        parent_id = response.json()['data'][0]['id']
        folders.append(response.json()['data'][0])

        log.debug("Looping over folders")
        for folder in folders:
            log.debug(f'Processing Folder: {folder['name']}')
            page_number = 1
            parent_id = [folder['id']]
            params = {'perPage': MAX_ENTRIES_PER_PAGE, 'page': page_number, 'parentIds': parent_id}
            response = get(API_BASE + '/api/v1/drive/file-entries', headers=headers, params=params)
            for i in response.json()['data']:
                if i['type'] == 'folder':
                    folders.append(i)
                else:
                    files.append(i)
            next_page = response.json()['next_page']
            while next_page != None:
                params = params = {'perPage': MAX_ENTRIES_PER_PAGE, 'page': next_page, 'parentIds': parent_id}
                response = get(API_BASE + '/api/v1/drive/file-entries', headers=headers, params=params)
                next_page = response.json()['next_page']
                for i in response.json()['data']:
                    if i['type'] == 'folder':
                        folders.append(i)
                    else:
                        files.append(i)
        files_dataframe = DataFrame(f for f in files if f['name'].endswith('.c1'))
        folders_dataframe = DataFrame(folders)
        
        total_length = len(files_dataframe)
        log.debug(f'Found {total_length} files')
        count = 1

        log.debug("Working through files")
        remote_files = {}
        for index, row in files_dataframe.iterrows():
            try:
                log.debug(f"Processing file: {count}/{total_length}")
                file_path_str: str = row['path']
                file_path: list = file_path_str.replace("/" + str(row['id']), '')
                parents = file_path.split('/')
                index = parents.index(str(base_id))
                sub_path_folders = parents[index + 1:]
                if len(sub_path_folders) == 0:
                    string_path = REMOTE_PATH + "/" + row['name']
                    log.debug(string_path)
                else:

                    log.debug(f'Constructing Folder Path for {row["name"]}')
                    string_path = REMOTE_PATH
                    for folder in sub_path_folders:
                        log.debug('Searching for folder with ID: ' + folder)
                        folder_row = folders_dataframe.loc[folders_dataframe['id'] == int(folder)].iloc[0].to_dict()
                        string_path = string_path + "/" + folder_row['name']
                    string_path = string_path + "/" + row['name']
                    log.debug(string_path)
                remote_files[row['id']] = {'remote_path': string_path, 'info': row.to_dict()}
                count += 1

            except Exception as e:
                log.error(f"Error processing file {row['name']}: {str(e)}")
        log.info("Finished remote index")
        return remote_files



    def upload_remote_file(self, local_path):
        sleep(0.25)
        file_name = basename(local_path)
        file_size = path.getsize(local_path)
        with open(local_path, 'rb') as f:
            progress = tqdm(total=file_size,unit='B',unit_scale=True,desc=file_name,leave=False,dynamic_ncols=True,mininterval=0.01,maxinterval=0.1,smoothing=0.1,colour='green')
            last_bytes_read = 0

            def callback(monitor):
                nonlocal last_bytes_read
                new_bytes = monitor.bytes_read - last_bytes_read
                if new_bytes > 0:
                    progress.update(new_bytes)
                    last_bytes_read = monitor.bytes_read
            
            remote_path = REMOTE_PATH + str(local_path).removeprefix(TEMP_FOLDER)
            remote_path = remote_path.replace("\\", "/")
            encoder = MultipartEncoder(fields={'file': (file_name, f,'application/octet-stream'),'relativePath': (None, remote_path)})
            monitor = MultipartEncoderMonitor(encoder, callback)
            headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': monitor.content_type, 'Connection': 'keep-alive'}
            response = post(self.base_url + "/api/v1/uploads", headers=headers, data=monitor, timeout=600, stream=True)
            progress.n = file_size
            progress.close()
            if response.status_code == 201:
                log.debug("Uploaded: " + file_name)
                return True
            else:
                log.error('Failed to upload: ' + file_name)
                progress.close()
                return False
            
    def delete_remote_file(self):
        pass

    def move_remote_file(self):
        pass

    def modify_remote_file(self):
        pass
        

class DatabaseHandler:
    Base = declarative_base()
    def __init__(self, db_path="sqlite:///.fjs.db"):
        self.engine = create_engine(db_path, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.Base.metadata.create_all(self.engine)

    class FileRecord(Base):
        __tablename__       = "tbl_local_files"
        id                  = Column(Integer, primary_key=True, autoincrement=True)
        file_name           = Column(String,  nullable=False)
        file_path           = Column(String,  nullable=False)
        created_at          = Column(String,  nullable=False)
        modified_at         = Column(String,  nullable=False)
        remote_base         = Column(String,  nullable=True)
        remote_exist        = Column(Boolean, nullable=True)
        encrypted_path      = Column(String,  nullable=True)

    def reindex(self, watch_path):
        log.info("Starting re-index process")

        db_files = {record.file_path: record for record in self.session.query(self.FileRecord).all()}
        current_files = {}
        for root, _, files in walk(watch_path):
            for file in files:
                full_path = path.normpath(path.join(root, file))
                current_files[full_path] = dt.fromtimestamp(getmtime(full_path)).isoformat()

        for file_path, mod_time in current_files.items():
            if file_path not in db_files:
                remote_base = file_path.replace(LOCAL_PATH, REMOTE_PATH).replace(basename(file_path), '').replace('\\', '/')
                new_file = self.FileRecord(file_name=basename(file_path),file_path=file_path,created_at=mod_time,modified_at=mod_time, remote_base=remote_base, remote_exist=False)
                self.session.add(new_file)

        for file_path, record in db_files.items():
            if file_path in current_files:
                new_time = current_files[file_path]
                if record.modified_at != new_time:
                    record.modified_at = new_time

        for file_path in db_files.keys() - current_files.keys():
            record = db_files[file_path]
            self.session.delete(record)

        self.session.commit()
        log.info("Finished re-index process")

class EncryptionHandler:
    def __init__(self, key_string: str):
        self.key = self._generate_key_from_string(key_string)
        self.cipher_suite = Fernet(self.key)

    def _generate_key_from_string(self, key_string: str):
        key_bytes = key_string.encode('utf-8')
        return urlsafe_b64encode(key_bytes.ljust(32)[:32])

    def encrypt_file(self, input_file: str, chunk_size=8192):
        output_file = input_file.replace(LOCAL_PATH, TEMP_FOLDER) + '.voxx'
        makedirs(output_file.replace(basename(output_file), ''), exist_ok=True)
        file_size = path.getsize(input_file)
        description = "Encrypting: " + basename(input_file)
        with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout, tqdm(total=file_size, unit='B', unit_scale=True, desc=description, colour='blue') as pbar:
            while True:
                chunk = fin.read(chunk_size)
                if not chunk:
                    break
                encrypted_chunk = self.cipher_suite.encrypt(chunk)
                fout.write(encrypted_chunk)
                pbar.update(len(chunk))
        return output_file

    def decrypt_file(self, input_file: str):
        output_file = input_file.replace(TEMP_FOLDER, LOCAL_PATH)
        with open(input_file, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        remove(input_file)
        with open(output_file, 'wb') as f:
            f.write(decrypted_data)
        return output_file

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, db_handler: DatabaseHandler, encryption_handler: EncryptionHandler, api_handler = ApiHandler):
        self.db_handler = db_handler
        self.encryption_handler = encryption_handler
        self.api_handler = api_handler
        
    def chunk_file(self, file_path, chunk_size=25000000):
        chunked_files = []
        base_name = path.basename(file_path)
        output_dir = path.dirname(file_path)
        with open(file_path, 'rb') as f:
            chunk_index = 1
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                chunk_name = f"{base_name}.c{chunk_index}"
                chunk_path = path.join(output_dir, chunk_name)
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
                chunked_files.append(chunk_path)
                chunk_index += 1
        return chunked_files

    def wait_for_file(self, file_path):
        while True:
            try:
                file = open(file_path, 'rb')
                file.close()
                return
            except (OSError, IOError):
                sleep(0.25)

    def on_created(self, event):
        log.debug('New file or folder detected: ' + str(event.src_path))
        
        # If it's a folder, check for files inside it
        if event.is_directory:
            log.debug(f"Folder created: {event.src_path}")
            
            # Recursively check the contents of the folder
            for root, dirs, files in walk(event.src_path):
                for file in files:
                    file_path = path.join(root, file)
                    self.handle_file_creation(file_path)
        
        # If it's a file (not a folder), handle it directly
        elif not any(event.src_path.startswith(p) for p in IGNORE_PREFIXES):
            self.handle_file_creation(event.src_path)

    def handle_file_creation(self, file_path):
        """Handles the creation of a file, encryption, chunking, and upload."""
        log.debug("Waiting for file: " + str(file_path))
        self.wait_for_file(file_path)
        encryption_path = str(file_path).replace(LOCAL_PATH, TEMP_FOLDER) + '.voxx'
        remote_path = REMOTE_PATH + str(file_path).removeprefix(LOCAL_PATH)
        remote_path = remote_path.replace("\\", "/")
        remote_base  = remote_path.removesuffix(basename(remote_path))
        new_file = self.db_handler.FileRecord(
            file_name=basename(file_path),
            file_path=file_path,
            created_at=str(dt.now()),
            modified_at=str(dt.now()),
            remote_base=remote_base
        )
        self.db_handler.session.add(new_file)
        self.db_handler.session.commit()
        self.encryption_handler.encrypt_file(file_path)
        chunks = self.chunk_file(encryption_path)
        remove(encryption_path)

        with ThreadPoolExecutor(max_workers=MAX_UPLOAD_THREADS) as executor:
            futures = {executor.submit(self.api_handler.upload_remote_file, chunk): chunk for chunk in chunks}
            for future in as_completed(futures):
                chunk = futures[future]
                try:
                    uploaded = future.result()
                    if uploaded:
                        remove(chunk)
                        log.debug('File Uploaded: ' + chunk)
                    else:
                        log.warning('Failed to upload file: ' + chunk)
                except Exception as e:
                    log.error(f'Failed to upload {chunk} due to error {e}')


    def on_deleted(self, event):
        log.debug('File deleted: ' + str(event.src_path))
        if not event.is_directory or not any(event.src_path.startswith(p) for p in IGNORE_PREFIXES):
            file_record = (self.db_handler.session.query(self.db_handler.FileRecord).filter_by(file_path=event.src_path).first())
            if file_record:
                self.db_handler.session.delete(file_record)
                self.db_handler.session.commit()
                log.info('Deleted record from database: ' + str(event.src_path))
    
    def on_modified(self, event):
        log.debug('File modified: ' + str(event.src_path))
        if not event.is_directory or not any(event.src_path.startswith(p) for p in IGNORE_PREFIXES):
            file_record = (self.db_handler.session.query(self.db_handler.FileRecord).filter_by(file_path=event.src_path).first())
            if file_record:
                file_record.modified_at = str(dt.now())
                file_record.file_path = event.src_path
                file_record.file_name = basename(event.src_path)
                self.db_handler.session.commit()

    def on_moved(self, event):
        log.debug('File Moved: ' + str(event.src_path) + ' -> ' + str(event.dest_path))
        if not event.is_directory or not any(event.src_path.startswith(p) for p in IGNORE_PREFIXES):
            file_record = (self.db_handler.session.query(self.db_handler.FileRecord).filter_by(file_path=event.src_path).first())
            if file_record:
                file_record.file_name = basename(event.dest_path)
                file_record.file_path = event.dest_path
                file_record.modified_at = str(dt.now())
                self.db_handler.session.commit()

def main() -> None:
    encryption_handler = EncryptionHandler('5uMmlPRlbrcKowtFSxQOJ0dJHVcsrIB31kgCOtgY5KlHRgOwkBIMB4PZfs0UtHRa')
    db_handler = DatabaseHandler()
    db_handler.reindex(LOCAL_PATH)
    api_handler = ApiHandler(API_BASE, REMOTE_PATH, API_KEY)
    event_handler = FileEventHandler(db_handler, encryption_handler, api_handler)
    remote_files = api_handler.remote_index()
    #print(remote_files)
    for key, value in remote_files.items():
        remote_filename = basename(value['remote_path'])
        remote_base = str(value['remote_path']).replace(remote_filename, '')
        log.debug('Searching database for remote_base: ' + remote_base)
        file_record = db_handler.session.query(db_handler.FileRecord).filter_by(remote_base=remote_base).first()
        if file_record is None:
            log.error('FAILED TO GET FILE RECORD FOR: ' + value['info']['name'])
        else:
            log.info('File Record retrieved for: ' + value['info']['name'])
            file_record.remote_exist = True
            db_handler.session.commit()

    # Check which files don't exist on the remote and need to be uploaded
    upload_files = db_handler.session.query(db_handler.FileRecord).filter_by(remote_exist=False).all()
    for file in upload_files:
        full_path = file.file_path
        event_handler.handle_file_creation(full_path)
    
    observer = Observer()
    observer.schedule(event_handler, LOCAL_PATH, recursive=True)
    observer.start()
    
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        log.close()
        _exit(0)
        

if __name__ == "__main__":
    main()
