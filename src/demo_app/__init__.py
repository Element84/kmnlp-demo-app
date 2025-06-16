"""Demo Chainlit app."""

import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

ctx_session_id: ContextVar[str] = ContextVar("sessionid", default="none")


class ChainlitSessionIdFilter(logging.Filter):
    """Inject the `ctx_session_id` into the log record.

    This filter reads the `ctx_session_id` `ContextVar` and adds it to the log
    record. The value is expected to be set by the application using the
    Chainlit User Session ID.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Set `sessionid` on the `record`.

        This method adds the `sessionid` to the `record`.

        The method should always return `True`, indicating that the log record
        should be logged.
        """
        record.sessionid = ctx_session_id.get()
        return True


_chainlit_session_id_filter = ChainlitSessionIdFilter()


def _configure_logging() -> None:
    """Configure logging.

    This sets up logging to the console as well as a .log file in logs/.

    Since we are running the app through Chainlit and Chainlit sets up its own
    logging config (https://github.com/Chainlit/chainlit/issues/1676), we
    cannot simply override it via logging.basicConfig(). Instead, we have to
    fetch the already configured root logger and modify it.
    """
    # Create logs directory if it doesn't exist
    Path("./logs/").mkdir(exist_ok=True)

    # Generate filename with timestamp
    log_filename = (
        f"logs/app_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')}.log"
    )

    # Create and add new handlers
    file_handler = logging.FileHandler(log_filename)
    stream_handler = logging.StreamHandler()

    # Create formatter
    formatter = logging.Formatter(
        (
            "%(asctime)s - %(name)s - %(levelname)s - %(sessionid).8s - "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set formatter for both handlers
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_chainlit_session_id_filter)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(_chainlit_session_id_filter)

    # Get the root logger
    log = logging.getLogger()

    # Remove existing handlers
    for handler in log.handlers[:]:
        log.removeHandler(handler)

    # Add handlers to logger
    log.addHandler(file_handler)
    log.addHandler(stream_handler)

    # Set log level for this app
    log.setLevel(logging.DEBUG)

    # Set log levels for other talkative packages
    logging.getLogger("botocore").setLevel(logging.INFO)
    logging.getLogger("aiobotocore").setLevel(logging.INFO)
    logging.getLogger("rastervision").setLevel(logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.INFO)
    logging.getLogger("fsspec").setLevel(logging.INFO)
    logging.getLogger("rasterio").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("s3fs").setLevel(logging.INFO)


_configure_logging()
