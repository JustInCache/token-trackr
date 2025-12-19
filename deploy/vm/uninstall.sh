#!/bin/bash
# Token Trackr Uninstall Script
# ================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR]${NC} This script must be run as root"
    exit 1
fi

echo "============================================"
echo "Token Trackr Uninstall"
echo "============================================"
echo ""
echo "This will remove:"
echo "  - Token Trackr services"
echo "  - Installation directory (/opt/token-trackr)"
echo "  - System user (tokentrackr)"
echo ""
echo "This will NOT remove:"
echo "  - Configuration (/etc/token-trackr)"
echo "  - Logs (/var/log/token-trackr)"
echo "  - Database data"
echo ""

read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstall cancelled"
    exit 0
fi

# Stop services
log_info "Stopping services..."
systemctl stop token-trackr-api 2>/dev/null || true
systemctl stop token-trackr-worker 2>/dev/null || true
systemctl stop token-trackr-daily.timer 2>/dev/null || true
systemctl stop token-trackr-monthly.timer 2>/dev/null || true

# Disable services
log_info "Disabling services..."
systemctl disable token-trackr-api 2>/dev/null || true
systemctl disable token-trackr-worker 2>/dev/null || true
systemctl disable token-trackr-daily.timer 2>/dev/null || true
systemctl disable token-trackr-monthly.timer 2>/dev/null || true

# Remove systemd files
log_info "Removing systemd files..."
rm -f /etc/systemd/system/token-trackr-api.service
rm -f /etc/systemd/system/token-trackr-worker.service
rm -f /etc/systemd/system/token-trackr-daily.service
rm -f /etc/systemd/system/token-trackr-daily.timer
rm -f /etc/systemd/system/token-trackr-monthly.service
rm -f /etc/systemd/system/token-trackr-monthly.timer
systemctl daemon-reload

# Remove logrotate config
log_info "Removing logrotate config..."
rm -f /etc/logrotate.d/token-trackr

# Remove installation directory
log_info "Removing installation directory..."
rm -rf /opt/token-trackr

# Remove user
log_info "Removing system user..."
userdel tokentrackr 2>/dev/null || true

log_info "Uninstall complete!"
echo ""
echo "Configuration and logs were preserved:"
echo "  - /etc/token-trackr"
echo "  - /var/log/token-trackr"
echo ""
echo "Remove manually if no longer needed."

