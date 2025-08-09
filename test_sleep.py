#!/usr/bin/env python3
"""
Test the sleep schedule functionality
"""

def is_sleep_time_test(current_hour, sleep_start_hour=12, wake_hour=6):
    """Test version of is_sleep_time with injectable hour"""
    # Sleep from sleep_start_hour (12) until wake_hour (6)
    if sleep_start_hour < wake_hour:
        # Normal case: sleep 12-18 (6pm)
        return sleep_start_hour <= current_hour < wake_hour
    else:
        # Overnight case: sleep 12 (noon) until 6am next day
        return current_hour >= sleep_start_hour or current_hour < wake_hour

def test_sleep_schedule():
    """Test different times against sleep schedule"""
    
    # Test cases: (hour, expected_result, description)
    test_cases = [
        (5, True, "5am - should be sleeping"),
        (6, False, "6am - wake time, should be awake"), 
        (11, False, "11am - should be awake"),
        (12, True, "12pm - sleep time, should be sleeping"),
        (18, True, "6pm - should be sleeping"),
        (23, True, "11pm - should be sleeping"),
    ]
    
    print("Testing sleep schedule (sleep from 12pm to 6am):")
    print("=" * 50)
    
    for hour, expected, description in test_cases:
        result = is_sleep_time_test(hour, sleep_start_hour=12, wake_hour=6)
        status = "✓" if result == expected else "✗"
        
        print(f"{status} {hour:2d}:00 - {description} -> {'sleeping' if result else 'awake'}")

if __name__ == "__main__":
    test_sleep_schedule()