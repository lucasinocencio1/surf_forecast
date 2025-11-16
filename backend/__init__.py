# backend/__init__.py
"""
backend package for surf forecast application
"""

from .models import SurfForecast
from .context import format_forecast_to_llm_context

__all__ = ["SurfForecast", "format_forecast_to_llm_context"]
