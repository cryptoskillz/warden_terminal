import emoji
from ansi.colour import fg


def logo():
    print(
        fg.brightgreen(f"""
  _   _           __        ___    ____     _
 | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
 | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
 | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
  \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"""))
    print("")
    print(
        emoji.emojize(
            "                                          Node Edition :key:"))
    print(
        fg.boldyellow(
            "                             Powered by NgU technology "))


def goodbye():
    for n in range(0, 100):
        print("")
    print(
        fg.brightgreen(f"""
  _  __                 ____  _             _    _               ____        _
 | |/ /___  ___ _ __   / ___|| |_ __ _  ___| | _(_)_ __   __ _  / ___|  __ _| |_ ___
 | ' // _ \/ _ \ '_ \  \___ \| __/ _` |/ __| |/ / | '_ \ / _` | \___ \ / _` | __/ __|.
 | . \  __/  __/ |_) |  ___) | || (_| | (__|   <| | | | | (_| |  ___) | (_| | |_\__ \.. .
 |_|\_\___|\___| .__/  |____/ \__\__,_|\___|_|\_\_|_| |_|\__, | |____/ \__,_|\__|___/... ...
               |_|                                       |___/"""))
    print("")
    print(
        emoji.emojize(
            "                                   Not your keys, not your Bitcoin :key:"
        ))
    print(fg.boldyellow("                                   See you later "))
