#!/usr/bin/env python3
"""
Wireless Card Configuration Dialog
Allows users to manually assign roles to wireless cards
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QGroupBox, QGridLayout,
                             QScrollArea, QWidget, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, List


class CardRoleWidget(QWidget):
    """Widget for configuring a single wireless card"""

    role_changed = pyqtSignal(str, str)  # interface, role

    def __init__(self, interface: str, driver: str, chipset: str,
                 current_role: str, parent=None):
        super().__init__(parent)
        self.interface = interface
        self.current_role = current_role

        # Create layout
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Interface name (bold)
        name_label = QLabel(f"<b>{interface}</b>")
        name_font = QFont()
        name_font.setPointSize(11)
        name_font.setBold(True)
        name_label.setFont(name_font)
        layout.addWidget(name_label, 0, 0, 1, 2)

        # Driver info
        driver_label = QLabel(f"Driver: {driver}")
        driver_label.setStyleSheet("color: #666;")
        layout.addWidget(driver_label, 1, 0, 1, 2)

        # Chipset info
        if chipset and chipset != "Unknown":
            chipset_label = QLabel(f"Chipset: {chipset[:40]}...")
            chipset_label.setStyleSheet("color: #666;")
            layout.addWidget(chipset_label, 2, 0, 1, 2)

        # Role selector
        role_label = QLabel("Role:")
        layout.addWidget(role_label, 3, 0)

        self.role_combo = QComboBox()
        self.role_combo.addItem("📡 Scanner - Continuous scanning", "scanner")
        self.role_combo.addItem("⚔️ Attacker - For attacks only", "attacker")
        self.role_combo.addItem("🔄 Both - Scan & attack (single card)", "both")
        self.role_combo.addItem("⏸️ Unassigned - No role", "unassigned")

        # Set current role
        role_map = {
            "scanner": 0,
            "attacker": 1,
            "both": 2,
            "unassigned": 3
        }
        self.role_combo.setCurrentIndex(role_map.get(current_role.lower(), 3))

        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        layout.addWidget(self.role_combo, 3, 1)

        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator, 4, 0, 1, 2)

    def _on_role_changed(self, index):
        """Handle role change"""
        role = self.role_combo.itemData(index)
        self.role_changed.emit(self.interface, role)

    def get_role(self) -> str:
        """Get selected role"""
        return self.role_combo.currentData()


class CardConfigDialog(QDialog):
    """Dialog for configuring wireless card roles"""

    roles_updated = pyqtSignal(dict)  # Dict[interface, role]

    def __init__(self, cards: List[Dict], parent=None):
        """
        Initialize card configuration dialog

        Args:
            cards: List of card dictionaries with keys:
                   interface, driver, chipset, role, state
        """
        super().__init__(parent)
        self.cards = cards
        self.card_widgets: Dict[str, CardRoleWidget] = {}

        self.setWindowTitle("Configure Wireless Cards")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self._init_ui()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel("<h2>Wireless Card Configuration</h2>")
        layout.addWidget(header_label)

        info_label = QLabel(
            "Configure roles for your wireless network adapters. "
            "Scanner cards continuously capture traffic, while Attacker cards "
            "are reserved for performing attacks."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        # Card count info
        card_count_label = QLabel(f"<b>Detected Cards: {len(self.cards)}</b>")
        layout.addWidget(card_count_label)

        # Recommendation
        if len(self.cards) == 1:
            rec_text = "💡 <b>Single Card Mode:</b> Assign 'Both' role to use for scanning and attacks"
            rec_color = "#0066cc"
        elif len(self.cards) == 2:
            rec_text = "💡 <b>Dual Card Mode:</b> Assign one as Scanner, one as Attacker for simultaneous operation"
            rec_color = "#00aa00"
        else:
            rec_text = "💡 <b>Multi-Card Mode:</b> Assign one Scanner and remaining as Attackers"
            rec_color = "#00aa00"

        rec_label = QLabel(rec_text)
        rec_label.setWordWrap(True)
        rec_label.setStyleSheet(f"background-color: {rec_color}22; color: {rec_color}; "
                               f"padding: 10px; border-radius: 5px; border: 1px solid {rec_color};")
        layout.addWidget(rec_label)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)

        # Container for card widgets
        card_container = QWidget()
        card_layout = QVBoxLayout(card_container)
        card_layout.setSpacing(5)

        # Create widget for each card
        for card in self.cards:
            card_widget = CardRoleWidget(
                interface=card.get('interface', 'Unknown'),
                driver=card.get('driver', 'Unknown'),
                chipset=card.get('chipset', 'Unknown'),
                current_role=card.get('role', 'unassigned')
            )
            card_widget.role_changed.connect(self._on_card_role_changed)

            self.card_widgets[card['interface']] = card_widget
            card_layout.addWidget(card_widget)

        card_layout.addStretch()
        scroll.setWidget(card_container)
        layout.addWidget(scroll, 1)  # Stretch factor 1

        # Button box
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Auto-assign button
        auto_btn = QPushButton("Auto-Assign Roles")
        auto_btn.setToolTip("Automatically assign roles based on card count")
        auto_btn.clicked.connect(self._auto_assign_roles)
        button_layout.addWidget(auto_btn)

        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply_changes)
        button_layout.addWidget(apply_btn)

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _on_card_role_changed(self, interface: str, role: str):
        """Handle individual card role change"""
        # Update internal state
        for card in self.cards:
            if card['interface'] == interface:
                card['role'] = role
                break

    def _auto_assign_roles(self):
        """Auto-assign roles based on number of cards"""
        if len(self.cards) == 0:
            return

        if len(self.cards) == 1:
            # Single card: BOTH
            self.card_widgets[self.cards[0]['interface']].role_combo.setCurrentIndex(2)  # Both

        elif len(self.cards) == 2:
            # Two cards: Scanner + Attacker
            self.card_widgets[self.cards[0]['interface']].role_combo.setCurrentIndex(0)  # Scanner
            self.card_widgets[self.cards[1]['interface']].role_combo.setCurrentIndex(1)  # Attacker

        else:
            # 3+ cards: First scanner, rest attackers
            self.card_widgets[self.cards[0]['interface']].role_combo.setCurrentIndex(0)  # Scanner
            for i in range(1, len(self.cards)):
                self.card_widgets[self.cards[i]['interface']].role_combo.setCurrentIndex(1)  # Attacker

    def _apply_changes(self):
        """Apply role changes"""
        # Collect all role assignments
        roles = {}
        for interface, widget in self.card_widgets.items():
            roles[interface] = widget.get_role()

        # Emit signal with role assignments
        self.roles_updated.emit(roles)

        # Close dialog
        self.accept()

    def get_role_assignments(self) -> Dict[str, str]:
        """Get current role assignments"""
        roles = {}
        for interface, widget in self.card_widgets.items():
            roles[interface] = widget.get_role()
        return roles
