#!/usr/bin/env python3
"""
MTA internal API client - using the same API as the official MTA app
"""

import requests
import json
import os
from datetime import datetime
from typing import List, Optional

class MTATrainEstimate:
    """Train estimate from MTA internal API"""
    
    def __init__(self, line: str, uptown_times: List[int] = None, downtown_times: List[int] = None):
        self.line = line
        self.uptown = uptown_times if uptown_times else []
        self.downtown = downtown_times if downtown_times else []

class MTAApi:
    """Client for MTA's internal API"""
    
    BASE_URL = "https://hub-mta-prod.camsys-apps.com/transit-services/v2"
    
    def __init__(self):
        """Initialize with API key from secrets file"""
        self.api_key = self._load_api_key()
    
    def _load_api_key(self) -> str:
        """Load API key from secrets.json file"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        secrets_path = os.path.join(script_dir, 'secrets.json')
        
        try:
            with open(secrets_path, 'r') as f:
                secrets = json.load(f)
                return secrets['mta_api_key']
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            raise Exception(f"Could not load MTA API key from secrets.json: {e}")
            
    def _get_api_key(self) -> str:
        """Get the API key"""
        return self.api_key
    
    # 23rd Street coordinates (approximate)
    LAT = 40.743397775491715
    LON = -73.99379700422287
    
    # Specific stop ID filters for 23rd Street (converted to arrivals API format)
    STOP_FILTERS = {
        'F': {'uptown': 'MTASBWY_D18N', 'downtown': 'MTASBWY_D18S'},  # 23 St F/M
        'M': {'uptown': 'MTASBWY_D18N', 'downtown': 'MTASBWY_D18S'},  # 23 St F/M (same as F)
        'R': {'uptown': 'MTASBWY_R19N', 'downtown': 'MTASBWY_R19S'},  # 23 St R/W
        'W': {'uptown': 'MTASBWY_R19N', 'downtown': 'MTASBWY_R19S'},  # 23 St R/W (same as R)
        '1': {'uptown': 'MTASBWY_130N', 'downtown': 'MTASBWY_130S'},  # 23 St 1
        'C': {'uptown': 'MTASBWY_A30N', 'downtown': 'MTASBWY_A30S'},  # 23 St C/E
        'E': {'uptown': 'MTASBWY_A30N', 'downtown': 'MTASBWY_A30S'},  # 23 St C/E (same as C)
        '6': {'uptown': 'MTASBWY_634N', 'downtown': 'MTASBWY_634S'},  # 23 St 6
    }
    
    def get_times(self, lines: List[str]) -> List[MTATrainEstimate]:
        """Get train times for specified lines near 23rd Street"""
        
        url = f"{self.BASE_URL}/arrivals-and-departures-for-location.json"
        params = {
            "key": self.api_key,
            "minutesAfter": 60,
            "lon": self.LON,
            "lat": self.LAT,
            "radius": 1000,
            "routeType": 1,  # Subway
            "maxCount": 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_response(data, lines)
            
        except Exception as e:
            raise Exception(f"Error fetching MTA data: {e}")
    
    def _parse_response(self, data, requested_lines) -> List[MTATrainEstimate]:
        """Parse API response into train estimates"""
        
        # Get arrivals from the correct structure
        arrivals = data.get('data', {}).get('entry', {}).get('arrivalsAndDepartures', [])
        
        # Group trains by line, direction, and trip ID to avoid duplicates
        trips_data = {}
        
        for item in arrivals:
            route_name = item.get('routeShortName', '')
            
            # Only include requested lines
            if route_name not in requested_lines:
                continue
            
            # Filter by specific stop ID if available
            stop_id = item.get('stopId', '')
            if route_name in self.STOP_FILTERS:
                direction = self._get_direction(item)
                if direction is None:
                    continue
                    
                expected_stop = self.STOP_FILTERS[route_name].get(direction)
                if expected_stop and stop_id != expected_stop:
                    continue  # Skip trains not at our target 23rd Street stop
                    
            else:
                direction = self._get_direction(item)
                if direction is None:
                    continue
                
            # Get arrival time
            arrival_minutes = self._get_arrival_minutes(item)
            if arrival_minutes is None:
                continue
            
            trip_id = item.get('tripId', '')
            if not trip_id:
                continue
                
            # Create unique key for this trip
            key = f"{route_name}_{direction}_{trip_id}"
            
            # Only keep the entry with predicted time if available, or the earliest time
            predicted_ms = item.get('predictedArrivalTime')
            has_prediction = predicted_ms and predicted_ms > 0
            
            if key not in trips_data:
                trips_data[key] = {
                    'route': route_name,
                    'direction': direction,
                    'minutes': arrival_minutes,
                    'has_prediction': has_prediction
                }
            else:
                # If we already have this trip, keep the one with predicted time,
                # or if both have/don't have predicted time, keep the earlier one
                existing = trips_data[key]
                if (has_prediction and not existing['has_prediction']) or \
                   (has_prediction == existing['has_prediction'] and arrival_minutes < existing['minutes']):
                    trips_data[key] = {
                        'route': route_name,
                        'direction': direction,
                        'minutes': arrival_minutes,
                        'has_prediction': has_prediction
                    }
        
        
        # Group by line and direction
        line_data = {}
        for trip_info in trips_data.values():
            route = trip_info['route']
            direction = trip_info['direction']
            minutes = trip_info['minutes']
            
            if route not in line_data:
                line_data[route] = {'uptown': [], 'downtown': []}
                
            line_data[route][direction].append(minutes)
        
        # Convert to estimates (already deduplicated by trip ID)
        estimates = []
        for line in requested_lines:
            if line in line_data:
                # Sort times for each direction
                uptown = sorted(line_data[line]['uptown'])
                downtown = sorted(line_data[line]['downtown'])
                
                # Filter out trains that are too close and remove very similar times
                def filter_useful_times(times_list):
                    if not times_list:
                        return []
                    
                    # Remove trains that are 0 minutes (at station or just left)
                    useful_times = [t for t in times_list if t >= 1]
                    
                    # If we have no useful times, keep the closest one
                    if not useful_times and times_list:
                        return [times_list[0]]
                    
                    # Remove duplicate or very close times (within 1 minute of each other)
                    deduplicated = []
                    for time in useful_times:
                        if not deduplicated or abs(time - deduplicated[-1]) >= 2:
                            deduplicated.append(time)
                    
                    return deduplicated[:3]  # Take first 3 useful trains
                
                uptown_filtered = filter_useful_times(uptown)
                downtown_filtered = filter_useful_times(downtown)
                
                estimates.append(MTATrainEstimate(line, uptown_filtered, downtown_filtered))
            else:
                # No data for this line
                estimates.append(MTATrainEstimate(line))
                
        return estimates
    
    def _get_direction(self, item) -> Optional[str]:
        """Determine if train is uptown or downtown"""
        direction = item.get('tripHeadsign', '').lower()
        
        if 'uptown' in direction or 'north' in direction:
            return 'uptown'
        elif 'downtown' in direction or 'south' in direction:
            return 'downtown'
        else:
            return None
    
    def _get_arrival_minutes(self, item) -> Optional[int]:
        """Extract arrival time in minutes from now"""
        try:
            # Try predicted time first, but only if it's not 0
            predicted_ms = item.get('predictedArrivalTime')
            scheduled_ms = item.get('scheduledArrivalTime')
            
            # Use predicted time if available and not 0, otherwise use scheduled
            if predicted_ms and predicted_ms > 0:
                arrival_ms = predicted_ms
                time_type = "predicted"
            else:
                arrival_ms = scheduled_ms
                time_type = "scheduled"
                
            if not arrival_ms:
                return None
                
            # Convert from milliseconds to datetime
            arrival_time = datetime.fromtimestamp(arrival_ms / 1000)
            now = datetime.now()
            
            # Calculate minutes from now
            diff = arrival_time - now
            minutes = int(diff.total_seconds() / 60)
            
            return max(0, minutes)  # Don't show negative times
            
        except (ValueError, TypeError):
            return None


def main():
    """Test the MTA API"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python mta_api.py F R 1")
        sys.exit(1)
        
    lines = [line.upper() for line in sys.argv[1:]]
    
    try:
        api = MTAApi()
        estimates = api.get_times(lines)
        
        for estimate in estimates:
            if estimate.uptown:
                uptown_str = ','.join(map(str, estimate.uptown))
                print(f"↑ {estimate.line} {uptown_str}")
            if estimate.downtown:
                downtown_str = ','.join(map(str, estimate.downtown))
                print(f"↓ {estimate.line} {downtown_str}")
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()