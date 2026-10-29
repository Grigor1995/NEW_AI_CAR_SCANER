class GenericObdClient:
    def __init__(self,*args,**kwargs): pass
    async def read_vin(self): return None
    async def read_dtcs(self): return []
    async def read_standard_live_data(self):
        return {"rpm":750.0,"coolant_temp_c":90.0,"vehicle_speed_kmh":0.0,"throttle_pct":32.0}
