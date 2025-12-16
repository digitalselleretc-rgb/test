# bridge.py
# --- RUN THIS WITH WINE PYTHON ---
import MetaTrader5 as mt5
import rpyc
from rpyc.utils.server import ThreadedServer

# This class exposes the MT5 functions to the outside world
class MT5Service(rpyc.Service):
    def on_connect(self, conn):
        print("Linux Client Connected!")
    
    def on_disconnect(self, conn):
        print("Linux Client Disconnected!")

    # This allows the client to access the 'mt5' module directly
    def exposed_get_mt5(self):
        return mt5

if __name__ == "__main__":
    # 1. Initialize MT5 inside Wine
    if not mt5.initialize():
        print("Startup Failed: MT5 initialize() error", mt5.last_error())
        quit()
    else:
        print("✅ MT5 Connected Successfully (Inside Wine)")

    # 2. Start the Server on Port 18812
    print("🚀 Bridge Server Running on port 18812...")
    server = ThreadedServer(MT5Service, port=18812, protocol_config={"allow_public_attrs": True})
    server.start()
