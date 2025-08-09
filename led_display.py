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
        
        # Helper function to get next useful train (≥2 minutes away)
        def get_next_train(times_list):
            if not times_list:
                return None
            # Find first train that's at least 2 minutes away
            for time in times_list:
                if time >= 2:
                    return time
            # If no trains ≥2 minutes, show the closest one
            return times_list[0] if times_list else None
        
        # Skip if no useful data for either direction
        next_uptown = get_next_train(estimate.uptown)
        next_downtown = get_next_train(estimate.downtown)
        if next_uptown is None and next_downtown is None:
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
        if next_uptown is not None:
            # Draw up arrow
            draw_up_arrow(draw, x_pos, 0)
            x_pos += 4  # Arrow width + 1 pixel spacing
            
            # Draw next uptown time
            uptown_text = str(next_uptown)
            text(draw, (x_pos, 0), uptown_text, fill="white", font=proportional(TINY_FONT))
            text_width = len(uptown_text) * 3  # TINY_FONT is ~3 pixels per char
            x_pos += text_width + 2  # Add 2 pixels spacing
        
        # Draw downtown if available
        if next_downtown is not None:
            # Draw down arrow
            draw_down_arrow(draw, x_pos, 0)
            x_pos += 4  # Arrow width + 1 pixel spacing
            
            # Draw next downtown time
            downtown_text = str(next_downtown)
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
                        # Remember what line we were showing before refresh
                        current_line = None
                        if estimates:
                            valid_estimates_before = [est for est in estimates if est.uptown or est.downtown]
                            if valid_estimates_before and current_page < len(valid_estimates_before):
                                current_line = valid_estimates_before[current_page].line
                        
                        estimates = mta.get_times(args.lines)
                        last_data_refresh = current_time
                        
                        # Try to find the same line in the new data
                        if current_line:
                            valid_estimates_after = [est for est in estimates if est.uptown or est.downtown]
                            for i, est in enumerate(valid_estimates_after):
                                if est.line == current_line:
                                    current_page = i
                                    break
                    
                    if estimates:
                        # Filter out estimates with no data
                        valid_estimates = [est for est in estimates if est.uptown or est.downtown]
                        
                        if valid_estimates:
                            # Ensure current_page is within bounds after data refresh
                            if current_page >= len(valid_estimates):
                                current_page = 0
                            # Display current valid estimate
                            current_estimate = valid_estimates[current_page % len(valid_estimates)]
                            display_estimate(device, current_estimate)
                            
                            # Show which page we're on with next useful trains
                            def get_next_train_for_display(times_list):
                                if not times_list:
                                    return "N/A"
                                # Find first train that's at least 2 minutes away
                                for time in times_list:
                                    if time >= 2:
                                        return str(time)
                                # If no trains ≥2 minutes, show the closest one
                                return str(times_list[0])
                            
                            uptown_text = get_next_train_for_display(current_estimate.uptown)
                            downtown_text = get_next_train_for_display(current_estimate.downtown)
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