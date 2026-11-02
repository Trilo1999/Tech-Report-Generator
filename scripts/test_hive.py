import os
from openai import OpenAI

# 1. Endpoints: Default CDN endpoint or Virginia routing node
DEFAULT_CDN_ENDPOINT = os.getenv("HIVE_CDN_ENDPOINT", "https://api-cdn.deploy.com/api/v1")
VIRGINIA_ENDPOINT = os.getenv("HIVE_VIRGINIA_ENDPOINT", "https://api-va1.deploy.com/api/v1")

# 2. Credential Routing: Strictly map 'Hive Secret Key' to api_key
# Ignore/isolate Access Key ID as metadata (cannot authorize completion requests)
HIVE_SECRET_KEY = os.getenv("HIVE_SECRET_KEY", "fLS6y0XYGkHLfwMKz43CAg==")
HIVE_ACCESS_KEY_ID = os.getenv("HIVE_ACCESS_KEY", "H23JpDXXQjsLsctw")  # Isolated metadata

# 3. Model Parameterization: exact workspace string provided by Hive
MODEL_NAME = "deepseek-ai/deepseek-v4.1-flash-1017"


def get_hive_client(regional_compliance: bool = False) -> OpenAI:
    base_url = VIRGINIA_ENDPOINT if regional_compliance else DEFAULT_CDN_ENDPOINT
    return OpenAI(
        base_url=base_url,
        api_key=HIVE_SECRET_KEY,
    )


def generate_completion(prompt: str, regional_compliance: bool = False) -> str:
    client = get_hive_client(regional_compliance=regional_compliance)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    result = generate_completion("Say 'Hive AI connected successfully' in 4 words.")
    print(result)
