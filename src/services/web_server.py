"""
Web Server Manager for Gattrose-NG
Provides HTTPS web interface for mobile/remote control
Uses nginx with high security settings
"""

import os
import subprocess
import socket
from pathlib import Path
from datetime import datetime, timedelta


class WebServerManager:
    """Manages HTTPS web server with nginx"""

    def __init__(self, port=8443):
        self.port = port
        self.project_root = Path(__file__).parent.parent.parent
        self.web_root = self.project_root / "web"
        self.ssl_dir = self.project_root / "data" / "ssl"
        self.nginx_config_dir = self.project_root / "data" / "nginx"
        self.pid_file = self.nginx_config_dir / "nginx.pid"

        # Security: 2-hour timeout timer
        self.start_time = None
        self.timeout_hours = 2
        self.timeout_callback = None

        # Create directories
        self.web_root.mkdir(parents=True, exist_ok=True)
        self.ssl_dir.mkdir(parents=True, exist_ok=True)
        self.nginx_config_dir.mkdir(parents=True, exist_ok=True)

    def cert_exists(self):
        """Check if SSL certificate exists"""
        cert_file = self.ssl_dir / "gattrose.crt"
        key_file = self.ssl_dir / "gattrose.key"
        return cert_file.exists() and key_file.exists()

    def generate_certificate(self, hostname="localhost"):
        """Generate self-signed SSL certificate"""
        try:
            cert_file = self.ssl_dir / "gattrose.crt"
            key_file = self.ssl_dir / "gattrose.key"

            # Generate DH parameters for perfect forward secrecy
            dhparam_file = self.ssl_dir / "dhparam.pem"
            if not dhparam_file.exists():
                print("[*] Generating DH parameters (this may take a while)...")
                subprocess.run([
                    'openssl', 'dhparam', '-out', str(dhparam_file), '2048'
                ], check=True)

            # Generate private key
            print("[*] Generating private key...")
            subprocess.run([
                'openssl', 'genrsa', '-out', str(key_file), '4096'
            ], check=True)

            # Generate certificate signing request and self-signed certificate
            print("[*] Generating self-signed certificate...")
            subprocess.run([
                'openssl', 'req', '-new', '-x509',
                '-key', str(key_file),
                '-out', str(cert_file),
                '-days', '3650',
                '-subj', f'/CN={hostname}/O=Gattrose-NG/C=US'
            ], check=True)

            # Set proper permissions
            os.chmod(key_file, 0o600)
            os.chmod(cert_file, 0o644)

            print("[✓] SSL certificate generated successfully")
            return True

        except Exception as e:
            print(f"[!] Error generating certificate: {e}")
            return False

    def create_nginx_config(self):
        """Create high-security nginx configuration"""
        config_file = self.nginx_config_dir / "gattrose.conf"

        cert_file = self.ssl_dir / "gattrose.crt"
        key_file = self.ssl_dir / "gattrose.key"
        dhparam_file = self.ssl_dir / "dhparam.pem"
        access_log = self.nginx_config_dir / "access.log"
        error_log = self.nginx_config_dir / "error.log"

        config = f"""# Gattrose-NG High-Security HTTPS Configuration
# Generated: {datetime.now().isoformat()}

# Run as current user
user {os.getenv('USER', 'root')};
worker_processes auto;
pid {self.pid_file};

events {{
    worker_connections 1024;
    use epoll;
}}

http {{
    # Basic Settings
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;  # Hide nginx version

    # Logging
    access_log {access_log};
    error_log {error_log} warn;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # HTTPS Server
    server {{
        listen {self.port} ssl http2;
        listen [::]:{self.port} ssl http2;

        server_name _;

        # SSL Configuration - SUPER HIGH SECURITY
        ssl_certificate {cert_file};
        ssl_certificate_key {key_file};
        ssl_dhparam {dhparam_file};

        # SSL Protocols - Only TLS 1.2 and 1.3
        ssl_protocols TLSv1.2 TLSv1.3;

        # SSL Ciphers - Modern, strong ciphers only
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
        ssl_prefer_server_ciphers off;

        # Perfect Forward Secrecy
        ssl_ecdh_curve secp384r1;

        # SSL Session Settings
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;

        # OCSP Stapling
        ssl_stapling off;  # Disabled for self-signed cert
        ssl_stapling_verify off;

        # Security Headers - Maximum Protection
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

        # Root directory
        root {self.web_root};
        index index.html;

        # Main location
        location / {{
            try_files $uri $uri/ /index.html;

            # CORS headers for API calls
            add_header Access-Control-Allow-Origin "https://$host:{self.port}" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        }}

        # API endpoint with rate limiting
        location /api/ {{
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Security headers
            add_header X-Content-Type-Options "nosniff" always;
            add_header X-Frame-Options "DENY" always;
        }}

        # Deny access to hidden files
        location ~ /\. {{
            deny all;
            access_log off;
            log_not_found off;
        }}

        # Deny access to sensitive files
        location ~ \.(py|pyc|db|sql|sqlite|conf)$ {{
            deny all;
            access_log off;
            log_not_found off;
        }}
    }}
}}
"""

        with open(config_file, 'w') as f:
            f.write(config)

        print(f"[✓] Nginx configuration created: {config_file}")
        return config_file

    def start(self, sudo_password=None):
        """Start nginx web server (requires sudo authentication)"""
        try:
            # Verify sudo access
            if not self.verify_sudo_access(sudo_password):
                raise Exception("Sudo authentication required to start web server")

            # Create nginx config
            config_file = self.create_nginx_config()

            # Check if nginx is installed
            try:
                subprocess.run(['which', 'nginx'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                raise Exception("nginx is not installed. Please install: sudo apt-get install nginx")

            # Test nginx configuration
            result = subprocess.run(
                ['nginx', '-t', '-c', str(config_file)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise Exception(f"Nginx config test failed: {result.stderr}")

            # Start nginx with sudo
            print("[*] Starting nginx with sudo...")
            if sudo_password:
                process = subprocess.Popen(
                    ['sudo', '-S', 'nginx', '-c', str(config_file)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=sudo_password + '\n')

                if process.returncode != 0:
                    raise Exception(f"Failed to start nginx: {stderr}")
            else:
                subprocess.run(
                    ['sudo', 'nginx', '-c', str(config_file)],
                    check=True,
                    capture_output=True
                )

            # Start Flask API server
            self.start_api_server()

            # Record start time for 2-hour timeout
            from datetime import datetime
            self.start_time = datetime.now()

            print(f"[✓] Web server started on port {self.port}")
            print(f"[!] SECURITY: Server will auto-stop after {self.timeout_hours} hours")
            return True

        except Exception as e:
            print(f"[!] Error starting web server: {e}")
            raise

    def verify_sudo_access(self, password=None):
        """Verify sudo access with password"""
        try:
            if password:
                process = subprocess.Popen(
                    ['sudo', '-S', 'true'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=password + '\n')
                return process.returncode == 0
            else:
                # Check if already authenticated
                result = subprocess.run(['sudo', '-n', 'true'], capture_output=True)
                return result.returncode == 0
        except Exception:
            return False

    def check_timeout(self):
        """Check if 2-hour timeout has been reached"""
        if not self.start_time:
            return False

        from datetime import datetime, timedelta
        elapsed = datetime.now() - self.start_time
        timeout_duration = timedelta(hours=self.timeout_hours)

        return elapsed >= timeout_duration

    def get_remaining_time(self):
        """Get remaining time before timeout (in minutes)"""
        if not self.start_time:
            return 0

        from datetime import datetime, timedelta
        elapsed = datetime.now() - self.start_time
        timeout_duration = timedelta(hours=self.timeout_hours)
        remaining = timeout_duration - elapsed

        return int(remaining.total_seconds() / 60)

    def stop(self, sudo_password=None):
        """Stop nginx web server (requires sudo)"""
        try:
            if self.pid_file.exists():
                with open(self.pid_file) as f:
                    pid = f.read().strip()

                print(f"[*] Stopping nginx (PID: {pid})...")

                # Stop with sudo
                if sudo_password:
                    process = subprocess.Popen(
                        ['sudo', '-S', 'kill', '-QUIT', pid],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    process.communicate(input=sudo_password + '\n')
                else:
                    subprocess.run(['sudo', 'kill', '-QUIT', pid], check=False)

                # Remove PID file
                if self.pid_file.exists():
                    self.pid_file.unlink()

            # Stop Flask API server
            self.stop_api_server()

            # Clear start time
            self.start_time = None

            print("[✓] Web server stopped")
            return True

        except Exception as e:
            print(f"[!] Error stopping web server: {e}")
            return False

    def start_api_server(self):
        """Start Flask API server"""
        try:
            # Start Flask in background
            from . import web_api

            # Run Flask in separate process
            import multiprocessing
            self.api_process = multiprocessing.Process(
                target=web_api.run_api_server,
                args=(5000,)
            )
            self.api_process.daemon = True
            self.api_process.start()

            print("[✓] API server started on port 5000")

        except Exception as e:
            print(f"[!] Error starting API server: {e}")

    def stop_api_server(self):
        """Stop Flask API server"""
        try:
            if hasattr(self, 'api_process') and self.api_process.is_alive():
                self.api_process.terminate()
                self.api_process.join(timeout=5)
                print("[✓] API server stopped")
        except Exception as e:
            print(f"[!] Error stopping API server: {e}")

    def is_running(self):
        """Check if web server is running"""
        return self.pid_file.exists()
