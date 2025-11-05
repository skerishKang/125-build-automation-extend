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

# Redis connection (only if enabled)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
redis_client = None

if REDIS_ENABLED:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
        decode_responses=True
    )
else:
    logger.info("Redis is disabled (REDIS_ENABLED=false)")


class BotMessenger:
    """Handle inter-bot communication via Redis Pub/Sub"""

    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.pubsub = None
        self.message_handlers: Dict[str, Callable] = {}

        if REDIS_ENABLED and redis_client:
            self.pubsub = redis_client.pubsub()
            logger.info(f"BotMessenger initialized for {bot_name} with Redis")
        else:
            logger.info(f"BotMessenger initialized for {bot_name} (Redis disabled - using mock mode)")
            self.pubsub = None

    def publish_task(self, task_type: str, task_data: Dict[str, Any]):
        """Publish task to specific bot"""
        if not REDIS_ENABLED or not redis_client:
            logger.info(f"[MOCK] Would publish task to {task_type}: {task_data}")
            return

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
        if not REDIS_ENABLED or not redis_client:
            logger.info(f"[MOCK] Would send result to chat_id {chat_id}: {result}")
            return

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
        if not REDIS_ENABLED or not redis_client:
            logger.info("[MOCK] BotMessenger.listen() called but Redis is disabled")
            while False:
                yield
            return

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
        if not REDIS_ENABLED or not redis_client:
            logger.info(f"[MOCK] Would notify progress to {chat_id}: {progress}")
            return

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
        if self.pubsub:
            self.pubsub.close()


def send_to_document_bot(chat_id: str, file_data: Dict[str, Any]):
    """Helper function to send document task to document bot"""
    if not REDIS_ENABLED or not redis_client:
        logger.info(f"[MOCK] Would send document task to chat_id {chat_id}")
        return

    messenger = BotMessenger("main_bot")
    messenger.publish_task("document", {
        "chat_id": chat_id,
        "file_data": file_data
    })
    messenger.close()


def send_to_audio_bot(chat_id: str, voice_data: Dict[str, Any]):
    """Helper function to send audio task to audio bot"""
    if not REDIS_ENABLED or not redis_client:
        logger.info(f"[MOCK] Would send audio task to chat_id {chat_id}")
        return

    messenger = BotMessenger("main_bot")
    messenger.publish_task("audio", {
        "chat_id": chat_id,
        "voice_data": voice_data
    })
    messenger.close()


def send_to_image_bot(chat_id: str, image_data: Dict[str, Any]):
    """Helper function to send image task to image bot"""
    if not REDIS_ENABLED or not redis_client:
        logger.info(f"[MOCK] Would send image task to chat_id {chat_id}")
        return

    messenger = BotMessenger("main_bot")
    messenger.publish_task("image", {
        "chat_id": chat_id,
        "image_data": image_data
    })
    messenger.close()


def send_status_notification(bot_status: Dict[str, Any]):
    """Send bot status to monitoring system"""
    if not REDIS_ENABLED or not redis_client:
        logger.info(f"[MOCK] Would send status notification: {bot_status}")
        return

    channel = "bot_status"
    redis_client.publish(channel, json.dumps(bot_status))


# Test connection
if __name__ == "__main__":
    if REDIS_ENABLED and redis_client:
        try:
            redis_client.ping()
            print("[OK] Redis connection successful")
        except Exception as e:
            print(f"[ERROR] Redis connection failed: {e}")
    else:
        print("[INFO] Redis is disabled (REDIS_ENABLED=false)")
