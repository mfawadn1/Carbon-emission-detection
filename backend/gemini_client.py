import requests

# Hard-code your API key here
GEMINI_API_KEY = "YOUR_REAL_GEMINI_KEY"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)

# Main function used by FastAPI
def call_gemini_text(prompt: str):
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:
        r = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=30,
        )

        if not r.ok:
            return f"Gemini error: {r.text}"

        data = r.json()

        output = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        return output or "No response"

    except Exception as e:
        return f"Assistant crashed: {str(e)}"
