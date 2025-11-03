module.exports = {
  apps: [
    {
      name: "125-backend",
      cwd: "./backend",
      script: "python",
      args: "-m uvicorn main:app --host 0.0.0.0 --port 8000",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1"
      },
      error_file: "./logs/backend-error.log",
      out_file: "./logs/backend-out.log",
      log_file: "./logs/backend.log",
      time: true
    },
    {
      name: "125-frontend",
      cwd: "./frontend",
      script: "npm",
      args: "run start",
      autorestart: true,
      max_restarts: 10,
      error_file: "./logs/frontend-error.log",
      out_file: "./logs/frontend-out.log",
      log_file: "./logs/frontend.log",
      time: true
    },
    {
      name: "125-telegram-bot",
      cwd: "./backend",
      script: "python",
      args: "bot_runner.py",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1"
      },
      error_file: "./logs/bot-error.log",
      out_file: "./logs/bot-out.log",
      log_file: "./logs/bot.log",
      time: true
    }
  ]
};
