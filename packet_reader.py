# packet_reader.py
import subprocess
import threading
import datetime
import state

class PacketReader:
    def __init__(self, data_queue):
        self.data_queue = data_queue

    def start(self):
        t = threading.Thread(target=self._read_loop)
        t.daemon = True
        t.start()

    def _read_loop(self):
        # Note: You still need sudo to run the main script!
        cmd = ["sudo", "packetlogger", "convert", "-s", "-f", "mpr"]
        
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                bufsize=0
            )
            
            for line in process.stdout:
                if not state.shared.running: break
                if "Receive" not in line: continue

                try:
                    hex_str = line.split("Receive")[1].strip()
                    parts = hex_str.split()
                    all_bytes = [int(p, 16) for p in parts]

                    if len(all_bytes) >= 17:
                        payload = all_bytes[11:17]
                        x = payload[1] | (payload[2] << 8)
                        if x > 32767: x -= 65536
                        y = payload[3] | (payload[4] << 8)
                        if y > 32767: y -= 65536

                        if x != 0 or y != 0:
                            self.data_queue.put({
                                "x": x, "y": y,
                                "hex": " ".join([f"{b:02X}" for b in payload]),
                                "time": datetime.datetime.now().strftime("%H:%M:%S")
                            })
                except Exception: continue
        except FileNotFoundError:
            self.data_queue.put("ERROR_CMD")
