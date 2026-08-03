"""
Hardware interface management for the Arduino serial connection.
Includes background reconnection handling and mock backup modes for local testing.
"""

import time
import logging
import threading
import serial
from python import config

logger = logging.getLogger("HardwareBridge")


class ArduinoBridge:
    def __init__(self):
        self.port = config.SERIAL_PORT
        self.baud = config.SERIAL_BAUD
        self.timeout = config.SERIAL_TIMEOUT
        
        self.device = None
        self.is_connected = False
        self.simulation_mode = False
        self._lock = threading.Lock()
        self._running = True
        
        # Start connection status manager thread
        self._monitor_thread = threading.Thread(
            target=self._connection_monitor,
            daemon=True,
            name="HardwareMonitor"
        )
        self._monitor_thread.start()

    def _connection_monitor(self):
        """Periodically checks and establishes connection to the microcontroller."""
        while self._running:
            if not self.is_connected and not self.simulation_mode:
                self._connect()
            time.sleep(config.SERIAL_RETRY_INTERVAL)

    def _connect(self):
        """Attempts physical serial connection, falls back to simulation mode on error."""
        with self._lock:
            try:
                logger.info(f"Connecting to Arduino on {self.port} at {self.baud} baud...")
                self.device = serial.Serial(
                    port=self.port,
                    baudrate=self.baud,
                    timeout=self.timeout
                )
                time.sleep(2.0)  # Wait for Arduino default boot-loader reset
                self.is_connected = True
                self.simulation_mode = False
                logger.info("Arduino communication link established.")
            except (serial.SerialException, ImportError) as e:
                logger.warning(
                    f"Physical serial communication failed ({e}). "
                    "Running in SIMULATION mode."
                )
                self.device = None
                self.is_connected = False
                self.simulation_mode = True

    def send_command(self, command: str) -> bool:
        """Sends clean string command to Arduino. Returns state status."""
        cmd_bytes = f"{command.strip()}\n".encode("utf-8")
        
        with self._lock:
            if self.is_connected and self.device:
                try:
                    self.device.write(cmd_bytes)
                    logger.info(f"Command sent to Arduino: '{command}'")
                    return True
                except Exception as ex:
                    logger.error(f"Failed to communicate with Arduino: {ex}. Closing port.")
                    self.is_connected = False
                    try:
                        self.device.close()
                    except Exception:
                        pass
                    self.device = None
                    return False
            elif self.simulation_mode:
                logger.info(f"[SIMULATED HARWARE OUT] Command: '{command}'")
                return True
            
        logger.debug(f"Action command '{command}' omitted, system link down.")
        return False

    def get_status(self) -> dict:
        """Returns connection diagnostics."""
        with self._lock:
            return {
                "connected": self.is_connected,
                "simulated": self.simulation_mode,
                "port": self.port
            }

    def close(self):
        """Kills watchdog monitor loop and closes serial ports cleanly."""
        self._running = False
        with self._lock:
            if self.device:
                try:
                    self.device.close()
                    logger.info("Closed serial connection to Arduino.")
                except Exception:
                    pass
                self.device = None
                self.is_connected = False
