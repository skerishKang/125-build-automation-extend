"""
Redis Pub/Sub Communication - Inter-Bot Message Passing
"""
import redis
import json
import time
import os
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger("redis_utils")

# Redis connection
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=0,
    decode_responses=True
)


class BotMessenger:
    """Handle inter-bot communication via Redis Pub/Sub"""

    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.pubsub = redis_client.pubsub()
        self.message_handlers: Dict[str, Callable] = {}

    def publish_task(self, task_type: str, task_data: Dict[str, Any]):
        """Publish task to specific bot"""
        channel = f"{task_type}_tasks"
        message = {
            "bot_name": self.bot_name,
            "task_type": task_type,
            "data": task_data,
            "timestamp": time.time()
        }
        redis_client.publish(channel, json.dumps(message))
        logger.info(f"Published task to {channel}: {task_type}")

    def send_result(self, chat_id: str, result: Dict[str, Any]):
        """Send result back to main bot"""
        channel = "main_bot_results"
        message = {
            "bot_name": self.bot_name,
            "chat_id": chat_id,
            "result": result,
            "timestamp": time.time()
        }
        redis_client.publish(channel, json.dumps(message))
        logger.info(f"Sent result to chat_id {chat_id}")

    def register_handler(self, message_type: str, handler: Callable):
        """Register message handler for specific type"""
        self.message_handlers[message_type] = handler

    def listen(self):
        """Listen for messages and call appropriate handlers"""
        self.pubsub.subscribe("main_bot_results", "shared_notifications")

        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    message_type = data.get('task_type', 'unknown')

                    if message_type in self.message_handlers:
                        self.message_handlers[message_type](data)
                    else:
                        logger.warning(f"No handler for message type: {message_type}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

    def notify_progress(self, chat_id: str, progress: str):
        """Send progress update to main bot"""
        channel = f"progress_{chat_id}"
        message = {
            "bot_name": self.bot_name,
            "chat_id": chat_id,
            "progress": progress,
            "timestamp": time.time()
        }
        redis_client.publish(channel, json.dumps(message))

    def close(self):
        """Close pubsub connection"""
        self.pubsub.close()


def send_to_document_bot(chat_id: str, file_data: Dict[str, Any]):
    """Helper function to send document task to document bot"""
    messenger = BotMessenger("main_bot")
    messenger.publish_task("document", {
        "chat_id": chat_id,
        "file_data": file_data
    })
    messenger.close()


def send_to_audio_bot(chat_id: str, voice_data: Dict[str, Any]):
    """Helper function to send audio task to audio bot"""
    messenger = BotMessenger("main_bot")
    messenger.publish_task("audio", {
        "chat_id": chat_id,
        "voice_data": voice_data
    })
    messenger.close()


def send_to_image_bot(chat_id: str, image_data: Dict[str, Any]):
    """Helper function to send image task to image bot"""
    messenger = BotMessenger("main_bot")
    messenger.publish_task("image", {
        "chat_id": chat_id,
        "image_data": image_data
    })
    messenger.close()


def send_status_notification(bot_status: Dict[str, Any]):
    """Send bot status to monitoring system"""
    channel = "bot_status"
    redis_client.publish(channel, json.dumps(bot_status))


# Test connection
if __name__ == "__main__":
    try:
        redis_client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
