"""
Serial number generation for all database entities
All records get unique alphanumeric serial numbers (16+ characters)
"""

import time
import random
import string
from datetime import datetime
from typing import Optional


class SerialGenerator:
    """Generate unique alphanumeric serial numbers for database records"""

    # Character set for serials (alphanumeric - no ambiguous chars)
    CHARSET = string.ascii_uppercase + string.digits
    CHARSET = CHARSET.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    # Results in: ABCDEFGHJKLMNPQRSTUVWXYZ23456789 (32 chars)

    @staticmethod
    def generate(prefix: str = "", length: int = 16) -> str:
        """
        Generate a unique serial number

        Args:
            prefix: Optional prefix (e.g., "AP", "CL", "EV", "TASK")
            length: Total length of serial (default 16, min 16)

        Returns:
            Alphanumeric serial like "AP7X4M9K2R5WBNQT" or "CL8Y3N6P4SMHVGZD"

        Format:
            [PREFIX][TIMESTAMP_BASE36][RANDOM]
            - Prefix: 2-4 chars (optional)
            - Timestamp: 8 chars (base36 encoded unix timestamp)
            - Random: remaining chars (cryptographically random)
        """
        if length < 16:
            length = 16

        # Encode current timestamp in base36 (compact)
        timestamp = int(time.time())
        timestamp_b36 = SerialGenerator._to_base36(timestamp)

        # Pad/trim to 8 chars
        timestamp_b36 = timestamp_b36[-8:].zfill(8)

        # Calculate random portion length
        if prefix:
            prefix = prefix.upper()
            random_length = length - len(prefix) - 8
        else:
            random_length = length - 8

        if random_length < 0:
            random_length = 8  # Minimum random portion

        # Generate random portion
        random_part = ''.join(random.choices(SerialGenerator.CHARSET, k=random_length))

        # Combine
        if prefix:
            serial = f"{prefix}{timestamp_b36}{random_part}"
        else:
            serial = f"{timestamp_b36}{random_part}"

        return serial

    @staticmethod
    def generate_ap_serial() -> str:
        """Generate serial for Access Point"""
        return SerialGenerator.generate("AP", 18)

    @staticmethod
    def generate_client_serial() -> str:
        """Generate serial for Client"""
        return SerialGenerator.generate("CL", 18)

    @staticmethod
    def generate_event_serial() -> str:
        """Generate serial for Event"""
        return SerialGenerator.generate("EV", 20)

    @staticmethod
    def generate_session_serial() -> str:
        """Generate serial for Scan Session"""
        return SerialGenerator.generate("SESS", 20)

    @staticmethod
    def generate_observation_serial() -> str:
        """Generate serial for Network Observation"""
        return SerialGenerator.generate("OBS", 20)

    @staticmethod
    def generate_task_serial() -> str:
        """Generate serial for Task"""
        return SerialGenerator.generate("TASK", 20)

    @staticmethod
    def generate_current_scan_network_serial() -> str:
        """Generate serial for Current Scan Network"""
        return SerialGenerator.generate("CSN", 20)

    @staticmethod
    def generate_current_scan_client_serial() -> str:
        """Generate serial for Current Scan Client"""
        return SerialGenerator.generate("CSC", 20)

    @staticmethod
    def _to_base36(number: int) -> str:
        """Convert number to base36 string"""
        if number == 0:
            return '0'

        alphabet = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        base36 = ''

        while number:
            number, remainder = divmod(number, 32)  # 32 chars in our charset
            base36 = alphabet[remainder] + base36

        return base36

    @staticmethod
    def parse_serial_timestamp(serial: str) -> Optional[datetime]:
        """
        Extract timestamp from serial number

        Args:
            serial: Serial number

        Returns:
            datetime object or None if can't parse
        """
        try:
            # Remove prefix if present
            if serial.startswith(('AP', 'CL', 'EV', 'SESS', 'OBS', 'TASK')):
                for prefix in ['SESS', 'TASK', 'OBS', 'EV', 'AP', 'CL']:
                    if serial.startswith(prefix):
                        serial = serial[len(prefix):]
                        break

            # Extract timestamp portion (first 8 chars)
            timestamp_b36 = serial[:8]

            # Convert from base36
            timestamp = SerialGenerator._from_base36(timestamp_b36)

            return datetime.fromtimestamp(timestamp)

        except Exception:
            return None

    @staticmethod
    def _from_base36(base36: str) -> int:
        """Convert base36 string to number"""
        alphabet = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        number = 0

        for char in base36:
            number = number * 32 + alphabet.index(char)

        return number


def generate_serial(entity_type: str = "") -> str:
    """
    Convenience function to generate serial based on entity type

    Args:
        entity_type: Type of entity ("ap", "client", "event", "session", etc.)

    Returns:
        Serial number
    """
    entity_type = entity_type.lower()

    if entity_type in ["ap", "access_point", "accesspoint"]:
        return SerialGenerator.generate_ap_serial()
    elif entity_type in ["cl", "client", "station"]:
        return SerialGenerator.generate_client_serial()
    elif entity_type in ["ev", "event"]:
        return SerialGenerator.generate_event_serial()
    elif entity_type in ["sess", "session", "scan_session", "scan"]:
        return SerialGenerator.generate_session_serial()
    elif entity_type in ["obs", "observation"]:
        return SerialGenerator.generate_observation_serial()
    elif entity_type in ["task"]:
        return SerialGenerator.generate_task_serial()
    elif entity_type in ["csn", "current_scan_network"]:
        return SerialGenerator.generate_current_scan_network_serial()
    elif entity_type in ["csc", "current_scan_client"]:
        return SerialGenerator.generate_current_scan_client_serial()
    elif entity_type in ["hs", "handshake"]:
        return SerialGenerator.generate("HS", 18)
    elif entity_type in ["wi", "wigle", "wigle_import"]:
        return SerialGenerator.generate("WI", 18)
    elif entity_type in ["ou", "oui", "oui_update"]:
        return SerialGenerator.generate("OU", 18)
    elif entity_type in ["aq", "attack", "attack_queue"]:
        return SerialGenerator.generate("AQ", 18)
    else:
        # Generic 16-char serial
        return SerialGenerator.generate(length=16)


# Example serials:
# AP: AP7X4M9K2R5WBNQT (18 chars)
# Client: CL8Y3N6P4SMHVGZD (18 chars)
# Event: EV9Z2H7M4KRBXTVQWN (20 chars)
# Session: SESS3P8M6V4HRXK2TYBW (20 chars)
# Observation: OBS7R4X9N2VHMK5TPQBW (20 chars)
# Task: TASK8M3X6P9NHRKV4TQBY (20 chars)
