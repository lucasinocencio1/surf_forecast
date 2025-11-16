"""
context formatting utilities for surf forecast models
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models import SurfForecast


def format_forecast_to_llm_context(forecast: "SurfForecast") -> str:
    """
    format forecast as concise, human-readable text optimized for llm context
    
    args:
        forecast: SurfForecast model instance
    
    returns:
        formatted string suitable for llm consumption
    """
    from services.helpers import degrees_to_compass
    
    lines = [
        f"# Surf Forecast: {forecast.location}",
        "",
        "## Current Conditions",
        f"Waves: {forecast.current_conditions.wave_height_m:.1f}m ({forecast.current_conditions.wave_period_s:.0f}s period)",
        f"  - Swell: {forecast.current_conditions.swell_wave_height_m:.1f}m from {degrees_to_compass(forecast.current_conditions.swell_wave_direction_deg).upper()}",
        f"  - Wind waves: {forecast.current_conditions.wind_wave_height_m:.1f}m",
        f"Wind: {forecast.current_conditions.wind_speed_knots:.0f} knots from {degrees_to_compass(forecast.current_conditions.wind_direction_deg).upper()} (gusts {forecast.current_conditions.wind_gusts_knots:.0f} knots)",
        f"Temperature: {forecast.current_conditions.temperature_c:.0f}°C",
        ""
    ]
    
    # add hourly forecast if available
    if forecast.hourly_forecast:
        lines.append("## Next Hours")
        for hour in forecast.hourly_forecast:
            # parse timestamp to get readable time
            try:
                if 'T' in hour.timestamp:
                    dt = datetime.fromisoformat(hour.timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                else:
                    time_str = hour.timestamp[-5:]
            except:
                time_str = hour.timestamp.split('T')[1] if 'T' in hour.timestamp else hour.timestamp[-5:]
            
            swell_dir = degrees_to_compass(hour.swell_wave_direction_deg).upper()
            wind_dir = degrees_to_compass(hour.wind_direction_deg).upper()
            lines.append(
                f"{time_str}: {hour.wave_height_m:.1f}m waves (swell {hour.swell_wave_height_m:.1f}m from {swell_dir}), "
                f"{hour.wind_speed_knots:.0f}kn wind from {wind_dir}"
            )
        lines.append("")
    
    lines.append("## 5-Day Forecast")
    
    for day in forecast.forecast_5day:
        wave_dir = degrees_to_compass(day.wave_direction_dominant_deg).upper()
        swell_dir = degrees_to_compass(day.swell_wave_direction_dominant_deg).upper()
        wind_dir = degrees_to_compass(day.wind_direction_dominant_deg).upper()
        
        lines.extend([
            f"{day.date}:",
            f"  Waves: {day.wave_height_max_m:.1f}m max (swell {day.swell_wave_height_max_m:.1f}m from {swell_dir})",
            f"  Wind: {day.wind_speed_max_knots:.0f} knots from {wind_dir}",
            f"  Temp: {day.temperature_min_c:.0f}-{day.temperature_max_c:.0f}°C"
        ])
    
    return "\n".join(lines)

