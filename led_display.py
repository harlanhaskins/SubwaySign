#!/usr/bin/env python3
"""
LED Matrix display for subway times
Displays subway arrival times on MAX7219 LED matrix via SPI
"""

import argparse
import sys
import time
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT

from subway_times import SubwayTimes


def create_device():
    """Create and configure the LED matrix device"""
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)
    return device


def format_subway_data(estimates):
    """Format subway estimates for LED display"""
    lines = []
    
    for estimate in estimates:
        line_name = estimate.line
        
        # Add uptown time if available
        if estimate.uptown is not None:
            lines.append(f"U{line_name} {estimate.uptown}")
        
        # Add downtown time if available  
        if estimate.downtown is not None:
            lines.append(f"D{line_name} {estimate.downtown}")
    
    return lines


def display_subway_times(device, lines):
    """Display formatted subway times on LED matrix"""
    if not lines:
        with canvas(device) as draw:
            text(draw, (0, 0), "No data", fill="white", font=proportional(TINY_FONT))
        return
    
    # Create scrolling text with all lines
    message = " | ".join(lines)
    
    # Show scrolling message
    show_message(device, message, fill="white", font=proportional(TINY_FONT), scroll_delay=0.1)


def main():
    parser = argparse.ArgumentParser(description='Display subway times on LED matrix')
    parser.add_argument('lines', nargs='+', help='Subway lines (F, M, R, W, 1, C, E, 6)')
    parser.add_argument('--refresh', '-r', type=int, default=30, 
                       help='Refresh interval in seconds (default: 30)')
    parser.add_argument('--once', action='store_true', 
                       help='Run once and exit (no continuous refresh)')
    args = parser.parse_args()

    try:
        # Initialize LED matrix
        device = create_device()
        
        # Initialize subway data fetcher
        subway = SubwayTimes()
        
        if args.once:
            # Run once and exit
            estimates = subway.get_times(args.lines)
            formatted_lines = format_subway_data(estimates)
            display_subway_times(device, formatted_lines)
        else:
            # Continuous refresh loop
            print(f"Starting LED display for lines: {', '.join(args.lines)}")
            print(f"Refresh interval: {args.refresh} seconds")
            print("Press Ctrl+C to exit")
            
            while True:
                try:
                    estimates = subway.get_times(args.lines)
                    formatted_lines = format_subway_data(estimates)
                    
                    print(f"Displaying: {' | '.join(formatted_lines)}")
                    display_subway_times(device, formatted_lines)
                    
                    time.sleep(args.refresh)
                    
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"Error fetching data: {e}")
                    with canvas(device) as draw:
                        text(draw, (0, 0), "Error", fill="white", font=proportional(TINY_FONT))
                    time.sleep(args.refresh)
                    
    except Exception as e:
        print(f"Error initializing LED matrix: {e}")
        print("Make sure SPI is enabled and the device is connected properly")
        sys.exit(1)


if __name__ == "__main__":
    main()