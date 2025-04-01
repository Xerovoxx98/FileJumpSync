import rich
import datetime
import multiprocessing

def logger_worker(log_queue, log_file):

    level_color = {
        'DEBUG': 'blue',
        'INFO ': 'green',
        'WARNING': 'dark_orange',
        'ERROR': 'red'
    }
    
    while True:
        try:
            record = log_queue.get()
            if record is None:
                break
            timestamp, level, message = record
            formatted_message = f"{timestamp} - {level} - {message}"
            color = level_color.get(level, 'white')
            rich.print(f"[{color}]{formatted_message}[/{color}]")
            if log_file:
                with open(log_file, 'a') as f:
                    f.write(formatted_message + '\n')
        except Exception as e:
            rich.print('Logging Failed: ' + str(e))

class Logger:
    """
    A simple logger class for logging messages to the console and optionally to a file.
    Logging is performed in a separate process.
    """
    _levels = {
        "debug": 10,
        "info": 20,
        "warning": 30,
        "error": 40,
    }

    def __init__(self, log_level='error', log_file=None):
        self.log_level = log_level
        self.log_file = log_file
        self._queue = multiprocessing.Queue()
        self._process = multiprocessing.Process(target=logger_worker, args=(self._queue, log_file))
        self._process.daemon = True
        self._process.start()

    def timestamp(self) -> str:
        return datetime.datetime.strftime(datetime.datetime.now(), '%d-%m-%Y %H:%M:%S')

    def _enqueue(self, level: str, message: str):
        current_level = self._levels.get(self.log_level, 40)
        message_level = self._levels.get(level.lower(), 40)
        if message_level >= current_level:
            self._queue.put((self.timestamp(), level, message))

    def debug(self, message):
        self._enqueue('DEBUG', message)

    def info(self, message):
        self._enqueue('INFO ', message)

    def warning(self, message):
        self._enqueue('WARNING', message)

    def error(self, message):
        self._enqueue('ERROR', message)

    def close(self):
        self._queue.put(None)
        self._process.join()