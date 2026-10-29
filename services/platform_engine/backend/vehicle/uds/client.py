class UdsClient:
    def __init__(self, transport): self.transport=transport
    async def request(self,payload): return await self.transport.request(payload)
