def dummy_wether(location):
    """
    A dummy function to simulate fetching weather information for a given location.
    
    Args:
        location (str): The location for which to fetch the weather.
    
    Returns:
        dict: A dictionary containing the weather information for the specified location.
    """
    # This is a simple simulation - replace with actual weather API call
    return {
        "location": location,
        "temperature": 25,
        "description": "Sunny"
    }