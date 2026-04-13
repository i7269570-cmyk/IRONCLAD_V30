from colorama import init, Fore, Back, Style
import logging

init(autoreset=True)

logging.basicConfig(
    filename='autotrade.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def status_normal(msg="정상 작동 중"):
    print(Back.BLACK + Fore.WHITE + f" [정상] {msg} " + Style.RESET_ALL)
    logging.info(msg)

def status_warning(msg):
    print(Back.YELLOW + Fore.BLACK + f" [주의] {msg} " + Style.RESET_ALL)
    logging.warning(msg)

def status_error(msg):
    print(Back.RED + Fore.WHITE + f" [에러] {msg} " + Style.RESET_ALL)
    logging.error(msg)