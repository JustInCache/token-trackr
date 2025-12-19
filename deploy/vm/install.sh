#!/bin/bash
# Token Trackr Installation Script
# ===================================
# Installs Token Trackr on Linux VMs (Ubuntu/Debian, RHEL/CentOS, Amazon Linux)
# Supports: AWS EC2, Azure VM, GCP Compute Engine, On-prem Linux

set -euo pipefail

# Configuration
INSTALL_DIR="/opt/token-trackr"
CONFIG_DIR="/etc/token-trackr"
LOG_DIR="/var/log/token-trackr"
USER="tokentrackr"
GROUP="tokentrackr"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect OS"
        exit 1
    fi
    
    log_info "Detected OS: $OS $VERSION"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y python3.11 python3.11-venv python3-pip curl wget
            ;;
        rhel|centos|rocky|almalinux|amzn)
            if [[ "$OS" == "amzn" ]]; then
                yum install -y python3.11 python3.11-pip curl wget
            else
                dnf install -y python3.11 python3.11-pip curl wget
            fi
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
}

# Create system user
create_user() {
    log_info "Creating system user..."
    
    if ! id "$USER" &>/dev/null; then
        useradd --system --shell /usr/sbin/nologin --home-dir "$INSTALL_DIR" "$USER"
    else
        log_warn "User $USER already exists"
    fi
}

# Create directories
create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$INSTALL_DIR/reports"
    
    chown -R "$USER:$GROUP" "$INSTALL_DIR"
    chown -R "$USER:$GROUP" "$LOG_DIR"
}

# Install Python application
install_application() {
    log_info "Installing Token Trackr..."
    
    # Create virtual environment
    python3.11 -m venv "$INSTALL_DIR/venv"
    
    # Upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
    
    # Install the application
    # Option 1: From PyPI (if published)
    # "$INSTALL_DIR/venv/bin/pip" install token-trackr
    
    # Option 2: From local source
    if [[ -d "/tmp/token-trackr-source" ]]; then
        "$INSTALL_DIR/venv/bin/pip" install /tmp/token-trackr-source
    else
        log_warn "No source found, installing dependencies only"
        "$INSTALL_DIR/venv/bin/pip" install \
            fastapi uvicorn pydantic pydantic-settings \
            sqlalchemy asyncpg psycopg2-binary alembic \
            httpx aiohttp apscheduler pyyaml structlog \
            tenacity prometheus-client redis boto3 openai \
            google-generativeai
    fi
    
    chown -R "$USER:$GROUP" "$INSTALL_DIR"
}

# Copy configuration files
copy_config() {
    log_info "Setting up configuration..."
    
    # Copy environment file
    if [[ ! -f "$CONFIG_DIR/token-trackr.env" ]]; then
        cat > "$CONFIG_DIR/token-trackr.env" << 'EOF'
# Token Trackr Configuration
# ============================

# Application
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000
APP_SECRET_KEY=change-this-secret-key-in-production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/token_trackr

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Metrics
METRICS_ENABLED=true

# Scheduler (for worker only)
SCHEDULER_ENABLED=false
DAILY_AGGREGATION_HOUR=2
MONTHLY_AGGREGATION_DAY=1
EOF
        chmod 600 "$CONFIG_DIR/token-trackr.env"
    else
        log_warn "Configuration already exists, not overwriting"
    fi
    
    # Copy pricing config
    if [[ -f "/tmp/token-trackr-source/config/pricing.yaml" ]]; then
        cp /tmp/token-trackr-source/config/pricing.yaml "$CONFIG_DIR/"
    fi
    
    chown -R root:$GROUP "$CONFIG_DIR"
    chmod 750 "$CONFIG_DIR"
}

# Install systemd services
install_systemd() {
    log_info "Installing systemd services..."
    
    # API service
    cat > /etc/systemd/system/token-trackr-api.service << EOF
[Unit]
Description=Token Trackr API
Documentation=https://github.com/your-org/token-trackr
After=network.target postgresql.service redis.service
Wants=postgresql.service

[Service]
Type=exec
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/token-trackr.env
ExecStart=$INSTALL_DIR/venv/bin/uvicorn backend.main:app --host \${APP_HOST} --port \${APP_PORT}
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=token-trackr-api

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$LOG_DIR $INSTALL_DIR/reports

[Install]
WantedBy=multi-user.target
EOF

    # Worker service
    cat > /etc/systemd/system/token-trackr-worker.service << EOF
[Unit]
Description=Token Trackr Worker
Documentation=https://github.com/your-org/token-trackr
After=network.target postgresql.service token-trackr-api.service
Wants=postgresql.service

[Service]
Type=exec
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/token-trackr.env
Environment=SCHEDULER_ENABLED=true
ExecStart=$INSTALL_DIR/venv/bin/python -m backend.jobs.scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=token-trackr-worker

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$LOG_DIR $INSTALL_DIR/reports

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
}

# Install systemd timers (alternative to APScheduler)
install_timers() {
    log_info "Installing systemd timers..."
    
    # Daily aggregation timer
    cat > /etc/systemd/system/token-trackr-daily.service << EOF
[Unit]
Description=Token Trackr Daily Aggregation
After=network.target postgresql.service

[Service]
Type=oneshot
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/token-trackr.env
ExecStart=$INSTALL_DIR/venv/bin/python -c "import asyncio; from backend.jobs.aggregation import DailyAggregationJob; asyncio.run(DailyAggregationJob().run())"
StandardOutput=journal
StandardError=journal
SyslogIdentifier=token-trackr-daily
EOF

    cat > /etc/systemd/system/token-trackr-daily.timer << EOF
[Unit]
Description=Token Trackr Daily Aggregation Timer

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

    # Monthly aggregation timer
    cat > /etc/systemd/system/token-trackr-monthly.service << EOF
[Unit]
Description=Token Trackr Monthly Aggregation
After=network.target postgresql.service

[Service]
Type=oneshot
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/token-trackr.env
ExecStart=$INSTALL_DIR/venv/bin/python -c "import asyncio; from backend.jobs.aggregation import MonthlyAggregationJob; asyncio.run(MonthlyAggregationJob().run())"
StandardOutput=journal
StandardError=journal
SyslogIdentifier=token-trackr-monthly
EOF

    cat > /etc/systemd/system/token-trackr-monthly.timer << EOF
[Unit]
Description=Token Trackr Monthly Aggregation Timer

[Timer]
OnCalendar=*-*-01 03:00:00
Persistent=true
RandomizedDelaySec=600

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
}

# Setup log rotation
setup_logrotate() {
    log_info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/token-trackr << EOF
$LOG_DIR/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $USER $GROUP
    sharedscripts
    postrotate
        systemctl reload token-trackr-api 2>/dev/null || true
    endscript
}
EOF
}

# Enable and start services
enable_services() {
    log_info "Enabling services..."
    
    systemctl enable token-trackr-api
    systemctl enable token-trackr-daily.timer
    systemctl enable token-trackr-monthly.timer
    
    log_info "Starting services..."
    systemctl start token-trackr-api
    systemctl start token-trackr-daily.timer
    systemctl start token-trackr-monthly.timer
}

# Print status
print_status() {
    log_info "Installation complete!"
    echo ""
    echo "============================================"
    echo "Token Trackr Installation Summary"
    echo "============================================"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo "Configuration:          $CONFIG_DIR/token-trackr.env"
    echo "Logs:                   $LOG_DIR or journalctl -u token-trackr-api"
    echo ""
    echo "Services:"
    echo "  - token-trackr-api.service     (main API)"
    echo "  - token-trackr-worker.service  (optional scheduler)"
    echo "  - token-trackr-daily.timer     (daily aggregation)"
    echo "  - token-trackr-monthly.timer   (monthly aggregation)"
    echo ""
    echo "Commands:"
    echo "  sudo systemctl status token-trackr-api"
    echo "  sudo systemctl restart token-trackr-api"
    echo "  sudo journalctl -u token-trackr-api -f"
    echo ""
    echo "IMPORTANT: Edit $CONFIG_DIR/token-trackr.env"
    echo "           with your database and other settings!"
    echo ""
}

# Main installation flow
main() {
    log_info "Starting Token Trackr installation..."
    
    check_root
    detect_os
    install_dependencies
    create_user
    create_directories
    install_application
    copy_config
    install_systemd
    install_timers
    setup_logrotate
    enable_services
    print_status
}

# Run main
main "$@"

