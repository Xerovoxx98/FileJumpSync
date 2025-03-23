from watchdog.observers import Observer
from watchdog.events    import FileSystemEventHandler
from sqlalchemy.orm     import sessionmaker
from dataclasses        import dataclass
from sqlalchemy         import create_engine
from sqlalchemy         import MetaData
from sqlalchemy         import Table
from sqlalchemy         import Column
from sqlalchemy         import Integer
from sqlalchemy         import String
from sqlalchemy         import select
from sqlalchemy         import delete
from dotenv             import load_dotenv
import niquests
import datetime
import time
import rich
import os

load_dotenv()

LOCAL_PATH =       "C:\\Users\\Xerovoxx98\\SyncFiles"
BASE_PATH =        os.path.basename(LOCAL_PATH)
DATABASE_PATH =    os.path.join(os.getenv("LOCALAPPDATA"), "FileJumpSync")
DATABASE_NAME =    'filesync.db'
REMOTE_PATH =      "/SyncFiles/DESKTOP-D8FTCGO"
BASE_URL =         os.getenv("BASE_URL")
HEADERS =          {"Authorization": f"Bearer {os.getenv('API_KEY')}"}


class Database:
    def __init__(self):
        os.makedirs(os.path.join(os.getenv("LOCALAPPDATA"), "FileJumpSync"), exist_ok=True)
        app_data_path =     os.path.join(os.getenv("LOCALAPPDATA"), "FileJumpSync")
        self.db_path =      os.path.join(app_data_path, DATABASE_NAME)
        self.engine =       create_engine(f"sqlite:///{self.db_path}")
        self.metadata =     MetaData()
        self.Session =      sessionmaker(bind=self.engine)
        self.create_tables()

    def create_tables(self):
        self.files_table = Table("files",
                                 self.metadata,
                                 Column("id", Integer, primary_key=True),
                                 Column("name", String, nullable=False),
                                 Column("url", String, nullable=False),
                                 Column("parent", String, nullable=True),
                                 Column("full_path", String, nullable=False))
        self.metadata.create_all(self.engine)

    def add_file(self, file_entry):
        with self.Session() as session:
            table = self.files_table
            insert_stmt = table.insert().values(**file_entry)
            session.execute(insert_stmt)
            session.commit()

    def get_file(self, full_path):
        with self.Session() as session:
            table = self.files_table
            select_stmt = select(table).where(table.c.full_path.ilike(full_path))
            result = session.execute(select_stmt).first()
            return result._mapping
        
    def delete_file(self, full_path):
        with self.Session() as session:
            table = self.files_table
            delete_stmt = delete(table).where(table.c.full_path.ilike(full_path))
            session.execute(delete_stmt)
            session.commit()

@dataclass
class Logger:
    log_level: str = 'error'
    def timestamp(self) -> str:
        return datetime.datetime.strftime(datetime.datetime.now(), '%d-%m-%Y %H:%M:%S')
    
    def debug(self, message):
        if self.log_level in ['debug']:
            rich.print(str(self.timestamp()) + " - [blue]DEBUG - " + message + "[/blue]")
    
    def info(self, message):
        if self.log_level in ['info', 'debug']:
            rich.print(str(self.timestamp()) + " - [green]INFO - " + message + "[/green]")

    def warning(self, message):
        if self.log_level in ['warning', 'info', 'debug']:
            rich.print(str(self.timestamp()) + " - [dark_orange]WARNING - " + message + "[/dark_orange]")

    def error(self, message):
        if self.log_level in ['error', 'warning', 'info', 'debug']:
            rich.print(str(self.timestamp()) + " - [red]ERROR - " + message + "[/red]")

log = Logger('debug')

class EventHandler(FileSystemEventHandler):
    def wait_for_file(self, file_path, retries=50, delay=2.5):
        """Wait until the file is accessible."""
        for _ in range(retries):
            try:
                with open(file_path, 'rb') as f:
                    return f.read()
            except PermissionError:
                time.sleep(delay)

    def on_created(self, event):
        content = self.wait_for_file(event.src_path)
        files = {'file': (os.path.basename(event.src_path), content),
                'relativePath': (None, REMOTE_PATH)}
        response = niquests.post(url=BASE_URL + "/uploads", headers=HEADERS, files=files)
        data = dict(response.json())['fileEntry']
        database_row = {'id': data['id'],
                        'name': data['name'],
                        'url': data['url'],
                        'parent': data['parent']['name'],
                        'full_path': data['parent']['name'] + "/" + data['name']}
        database = Database()
        database.add_file(database_row)
        log.info('File Created: ' + "'" + str(event.src_path) + "'")

    def on_deleted(self, event):
        database = Database()
        file_record = database.get_file(BASE_PATH + "/" + os.path.basename(event.src_path))
        url = BASE_URL + "/file-entries/" + str(file_record['id'] )
        response = niquests.delete(url=url, headers=HEADERS)
        if response.status_code != 200:
            log.error('Failed to delete file: ' + event.src_path)
        database.delete_file(os.path.basename(event.src_path))
        log.info('File Deleted: ' + "'" + str(event.src_path) + "'")

    def on_modified(self, event):
        log.info('File Modified: ' + "'" + str(event.src_path) + "'")
        log.warning('Modification not yet implemented. This file may be broken.')

    def on_moved(self, event):
        log.info('File Moved (1): ' + "'" + str(event.src_path) + "'")
        log.info('File Moved (2): ' + "'" + str(event.dest_path) + "'")
        log.warning('Moving not yet implemented')

def main():
    log.info('Starting FileJumpSync')
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, LOCAL_PATH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        log.info('Stopping FileJumpSync')
    observer.join()

if __name__ == "__main__":
    main()