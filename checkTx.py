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
    time.sleep(2)
    manager.StartUnit('chain-maind.service', 'replace')

# wait for the next block height
# can be usefull to restart the service between 2 block and
# limite the lost of commits
def sync_block(request_session):
    url_info = "http://localhost:26657/status"
    start_block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"]) 
    while True:
        block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"])
        print(f"wait new block {block} {start_block}", end='\r')
        if block == start_block:
            time.sleep(1)
            continue
        else:
            print("")
            break

def main():
    # the URL to retrieve the leaderboard informations
    crypto_url = "https://chain.crypto.com/explorer/crossfire/api/v1/crossfire/validators"
    checkblock_url = "https://chain.crypto.com/explorer/crossfire/api/v1/blocks?pagination=offset&page=1&limit=1&order=height.desc"
    
    Tolosa_Node_Hex = "F54D08F05DFCB27207E3606FCCDA6DFCB11AB6AB"
    r = requests.Session()
    #create a logger
    logger = logging.getLogger('mylogger')
    #set logger level
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler('perf_data.log')
    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    totalTxSent = 0
    prev_totalTxSent = 0
    block_count = 0
    prev_block_count = 0
    height = 0
    prev_height = 0
    percent_commit = 0
    miss = 0
    signed = False
    force = False
    while True:
        sync_block(r)
        try:
            response = r.get(crypto_url)
            validators = response.json()["result"]
        except Exception as e:
            print(e)
        else:
            for validator in validators :
                moniker = validator["moniker"]
                # find my moniker
                if moniker == "Tolosa-node":
                    stats = validator["stats"]
                    prev_totalTxSent = totalTxSent
                    totalTxSent = stats["totalTxSent"]
                    prev_block_count = block_count
                    block_count = int(stats["phase3BlockCount"])
                    percent_commit = int(stats["commitCountPhase3"])*100.0 / int(stats["phase3BlockCount"])
                    miss = int(stats["phase3BlockCount"]) - int(stats["commitCountPhase3"])
        # if they don't, the totalTx is not relevant
        try:
            response = r.get(checkblock_url)
            last_block = response.json()["result"][0]
        except Exception as e:
            print(e)
        else:
            prev_height = height
            height = last_block["blockHeight"]
            for commiter in last_block["committedCouncilNodes"]:
                if commiter["address"] == Tolosa_Node_Hex:
                    signed = True
                    
        # write some stats
        print("Tx total: {} P2_Blocks {}\t{:.2f}% {} miss".format(totalTxSent, block_count, percent_commit, miss))

        logger.info(f"{totalTxSent} ")

        # if the number of Tx did not increment since last read, reset the service
        if force or (prev_block_count != block_count):
            if force or (totalTxSent == prev_totalTxSent):
                # restart service
                print(f"Total send does not progress ({totalTxSent})")
                sync_block(r)
                time.sleep(0.1)
                restart_daemon()
                totalTxSent = 0
                prev_totalTxSent = 0
                force = False
        else:
            print("data don't change")
            # explorer is stuck. reset value to not fall in error when it come back
            prev_block_count = 0
            block_count = 0
            totalTxSent = 0
            prev_totalTxSent = 0

        # wait for 2 minutes
        #force = True
        time.sleep(300)
        

if __name__ == "__main__":
    main()
