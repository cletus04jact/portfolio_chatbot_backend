from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import re
import os
from dotenv import load_dotenv
from pydantic import ValidationError
import requests

load_dotenv()

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cletus.justsee.live"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini API key and init
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# Resume data (this can be dynamically loaded from a file)
RESUME_DATA = {
    "name": "Cletus",
    "skills": ["Python", "Flask", "Machine Learning", "Langchain", "AWS Redshift","PowerBI"],
    "experience": "Over 8+ Months of hands-on experience in Data Science and Full-Stack Development, diverse project work across multiple organizations as an intern and freelance developer. Proven ability to deliver end-to-end solutions — from building robust data pipelines and machine learning models to deploying scalable web applications.",
    "projects": [
        "Detection of Fake images,videos",
        "AI complaint categorization system",
    ],
    "email": "cletusbobola@gmail.com",
    "phone": "6381174925",
    "Tell me about yourself": "I am Cletus Sylphia,Machine Learning and Data Engineer with a passion for transforming raw data into intelligent, scalable solutions. I specialize in building ML models, data pipelines, and deploying AI-powered applications that drive real impact.Let’s build something amazing together!"
}

# State memory (for demo purposes only - not persistent)
user_sessions = {}

class Message(BaseModel):
    session_id: str
    text: str
def send_full_chat_history_via_emailjs(name, email, phone, full_chat):
    service_id = "service_qcqv9vd"
    template_id ="template_gri0orb"
    public_key = "mLG_qJwlKvHNN7g2G"

    payload = {
        "service_id": service_id,
        "template_id": template_id,
        "user_id": public_key,
        "template_params": {
            "from_name": name,
            "reply_to": email,
            "phone": phone,
            "full_chat": full_chat,
        }
    }

    headers = {
        "origin": "http://cletus.justsee.live",  # or your deployed frontend origin
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://api.emailjs.com/api/v1.0/email/send", json=payload, headers=headers)
        response.raise_for_status()
        print("✅ Full chat sent via EmailJS.")
    except Exception as e:
        print("❌ Failed to send chat history:", str(e))

# Regex for phone validation
def is_valid_phone(phone):
    return re.fullmatch(r"\+?\d{10,14}", phone) is not None
def is_valid_email(email: str) -> bool:
    return re.fullmatch(r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+", email) is not None


@app.post("/chat")
async def chat(message: Message):
    session = user_sessions.setdefault(message.session_id, {
        "step": 0,
        "name": "",
        "email": "",
        "phone": "",
        "wants_phone": False,
        "gemini_count": 0 
    })

    text = message.text.strip()

    if session['step'] == 0:
        session['step'] = 1
        return {"reply": "👋 Hi there! I'm Cletus. May I know your name?"}

    elif session['step'] == 1:
        session['name'] = text
        session['step'] = 2
        return {"reply": f"Thanks {text}! Could you please share your email?"}

    elif session['step'] == 2:
        if is_valid_email(text):
            session['email'] = text
            session['step'] = 3
            return {"reply": "Would you like to provide your phone number? (yes/no)"}
        else:
            return {"reply": " Invalid email format. Please enter a valid email like name@example.com."}


    elif session['step'] == 3:
        if text.lower() == "yes":
            session['wants_phone'] = True
            session['step'] = 4
            return {"reply": "Please enter your phone number:"}
        else:
            session['wants_phone'] = False
            session['step'] = 5
            return {"reply": "Awesome! You can now ask me anything about my resume or other queries."}

    # Step 4: Phone number or "contact me" shortcut
    elif session['step'] == 4:
        if "contact" in text or "how to reach" in text:
            session['step'] = 5  # allow future Qs
            return {
                "reply": f"📧 You can contact me at {RESUME_DATA['email']} or call me at 📞 {RESUME_DATA['phone']}."
            }
        elif is_valid_phone(text):
            session['phone'] = text
            session['step'] = 5
            return {"reply": "Got it! Now feel free to ask anything about my resume or contact me."}
        else:
            return {"reply": "Invalid phone number. Please enter a valid one or type 'contact me' to skip."}

    elif session['step'] >= 5:
        # Resume-based questions
        if any(kw in text for kw in ["resume", "skill", "experience", "project", "email", "phone", "contact"]):
            bot_reply = ""
            if "skill" in text:
                bot_reply = f"Here are my skills: {', '.join(RESUME_DATA['skills'])}"
            elif "experience" in text:
                bot_reply = f"Experience: {RESUME_DATA['experience']}"
            elif "project" in text:
                bot_reply = f"Projects: {', '.join(RESUME_DATA['projects'])}"
            elif "email" in text or "contact" in text:
                bot_reply = f"You can email me at {RESUME_DATA['email']}"
            elif "phone" in text or "call" in text:
                bot_reply = f" My phone number is {RESUME_DATA['phone']}"
            else:
                bot_reply = "Can you clarify what you'd like to know about my resume?"

            # Store chat history
            chat_log = session.setdefault("chat_history", [])
            chat_log.append(f"User: {text}")
            chat_log.append(f"Cletus: {bot_reply}")

            return {"reply": bot_reply}

        # Block inappropriate queries
        banned_words = ["love", "sex", "marry", "date", "go out", "relationship"]
        if any(bad in text for bad in banned_words):
            reply = "I'm here to assist you professionally. Let's keep our conversation respectful. You can contact me for work-related queries. 👋"
            session.setdefault("chat_history", []).append(f"User: {text}")
            session["chat_history"].append(f"Cletus: {reply}")
            return {"reply": reply}

        # Limit to 1 Gemini query
        if session['gemini_count'] >= 1:
            reply = "I've answered your questions! 😊 For anything more, feel free to contact me at:\ncletusbobola@gmail.com\nWhatsApp: 6381174925"
            session.setdefault("chat_history", []).append(f"User: {text}")
            session["chat_history"].append(f"Cletus: {reply}")
            return {"reply": reply}

        # Gemini reply
        try:
            session['gemini_count'] += 1
            response = model.generate_content(
                f"""You are Cletus, a startup-minded Machine Learning and Data Engineer.
    Your tone should be casual, confident, and clear—like a friendly tech founder explaining to someone new.
    Respond in first person with clear, thoughtful answers.
    Q: {message.text}"""
            )
            bot_reply = response.text.strip()

            # Save chat history
            chat_log = session.setdefault("chat_history", [])
            chat_log.append(f"User: {text}")
            chat_log.append(f"Cletus: {bot_reply}")

            # ✅ Send email if name/email available and not already sent
            if session['name'] and session['email'] and not session.get('history_sent') and len(chat_log) >= 4:
                full_chat = "\n".join(chat_log)
                send_full_chat_history_via_emailjs(
                    session['name'],
                    session['email'],
                    session.get('phone', 'Not Provided'),
                    full_chat
                )
                session['history_sent'] = True

            return {"reply": bot_reply}

        except Exception as e:
            return {"reply": "Sorry, I had trouble generating a response. Please try again later."}


    return {"reply": "I didn't understand that. Could you try rephrasing your question?"}