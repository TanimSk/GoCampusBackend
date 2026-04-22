# websocket_app/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q
import uuid
import asyncio
from utils.redis_handler import get_async_redis


class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sender = self.scope["user"]
        self.room_group_name = None

        try:
            self.session_id = self.scope["url_route"]["kwargs"]["session_id"]

        except ValueError:
            await self.close()
            return

        # Create room
        self.room_group_name = f"{self.session_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        self.broadcast_task = asyncio.create_task(self.broadcast_messages())

    async def broadcast_messages(self):
        """Broadcast a message every 1 second"""
        try:
            while True:
                print(f"Broadcasting message for session: {self.session_id}")
                # get redis session data
                session_data = await get_async_redis().get(f"session:{self.session_id}")
                if session_data:
                    session_data = json.loads(session_data)

                print(f"Broadcasting message: {session_data}")

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": session_data,
                    },
                )
                await asyncio.sleep(4)  # Wait 1 second

        except Exception as e:
            print(
                f"Broadcast task cancelled for session: {self.session_id}, error: {e}"
            )
            # Task was cancelled during disconnect
            pass

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

            # kill the broadcast task
            if hasattr(self, "broadcast_task"):
                self.broadcast_task.cancel()

    async def chat_message(self, event):
        message = event["message"]

        await self.send(
            text_data=json.dumps(
                {
                    "message": message,
                }
            )
        )
