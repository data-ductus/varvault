import os
import logging
import tempfile


def get_logger(name, remove_existing_log_file=False):
    """Returns a logger for name that logs to a specific file."""

    class CustomFormat(logging.Formatter):
        FORMATS = {logging.INFO: logging.PercentStyle(f'%(levelname)s - %(asctime)s %(name)s - %(message)s'),
                   logging.DEBUG: logging.PercentStyle(f'%(levelname)s - %(asctime)s %(name)s - %(message)s'),
                   logging.WARNING: logging.PercentStyle(f'%(levelname)s - %(asctime)s %(name)s - %(message)s'),
                   logging.ERROR: logging.PercentStyle(f'%(levelname)s - %(asctime)s %(name)s - %(message)s'),
                   "DEFAULT": logging.PercentStyle(f'%(levelname)s - %(asctime)s %(name)s - %(message)s')}

        def __init__(self):
            default_style = CustomFormat.FORMATS["DEFAULT"]
            super(CustomFormat, self).__init__(fmt=default_style._fmt, style="%")

        def format(self, record):

            self._style = CustomFormat.FORMATS.get(record.levelno, CustomFormat.FORMATS["DEFAULT"])
            result = logging.Formatter.format(self, record)
            return result

    name = f"varvault-{name}"
    temp_file = tempfile.NamedTemporaryFile(suffix=".log")
    temp_file.close()
    temp_dir = os.path.dirname(temp_file.name)
    temp_file.name = os.path.join(temp_dir, "varvault-logs", f"{name}.log")
    try:
        os.makedirs(os.path.dirname(temp_file.name), exist_ok=True)
    except OSError:
        pass
    log_file = temp_file.name
    if remove_existing_log_file:
        try:
            os.remove(log_file)
        except:
            pass

    log = logging.getLogger(name)
    log.handlers.clear()

    formatter = CustomFormat()

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    log.addHandler(ch)

    ch = logging.FileHandler(filename=log_file)
    ch.setFormatter(formatter)
    log.addHandler(ch)

    configure_logger(log)

    log.info(f"Logger '{log.name}' created and logging to file '{log_file}'.")

    return log


def configure_logger(logger: logging.Logger, overall_level=logging.DEBUG, stream_level=logging.INFO, file_level=logging.DEBUG):
    """Configures a logger by setting the logging levels for the different handlers."""
    logger.setLevel(overall_level)

    for handler in logger.handlers:
        # FileHandler is an instance of StreamHandler so need to check FileHandler first.
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(file_level)
        elif isinstance(handler, logging.StreamHandler):
            handler.setLevel(stream_level)
