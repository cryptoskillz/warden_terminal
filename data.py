import ast
import os
import sys
import subprocess
import emoji
import pickle
import urwid

from requests.api import request
import pyfiglet

import pyttsx3
import logging
from tabulate import tabulate
from random import randrange

from datetime import datetime, timedelta
from dateutil import parser

from connections import test_tor, tor_request
from ansi_management import (warning, success, error, info, bold, jformat,
                             muted, time_ago, cleanfloat, yellow)

from pricing_engine import multiple_price_grab, GBTC_premium, fxsymbol


def data_tor(tor=None):
    from node_warden import load_config
    config = load_config(quiet=True)
    if not tor:
        tor = test_tor()

    import socket
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = 'Error getting local IP'

    if not config['MAIN'].getboolean('hide_private_info'):
        tor_string = f"""   {success('TOR Connected')}
    Running on port {info(bold(tor['port']))}
    Tor IP Address {warning(tor['post_proxy']['origin'])}
    Ping Time {tor['post_proxy_ping']}
    Global IP Address {warning(tor['pre_proxy']['origin'])}
    Ping Time {muted(tor['pre_proxy_ping'])}
    Local IP Address {warning(local_ip)}
    """
    else:
        tor_string = f"""   {success('TOR Connected')}
    Running on port {info(bold(tor['port']))}
    Tor IP Address {yellow('** HIDDEN **')}
    Ping Time {tor['post_proxy_ping']}
    Global IP Address {yellow('** HIDDEN **')}
    Ping Time {muted(tor['pre_proxy_ping'])}
    Local IP Address {yellow('** HIDDEN **')}
    """
    return (tor_string)


def data_login():
    tabs = []
    processes = subprocess.check_output("last")
    processes = list(processes.splitlines())
    for process in processes:
        try:
            process = process.decode("utf-8")
            if 'still' not in process or 'boot' in process:
                continue
            user = process.split()[0]
            process = process.replace(user, '')
            console = process.split()[0]
            process = process.replace(console, '')
            date_str = parser.parse(process, fuzzy=True)
            # Check if someone logged in the last 60 minutes
            expiration = 60
            too_soon = datetime.now() - timedelta(minutes=expiration)
            if date_str > too_soon:
                warn = warning(emoji.emojize(':warning:'))
                tabs.append([
                    f" {warn} {error(f'Recent Login (last {expiration} min)')}:"
                ])
            tabs.append([
                f"   {warning(user)} at {muted(console)} " + bold(
                    f"logged on {success(date_str.strftime('%H:%M (%b-%d)' ))}"
                )
            ])
        except Exception:
            tabs.append([f"  {process}"])
    if tabs != []:
        tabs = tabulate(tabs,
                        headers=['Users Logged in to this computer'],
                        colalign=["left"])
    else:
        tabs = muted(
            'List of users logged in to this computer is empty.\nEither no outside users are logged in or login info is not available.'
        )

    return (tabs)


def btc_price_data():
    price_data = multiple_price_grab('BTC', 'USD')
    return (price_data)


def data_large_price():
    from node_warden import load_config
    config = load_config(quiet=True)
    ft_config = config['MAIN']
    font = ft_config.get('large_text_font')
    btc = btc_price_data()
    try:
        btc_price = cleanfloat(btc['DISPLAY']['BTC']['USD']['PRICE'])
    except Exception:
        return (error(' >> Error getting price data. Retrying...'))
    custom_fig = pyfiglet.Figlet(font=font)
    return_fig = custom_fig.renderText('$  ' + jformat(btc_price, 0))
    return_fig = yellow(return_fig)

    chg_str = btc['DISPLAY']['BTC']['USD']['CHANGEPCTDAY']
    chg = cleanfloat(chg_str)
    msg = '\n'

    if chg >= 0:
        msg += success(f'24hr Change: +{chg_str}%\n')
    if chg > 5:
        msg += (info("[NgU] ") + muted(f"Looks like Bitcoin is pumping ") +
                emoji.emojize(":rocket:"))

    if chg < 0:
        msg += error(f'24hr Change: {chg_str}%\n')
    if chg < -5:
        msg += muted(
            f"Bitcoin dropping? Buy the dip!\nTime to stack some sats. ")

    return_fig = muted(return_fig)
    return_fig += msg

    return (return_fig)


def data_btc_price():
    from node_warden import launch_logger
    launch_logger()

    from node_warden import load_config
    config = load_config(quiet=True)
    fx_config = config['CURRENCIES']
    currencies = ast.literal_eval(fx_config.get('fx_list'))
    primary_fx = ast.literal_eval(fx_config.get('primary_fx'))
    price_data = multiple_price_grab('BTC', ','.join(currencies))
    # Get prices in different currencies
    tabs = []
    btc_usd_price = 0
    for fx in currencies:
        try:
            try:
                price_str = price_data['RAW']['BTC'][fx]['PRICE']
                price_str = fxsymbol(fx) + jformat(price_str, 2)
                high = price_data['RAW']['BTC'][fx]['HIGHDAY']
                high = fxsymbol(fx) + jformat(high, 0)
                low = price_data['RAW']['BTC'][fx]['LOWDAY']
                low = fxsymbol(fx) + jformat(low, 0)
            except Exception:
                price_str = price_data['DISPLAY']['BTC'][fx]['PRICE']
                high = price_data['DISPLAY']['BTC'][fx]['HIGHDAY']
                low = price_data['DISPLAY']['BTC'][fx]['LOWDAY']

            chg_str = price_data['DISPLAY']['BTC'][fx]['CHANGEPCTDAY']
            last_up_str = price_data['DISPLAY']['BTC'][fx]['LASTUPDATE']
            market = muted(price_data['DISPLAY']['BTC'][fx]['LASTMARKET'])
            try:
                chg = float(chg_str)
                if chg >= 0:
                    chg_str = success('+' + chg_str + '%')
                elif chg < 0:
                    chg_str = error(chg_str + '%')
            except Exception:
                chg_str = muted(chg_str + '%')

            if fx == 'USD':
                btc_usd_price = cleanfloat(price_str)

            if fx == primary_fx:
                fx = info(fx)
            tabs.append([
                u'  ' + fx, price_str, chg_str, low + ' - ' + high, market,
                last_up_str
            ])

        except Exception as e:
            tabs.append(['error: ' + str(e)])

    if tabs == []:
        return (
            error(' >> Error getting data from CryptoCompare. Retrying...'))

    try:
        tabs = tabulate(
            tabs,
            headers=[
                'Fiat', 'Price', '% change', '24h Range', 'Source',
                'Last Update'
            ],
            colalign=["center", "right", "right", "center", "center", "right"])
    except Exception:
        return (
            error(' >> Error getting data from CryptoCompare. Retrying...'))

    # GBTC
    gbtc_config = config['STOCKS']
    try:
        if gbtc_config.getboolean('GBTC_enabled'):
            tabs += '\n\n'
            gbtc_url = 'https://finnhub.io/api/v1/quote?symbol=GBTC&token=bvfhuqv48v6rhdtvnks0'
            gbtc_data = tor_request(gbtc_url).json()
            gbtc_tabs = []
            GBTC_shares = gbtc_config.getfloat('gbtc_shares')
            fairvalue, premium = (GBTC_premium((gbtc_data['c']), btc_usd_price,
                                               GBTC_shares))

            if premium * 1 > 0:
                premium = success('+' + jformat(premium, 2, 0.01) + '%')
            elif premium * 1 < 0:
                premium = error(jformat(premium, 2, 0.01) + '%')

            fairvalue = jformat(fairvalue, 2)

            chg_str = gbtc_data['c'] / gbtc_data['pc']
            try:
                chg = (chg_str)
                if chg > 0:
                    chg_str = success('+' + jformat(chg, 2) + ' %')
                elif chg < 0:
                    chg_str = error(jformat(chg, 2) + ' %')
            except Exception:
                chg_str = muted(chg_str)

            gbtc_tabs.append([
                'GBTC',
                jformat(gbtc_data['c'], 2), chg_str,
                jformat(gbtc_data['l'], 2) + ' - ' +
                jformat(gbtc_data['h'], 2), premium, fairvalue,
                time_ago(gbtc_data['t'])
            ])
            gbtc_tabs = tabulate(gbtc_tabs,
                                 headers=[
                                     'Ticker', 'Price', '%', '24h', 'Premium',
                                     'Fair', 'Update'
                                 ],
                                 colalign=[
                                     "center", "right", "right", "center",
                                     "right", "right", "right"
                                 ])
            tabs += gbtc_tabs

    except Exception as e:
        er_st = error(f' Error getting GBTC data: {e}')
        tabs += er_st

    tabs += (
        f"\n\n Last Refresh on: {info(datetime.now().strftime('%H:%M:%S'))}")
    return tabs


def data_sys():
    tabs = []
    os_info = pickle_it('load', 'os_info.pkl')
    umbrel = pickle_it('load', 'umbrel.pkl')
    # Get OS info
    tabs.append([
        " OS / System",
        os_info["uname"].sysname + ' / ' + os_info["uname"].machine
    ])
    if os_info["rpi"] != 'Not a Raspberry Pi':
        tabs.append([" Raspberry Pi", os_info["rpi"][0]])
    if umbrel:
        tabs.append([" Umbrel Node found @", 'http://umbrel.local/'])

    try:
        import psutil
        last_boot = psutil.boot_time()
        tabs.append(
            ["  Last Boot Time",
             time_ago(datetime.fromtimestamp(last_boot))])

    except Exception:
        pass

    try:
        if os_info["rpi"] != 'Not a Raspberry Pi':
            messages = raspi_get_throttled()
            for message in messages:
                logging.info(info('[POWER] ') + message)
    except Exception:
        pass

    tabs = tabulate(tabs, colalign=["left", "right"])

    tabs += '\n\nSystem Resources\n----------------'

    # Get current size of window
    rows, columns = subprocess.check_output(['stty', 'size']).split()
    bar_size = int(int(columns) / 3) - 35

    # Create CPU Temperature Bar
    try:
        import psutil
        temp_result = psutil.sensors_temperatures()
        temp_result = round(temp_result['cpu_thermal'][0].current, 2)
        # RPI temperature guidelines:
        # https://www.raspberrypi.org/documentation/faqs/#pi-performance
        temp_bar = printProgressBar(
            iteration=temp_result,
            total=80,
            prefix='CPU Temperature',
            suffix=
            f'{temp_result}°C\n                 (ideal range = 0°C to 70°C)',
            length=bar_size,
            unit='°C',
            perc=False,
            printEnd='',
            max_min=(0, 70))
        tabs += f'\n{temp_bar}'
    except Exception:
        pass

    # Create CPU Usage Bar
    try:
        import psutil
        cpu_result = psutil.cpu_percent(interval=0.1)
        cpu_result = round(cpu_result, 2)
        cpu_bar = printProgressBar(iteration=cpu_result,
                                   total=100,
                                   prefix='CPU Usage      ',
                                   suffix=f'{cpu_result}%',
                                   length=bar_size,
                                   perc=True,
                                   printEnd='',
                                   max_min=(0, 85))

    except Exception:
        cpu_bar = warning('[i] Could not retrieve CPU Usage')

    tabs += f'\n{cpu_bar}'

    # Create Memory Usage Bar
    try:
        import psutil
        mem_result = psutil.virtual_memory()
        mem_bar = printProgressBar(
            iteration=round(mem_result.percent, 2),
            total=100,
            prefix='Memory Usage   ',
            suffix=
            f'{round(mem_result.percent, 2)}%\n                 Total Memory {round(mem_result.total/1000000000,0)} GB',
            length=bar_size,
            perc=True,
            printEnd='',
            max_min=(0, 85))

    except Exception:
        mem_bar = warning('[i] Could not retrieve Memory Usage')

    tabs += f'\n{mem_bar}'

    # Create Disk Usage Bar(s)
    # Get list of devices
    tabs += '\n\nStorage\n---------------'
    try:
        import shutil
        partitions = ['/', '/mnt/data', 'mnt/hdd']

        for partition in partitions:
            try:
                total, used, free = shutil.disk_usage(partition)
                # Get partition name and truncate / fix size
                prefix = str(partition)
                prefix = '{:<15}'.format(prefix[:15])
                perc_c = 100 - ((free / total) * 100)
                disk_bar = printProgressBar(
                    iteration=round(perc_c, 2),
                    total=100,
                    prefix=prefix,
                    suffix=
                    (f'{round(perc_c, 2)}%' +
                     f'\n                 {round(free / (10**9), 2)} GB available of {round(total / (10 ** 9), 2)} GB'
                     ),
                    length=bar_size,
                    perc=True,
                    printEnd='',
                    max_min=(0, 90))

                tabs += f'\n{disk_bar}'

            except Exception:
                pass

    except Exception:
        disk_bar = warning('[!] Could not retrieve Disk Usage')

    return (tabs)


# Print progress bar
def printProgressBar(iteration,
                     total,
                     prefix='',
                     suffix='',
                     decimals=2,
                     length=100,
                     fill='█',
                     unit='%',
                     perc=True,
                     max_min=None,
                     printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        unit        - Optional  : Unit of account (Str)
        perc        - Optional  : True to display percentages, False in absolutes (Bool)
        max_min     - Optional  : Tuple with max and min values to warn (Tuple)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    if perc:
        percent = ("{0:." + str(decimals) + "f}").format(
            100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        if max_min is not None:
            if iteration > max_min[1] or iteration < max_min[0]:
                prefix = error(prefix)
                bar = warning(bar)
            else:
                prefix = success(prefix)
                bar = success(bar)
        return (f'{prefix} |{bar}| {suffix} {printEnd}')

    else:
        percent = ("{0:." + str(decimals) + "f}").format((iteration))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        if max_min is not None:
            if iteration > max_min[1] or iteration < max_min[0]:
                prefix = error(prefix)
                bar = warning(bar)
            else:
                prefix = success(prefix)
                bar = success(bar)
        return (f'{prefix} |{bar}| {suffix} {printEnd}')


def data_mempool():
    from node_warden import load_config
    from node_warden import launch_logger
    launch_logger()

    config = load_config(quiet=True)
    mp_config = config['MEMPOOL']
    url = mp_config.get('url')
    tabs = []

    # Get recommended fees
    forced_mps = False
    try:
        mp_fee = tor_request(url + '/api/v1/fees/recommended').json()
    except Exception:
        try:
            url = 'http://mempool.space'
            mp_fee = tor_request(url + '/api/v1/fees/recommended').json()
            forced_mps = True
        except Exception as e:
            return (
                error(f' >> Error getting data from {url}. Retrying... {e}'))

    tabs = list(mp_fee.values())
    tabs = [[str(x) + ' sats/Vb' for x in tabs]]
    tabs = tabulate(tabs,
                    headers=["Fastest Fee", "30 min fee", "1 hour fee"],
                    colalign=["center", "center", "center"])
    try:
        block_height = tor_request(url + '/api/blocks/tip/height').json()
    except Exception:
        return (error(f' >> Error getting data from {url}. Retrying...'))
    # Save the latest block height
    saved_block = pickle_it(action='load', filename='block.pkl')
    if (saved_block != block_height) and (
            config['MEMPOOL'].getboolean('block_found_sound')):
        # Block found play sound
        try:
            if config['MAIN'].getboolean('sound'):
                engine = pyttsx3.init()
                engine.setProperty('rate', 270)
                engine.say(config['MEMPOOL'].get('block_found_txt'))
                engine.runAndWait()
        except Exception:
            pass
        logging.info(
            info('[MEMPOOL] ') +
            success("A new Bitcoin Block was just found. ") +
            yellow("'Tick. Tock. Next block.'"))

    pickle_it(action='save', filename='block.pkl', data=block_height)

    block_txt = success(f' Block Height: {jformat(block_height, 0)}\n\n')
    tabs = block_txt + info(' Mempool Fee Estimates: \n') + tabs

    try:
        mp_blocks = tor_request(url + '/api/blocks').json()
    except Exception:
        return (error(" >> Error getting Mempool data. Retrying..."))

    mp_tabs = []
    gradient_color = 0
    for block in mp_blocks:
        mp_tabs.append([
            time_ago(block['timestamp']),
            jformat(block['height'], 0),
            jformat(block['tx_count'], 0),
            jformat(block['size'], 2, 1000000) + ' MB'
        ])
        gradient_color += 1

    mp_tabs = tabulate(mp_tabs,
                       headers=[" Time", "Height", "Tx Count", "Size"],
                       colalign=["right", "center", "center", "right"])
    tabs += info('\n\n Latest Blocks: \n') + mp_tabs
    if not forced_mps:
        tabs += muted(f"\n\n Source: {url} \n")
    else:
        tabs += warning(f"\n\n [!] Source: {url} [Alternate]")
    return tabs


def data_whitepaper():
    from node_warden import launch_logger
    launch_logger()
    logging.info("Downloading Whitepaper >> bitcoin.pdf")
    try:
        from pathlib import Path
        filename = Path('bitcoin.pdf')
        url = 'https://bitcoin.org/bitcoin.pdf'
        response = tor_request(url)
        filename.write_bytes(response.content)
        logging.info(success("File bitcoin.pdf saved [Success]"))
    except Exception as e:
        logging.error(
            warning(
                f"    Could not download bitcoin.pdf >> error: {e} [ERROR]"))


def data_logger():
    from node_warden import debug_file
    try:
        lines = 8
        log_txt = tail(debug_file, lines)
        return_str = []
        for element in log_txt:
            if 'INFO' in element:
                return_str.append(info(element))
            elif 'ERROR' in log_txt:
                return_str.append(error(element))
            elif 'WARN' in log_txt:
                return_str.append(warning(element))
            else:
                return_str.append((element))
        return_str = ''.join(return_str)
    except Exception:
        return yellow('>> Error Loading Log Messages. Retying...')
    return return_str


def data_random_satoshi():
    from node_warden import load_config
    config = load_config(quiet=True)
    url = config['QUOTES'].get('url')
    try:
        quotes = tor_request(url).json()
    except Exception:
        return (error(' >> Error contacting server. Retrying... '))
    quote = quotes[randrange(len(quotes))]
    return_str = info(f"Satoshi Quotes | Subject: {quote['category']}\n")
    return_str += muted(f"{quote['date']} on {quote['medium']}\n")
    return_str += yellow(f"{quote['text']} \n\n")
    return_str += muted("Source: Nakamoto Institute")
    return (return_str)


def main():
    arg = sys.argv[1]
    if arg == 'data_btc_price':
        print(data_btc_price())
    if arg == 'data_tor':
        print(data_tor())
    if arg == 'data_login':
        print(data_login())
    if arg == 'data_mempool':
        print(data_mempool())
    if arg == 'data_sys':
        print(data_sys())
    if arg == 'data_logger':
        print(data_logger())
    if arg == 'data_random_satoshi':
        print(data_random_satoshi())
    if arg == 'data_large_price':
        print(data_large_price())
    if arg == 'data_whitepaper':
        data_whitepaper()


# HELPERS ------------------------------------------
# Function to load and save data into pickles
def pickle_it(action='load', filename=None, data=None):
    home_path = os.path.dirname(os.path.abspath(__file__))
    filename = 'static/save/' + filename
    filename = os.path.join(home_path, filename)
    if action == 'load':
        try:
            with open(filename, 'rb') as handle:
                ld = pickle.load(handle)
                handle.close()
                return (ld)
        except Exception:
            return ("file not found")
    else:
        with open(filename, 'wb') as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            handle.close()
            return ("saved")


def tail(file, n=1, bs=1024):
    f = open(file)
    f.seek(0, 2)
    l = 1 - f.read(1).count('\n')
    B = f.tell()
    while n >= l and B > 0:
        block = min(bs, B)
        B -= block
        f.seek(B, 0)
        l += f.read(block).count('\n')
    f.seek(B, 0)
    l = min(l, n)
    lines = f.readlines()[-l:]
    f.close()
    return lines


if __name__ == "__main__":
    main()
