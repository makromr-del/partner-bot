try:
    from telegram import __version__
    print(f"✅ python-telegram-bot version: {__version__}")

    import dotenv
    print("✅ dotenv is installed")
    
    print("🎉 All dependencies are installed correctly!")
    print("🚀 Bot is ready to run!")

except ImportError as e:
    print(f"❌ Error: {e}")
    print("💡 Make sure you activated virtual environment and installed requirements")