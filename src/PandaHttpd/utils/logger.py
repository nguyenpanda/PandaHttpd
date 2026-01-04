import logging
import datetime
import sys
import re
from pathlib import Path
from typing import Optional
from nguyenpanda.swan import green, red, yellow, blue

def magenta(text: str) -> str:
    return f'\033[1;95m{text}\033[0m'

def cyan(text: str) -> str:
    return f'\033[1;96m{text}\033[0m'


class ColoredConsoleFormatter(logging.Formatter):
    
    _map = {
		logging.INFO: ('INFO', green),
		logging.WARNING: ('WARN', yellow),
		logging.DEBUG: ('DEBUG', magenta),
		logging.ERROR: ('ERROR', red),
		logging.CRITICAL: ('FATAL', red),
	}
    
    def format(self, record):
        log_time = self.formatTime(record, self.datefmt)
        message = record.getMessage()
        
        label, color = self._map.get(record.levelno, (record.levelname, lambda x: x))
        level_tag = color(f'[{label:^6}]')

        return f'[{log_time}]{level_tag} {message}'


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
        save_dir: Optional[str | Path] = None
    ):
        self.logger_name = logger_name
        
        self.save_dir = Path(save_dir) if save_dir else (Path.cwd() / 'losg')
        self.save_dir.mkdir(exist_ok=True, parents=True)

        self.log_filename = f'{datetime.datetime.now().strftime('%y%m%d-%H%M%S')}.log' \
            if file_name is None \
            else file_name
        self.log_path = self.save_dir / self.log_filename

    def setup(self):
        self._logger = logging.getLogger(self.logger_name)
        self._logger.setLevel(logging.INFO)
        self._logger.handlers = []
        self._logger.propagate = False

        fh = logging.FileHandler(self.log_path, encoding='utf-8')
        file_formatter = FileFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(file_formatter)
        self._logger.addHandler(fh)

        sh = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredConsoleFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        sh.setFormatter(console_formatter)
        self._logger.addHandler(sh)

        self._logger.info(f'Logger initialized. File: {self.log_path}')
        return self
        
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
            