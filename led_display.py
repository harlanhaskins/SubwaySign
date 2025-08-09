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

from mta_api import MTAApi


def create_device():
    """Create and configure the LED matrix device"""
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)
    return device


def format_subway_data(estimates):
    """Format subway estimates for LED display - just return the estimates"""
    return estimates


def draw_up_arrow(draw, x, y):
    """Draw a 3-pixel wide up arrow (5px tall, starting at row 1)"""
    # Arrow tip
    draw.point((x+1, y+1), fill="white")
    # Arrow body spreading down
    draw.point((x, y+2), fill="white")
    draw.point((x+1, y+2), fill="white") 
    draw.point((x+2, y+2), fill="white")
    # Stem going down
    draw.point((x+1, y+3), fill="white")
    draw.point((x+1, y+4), fill="white")
    draw.point((x+1, y+5), fill="white")


def draw_down_arrow(draw, x, y):
    """Draw a 3-pixel wide down arrow (5px tall, starting at row 1)"""
    # Stem going down
    draw.point((x+1, y+1), fill="white")
    draw.point((x+1, y+2), fill="white")
    draw.point((x+1, y+3), fill="white")
    # Arrow body
    draw.point((x, y+4), fill="white")
    draw.point((x+1, y+4), fill="white")
    draw.point((x+2, y+4), fill="white")
    # Arrow tip
    draw.point((x+1, y+5), fill="white")


def display_estimate(device, estimate):
    """Display a single subway line estimate on LED matrix"""
    with canvas(device) as draw:
        if not estimate:
            text(draw, (0, 0), "No data", fill="white", font=proportional(TINY_FONT))
            return
        
        # Skip if no data for either direction
        if not estimate.uptown and not estimate.downtown:
            return
        
        # Display format: [LINE] [↑] [UP-TIMES] [↓] [DOWN-TIMES] (skip missing directions)
        # With 4 matrices (32x8), we have 32 pixels width, 8 pixels height
        x_pos = 1  # Start with 1px padding
        
        # Draw line name with colon
        line_text = f"{estimate.line}:"
        text(draw, (x_pos, 0), line_text, fill="white", font=proportional(TINY_FONT))
        text_width = len(line_text) * 3  # TINY_FONT is ~3 pixels per char
        x_pos += text_width + 1  # Add 1 pixel spacing
        
        # Draw uptown if available
        if estimate.uptown:
            # Draw up arrow
            draw_up_arrow(draw, x_pos, 0)
            x_pos += 4  # Arrow width + 1 pixel spacing
            
            # Draw uptown times (comma separated)
            uptown_text = ','.join(map(str, estimate.uptown[:3]))  # Max 3 times
            text(draw, (x_pos, 0), uptown_text, fill="white", font=proportional(TINY_FONT))
            text_width = len(uptown_text) * 3  # TINY_FONT is ~3 pixels per char
            x_pos += text_width + 2  # Add 2 pixels spacing
        
        # Draw downtown if available
        if estimate.downtown:
            # Draw down arrow
            draw_down_arrow(draw, x_pos, 0)
            x_pos += 4  # Arrow width + 1 pixel spacing
            
            # Draw downtown times (comma separated)
            downtown_text = ','.join(map(str, estimate.downtown[:3]))  # Max 3 times
            text(draw, (x_pos, 0), downtown_text, fill="white", font=proportional(TINY_FONT))
            text_width = len(downtown_text) * 3  # TINY_FONT is ~3 pixels per char
            x_pos += text_width + 2  # Add 2 pixels spacing


def main():
    parser = argparse.ArgumentParser(description='Display subway times on LED matrix')
    parser.add_argument('lines', nargs='+', help='Subway lines (F, M, R, W, 1, C, E, 6)')
    parser.add_argument('--refresh', '-r', type=int, default=30, 
                       help='Data refresh interval in seconds (default: 30)')
    parser.add_argument('--page-time', '-p', type=int, default=5,
                       help='Time to show each page in seconds (default: 5)')
    parser.add_argument('--once', action='store_true', 
                       help='Run once and exit (no continuous refresh)')
    args = parser.parse_args()

    try:
        # Initialize LED matrix
        device = create_device()
        
        # Initialize MTA API client
        mta = MTAApi()
        
        if args.once:
            # Run once and exit
            estimates = mta.get_times(args.lines)
            if estimates:
                display_estimate(device, estimates[0])
        else:
            # Continuous refresh loop with page cycling
            print(f"Starting LED display for lines: {', '.join(args.lines)}")
            print(f"Data refresh interval: {args.refresh} seconds")
            print(f"Page display time: {args.page_time} seconds")
            print("Press Ctrl+C to exit")
            
            current_page = 0
            last_data_refresh = 0
            estimates = []
            
            # Get initial data
            estimates = mta.get_times(args.lines)
            last_data_refresh = time.time()
            print(f"Initial data loaded - {len(estimates)} lines")
            
            while True:
                try:
                    current_time = time.time()
                    
                    # Refresh data if needed
                    if current_time - last_data_refresh >= args.refresh:
                        estimates = mta.get_times(args.lines)
                        last_data_refresh = current_time
                        current_page = 0  # Reset to first page on data refresh
                        print(f"Data refreshed - {len(estimates)} lines")
                    
                    if estimates:
                        # Filter out estimates with no data
                        valid_estimates = [est for est in estimates if est.uptown or est.downtown]
                        
                        if valid_estimates:
                            # Display current valid estimate
                            current_estimate = valid_estimates[current_page % len(valid_estimates)]
                            display_estimate(device, current_estimate)
                            
                            # Show which page we're on
                            uptown_text = ','.join(map(str, current_estimate.uptown[:3])) if current_estimate.uptown else "N/A"
                            downtown_text = ','.join(map(str, current_estimate.downtown[:3])) if current_estimate.downtown else "N/A"
                            print(f"Page {current_page + 1}/{len(valid_estimates)}: {current_estimate.line} U{uptown_text} D{downtown_text}")
                            
                            # Move to next page
                            current_page = (current_page + 1) % len(valid_estimates)
                        else:
                            # No valid data for any line
                            with canvas(device) as draw:
                                text(draw, (0, 0), "No trains", fill="white", font=proportional(TINY_FONT))
                            print("No valid train data available")
                    
                    time.sleep(args.page_time)
                    
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    with canvas(device) as draw:
                        text(draw, (0, 0), "Error", fill="white", font=proportional(SINCLAIR_FONT))
                    time.sleep(args.page_time)
                    
    except Exception as e:
        print(f"Error initializing LED matrix: {e}")
        print("Make sure SPI is enabled and the device is connected properly")
        sys.exit(1)


if __name__ == "__main__":
    main()