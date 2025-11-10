#!/usr/bin/env python3
"""
Wireless Card Manager
Manages multiple wireless cards, their roles, and coordinates scanning/attacking
"""

import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import pyudev


class CardRole(Enum):
    """Wireless card role"""
    UNASSIGNED = "unassigned"
    SCANNER = "scanner"
    ATTACKER = "attacker"
    BOTH = "both"  # For when we have 3+ cards


class CardState(Enum):
    """Card state"""
    DETECTED = "detected"
    READY = "ready"  # In managed mode
    MONITOR = "monitor"  # In monitor mode
    IN_USE = "in_use"  # Actively scanning or attacking
    ERROR = "error"


@dataclass
class WirelessCard:
    """Represents a wireless network card"""
    interface: str  # e.g., wlan0
    phy: str  # e.g., phy0
    driver: str
    chipset: str
    mac: str
    monitor_interface: Optional[str] = None  # e.g., wlan0mon
    role: CardRole = CardRole.UNASSIGNED
    state: CardState = CardState.DETECTED
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

    def to_dict(self) -> dict:
        return {
            'interface': self.interface,
            'phy': self.phy,
            'driver': self.driver,
            'chipset': self.chipset,
            'mac': self.mac,
            'monitor_interface': self.monitor_interface,
            'role': self.role.value,
            'state': self.state.value,
            'capabilities': self.capabilities
        }


class WirelessCardManager:
    """Manages multiple wireless cards and their roles"""

    def __init__(self):
        self.cards: Dict[str, WirelessCard] = {}  # interface -> WirelessCard
        self._lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False

        # Callbacks for events
        self.on_card_added: Optional[Callable[[WirelessCard], None]] = None
        self.on_card_removed: Optional[Callable[[str], None]] = None  # interface name
        self.on_card_role_changed: Optional[Callable[[WirelessCard], None]] = None

    def detect_cards(self) -> List[WirelessCard]:
        """Detect all wireless cards"""
        cards = []

        try:
            # Use iw dev to list all wireless interfaces
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, timeout=5)

            current_phy = None
            current_interface = None

            for line in result.stdout.split('\n'):
                line = line.strip()

                # Parse phy
                if line.startswith('phy#'):
                    current_phy = line.split('#')[1] if '#' in line else None

                # Parse interface
                elif 'Interface' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_interface = parts[1]

                # Parse MAC address
                elif 'addr' in line and current_interface and current_phy:
                    parts = line.split()
                    if len(parts) >= 2:
                        mac = parts[1]

                        # Get driver and chipset info
                        driver, chipset = self._get_card_details(current_interface)

                        card = WirelessCard(
                            interface=current_interface,
                            phy=f"phy{current_phy}",
                            driver=driver,
                            chipset=chipset,
                            mac=mac
                        )

                        # Check if already in monitor mode
                        if 'mon' in current_interface:
                            card.state = CardState.MONITOR
                            card.monitor_interface = current_interface

                        cards.append(card)

            with self._lock:
                # Update cards dictionary
                for card in cards:
                    if card.interface not in self.cards:
                        self.cards[card.interface] = card
                        if self.on_card_added:
                            self.on_card_added(card)

                # Remove cards that are no longer present
                current_interfaces = {card.interface for card in cards}
                removed = [iface for iface in self.cards.keys() if iface not in current_interfaces]
                for iface in removed:
                    del self.cards[iface]
                    if self.on_card_removed:
                        self.on_card_removed(iface)

            return cards

        except Exception as e:
            print(f"[!] Error detecting cards: {e}")
            return []

    def _get_card_details(self, interface: str) -> tuple[str, str]:
        """Get driver and chipset details for interface"""
        try:
            # Get driver
            driver_path = f"/sys/class/net/{interface}/device/driver"
            if Path(driver_path).exists():
                driver = Path(driver_path).resolve().name
            else:
                driver = "Unknown"

            # Get chipset (from modalias or uevent)
            modalias_path = f"/sys/class/net/{interface}/device/modalias"
            if Path(modalias_path).exists():
                chipset = Path(modalias_path).read_text().strip()
            else:
                chipset = "Unknown"

            return driver, chipset

        except Exception as e:
            print(f"[!] Error getting card details for {interface}: {e}")
            return "Unknown", "Unknown"

    def start_monitoring_hotplug(self):
        """Start monitoring for card hotplug events using pyudev"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_hotplug, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring_hotplug(self):
        """Stop monitoring for card hotplug events"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _monitor_hotplug(self):
        """Monitor for USB wireless card hotplug events"""
        try:
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem='net')

            print("[*] Wireless card hotplug monitoring started")

            for device in iter(monitor.poll, None):
                if not self._monitoring:
                    break

                if device.action == 'add':
                    # New network device added, check if wireless
                    time.sleep(1)  # Wait for device to initialize
                    self.detect_cards()

                elif device.action == 'remove':
                    # Device removed
                    interface = device.sys_name
                    with self._lock:
                        if interface in self.cards:
                            del self.cards[interface]
                            if self.on_card_removed:
                                self.on_card_removed(interface)
                            print(f"[*] Wireless card removed: {interface}")

        except Exception as e:
            print(f"[!] Hotplug monitoring error: {e}")

    def assign_role(self, interface: str, role: CardRole) -> bool:
        """Assign a role to a wireless card"""
        with self._lock:
            if interface not in self.cards:
                print(f"[!] Interface {interface} not found")
                return False

            card = self.cards[interface]
            old_role = card.role
            card.role = role

            if self.on_card_role_changed and old_role != role:
                self.on_card_role_changed(card)

            print(f"[*] {interface} role changed: {old_role.value} -> {role.value}")
            return True

    def auto_assign_roles(self):
        """Auto-assign roles based on number of cards"""
        with self._lock:
            card_list = list(self.cards.values())
            num_cards = len(card_list)

            if num_cards == 0:
                print("[!] No wireless cards detected")
                return

            elif num_cards == 1:
                # Single card: dual role (scan when idle, attack when needed)
                card_list[0].role = CardRole.BOTH
                print(f"[*] Single card mode: {card_list[0].interface} = BOTH (scan/attack)")

            elif num_cards == 2:
                # Two cards: one scanner, one attacker
                card_list[0].role = CardRole.SCANNER
                card_list[1].role = CardRole.ATTACKER
                print(f"[*] Dual card mode: {card_list[0].interface} = SCANNER, {card_list[1].interface} = ATTACKER")

            else:
                # 3+ cards: first card scanner, rest attackers, or assign BOTH
                card_list[0].role = CardRole.SCANNER
                for i in range(1, num_cards):
                    card_list[i].role = CardRole.ATTACKER
                print(f"[*] Multi-card mode: {card_list[0].interface} = SCANNER, others = ATTACKER")

            # Notify about role changes
            if self.on_card_role_changed:
                for card in card_list:
                    self.on_card_role_changed(card)

    def enable_monitor_mode(self, interface: str) -> tuple[bool, Optional[str]]:
        """Enable monitor mode on interface"""
        try:
            with self._lock:
                if interface not in self.cards:
                    return False, None

                card = self.cards[interface]

                # Check if already in monitor mode
                if card.state == CardState.MONITOR:
                    return True, card.monitor_interface

            print(f"[*] Enabling monitor mode on {interface}")

            # Kill interfering processes (but preserve NetworkManager)
            # Only kill wpa_supplicant and dhclient which actually interfere
            try:
                subprocess.run(['sudo', 'pkill', '-9', 'wpa_supplicant'],
                              capture_output=True, timeout=5)
                subprocess.run(['sudo', 'pkill', '-9', 'dhclient'],
                              capture_output=True, timeout=5)
            except Exception:
                pass  # Not critical if these don't exist

            # Enable monitor mode
            result = subprocess.run(['sudo', 'airmon-ng', 'start', interface],
                                   capture_output=True, text=True, timeout=10)

            # Parse output to find monitor interface name
            monitor_iface = None
            for line in result.stdout.split('\n'):
                if 'monitor mode' in line.lower() and 'enabled' in line.lower():
                    # Extract interface name
                    parts = line.split()
                    for part in parts:
                        if 'mon' in part.lower() or interface in part:
                            monitor_iface = part
                            break

            if not monitor_iface:
                # Try default naming
                monitor_iface = f"{interface}mon"

            with self._lock:
                card.monitor_interface = monitor_iface
                card.state = CardState.MONITOR

            print(f"[+] Monitor mode enabled: {monitor_iface}")
            return True, monitor_iface

        except Exception as e:
            print(f"[!] Failed to enable monitor mode on {interface}: {e}")
            return False, None

    def disable_monitor_mode(self, interface: str) -> bool:
        """Disable monitor mode"""
        try:
            with self._lock:
                if interface not in self.cards:
                    return False

                card = self.cards[interface]
                monitor_iface = card.monitor_interface or interface

            print(f"[*] Disabling monitor mode on {monitor_iface}")

            subprocess.run(['sudo', 'airmon-ng', 'stop', monitor_iface],
                          capture_output=True, timeout=10)

            with self._lock:
                card.monitor_interface = None
                card.state = CardState.READY

            print(f"[+] Monitor mode disabled on {interface}")
            return True

        except Exception as e:
            print(f"[!] Failed to disable monitor mode: {e}")
            return False

    def get_scanner_cards(self) -> List[WirelessCard]:
        """Get all cards assigned to scanning role"""
        with self._lock:
            return [card for card in self.cards.values()
                    if card.role in [CardRole.SCANNER, CardRole.BOTH]]

    def get_attacker_cards(self) -> List[WirelessCard]:
        """Get all cards assigned to attacker role"""
        with self._lock:
            return [card for card in self.cards.values()
                    if card.role in [CardRole.ATTACKER, CardRole.BOTH]]

    def get_all_cards(self) -> List[WirelessCard]:
        """Get all detected cards"""
        with self._lock:
            return list(self.cards.values())

    def get_card(self, interface: str) -> Optional[WirelessCard]:
        """Get card by interface name"""
        with self._lock:
            return self.cards.get(interface)


# Singleton instance
_manager_instance: Optional[WirelessCardManager] = None

def get_card_manager() -> WirelessCardManager:
    """Get singleton card manager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = WirelessCardManager()
    return _manager_instance
