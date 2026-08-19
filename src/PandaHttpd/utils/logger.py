import logging
import datetime
import sys
import re
from pathlib import Path
from typing import Any, Optional


def green(text: Any) -> str:
    return f'\033[38;5;22;48;5;157m{text}\033[0m'

def yellow(text: Any) -> str:
    return f'\033[38;5;94;48;5;229m{text}\033[0m'

def magenta(text: Any) -> str:
    return f'\033[38;5;53;48;5;225m{text}\033[0m'

def red(text: Any) -> str:
    return f'\033[38;5;88;48;5;217m{text}\033[0m'

def fatal(text: Any) -> str:
    return f'\033[38;5;52;48;5;210m{text}\033[0m'

def time_style(text: Any) -> str:
    return f'\033[38;5;23;48;5;195m{text}\033[0m'


class ColoredConsoleFormatter(logging.Formatter):
    
    _map = {
		logging.INFO: ('INFO', green),
		logging.WARNING: ('WARN', yellow),
		logging.DEBUG: ('DEBUG', magenta),
		logging.ERROR: ('ERROR', red),
		logging.CRITICAL: ('FATAL', fatal),
	}
    
    def format(self, record):
        log_time = self.formatTime(record, self.datefmt)
        message = record.getMessage()
        
        label, color = self._map.get(record.levelno, (record.levelname, lambda x: x))
        
        log_time = time_style(f'{log_time:^21}')
        level_tag = color(f'{label:^6}')

        return f'{log_time}{level_tag} {message}'


class FileFormatter(logging.Formatter):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def format(self, record):
        log_time = self.formatTime(record, self.datefmt)
        message = record.getMessage()
        
        clean_message = self.ansi_escape.sub('', message)
        
        levelname = record.levelname
        if levelname == 'CRITICAL':
            levelname = 'FATAL'
        elif levelname == 'WARNING':
            levelname = 'WARN'
            
        return f'[{log_time}][{levelname:^6}] {clean_message}'
    

class PandaLogger:
    
    def __init__(self, 
        logger_name: str = 'PandaLogger', 
        file_name: Optional[str] = None, 
        save_dir: Optional[str | Path] = None,
        level: int | str = logging.INFO,
    ):
        self.logger_name = logger_name
        
        self.save_dir = Path(save_dir) if save_dir else (Path.cwd() / 'logs')
        self.save_dir.mkdir(exist_ok=True, parents=True)

        self.log_filename = f'{datetime.datetime.now().strftime('%y%m%d-%H%M%S')}.log' \
            if file_name is None \
            else file_name
        self.log_path = self.save_dir / self.log_filename
        self.level = level
        
        self.file_formatter = None
        self.console_formatter = None

    def setup(self):
        self._logger = logging.getLogger(self.logger_name)
        self._logger.setLevel(self.level)
        self._logger.handlers = []
        self._logger.propagate = False

        fh = logging.FileHandler(self.log_path, encoding='utf-8')
        self.file_formatter = FileFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(self.file_formatter)
        self._logger.addHandler(fh)

        sh = logging.StreamHandler(sys.stdout)
        self.console_formatter = ColoredConsoleFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        sh.setFormatter(self.console_formatter)
        self._logger.addHandler(sh)

        self._logger.info(f'Logger initialized. File: {self.log_path}')
        return self
    
    def setLevel(self, level: int | str):
        self._logger.setLevel(level)
        
    def __call__(self, message: str, level: str = 'info'):
        level = level.lower()
        if level == 'error':
            self.error(message)
        elif level == 'warning':
            self.warning(message)
        else:
            self.info(message)

    def info(self, message: str):
        self._logger.info(message)

    def error(self, message: str):
        self._logger.error(message)

    def warning(self, message: str):
        self._logger.warning(message)
        
    def debug(self, message: str):
        self._logger.debug(message)
        
    def critical(self, message: str):
        self._logger.critical(message)
        
    def save(self, name: str, message: str):
        with open(self.save_dir / name, 'w') as f:
            f.write(message)
            