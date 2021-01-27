import time
import requests
import logging


from dbus import SystemBus, Interface
from dbus.exceptions import DBusException

def is_service_active(service):
    """
    is_service_active method will check if service is running or not.
    It raise exception if there is service is not loaded
    Return value, True if service is running otherwise False.
    :param str service: name of the service
    """
   
    bus = SystemBus()
    systemd = bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    manager = Interface(systemd, 'org.freedesktop.systemd1.Manager')
    
    try:
        manager.GetUnit('chain-maind.service')
        return True
    except:
        return False
 
def restart_daemon():
    cmd = f"systemctl restart chain-maind"
    print("### Restart service ###")
    sysbus = SystemBus()
    systemd1 = sysbus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    manager = Interface(systemd1, dbus_interface='org.freedesktop.systemd1.Manager')
    if is_service_active('chain-maind.service'):
        manager.StopUnit('chain-maind.service', 'replace')
     #job = manager.RestartUnit('chain-maind.service', 'fail')
    time.sleep(5)
    manager.StartUnit('chain-maind.service', 'replace')

def sync_block(request_session):
    url_info = "http://localhost:26657/status"
    start_block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"]) 
    while True:
        block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"])
        print(f"wait new block {block} {start_block}")
        if block == start_block:
            time.sleep(1)
            continue
        else:
            break

def main():
    # the api port setted in ${home_dir of chain-maind}/config/app.toml, the default is ~/.chain-maind/config/app.toml
    crypto_url = "https://chain.crypto.com/explorer/crossfire/api/v1/crossfire/validators"
    
    r = requests.Session()
    #create a logger
    logger = logging.getLogger('mylogger')
    #set logger level
    logger.setLevel(logging.INFO)
    #or you can set the following level
    #logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler('perf_data.log')
    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    totalTxSent = 0
    prev_totalTxSent = 0
    while True:
        try:
            response = r.get(crypto_url)
            validators = response.json()["result"]
        except:
            pass
        else:
            for validator in validators :
                moniker = validator["moniker"]
                if moniker == "Tolosa-node":
                    stats = validator["stats"]
                    prev_totalTxSent = totalTxSent
                    totalTxSent = stats["totalTxSent"]
                if moniker == "Staking Fund":
                    stats = validator["stats"]
                    totalTxSent_SF = stats["totalTxSent"]
                if moniker == "mjolnir":
                    stats = validator["stats"]
                    totalTxSent_M = stats["totalTxSent"]

        print(f"{totalTxSent}")
        logger.info(f"{totalTxSent} {totalTxSent_SF} {totalTxSent_M}")
        if totalTxSent == prev_totalTxSent:
            # restart service
            print(f"Total send does not progress ({totalTxSent})")
            sync_block(r)
            restart_daemon()
            totalTxSent = 0
            prev_totalTxSent = 0
        time.sleep(60)

        

if __name__ == "__main__":
    main()
