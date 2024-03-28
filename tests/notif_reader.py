import random
import subprocess
import time
import traceback
from multiprocessing import Process
from typing import List, Dict

import varvault
from commons import *


class NotifReader:
    class Keyring(varvault.Keyring):
        notifs = varvault.Key("notifs", valid_type=dict)

    def __init__(self, vault_path=None, services=600, do_sleep=True):

        self.notif_dict = {}
        self.killed = False
        subprocess.call(f"rm -f {vault_path}", shell=True)
        self.process = Process(target=self.run, args=(vault_path, services, do_sleep))
        self.process.start()
        start = time.time()
        while not os.path.exists(vault_path) and time.time() - start < 60:
            assert self.process.is_alive(), "Process is not alive, but it should be because we haven't killed it yet. It's likely that no notifs were received while we were waiting"
            time.sleep(0.1)
        if not os.path.exists(vault_path):
            self.kill()
            raise FileNotFoundError(f"Vault file {vault_path} does not exist: {self.process.exitcode}")
        self.vault_reader = varvault.create(keyring=NotifReader.Keyring, resource=varvault.JsonResource(vault_path, mode=varvault.ResourceModes.READ_W_LIVE_UPDATE))

    def run(self, vault_path: str, services: int = 600, do_sleep=True) -> None:
        notifs = dict()
        try:
            resource = varvault.JsonResource(vault_path, mode=varvault.ResourceModes.WRITE)
            vault = varvault.create(varvault.Flags.permit_modifications, keyring=NotifReader.Keyring, resource=resource)
            for n in range(services):
                t = time.time()
                notif = {
                    "eventTime": t,
                    "service": f"service-{n}",
                    "component": "self",
                    "state": "ready",
                    "operation": "created",
                    "status": "reached"
                }
                notifs[f"service-{n}"] = notif
                vault.insert(NotifReader.Keyring.notifs, notifs)
                if do_sleep:
                    # sleep for a random amount of time between 0 and 1 seconds
                    time.sleep(random.uniform(0, 1))

        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()

    def get_notifs(self, key: str) -> Dict:
        # if not self.process.is_alive() and not self.killed:
        #     raise TimeoutError(f"Process is not alive, but it should be because we haven't killed it yet. It's likely that no notifs were received while we were waiting")
        notifs_all = self.vault_reader.get(NotifReader.Keyring.notifs, varvault.Flags.silent, varvault.Flags.input_key_can_be_missing, default={})
        notifs_service = notifs_all.get(key, [])
        return notifs_service

    def kill(self):
        self.killed = True
        self.process.kill()

        def check_status():
            assert not self.process.is_alive(), "Process is still alive, but it should be dead."

        check_status()