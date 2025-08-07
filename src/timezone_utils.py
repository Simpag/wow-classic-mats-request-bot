"""
Timezone utilities for WoW server time handling.
"""

import pytz
from datetime import datetime
from typing import Optional

# WoW Server Timezones
WOW_TIMEZONES = {
    "US": "US/Pacific",  # US servers use Pacific Time
    "EU": "Europe/Paris",  # EU servers use Central European Time
    "OCE": "Australia/Sydney",  # Oceanic servers use Australian Eastern Time
}

# Default to US servers (Pacific Time) - you can change this
DEFAULT_WOW_REGION = "US"


class WoWTimeHandler:
    def __init__(self, region: str = DEFAULT_WOW_REGION):
        """Initialize with a WoW server region."""
        if region not in WOW_TIMEZONES:
            raise ValueError(
                f"Invalid region. Must be one of: {list(WOW_TIMEZONES.keys())}"
            )

        self.region = region
        self.timezone = pytz.timezone(WOW_TIMEZONES[region])

    def now(self) -> datetime:
        """Get current time in WoW server timezone."""
        return datetime.now(self.timezone)

    def utc_to_wow_time(self, utc_dt: datetime) -> datetime:
        """Convert UTC datetime to WoW server time."""
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(self.timezone)

    def wow_time_to_utc(self, wow_dt: datetime) -> datetime:
        """Convert WoW server time to UTC."""
        if wow_dt.tzinfo is None:
            wow_dt = self.timezone.localize(wow_dt)
        return wow_dt.astimezone(pytz.utc)

    def format_wow_time(
        self, dt: Optional[datetime] = None, include_timezone: bool = True
    ) -> str:
        """Format datetime for display in WoW server time."""
        if dt is None:
            dt = self.now()
        elif dt.tzinfo is None:
            # Assume it's UTC if no timezone
            dt = pytz.utc.localize(dt)

        # Convert to WoW server time
        wow_time = dt.astimezone(self.timezone)

        if include_timezone:
            return wow_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            return wow_time.strftime("%Y-%m-%d %H:%M:%S")

    def discord_timestamp(self, dt: Optional[datetime] = None, style: str = "R") -> str:
        """
        Create Discord timestamp formatting.

        Styles:
        - 't': Short time (16:20)
        - 'T': Long time (16:20:30)
        - 'd': Short date (20/04/2021)
        - 'D': Long date (20 April 2021)
        - 'f': Short date/time (20 April 2021 16:20)
        - 'F': Long date/time (Tuesday, 20 April 2021 16:20)
        - 'R': Relative time (2 months ago) - DEFAULT
        """
        if dt is None:
            dt = self.now()
        elif dt.tzinfo is None:
            # Assume it's UTC if no timezone
            dt = pytz.utc.localize(dt)

        timestamp = int(dt.timestamp())
        return f"<t:{timestamp}:{style}>"

    def get_region_info(self) -> dict:
        """Get information about the current WoW region."""
        return {
            "region": self.region,
            "timezone": WOW_TIMEZONES[self.region],
            "current_time": self.format_wow_time(),
        }


# Global instance - you can change the region here
wow_time = WoWTimeHandler("US")  # Default to US servers

# Guild-specific timezone handlers
guild_timezones = {}  # guild_id -> WoWTimeHandler


# Convenience functions
def get_wow_time(guild_id: Optional[int] = None) -> datetime:
    """Get current WoW server time for a specific guild or global default."""
    if guild_id and guild_id in guild_timezones:
        return guild_timezones[guild_id].now()
    return wow_time.now()


def format_for_discord(
    dt: Optional[datetime] = None, style: str = "R", guild_id: Optional[int] = None
) -> str:
    """Format datetime for Discord timestamp display."""
    if guild_id and guild_id in guild_timezones:
        return guild_timezones[guild_id].discord_timestamp(dt, style)
    return wow_time.discord_timestamp(dt, style)


def format_wow_time(
    dt: Optional[datetime] = None, guild_id: Optional[int] = None
) -> str:
    """Format datetime in WoW server time."""
    if guild_id and guild_id in guild_timezones:
        return guild_timezones[guild_id].format_wow_time(dt)
    return wow_time.format_wow_time(dt)


def set_wow_region(region: str):
    """Change the global WoW server region."""
    global wow_time
    wow_time = WoWTimeHandler(region)


def set_guild_wow_region(guild_id: int, region: str):
    """Set WoW server region for a specific guild."""
    guild_timezones[guild_id] = WoWTimeHandler(region)


def get_guild_wow_region(guild_id: int) -> Optional[str]:
    """Get the WoW region for a specific guild."""
    if guild_id in guild_timezones:
        return guild_timezones[guild_id].region
    return None


def get_wow_region_info(guild_id: Optional[int] = None) -> dict:
    """Get current WoW region information."""
    if guild_id and guild_id in guild_timezones:
        return guild_timezones[guild_id].get_region_info()
    return wow_time.get_region_info()


def get_available_regions() -> dict:
    """Get all available WoW regions."""
    return WOW_TIMEZONES.copy()
