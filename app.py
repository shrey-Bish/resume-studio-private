import importlib


if __name__ == "__main__":
    app_module = importlib.import_module("resume_studio.app")
    app_module.main()
