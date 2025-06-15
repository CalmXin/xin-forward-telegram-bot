from src.app import Application, logger


def main():
    try:
        app = Application()
        app.execute()
    except Exception as e:
        logger.exception(e)


if __name__ == '__main__':
    main()
