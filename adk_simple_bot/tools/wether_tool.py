import requests

def get_weather(city_name: str) -> str:
    """Fetches the current live weather conditions for a city without requiring an API key."""
    city_name = city_name.strip()
    url = f"https://wttr.in/{city_name}?format=j1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            temp_c = current.get('temp_C')
            temp_f = current.get('temp_F')
            desc = current.get('weatherDesc')[0].get('value')
            wind = current.get('windspeedKmph')
            humidity = current.get('humidity')
            
            area = data.get('nearest_area', [{}])[0]
            region = area.get('region', [{}])[0].get('value')
            country = area.get('country', [{}])[0].get('value')
            resolved_loc = f"{city_name} ({region}, {country})" if region and country else city_name
            
            return (
                f"Location: {resolved_loc}\n"
                f"Condition: {desc}\n"
                f"Temperature: {temp_c}°C ({temp_f}°F)\n"
                f"Wind Speed: {wind} km/h\n"
                f"Humidity: {humidity}%"
            )
        else:
            return f"Error: Weather service wttr.in returned status code {response.status_code}."
    except Exception as e:
        return f"Error fetching weather from wttr.in: {str(e)}"
