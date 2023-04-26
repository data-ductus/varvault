import threading


class SubscriberThread(threading.Thread):
    def __init__(self, subscriber, varvault, *args, **kwargs):
        super(SubscriberThread, self).__init__(*args, **kwargs)
        self.subscriber = subscriber
        self.varvault = varvault

    def run(self):
        from .vault import VarVault
        self.varvault.logger.info(f"Starting subscriber thread for {self.subscriber.__name__}...")
        self.subscriber()
        self.varvault: VarVault
        self.varvault.purge_stopped_thread(self)
