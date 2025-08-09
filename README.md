# SubwaySign

Real-time NYC subway arrival times on an LED matrix display for your apartment. Shows accurate train times from 23rd Street using the same internal API as the official MTA app.

## Setup

1. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   ```bash
   cp secrets.json.template secrets.json
   # Edit secrets.json and add your MTA API key
   ```

3. **Run the display:**
   ```bash
   # Test with CLI output
   python3 mta_api.py F R 1 6
   
   # Run on LED matrix (requires Raspberry Pi with SPI enabled)
   python3 led_display.py F M R W 1 C E 6
   ```

## Systemd Service (Raspberry Pi)

To run automatically at boot:

1. **Install as service:**
   ```bash
   ./install-service.sh
   ```

2. **Service management:**
   ```bash
   sudo systemctl status subway-sign    # Check status
   sudo systemctl stop subway-sign      # Stop service
   sudo systemctl start subway-sign     # Start service  
   sudo systemctl restart subway-sign   # Restart service
   sudo journalctl -u subway-sign -f    # View logs
   ```

## Features

- **Station-specific data** - Only shows trains actually stopping at 23rd Street
- **Real-time accuracy** - Uses MTA's internal API with proper trip deduplication
- **Smart filtering** - Shows only next useful train (≥2 minutes away)
- **Multiple train lines** - Supports F, M, R, W, 1, C, E, and 6 trains
- **LED matrix display** - Cycles through train lines with custom arrows
- **Direction aware** - Only shows directions that actually have service
- **Error handling** - Loading spinner and error messages for network issues
- **Sleep schedule** - Automatically sleeps at noon, wakes at 6am (configurable)
- **Systemd service** - Auto-start at boot with proper service management
- **Robust operation** - Graceful error recovery and cached data fallback

## Hardware

- Raspberry Pi (any model with GPIO)
- MAX7219 LED matrix display (4x 8x8 matrices recommended)
- SPI connection via GPIO pins

## Files

- `mta_api.py` - Core MTA API client with accurate timing data
- `led_display.py` - LED matrix display with page cycling  
- `secrets.json` - API key configuration (git ignored)
- `secrets.json.template` - Template for API key setup
