#!/bin/bash
#
# Install subway-sign as a systemd service
# Run this script on your Raspberry Pi to set up automatic startup
#

set -e

# Check if running as root (needed for systemctl)
if [[ $EUID -eq 0 ]]; then
   echo "Don't run this script as root. Run as the pi user instead."
   exit 1
fi

# Get the current directory (should be the SubwaySign directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/subway-sign.service"

echo "Installing subway-sign systemd service..."
echo "Working directory: $SCRIPT_DIR"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: subway-sign.service not found in $SCRIPT_DIR"
    exit 1
fi

# Check if secrets.json exists
if [ ! -f "$SCRIPT_DIR/secrets.json" ]; then
    echo "Error: secrets.json not found. Please copy secrets.json.template to secrets.json and add your API key."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Error: Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Update service file paths to match current directory
sed "s|/home/pi/SubwaySign|$SCRIPT_DIR|g" "$SERVICE_FILE" > "/tmp/subway-sign.service"

# Copy service file to systemd directory (requires sudo)
echo "Installing service file (requires sudo)..."
sudo cp "/tmp/subway-sign.service" "/etc/systemd/system/subway-sign.service"
sudo chown root:root "/etc/systemd/system/subway-sign.service"
sudo chmod 644 "/etc/systemd/system/subway-sign.service"

# Enable GPIO and SPI (if not already enabled)
echo "Checking SPI configuration..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null; then
    echo "Enabling SPI interface (requires sudo and reboot)..."
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    NEED_REBOOT=true
fi

# Reload systemd and enable service
echo "Enabling and starting subway-sign service..."
sudo systemctl daemon-reload
sudo systemctl enable subway-sign.service
sudo systemctl start subway-sign.service

# Show status
echo ""
echo "Installation complete!"
echo ""
echo "Service status:"
sudo systemctl status subway-sign.service --no-pager

echo ""
echo "Useful commands:"
echo "  sudo systemctl status subway-sign    # Check status"
echo "  sudo systemctl stop subway-sign      # Stop service"
echo "  sudo systemctl start subway-sign     # Start service"
echo "  sudo systemctl restart subway-sign   # Restart service"
echo "  sudo journalctl -u subway-sign -f    # View logs"

if [ "$NEED_REBOOT" = true ]; then
    echo ""
    echo "IMPORTANT: SPI was enabled. Please reboot your Raspberry Pi:"
    echo "  sudo reboot"
fi