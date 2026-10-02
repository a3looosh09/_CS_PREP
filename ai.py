import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def grade_answer(question, max_marks, expected_concepts, student_answer):

    prompt = f"""
You are an IB Computer Science teacher marking a student's answer.

Question:
{question}

Maximum marks:
{max_marks}

Mark scheme:
{expected_concepts}

Student answer:
{student_answer}

Mark the student's answer strictly according to the mark scheme.

Give:
1. A score from 0 to {max_marks}
2. Concise feedback explaining what the student got correct and what they missed.

Do not give marks for information that is not supported by the mark scheme.
Do not give partial credit unless the student's answer demonstrates the relevant concept.
Do not exceed the maximum mark.

Return your response in exactly this format:

SCORE: X
FEEDBACK: Your feedback here
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    text = response.text.strip()

    score = 0
    feedback = "Unable to generate feedback."

    for line in text.splitlines():
        if line.startswith("SCORE:"):
            try:
                score = int(line.replace("SCORE:", "").strip())
            except ValueError:
                score = 0

        elif line.startswith("FEEDBACK:"):
            feedback = line.replace("FEEDBACK:", "").strip()

    score = max(0, min(score, max_marks))

    return {
        "score": score,
        "feedback": feedback
    }