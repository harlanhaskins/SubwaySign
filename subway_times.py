#!/usr/bin/env python3
"""
Subway times CLI for RPi LED matrix display
Shows next uptown and downtown trains from 23rd Street
"""

import argparse
import sys
from datetime import datetime, timezone
from nyct_gtfs import NYCTFeed


class TrainEstimate:
    """Represents train time estimates for a specific line"""
    
    def __init__(self, line, uptown_mins=None, downtown_mins=None):
        self.line = line
        self.uptown = uptown_mins
        self.downtown = downtown_mins


class SubwayTimes:
    """Main class for fetching subway times from 23rd Street"""
    
    # 23rd Street stop IDs for different lines
    STOP_IDS = {
        'F': {'uptown': 'F20N', 'downtown': 'F20S'},  # 23 St (F/M)
        'M': {'uptown': 'F20N', 'downtown': 'F20S'},  # 23 St (F/M)
        'R': {'uptown': 'R23N', 'downtown': 'R23S'},  # 23 St (R/W)
        'W': {'uptown': 'R23N', 'downtown': 'R23S'},  # 23 St (R/W)
        '1': {'uptown': '120N', 'downtown': '120S'},  # 23 St (1)
        'C': {'uptown': 'A25N', 'downtown': 'A25S'},  # 23 St (C/E)
        'E': {'uptown': 'A25N', 'downtown': 'A25S'},  # 23 St (C/E)
        '6': {'uptown': '629N', 'downtown': '629S'},  # 23 St (6)
    }
    
    def get_times(self, lines):
        """Get train estimates for one or more lines"""
        # Handle single line input
        if isinstance(lines, str):
            lines = [lines]
        
        estimates = []
        
        for line in lines:
            line = line.upper()
            
            if line not in self.STOP_IDS:
                raise ValueError(f"Line '{line}' not supported. Use: F, M, R, W, 1, C, E, 6")
            
            try:
                feed = NYCTFeed(line)
                
                # Get uptown trains
                uptown_stop = self.STOP_IDS[line]['uptown']
                uptown_trips = feed.filter_trips(
                    line_id=[line],
                    headed_for_stop_id=[uptown_stop],
                    underway=True
                )
                
                # Get downtown trains
                downtown_stop = self.STOP_IDS[line]['downtown']
                downtown_trips = feed.filter_trips(
                    line_id=[line],
                    headed_for_stop_id=[downtown_stop],
                    underway=True
                )
                
                # Find next arrival times
                uptown_time = self._get_next_arrival(uptown_trips, uptown_stop)
                downtown_time = self._get_next_arrival(downtown_trips, downtown_stop)
                
                # Calculate minutes
                uptown_mins = self._calculate_minutes_away(uptown_time) if uptown_time else None
                downtown_mins = self._calculate_minutes_away(downtown_time) if downtown_time else None
                
                estimates.append(TrainEstimate(line, uptown_mins, downtown_mins))
                
            except Exception as e:
                raise Exception(f"Error fetching data for line {line}: {e}")
        
        return estimates
    
    def _calculate_minutes_away(self, arrival_time):
        """Calculate minutes until arrival"""
        if not arrival_time:
            return None
        
        # Both times should be timezone-unaware and in local NY time
        now = datetime.now()
        diff = arrival_time - now
        minutes = int(diff.total_seconds() / 60)
        return max(0, minutes)
    
    def _get_next_arrival(self, trips, stop_id):
        """Get the next realistic arrival time for a specific stop (skip trains < 2 minutes)"""
        arrivals = []
        
        for trip in trips:
            for stop_update in trip.stop_time_updates:
                if stop_update.stop_id == stop_id:
                    arrival_time = stop_update.arrival if stop_update.arrival else None
                    if arrival_time:
                        minutes_away = self._calculate_minutes_away(arrival_time)
                        if minutes_away is not None:
                            arrivals.append((arrival_time, minutes_away))
        
        # Sort by minutes away (ascending)
        arrivals.sort(key=lambda x: x[1])
        
        # Find first train that's >= 2 minutes away
        for arrival_time, minutes_away in arrivals:
            if minutes_away >= 2:
                return arrival_time
        
        # If no trains >= 2 minutes, return the closest one
        if arrivals:
            return arrivals[0][0]
        
        return None

def main():
    parser = argparse.ArgumentParser(description='Get next subway times from 23rd Street')
    parser.add_argument('lines', nargs='+', help='Subway lines (F, M, R, W, 1, C, E, 6)')
    args = parser.parse_args()

    try:
        subway = SubwayTimes()
        estimates = subway.get_times(args.lines)
        
        # Display results
        for estimate in estimates:
            if estimate.uptown is not None:
                print(f"↑ {estimate.line} {estimate.uptown}")
            if estimate.downtown is not None:
                print(f"↓ {estimate.line} {estimate.downtown}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()