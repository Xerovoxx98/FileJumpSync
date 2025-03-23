import rich
import datetime

class Logger:
    """
    A simple logger class for logging messages to the console and optionally to a file.
    """
    def __init__(self, log_level='error', log_file=None):
        self.log_level = log_level
        self.log_file = log_file

    def timestamp(self) -> str:
        """Generate a timestamp for log messages."""
        return datetime.datetime.strftime(datetime.datetime.now(), '%d-%m-%Y %H:%M:%S')

    def _log_to_file(self, message):
        """Write a log message to the log file if logging to a file is enabled."""
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(message + '\n')

    def debug(self, message):
        """Log a debug-level message."""
        if self.log_level in ['debug']:
            formatted_message = f"{self.timestamp()} - DEBUG - {message}"
            rich.print(f"[blue]{formatted_message}[/blue]")
            self._log_to_file(formatted_message)

    def info(self, message):
        """Log an info-level message."""
        if self.log_level in ['info', 'debug']:
            formatted_message = f"{self.timestamp()} - INFO - {message}"
            rich.print(f"[green]{formatted_message}[/green]")
            self._log_to_file(formatted_message)

    def warning(self, message):
        """Log a warning-level message."""
        if self.log_level in ['warning', 'info', 'debug']:
            formatted_message = f"{self.timestamp()} - WARNING - {message}"
            rich.print(f"[dark_orange]{formatted_message}[/dark_orange]")
            self._log_to_file(formatted_message)

    def error(self, message):
        """Log an error-level message."""
        if self.log_level in ['error', 'warning', 'info', 'debug']:
            formatted_message = f"{self.timestamp()} - ERROR - {message}"
            rich.print(f"[red]{formatted_message}[/red]")
            self._log_to_file(formatted_message)