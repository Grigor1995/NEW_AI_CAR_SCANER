"""Backend-owned human-readable names; stable wire channel IDs remain unchanged."""
CHANNELS = (
    ('rpm','Engine speed','0x0C','010C','engine_rpm'),
    ('coolant_temp','Coolant temperature','0x05','0105','coolant_c','coolant_temp_c'),
    ('vehicle_speed','Vehicle speed','0x0D','010D','speed_kmh','vehicle_speed_kmh'),
    ('throttle','Throttle position','0x11','0111','throttle_percent','throttle_pct'),
    ('map','MAP pressure','0x0B','010B','map_kpa'),
    ('maf','MAF airflow','0x10','0110','maf_gps'),
    ('engine_load_percent','Engine load','0x04','0104'),
    ('intake_air_c','Intake air temperature','0x0F','010F'),
    ('stft','Short-term fuel trim','0x06','0106','short_fuel_trim_percent'),
    ('ltft','Long-term fuel trim','0x07','0107','long_fuel_trim_percent'),
    ('battery_voltage','Battery voltage'),
    ('o2','O2 sensor'),
)
_NAMES = {alias.casefold(): name for key,name,*aliases in CHANNELS for alias in (key,*aliases)}


def channel_name(channel: str) -> str:
    return _NAMES.get(str(channel).casefold(), str(channel))
