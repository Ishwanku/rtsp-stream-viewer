import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('streams', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('streams', self.channel_name)

    async def stream_update(self, event):
        await self.send(text_data=json.dumps({
            'stream_id': event['stream_id'],
            'status': event['status'],
            'error': event.get('error', '')
        }))