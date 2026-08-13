import logging
import signal
import time

from app.services.operations import process_next_operation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ctec.worker")
running = True


def _stop(_signum: int, _frame: object) -> None:
    global running
    running = False


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    logger.info("CTec operation worker started")
    while running:
        try:
            if not process_next_operation():
                time.sleep(1)
        except Exception:
            logger.exception("Operation polling failed")
            time.sleep(2)
    logger.info("CTec operation worker stopped")


if __name__ == "__main__":
    main()
