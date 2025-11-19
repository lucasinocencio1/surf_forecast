"""
geocoding api client for converting city names to coordinates
https://geopy.readthedocs.io/en/stable/
"""

from geopy.geocoders import Nominatim
import sys

def geocode_location(city_name: str) -> tuple[float, float, str]:
    """
    convert city name to latitude and longitude coordinates
    
    args:
        city_name: name of the city or location
    
    returns:
        tuple of (latitude, longitude, full_location_name)
    
    raises:
        ValueError: if location cannot be found
    """
    geolocator = Nominatim(user_agent="surf_forecast_mcp")
    location = geolocator.geocode(city_name)
    
    if location is None:
        raise ValueError(f"could not find location: {city_name}")
    
    return location.latitude, location.longitude, location.address

if __name__ == "__main__":
    city_query = " ".join(sys.argv[1:]).strip() or "Lisbon" #example: python api/geocoding.py "Lisbon"
    try:
        lat, lon, addr = geocode_location(city_query)
        print(addr)
        print(f"{lat},{lon}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise
