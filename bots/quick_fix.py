import re

# Fix redis_utils.py
with open('shared/redis_utils.py', 'r') as f:
    content = f.read()

# Add REDIS_ENABLED
content = re.sub(
    r'logger = logging\.getLogger\("redis_utils"\)\n\n# Redis connection\nredis_client = redis\.Redis\(',
    '''logger = logging.getLogger("redis_utils")

# Redis connection (only if enabled)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
redis_client = None

if REDIS_ENABLED:
    redis_client = redis.Redis(
''',
    content
)

# Add check to __init__
if 'self.pubsub = None' not in content:
    content = content.replace(
        'self.bot_name = bot_name\n        self.pubsub = redis_client.pubsub()\n        self.message_handlers: Dict[str, Callable] = {}',
        '''self.bot_name = bot_name
        self.pubsub = None
        self.message_handlers: Dict[str, Callable] = {}

        if REDIS_ENABLED and redis_client:
            self.pubsub = redis_client.pubsub()
            logger.info(f"BotMessenger initialized for {bot_name} with Redis")
        else:
            logger.info(f"BotMessenger initialized for {bot_name} (Redis disabled - using mock mode)")
            self.pubsub = None'''
    )

with open('shared/redis_utils.py', 'w') as f:
    f.write(content)

print("Fixed redis_utils.py")
