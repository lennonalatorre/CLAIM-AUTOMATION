import logging, sys, traceback, os
from datetime import datetime

def setup_debugger():
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"error_log_{datetime.now():%Y-%m-%d}.txt")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.error("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc_value, exc_traceback))
        print(f"\n[!] A crash occurred — see {log_file} for details.\n")

    sys.excepthook = handle_exception
    logging.info("Debugger initialized. Logs will be written to %s", log_file)
