class UdsEcuSimulator:
    def __init__(self,bus,request_id,response_id,vin=None,software_version=None,hardware_version=None,dtc_records=None):
        self.bus=bus; self.request_id=request_id; self.response_id=response_id
        self.vin=vin; self.software_version=software_version; self.hardware_version=hardware_version
        self.dtc_records=dtc_records or []
