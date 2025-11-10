"""
Dictionary Management Service for Gattrose-NG
Downloads, deduplicates, and manages password dictionaries from online sources
"""

import requests
import gzip
import sqlite3
import io
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Optional


class DictionaryManager:
    """Manages password dictionaries with deduplication"""

    # Public password dictionary sources
    DICT_SOURCES = {
        'rockyou': {
            'url': 'https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt',
            'size': '133MB',
            'count': 14344395
        },
        'weakpass_100k': {
            'url': 'https://weakpass.com/wordlist/90',
            'size': '822KB',
            'count': 100000
        },
        'darkc0de': {
            'url': 'https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/darkc0de.txt',
            'size': '120KB',
            'count': 16593
        },
        'common_credentials': {
            'url': 'https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-1000000.txt',
            'size': '8.2MB',
            'count': 1000000
        },
        'probable_v2': {
            'url': 'https://raw.githubusercontent.com/berzerk0/Probable-Wordlists/master/Real-Passwords/Top12Thousand-probable-v2.txt',
            'size': '97KB',
            'count': 12645
        }
    }

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("/opt/gattrose-ng/data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.dict_dir = self.data_dir / "dictionaries"
        self.dict_dir.mkdir(exist_ok=True)

        self.db_path = self.data_dir / "passwords.db"
        self.init_database()

    def init_database(self):
        """Initialize password database with deduplication"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Main passwords table
        c.execute('''
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password TEXT UNIQUE NOT NULL,
                password_hash TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                length INTEGER NOT NULL,
                complexity_score REAL NOT NULL,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Indexes for fast lookups
        c.execute('CREATE INDEX IF NOT EXISTS idx_password_hash ON passwords(password_hash)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_length ON passwords(length)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_complexity ON passwords(complexity_score)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_frequency ON passwords(frequency)')

        # Download history
        c.execute('''
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                passwords_imported INTEGER DEFAULT 0,
                duplicates_found INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

        print(f"[DICT] Database initialized at {self.db_path}")

    def download_all_sources(self, progress_callback=None):
        """Download all dictionary sources"""
        total = len(self.DICT_SOURCES)
        for i, (name, info) in enumerate(self.DICT_SOURCES.items(), 1):
            print(f"[DICT] Downloading {name} ({i}/{total})...")

            if progress_callback:
                progress_callback(name, i, total)

            success = self.download_source(name, info['url'])

            if success:
                print(f"[DICT] ✓ Downloaded and imported {name}")
            else:
                print(f"[DICT] ✗ Failed to download {name}")

    def download_source(self, name: str, url: str) -> bool:
        """Download and import a dictionary source"""
        try:
            print(f"[DICT] Fetching {url}...")

            # Download
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            # Save to file
            dest_file = self.dict_dir / f"{name}.txt"

            # Handle gzipped content
            if url.endswith('.gz') or 'gzip' in response.headers.get('Content-Type', ''):
                with gzip.open(io.BytesIO(response.content)) as f:
                    with open(dest_file, 'wb') as out:
                        out.write(f.read())
            else:
                with open(dest_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

            print(f"[DICT] Saved to {dest_file}")

            # Import into database
            self.import_dictionary(dest_file, name)

            return True

        except Exception as e:
            print(f"[DICT] Error downloading {name}: {e}")
            return False

    def import_dictionary(self, file_path: Path, source: str):
        """Import dictionary file into database with deduplication"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        imported = 0
        duplicates = 0
        batch = []
        batch_size = 10000

        print(f"[DICT] Importing {file_path}...")

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    password = line.strip()
                    if not password or len(password) > 128:  # Skip empty or too long
                        continue

                    # Calculate hash for dedup
                    pwd_hash = hashlib.md5(password.encode()).hexdigest()

                    # Calculate complexity
                    complexity = self.calculate_complexity(password)

                    batch.append((
                        password,
                        pwd_hash,
                        source,
                        len(password),
                        complexity
                    ))

                    if len(batch) >= batch_size:
                        imported_count, dup_count = self._insert_batch(c, batch)
                        imported += imported_count
                        duplicates += dup_count
                        batch = []

                        if imported % 100000 == 0:
                            conn.commit()
                            print(f"[DICT] Progress: {imported:,} imported, {duplicates:,} duplicates")

            # Insert remaining
            if batch:
                imported_count, dup_count = self._insert_batch(c, batch)
                imported += imported_count
                duplicates += dup_count

            # Record download history
            c.execute('''
                INSERT INTO download_history (source_name, passwords_imported, duplicates_found)
                VALUES (?, ?, ?)
            ''', (source, imported, duplicates))

            conn.commit()

            print(f"[DICT] ✓ Imported {imported:,} passwords from {source}")
            print(f"[DICT] ✓ Skipped {duplicates:,} duplicates")

        except Exception as e:
            print(f"[DICT] Error importing {file_path}: {e}")
            conn.rollback()

        finally:
            conn.close()

    def _insert_batch(self, cursor, batch):
        """Insert batch of passwords with deduplication"""
        imported = 0
        duplicates = 0

        for pwd_data in batch:
            try:
                cursor.execute('''
                    INSERT INTO passwords (password, password_hash, source, length, complexity_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', pwd_data)
                imported += 1
            except sqlite3.IntegrityError:
                # Duplicate - update frequency
                cursor.execute('''
                    UPDATE passwords
                    SET frequency = frequency + 1
                    WHERE password_hash = ?
                ''', (pwd_data[1],))
                duplicates += 1

        return imported, duplicates

    def calculate_complexity(self, password: str) -> float:
        """Calculate password complexity score 0-100"""
        score = 0

        # Length score (max 40 points)
        score += min(len(password) * 4, 40)

        # Character variety (60 points total)
        if any(c.isupper() for c in password):
            score += 10  # Uppercase
        if any(c.islower() for c in password):
            score += 10  # Lowercase
        if any(c.isdigit() for c in password):
            score += 15  # Numbers
        if any(not c.isalnum() for c in password):
            score += 25  # Special characters

        return min(score, 100)

    def export_optimized_wordlist(self, output_file: Path,
                                  max_passwords: int = 10000000,
                                  min_length: int = 8,
                                  max_length: int = 63) -> int:
        """
        Export optimized wordlist sorted by frequency and complexity
        WPA passwords must be 8-63 characters
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        print(f"[DICT] Exporting wordlist to {output_file}...")
        print(f"[DICT] Length range: {min_length}-{max_length}, Max passwords: {max_passwords:,}")

        # Export most common passwords first (low complexity, high frequency)
        # Then less common but still likely (higher complexity)
        c.execute('''
            SELECT password FROM passwords
            WHERE length >= ? AND length <= ?
            ORDER BY frequency DESC, complexity_score ASC
            LIMIT ?
        ''', (min_length, max_length, max_passwords))

        count = 0
        with open(output_file, 'w', encoding='utf-8') as f:
            for row in c.fetchall():
                f.write(row[0] + '\n')
                count += 1

                if count % 1000000 == 0:
                    print(f"[DICT] Exported {count:,} passwords...")

        conn.close()

        print(f"[DICT] ✓ Exported {count:,} passwords to {output_file}")
        return count

    def get_statistics(self) -> dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM passwords')
        total = c.fetchone()[0]

        c.execute('SELECT COUNT(DISTINCT source) FROM passwords')
        sources = c.fetchone()[0]

        c.execute('SELECT AVG(complexity_score) FROM passwords')
        avg_complexity = c.fetchone()[0] or 0

        c.execute('SELECT SUM(frequency) FROM passwords')
        total_occurrences = c.fetchone()[0] or 0

        conn.close()

        return {
            'total_passwords': total,
            'unique_sources': sources,
            'average_complexity': round(avg_complexity, 2),
            'total_occurrences': total_occurrences,
            'database_size': self.db_path.stat().st_size if self.db_path.exists() else 0
        }

    def search_password(self, password: str) -> Optional[dict]:
        """Check if password exists in database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        pwd_hash = hashlib.md5(password.encode()).hexdigest()

        c.execute('''
            SELECT source, frequency, complexity_score, first_seen
            FROM passwords
            WHERE password_hash = ?
        ''', (pwd_hash,))

        result = c.fetchone()
        conn.close()

        if result:
            return {
                'found': True,
                'source': result[0],
                'frequency': result[1],
                'complexity': result[2],
                'first_seen': result[3]
            }

        return {'found': False}
