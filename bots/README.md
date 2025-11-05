# 4-Bot Distributed Telegram System

A high-performance, distributed Telegram bot system with 4 specialized bots working together to provide document processing, audio transcription, and image analysis capabilities using Gemini AI.

## 🎯 Architecture Overview

### System Design

This system implements a **distributed microservice architecture** where each bot has a specific responsibility:

```
┌─────────────────────────────────────────────────────────────┐
│                     User (Telegram)                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   MAIN BOT (Task Distributor)               │
│  • User conversation handling                               │
│  • Task distribution to specialized bots                   │
│  • Result aggregation and response                         │
│  • Non-blocking immediate responses                        │
└─────────────────────────────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
          ┌─────────────┐  ┌─────────────┐
          │   REDIS     │  │   GEMINI    │
          │   PUB/SUB   │  │    AI       │
          └─────────────┘  └─────────────┘
                    │             │
                    ▼             ▼
          ┌─────────────┐  ┌─────────────┐
          │ Specialized │  │  Shared     │
          │    Bots     │  │ Utilities   │
          └─────────────┘  └─────────────┘
```

### Bot Specialization

| Bot | Primary Function | File Types | AI Features |
|-----|-----------------|------------|-------------|
| **Main Bot** | Task distribution, user interaction | All messages | Gemini conversational AI |
| **Document Bot** | Document analysis | PDF, DOCX, TXT, CSV, XLSX, PPTX | Text extraction + AI summary |
| **Audio Bot** | Audio transcription | OGG, MP3, WAV | Whisper ASR + AI analysis |
| **Image Bot** | Image analysis | JPG, PNG, GIF, WEBP | Gemini Vision AI |

### Key Features

- ⚡ **Non-blocking Main Bot**: Always responds immediately, delegates work to specialized bots
- 🔄 **Redis Pub/Sub**: Lightweight inter-bot communication
- 🤖 **Gemini AI Integration**: Advanced multimodal analysis
- 📄 **Multi-format Support**: 15+ document types, multiple media formats
- 🐳 **Docker Ready**: Full containerization support
- 📊 **Progress Tracking**: Real-time task status updates
- 🔧 **Independent Scaling**: Each bot can be scaled independently
- 🎯 **Task-based Architecture**: Clear separation of concerns

## 📁 Project Structure

```
bots/
├── main_bot/              # Task distributor & user interaction
│   ├── main_bot.py       # Main bot implementation
│   └── requirements.txt  # Python dependencies
│
├── document_bot/         # Document processing specialist
│   ├── document_bot.py  # Document analysis logic
│   └── requirements.txt # Python dependencies
│
├── audio_bot/            # Audio transcription specialist
│   ├── audio_bot.py     # Audio processing logic
│   └── requirements.txt # Python dependencies
│
├── image_bot/            # Image analysis specialist
│   ├── image_bot.py     # Image processing logic
│   └── requirements.txt # Python dependencies
│
├── shared/               # Shared utilities & modules
│   ├── redis_utils.py   # Redis Pub/Sub messaging
│   ├── gemini_client.py # Gemini AI client
│   └── telegram_utils.py# Telegram utilities
│
├── docker/               # Docker configuration
│   ├── Dockerfile       # Multi-stage build
│   └── docker-compose.yml # Orchestration config
│
├── run_bots.py           # Unified startup script
└── README.md             # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Redis Server
- Telegram Bot Token
- Gemini API Key

### 1. Environment Setup

**Option A: Use `.env` Template (Windows Users - Recommended)**
```bash
cd bots
copy .env.example .env
notepad .env
```

Edit `.env` and add your Gemini API keys:
```env
# Bot Tokens (already set)
MAIN_BOT_TOKEN=8582906961:AAEx7WaxK6hMj_pvDnE8jZlcxxAxAOXh2JA
DOCUMENT_BOT_TOKEN=8265722750:AAHYoAbXr9SVvJ7NL94BoO3H4BzRYYMpQBY
AUDIO_BOT_TOKEN=8293899599:AAHdenSXbmuH4ArjrewPf9dvjB5_KlbyRUg
IMAGE_BOT_TOKEN=8334662540:AAEZxxFf9Ldn37H45bA0WSx9dIf0aKnDz5Q

# Individual Gemini API Keys for Load Distribution
GEMINI_API_KEY_MAIN=your_first_gemini_api_key
GEMINI_API_KEY_DOCUMENT=your_second_gemini_api_key
GEMINI_API_KEY_AUDIO=your_third_gemini_api_key
GEMINI_API_KEY_IMAGE=your_fourth_gemini_api_key

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Option B: Manual Creation**
Create a `.env` file in the `bots/` directory with the content above.

### 2. Install Dependencies

Install dependencies for each bot:

```bash
# Main bot
cd bots/main_bot
pip install -r requirements.txt

# Document bot
cd ../document_bot
pip install -r requirements.txt

# Audio bot
cd ../audio_bot
pip install -r requirements.txt

# Image bot
cd ../image_bot
pip install -r requirements.txt
```

Or install all at once:

```bash
for bot in main_bot document_bot audio_bot image_bot; do
    pip install -r $bot/requirements.txt
done
```

### 3. Start Redis Server

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download Redis from: https://github.com/microsoftarchive/redis/releases

### 4. Run the System

#### Option A: Unified Startup (Recommended)

**Windows Users:**
```cmd
# Double-click to run (easiest)
start_4bots.bat

# Or from Command Prompt
start_4bots.bat

# Or from PowerShell
./start_4bots.bat
```

**macOS/Linux Users:**
```bash
cd bots
python run_bots.py
```

**Option B: Individual Bots (Development)**
```bash
# Terminal 1 - Main Bot
cd bots/main_bot
python main_bot.py

# Terminal 2 - Document Bot
cd bots/document_bot
python document_bot.py

# Terminal 3 - Audio Bot
cd bots/audio_bot
python audio_bot.py

# Terminal 4 - Image Bot
cd bots/image_bot
python image_bot.py
```

### 5. Test the System

Start a conversation with your Telegram bot:

```
/start    - Welcome message
/help     - Help information
/status   - Bot status
/bots     - Specialized bot information

Send a file:
  📄 Document → Document Bot processes it
  🎤 Voice → Audio Bot transcribes it
  🖼️ Image → Image Bot analyzes it
  💬 Text → Gemini AI responds
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. Build and start:
```bash
cd bots/docker
docker-compose up --build
```

2. Stop:
```bash
docker-compose down
```

3. View logs:
```bash
docker-compose logs -f
```

### Manual Docker Build

```bash
cd bots
docker build -f docker/Dockerfile -t telegram-4-bot-system .
docker run -d \
  --name telegram-bots \
  --env-file .env \
  telegram-4-bot-system
```

### Docker Compose with Redis

The included `docker-compose.yml` starts both Redis and the bot system:

```bash
cd bots/docker
docker-compose up -d
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MAIN_BOT_TOKEN` | Main bot (task distributor) token | ✅ | - |
| `DOCUMENT_BOT_TOKEN` | Document bot token | ✅ | - |
| `AUDIO_BOT_TOKEN` | Audio bot token | ✅ | - |
| `IMAGE_BOT_TOKEN` | Image bot token | ✅ | - |
| `GEMINI_API_KEY` | Google Gemini API key | ✅ | - |
| `REDIS_HOST` | Redis server host | ❌ | localhost |
| `REDIS_PORT` | Redis server port | ❌ | 6379 |

### Bot Configuration

Each bot has specific dependencies in their `requirements.txt`:

- **Main Bot**: `python-telegram-bot`, `redis`, `google-generativeai`
- **Document Bot**: Adds `PyPDF2`, `python-docx`, `python-pptx`, `pandas`, `openpyxl`, `chardet`
- **Audio Bot**: Adds `faster-whisper` (Whisper ASR)
- **Image Bot**: Adds `Pillow` (Image processing)

## 📊 Bot Details

### Main Bot (Task Distributor)

**Responsibilities:**
- Handle user messages and commands
- Distribute tasks to specialized bots via Redis
- Aggregate results and respond to users
- Track active tasks per chat

**Commands:**
- `/start` - Welcome message
- `/help` - Help information
- `/status` - Show bot status
- `/bots` - List specialized bots

**Features:**
- Immediate acknowledgment of all requests
- Real-time progress notifications
- Task status tracking
- Non-blocking architecture

### Document Bot (PDF/DOCX/TXT Specialist)

**Supported Formats:**
- PDF (PyPDF2)
- DOCX (python-docx)
- TXT (chardet for encoding detection)
- CSV (pandas)
- XLSX (pandas/openpyxl)
- PPTX (python-pptx)

**Process Flow:**
1. Download file from Telegram
2. Extract text based on file type
3. Limit to 10,000 characters for AI processing
4. Gemini AI generates summary
5. Send result back to Main Bot

### Audio Bot (OGG/MP3/WAV Specialist)

**Supported Formats:**
- OGG (Telegram voice messages)
- MP3
- WAV

**Process Flow:**
1. Download audio from Telegram
2. Transcribe using Whisper (small model)
3. Gemini AI analyzes transcription
4. Send result back to Main Bot

**Model Options:**
- `tiny` - Fastest, lower accuracy
- `base` - Balanced (default)
- `small` - Good accuracy (current)
- `medium` - Higher accuracy, slower
- `large` - Best accuracy, slowest

### Image Bot (JPG/PNG Specialist)

**Supported Formats:**
- JPG/JPEG
- PNG
- GIF
- WEBP

**Process Flow:**
1. Download image from Telegram
2. Encode as base64
3. Gemini Vision AI analyzes
4. Send result back to Main Bot

**AI Features:**
- Image description
- Object detection
- Scene understanding
- Text extraction (OCR)
- Visual analysis

## 🔄 Inter-Bot Communication

### Redis Pub/Sub Channels

| Channel | Purpose | Publisher | Subscriber |
|---------|---------|-----------|------------|
| `document_tasks` | Document processing requests | Main Bot | Document Bot |
| `audio_tasks` | Audio transcription requests | Main Bot | Audio Bot |
| `image_tasks` | Image analysis requests | Main Bot | Image Bot |
| `main_bot_results` | Results from all bots | All Bots | Main Bot |
| `progress_{chat_id}` | Progress updates | All Bots | Main Bot |

### Message Format

**Task Message:**
```json
{
  "bot_name": "main_bot",
  "task_type": "document",
  "data": {
    "chat_id": "123456789",
    "file_data": {
      "file_id": "ABC123...",
      "file_name": "document.pdf",
      "file_size": 1024000
    },
    "user_id": "987654321"
  },
  "timestamp": 1234567890.123
}
```

**Result Message:**
```json
{
  "bot_name": "document_bot",
  "chat_id": "123456789",
  "result": {
    "text": "Extracted text...",
    "summary": "AI-generated summary...",
    "file_name": "document.pdf",
    "processed_at": "2024-01-01T12:00:00"
  },
  "timestamp": 1234567890.456
}
```

## 🎨 Usage Examples

### Example 1: Document Processing

1. User uploads a PDF file
2. Main Bot acknowledges: "📄 Document received, processing..."
3. Document Bot downloads and extracts text
4. Gemini AI generates summary
5. Main Bot sends result: "📄 Analysis complete! Here's the summary..."

### Example 2: Audio Transcription

1. User sends a voice message (30 seconds)
2. Main Bot acknowledges: "🎤 Voice received, transcribing..."
3. Audio Bot downloads and transcribes with Whisper
4. Gemini AI summarizes content
5. Main Bot sends result: "🎤 Transcription complete! Summary: ..."

### Example 3: Image Analysis

1. User uploads an image
2. Main Bot acknowledges: "🖼️ Image received, analyzing..."
3. Image Bot downloads and encodes image
4. Gemini Vision AI analyzes image
5. Main Bot sends result: "🖼️ Analysis complete! ..."

### Example 4: Text Conversation

1. User sends: "What is artificial intelligence?"
2. Main Bot responds immediately with Gemini AI answer

## 🔍 Monitoring & Logs

### Log Files

Each bot creates its own log file:
- `main_bot.log`
- `document_bot.log`
- `audio_bot.log`
- `image_bot.log`
- `bot_runner.log` (from run_bots.py)

### Real-time Monitoring

View logs in real-time:
```bash
tail -f bots/*/bot*.log
```

Or use Docker:
```bash
docker-compose logs -f telegram-bots
```

### Log Format

```
2024-01-01 12:00:00,123 - main_bot - INFO - User 123456789 started the bot
2024-01-01 12:00:01,456 - document_bot - INFO - Processing document: report.pdf for chat 123456789
2024-01-01 12:00:02,789 - main_bot - INFO - Completed task for chat 123456789
```

## 🚨 Troubleshooting

### Common Issues

**1. Redis Connection Error**
```
❌ ERROR: Failed to connect to Redis
```
**Solution:**
- Ensure Redis server is running
- Check `REDIS_HOST` and `REDIS_PORT` in `.env`

**2. Unicode Encoding Error (Windows)**
```
UnicodeEncodeError: 'cp949' codec can't encode character
```
**Solution:**
- Use the provided bat file: `start_4bots.bat`
- The bat file automatically sets `PYTHONIOENCODING=utf-8`
- **OR** set PowerShell profile permanently:
```powershell
# Open PowerShell profile
notepad $PROFILE
# Add this line:
$env:PYTHONIOENCODING="utf-8"
```

**3. ModuleNotFoundError: No module named 'shared'**
```
ModuleNotFoundError: No module named 'shared'
```
**Solution:**
- Ensure you're running from the `bots/` directory
- The bot runner automatically sets PYTHONPATH
- Use: `start_4bots.bat` instead of running `python run_bots.py` directly

**4. Windows: Setting PYTHONIOENCODING Permanently**

There are 3 ways:

**Method 1: Using bat files (Easiest)**
- Just use `start_4bots.bat` or `bots/start_bots.bat`
- No manual setup required!

**Method 2: PowerShell Profile (Permanent)**
```powershell
# Create and edit profile
if (!(Test-Path -Path $PROFILE)) {
    New-Item -Type File -Path $PROFILE -Force
}
notepad $PROFILE
# Add: $env:PYTHONIOENCODING="utf-8"
```

**Method 3: System Environment Variables**
1. Win+R → `sysdm.cpl` → Advanced → Environment Variables
2. System Variables → Add:
   - Name: `PYTHONIOENCODING`
   - Value: `utf-8`
3. Restart PowerShell/Command Prompt
- Test: `redis-cli ping` should return `PONG`

**2. Telegram Bot Token Invalid**
```
❌ ERROR: Failed to connect to Telegram
```
**Solution:**
- Verify token from @BotFather
- Ensure no extra spaces in token
- Check bot is active (not deleted)

**3. Gemini API Key Invalid**
```
⚠️ WARNING: GEMINI_API_KEY is missing - AI features will be disabled
```
**Solution:**
- Get API key from Google AI Studio
- Add to `.env` file
- Restart bots

**4. Import Errors**
```
ModuleNotFoundError: No module named 'xxx'
```
**Solution:**
```bash
pip install -r requirements.txt
```

**5. Whisper Model Download Issues**
```
Error downloading Whisper model
```
**Solution:**
- Check internet connection
- Models are cached in `~/.cache/whisper`
- Restart bot to retry download

### Debug Mode

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Check bot status:
```bash
python -c "
from shared.redis_utils import redis_client
try:
    redis_client.ping()
    print('✅ Redis: OK')
except:
    print('❌ Redis: FAILED')
"
```

## 🔒 Security Considerations

1. **API Keys**: Never commit `.env` file to Git
2. **Bot Token**: Rotate periodically
3. **Redis**: Use password in production
4. **File Size**: 50MB limit for documents
5. **Audio Duration**: 5-minute limit
6. **Input Validation**: All file types validated
7. **Temp Files**: Automatically cleaned up
8. **Rate Limiting**: Consider adding for production

## 📈 Performance Tuning

### Whisper Model Selection

Edit `audio_bot/audio_bot.py`:
```python
# Faster, lower accuracy
model_size = "tiny"

# Balanced (default)
model_size = "base"

# Slower, higher accuracy
model_size = "medium"
```

### Redis Configuration

For production, update `redis.conf`:
```
maxmemory 1gb
maxmemory-policy allkeys-lru
```

### Concurrent Tasks

Each bot handles one task at a time. For higher throughput:
- Run multiple bot instances
- Use Redis clustering
- Implement task queue (e.g., Celery)

## 🛠️ Development

### Adding New Bot

1. Create new directory: `bots/{bot_name}_bot/`
2. Create `{bot_name}_bot.py`
3. Create `requirements.txt`
4. Update `run_bots.py` configuration
5. Add to `docker/Dockerfile` if using Docker

### Extending Document Support

Edit `document_bot/document_bot.py`:
```python
def extract_text_from_format(file_path: str) -> str:
    """Extract text from your format"""
    # Implementation here
    return text

# Register in process_document_task()
if file_ext == '.your_ext':
    extracted_text = extract_text_from_format(file_path)
```

### Custom AI Prompts

Edit `shared/gemini_client.py`:
```python
def analyze_custom(text: str) -> str:
    prompt = f"Your custom prompt here: {text}"
    return self.generate_response(prompt)
```

## 📚 API Reference

### Gemini Client (`shared/gemini_client.py`)

#### Methods

```python
# Text analysis
gemini.analyze_text(text: str) -> str

# Document analysis
gemini.analyze_document(text: str) -> str

# Audio analysis
gemini.analyze_audio(transcription: str) -> str

# Image description
gemini.analyze_image_description(image_path: str) -> str

# Image analysis
gemini.analyze_image(image_path: str) -> str
```

### Redis Utils (`shared/redis_utils.py`)

#### BotMessenger Class

```python
# Publish task
messenger.publish_task(task_type: str, task_data: Dict)

# Send result
messenger.send_result(chat_id: str, result: Dict)

# Notify progress
messenger.notify_progress(chat_id: str, progress: str)
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Google Gemini** - Multimodal AI capabilities
- **Whisper** - Speech recognition by OpenAI
- **python-telegram-bot** - Telegram Bot API wrapper
- **Redis** - In-memory data structure store
- **PyPDF2, python-docx, python-pptx** - Document processing
- **Pillow** - Image processing

## 📞 Support

For issues and questions:
1. Check logs for error messages
2. Review troubleshooting section
3. Open GitHub issue with:
   - Full error log
   - Environment details
   - Steps to reproduce

---

**Built with ❤️ using Python, Redis, and Gemini AI**
