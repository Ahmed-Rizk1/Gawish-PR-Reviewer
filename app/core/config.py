from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

GITHUB_TOKEN: str = os.environ["GITHUB_TOKEN"]
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY")
