class IsoTpStack:
    def __init__(self, channel, request_id, response_id):
        self.channel=channel; self.request_id=request_id; self.response_id=response_id
    async def request(self, payload, timeout_ms=1000):
        return await self.channel.receive(timeout_ms)
