"""
pydantic models for structured surf forecast output with validation
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


class CurrentConditions(BaseModel):
    """current surf conditions with validation"""
    timestamp: str = Field(description="current time in iso format")
    wave_height_m: float = Field(ge=0, le=30, description="significant wave height in meters")
    swell_wave_height_m: float = Field(ge=0, le=30, description="swell wave height in meters")
    wind_wave_height_m: float = Field(ge=0, le=30, description="wind wave height in meters")
    wave_direction_deg: float = Field(ge=0, le=360, description="wave direction in degrees")
    swell_wave_direction_deg: float = Field(ge=0, le=360, description="swell wave direction in degrees")
    wave_period_s: float = Field(ge=0, le=30, description="wave period in seconds")
    swell_wave_period_s: float = Field(ge=0, le=30, description="swell wave period in seconds")
    wind_speed_knots: float = Field(ge=0, le=200, description="wind speed in knots")
    wind_direction_deg: float = Field(ge=0, le=360, description="wind direction in degrees")
    wind_gusts_knots: float = Field(ge=0, le=200, description="wind gusts in knots")
    temperature_c: float = Field(ge=-50, le=60, description="air temperature in celsius")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """validate timestamp is in iso format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"invalid iso format timestamp: {v}")
        return v

    @model_validator(mode='after')
    def validate_wave_components(self):
        """validate wave height components sum logically"""
        total = self.wave_height_m
        swell = self.swell_wave_height_m
        wind = self.wind_wave_height_m
        
        # allow some tolerance for measurement differences
        if swell + wind > total * 1.5:
            raise ValueError(
                f"wave components inconsistent: swell ({swell}) + wind ({wind}) "
                f"should not greatly exceed total ({total})"
            )
        return self


class DailyForecast(BaseModel):
    """daily surf forecast with validation"""
    date: str = Field(description="date in yyyy-mm-dd format")
    wave_height_max_m: float = Field(ge=0, le=30, description="maximum wave height in meters")
    swell_wave_height_max_m: float = Field(ge=0, le=30, description="maximum swell wave height in meters")
    wind_wave_height_max_m: float = Field(ge=0, le=30, description="maximum wind wave height in meters")
    wave_direction_dominant_deg: float = Field(ge=0, le=360, description="dominant wave direction in degrees")
    swell_wave_direction_dominant_deg: float = Field(ge=0, le=360, description="dominant swell wave direction in degrees")
    wave_period_max_s: float = Field(ge=0, le=30, description="maximum wave period in seconds")
    swell_wave_period_max_s: float = Field(ge=0, le=30, description="maximum swell wave period in seconds")
    wind_speed_max_knots: float = Field(ge=0, le=200, description="maximum wind speed in knots")
    wind_direction_dominant_deg: float = Field(ge=0, le=360, description="dominant wind direction in degrees")
    wind_gusts_max_knots: float = Field(ge=0, le=200, description="maximum wind gusts in knots")
    temperature_max_c: float = Field(ge=-50, le=60, description="maximum temperature in celsius")
    temperature_min_c: float = Field(ge=-50, le=60, description="minimum temperature in celsius")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """validate date is in yyyy-mm-dd format"""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"invalid date format: {v}, expected yyyy-mm-dd")
        return v

    @model_validator(mode='after')
    def validate_temperature_range(self):
        """validate min temperature is less than max"""
        if self.temperature_min_c > self.temperature_max_c:
            raise ValueError(
                f"min temperature ({self.temperature_min_c}) cannot be greater than "
                f"max temperature ({self.temperature_max_c})"
            )
        return self


class SurfForecast(BaseModel):
    """complete surf forecast for a location with validation"""
    location: str = Field(min_length=1, description="location name")
    latitude: float = Field(ge=-90, le=90, description="latitude coordinate")
    longitude: float = Field(ge=-180, le=180, description="longitude coordinate")
    current_conditions: CurrentConditions = Field(description="current surf conditions")
    hourly_forecast: list[CurrentConditions] = Field(
        default=[],
        description="hourly forecast for next hours"
    )
    forecast_5day: list[DailyForecast] = Field(
        min_length=1,
        max_length=5,
        description="5 day surf forecast"
    )
    surf_quality_notes: str = Field(min_length=1, description="interpretation of conditions for surfing")

    @field_validator("forecast_5day")
    @classmethod
    def validate_forecast_days(cls, v: list[DailyForecast]) -> list[DailyForecast]:
        """validate forecast days are in chronological order"""
        if len(v) > 1:
            dates = [datetime.strptime(day.date, "%Y-%m-%d") for day in v]
            for i in range(len(dates) - 1):
                if dates[i] >= dates[i + 1]:
                    raise ValueError("forecast days must be in chronological order")
        return v
    
    def to_llm_context(self) -> str:
        """
        format forecast as concise, human-readable text optimized for llm context
        
        returns:
            formatted string suitable for llm consumption
        """
        from services.helpers import degrees_to_compass
        
        lines = [
            f"# Surf Forecast: {self.location}",
            "",
            "## Current Conditions",
            f"Waves: {self.current_conditions.wave_height_m:.1f}m ({self.current_conditions.wave_period_s:.0f}s period)",
            f"  - Swell: {self.current_conditions.swell_wave_height_m:.1f}m from {degrees_to_compass(self.current_conditions.swell_wave_direction_deg).upper()}",
            f"  - Wind waves: {self.current_conditions.wind_wave_height_m:.1f}m",
            f"Wind: {self.current_conditions.wind_speed_knots:.0f} knots from {degrees_to_compass(self.current_conditions.wind_direction_deg).upper()} (gusts {self.current_conditions.wind_gusts_knots:.0f} knots)",
            f"Temperature: {self.current_conditions.temperature_c:.0f}°C",
            ""
        ]
        
        # add hourly forecast if available
        if self.hourly_forecast:
            lines.append("## Next Hours")
            for hour in self.hourly_forecast:
                # parse timestamp to get readable time
                try:
                    from datetime import datetime
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
        
        for day in self.forecast_5day:
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


# api response validation models
class MarineHourly(BaseModel):
    """validation model for marine api hourly response"""
    time: list[str]
    wave_height: list[Optional[float]]
    wave_direction: list[Optional[float]]
    wave_period: list[Optional[float]]
    wind_wave_height: list[Optional[float]]
    wind_wave_direction: list[Optional[float]]
    wind_wave_period: list[Optional[float]]
    swell_wave_height: list[Optional[float]]
    swell_wave_direction: list[Optional[float]]
    swell_wave_period: list[Optional[float]]


class MarineDaily(BaseModel):
    """validation model for marine api daily response"""
    time: list[str]
    wave_height_max: list[Optional[float]]
    wave_direction_dominant: list[Optional[float]]
    wave_period_max: list[Optional[float]]
    wind_wave_height_max: list[Optional[float]]
    wind_wave_direction_dominant: list[Optional[float]]
    wind_wave_period_max: list[Optional[float]]
    swell_wave_height_max: list[Optional[float]]
    swell_wave_direction_dominant: list[Optional[float]]
    swell_wave_period_max: list[Optional[float]]


class MarineResponse(BaseModel):
    """validation model for marine api response"""
    hourly: MarineHourly
    daily: MarineDaily


class WeatherHourly(BaseModel):
    """validation model for weather api hourly response"""
    time: list[str]
    temperature_2m: list[Optional[float]]
    windspeed_10m: list[Optional[float]]
    winddirection_10m: list[Optional[float]]
    windgusts_10m: list[Optional[float]]


class WeatherDaily(BaseModel):
    """validation model for weather api daily response"""
    time: list[str]
    temperature_2m_max: list[Optional[float]]
    temperature_2m_min: list[Optional[float]]
    windspeed_10m_max: list[Optional[float]]
    winddirection_10m_dominant: list[Optional[float]]
    windgusts_10m_max: list[Optional[float]]


class WeatherResponse(BaseModel):
    """validation model for weather api response"""
    hourly: WeatherHourly
    daily: WeatherDaily


__all__ = [
    "CurrentConditions",
    "DailyForecast",
    "SurfForecast",
    "MarineResponse",
    "WeatherResponse"
]
