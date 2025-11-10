"""
Prerequisite detection and validation system
Checks for required system tools and Python packages
"""

import subprocess
import shutil
from dataclasses import dataclass
from typing import List, Optional, Tuple
import importlib.util


@dataclass
class Prerequisite:
    """Represents a system or Python prerequisite"""
    name: str
    type: str  # 'system', 'python', 'service'
    description: str
    check_command: Optional[str] = None
    install_command: Optional[str] = None
    package_name: Optional[str] = None
    required: bool = True
    installed: bool = False
    version: Optional[str] = None


class PrerequisiteChecker:
    """Checks and validates all prerequisites"""

    def __init__(self):
        self.prerequisites: List[Prerequisite] = []
        self._define_prerequisites()

    def _define_prerequisites(self):
        """Define all required and optional prerequisites"""

        # System tools for wireless pentesting
        self.prerequisites = [
            # Essential wireless tools
            Prerequisite(
                name="aircrack-ng",
                type="system",
                description="Wireless network security auditing suite",
                check_command="aircrack-ng --help",
                install_command="sudo apt-get install -y aircrack-ng",
                required=True
            ),
            Prerequisite(
                name="iw",
                type="system",
                description="Wireless configuration tool",
                check_command="iw --version",
                install_command="sudo apt-get install -y iw",
                required=True
            ),
            # iwconfig removed - legacy tool not needed on modern systems
            # Modern systems use 'iw' which is already required above
            # Additional pentesting tools
            Prerequisite(
                name="reaver",
                type="system",
                description="WPS brute-force attack tool",
                check_command="reaver -h",
                install_command="sudo apt-get install -y reaver",
                required=False
            ),
            Prerequisite(
                name="bully",
                type="system",
                description="Alternative WPS attack tool",
                check_command="bully -h",
                install_command="sudo apt-get install -y bully",
                required=False
            ),
            Prerequisite(
                name="hashcat",
                type="system",
                description="Advanced password recovery",
                check_command="hashcat --version",
                install_command="sudo apt-get install -y hashcat",
                required=False
            ),
            Prerequisite(
                name="hcxtools",
                type="system",
                description="PCAP analysis and handshake conversion",
                check_command="hcxpcapngtool --version",
                install_command="sudo apt-get install -y hcxtools",
                required=False
            ),
            Prerequisite(
                name="macchanger",
                type="system",
                description="MAC address spoofing tool",
                check_command="macchanger --version",
                install_command="sudo apt-get install -y macchanger",
                required=False
            ),
            # Database tools
            Prerequisite(
                name="sqlite3",
                type="system",
                description="SQLite database engine",
                check_command="sqlite3 --version",
                install_command="sudo apt-get install -y sqlite3",
                required=True
            ),
            # Network utilities
            Prerequisite(
                name="tcpdump",
                type="system",
                description="Network packet analyzer",
                check_command="tcpdump --version",
                install_command="sudo apt-get install -y tcpdump",
                required=True
            ),
        ]

    def check_system_tool(self, prereq: Prerequisite) -> Tuple[bool, Optional[str]]:
        """Check if a system tool is installed"""
        if prereq.check_command:
            try:
                result = subprocess.run(
                    prereq.check_command.split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    text=True
                )
                # Tool exists if command runs (even with non-zero exit for help commands)
                if result.returncode in [0, 1]:  # Many tools return 1 for --help
                    # Try to extract version
                    version = self._extract_version(result.stdout + result.stderr)
                    return True, version
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

        # Fallback: check if command exists in PATH
        return shutil.which(prereq.name) is not None, None

    def check_python_package(self, prereq: Prerequisite) -> Tuple[bool, Optional[str]]:
        """Check if a Python package is installed"""
        package_name = prereq.package_name or prereq.name

        try:
            spec = importlib.util.find_spec(package_name)
            if spec is not None:
                # Try to get version
                module = importlib.import_module(package_name)
                version = getattr(module, '__version__', None)
                return True, version
        except (ImportError, ModuleNotFoundError):
            pass

        return False, None

    def _extract_version(self, output: str) -> Optional[str]:
        """Extract version number from command output"""
        import re

        # Common version patterns
        patterns = [
            r'version\s+(\d+\.\d+(?:\.\d+)?)',
            r'v(\d+\.\d+(?:\.\d+)?)',
            r'(\d+\.\d+(?:\.\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def check_all(self) -> List[Prerequisite]:
        """Check all prerequisites and return results"""
        for prereq in self.prerequisites:
            if prereq.type == "system":
                installed, version = self.check_system_tool(prereq)
            elif prereq.type == "python":
                installed, version = self.check_python_package(prereq)
            else:
                installed, version = False, None

            prereq.installed = installed
            prereq.version = version

        return self.prerequisites

    def get_missing_required(self) -> List[Prerequisite]:
        """Get list of missing required prerequisites"""
        return [p for p in self.prerequisites if p.required and not p.installed]

    def get_missing_optional(self) -> List[Prerequisite]:
        """Get list of missing optional prerequisites"""
        return [p for p in self.prerequisites if not p.required and not p.installed]

    def get_installed(self) -> List[Prerequisite]:
        """Get list of installed prerequisites"""
        return [p for p in self.prerequisites if p.installed]

    def all_required_met(self) -> bool:
        """Check if all required prerequisites are met"""
        return len(self.get_missing_required()) == 0
