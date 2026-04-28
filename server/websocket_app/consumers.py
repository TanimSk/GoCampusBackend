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
        # Create room
        self.room_group_name = "geolocation"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        self.broadcast_task = asyncio.create_task(self.broadcast_messages())

    async def broadcast_messages(self):
        """Broadcast a message every 1 second"""
        try:
            while True:
                print(f"Broadcasting message")
                # get redis session data
                session_data = await get_async_redis().get(f"geolocation")
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
                f"Broadcast task cancelled error: {e}"
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


    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)        
        user_id = text_data_json.get("user_id")
        latitude = text_data_json.get("latitude")
        longitude = text_data_json.get("longitude")

        # Store the geolocation data in Redis
        all_ecart_data = await get_async_redis().get(f"geolocation")
        if all_ecart_data:
            all_ecart_data = json.loads(all_ecart_data)
        else:
            all_ecart_data = []

        # Update or add the user's geolocation data
        user_data = {
            "user_id": user_id,
            "latitude": latitude,
            "longitude": longitude,
        }

        # Check if the user already exists in the data
        existing_user_index = next(
            (index for (index, d) in enumerate(all_ecart_data) if d["user_id"] == user_id), None
        )

        if existing_user_index is not None:
            # Update existing user data
            all_ecart_data[existing_user_index] = user_data
        else:
            # Add new user data
            all_ecart_data.append(user_data)

        # Store the updated geolocation data in Redis
        await get_async_redis().set(f"geolocation", json.dumps(all_ecart_data))