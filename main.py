from src.app import Application, logger


def main():
    logger.info("Starting...")
    try:
        app = Application()
        app.execute()
    except Exception as e:
        logger.exception(e)
    logger.info("Stopped.")


if __name__ == '__main__':
    main()
