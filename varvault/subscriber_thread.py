import threading


class SubscriberThread(threading.Thread):
    def __init__(self, subscriber, varvault, *args, **kwargs):
        super(SubscriberThread, self).__init__(*args, **kwargs)
        self.subscriber = subscriber
        self.varvault = varvault
        self.exception = None

    def run(self):
        from .vault import VarVault
        self.varvault.logger.debug(f"Starting subscriber thread for {self.subscriber.__name__}...")
        try:
            self.subscriber()
        except Exception as e:
            self.varvault.logger.info(f"Subscriber thread for {self.subscriber.__name__} stopped with exception: {e}")
            self.exception = e
        finally:
            self.varvault: VarVault
            self.varvault.purge_stopped_thread(self)
