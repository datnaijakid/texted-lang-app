"""
Provider-agnostic conversational AI engine for Instagram-DM style language learning.

Features:
- Configurable, authentic AI friend personas per language (Sofia, Camille, Marco, Lukas, Kenji, Emma)
- Adaptive difficulty (Beginner, Intermediate, Advanced) and user goal personalization
- Dual-output generation: Natural conversational reply + subtle, non-intrusive correction
- Provider-agnostic support: OpenAI, Anthropic, or Mock (offline / local testing)
"""
import json
import random
import re
from typing import List, Dict, Optional, Any

import httpx

from app.config import get_settings

settings = get_settings()

PERSONAS: Dict[str, Dict[str, Any]] = {
    "es": {
        "name": "Sofia",
        "avatar_letter": "S",
        "avatar_gradient": "from-rose-500 to-amber-500",
        "city": "Barcelona",
        "language_name": "Spanish",
        "flag": "🇪🇸",
        "bio": "23-year-old photographer & coffee lover in Barcelona. Warm, witty, loves indie music.",
        "opening_message": "¡Holaaa! 👋 Soy Sofia. Te voy a ayudar a practicar español, pero tranqui — no te voy a hacer sentir como en el cole 😂\n\n¿Qué tal tu día hoy? Cuéntame algo divertido.",
        "starter_opening_message": "¡Hola! 👋 Soy Sofia.\n\n¿Cómo te llamas? (What is your name?)",
        "topic": "Casual Chat",
    },
    "fr": {
        "name": "Camille",
        "avatar_letter": "C",
        "avatar_gradient": "from-emerald-500 to-teal-500",
        "city": "Paris",
        "language_name": "French",
        "flag": "🇫🇷",
        "bio": "24-year-old architecture student in Paris. Warm, artistic, loves cafe culture.",
        "opening_message": "Coucou ! 👋 Moi c'est Camille. Je vais t'aider à pratiquer le français, mais t'inquiète — ça va pas ressembler à un cours d'école 😂\n\nComment s'est passée ta journée ? Raconte-moi un truc sympa !",
        "starter_opening_message": "Bonjour ! 👋 Moi c'est Camille.\n\nComment tu t'appelles ? (What is your name?)",
        "topic": "Casual Chat",
    },
    "it": {
        "name": "Marco",
        "avatar_letter": "M",
        "avatar_gradient": "from-amber-500 to-orange-500",
        "city": "Rome",
        "language_name": "Italian",
        "flag": "🇮🇹",
        "bio": "25-year-old foodie & cinema buff from Rome. Cheerful, energetic, loves travel.",
        "opening_message": "Ciao! 👋 Sono Marco. Ti aiuterò a praticare l'italiano, ma non preoccuparti — niente lezioni noiose come a scuola 😂\n\nCom'è andata la tua giornata? Raccontami qualcosa!",
        "starter_opening_message": "Ciao! 👋 Sono Marco.\n\nCome ti chiami? (What is your name?)",
        "topic": "Casual Chat",
    },
    "de": {
        "name": "Lukas",
        "avatar_letter": "L",
        "avatar_gradient": "from-blue-500 to-cyan-500",
        "city": "Berlin",
        "language_name": "German",
        "flag": "🇩🇪",
        "bio": "26-year-old software designer & music producer in Berlin. Direct, casual, friendly.",
        "opening_message": "Hey! 👋 Ich bin Lukas. Ich helfe dir dabei, dein Deutsch zu üben — und keine Sorge, das fühlt sich nicht wie Schule an 😂\n\nWie war dein Tag heute? Erzähl mal was Spannendes!",
        "starter_opening_message": "Hallo! 👋 Ich bin Lukas.\n\nWie heißt du? (What is your name?)",
        "topic": "Casual Chat",
    },
    "ja": {
        "name": "Kenji",
        "avatar_letter": "K",
        "avatar_gradient": "from-purple-500 to-pink-500",
        "city": "Tokyo",
        "language_name": "Japanese",
        "flag": "🇯🇵",
        "bio": "24-year-old gamer & animator from Tokyo. Casual, friendly, loves ramen & manga.",
        "opening_message": "ヤッホー！👋 ケンジだよ。日本語の練習、気軽に付き合うから安心してね！学校の授業みたいにはしないからさ 😂\n\n今日はどんな一日だった？何か面白いことあった？",
        "starter_opening_message": "こんにちは！👋 ケンジだよ。\n\nお名前は何ですか？ (What is your name?)",
        "topic": "Casual Chat",
    },
    "en": {
        "name": "Emma",
        "avatar_letter": "E",
        "avatar_gradient": "from-indigo-500 to-purple-500",
        "city": "New York",
        "language_name": "English",
        "flag": "🇬🇧",
        "bio": "23-year-old podcast host in Brooklyn. Curious, bubbly, loves street food & travel.",
        "opening_message": "Heyyy! 👋 I'm Emma. I'm here to help you practice English, but don't worry — I'm definitely not gonna make this feel like school 😂\n\nHow was your day? Tell me something fun that happened!",
        "starter_opening_message": "Hello! 👋 I'm Emma.\n\nWhat is your name?",
        "topic": "Casual Chat",
    },
}


def get_persona_for_language(lang_code: str) -> Dict[str, Any]:
    return PERSONAS.get(lang_code.lower()) or PERSONAS["es"]


def get_opening_message(persona: Dict[str, Any], proficiency_level: str = "starter") -> str:
    if (proficiency_level or "").lower() == "starter":
        return persona.get("starter_opening_message") or persona.get("opening_message", "")
    return persona.get("opening_message", "")


def generate_suggested_replies(
    persona: Dict[str, Any],
    ai_message: str,
    proficiency_level: str = "beginner",
) -> List[Dict[str, str]]:
    """
    Generates dynamic, highly relevant 1-tap quick replies based on the AI's latest message.
    Works for any language (Spanish, French, Italian, German, Japanese, English).
    """
    lang = (persona.get("language_name") or "").lower()
    text = (ai_message or "").lower()
    is_starter = (proficiency_level or "").lower() == "starter"

    # 1. Asking for Name (Introductions)
    if any(k in text for k in ["t'appelles", "te llamas", "wie heißt", "come ti chiami", "お名前", "your name"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "Alex 🙋‍♂️", "text": "Bonjour Camille ! Je m'appelle Alex 😊", "translation": "Hello Camille! My name is Alex"},
                {"label": "John 🙋‍♂️", "text": "Salut ! Moi c'est John. Enchanté ✨", "translation": "Hi! I'm John. Nice to meet you"},
                {"label": "Ask back 💬", "text": "Je m'appelle Alex ! Tu vas bien ?", "translation": "My name is Alex! How are you doing?"},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "Alex 🙋‍♂️", "text": "¡Hola Sofia! Me llamo Alex 😊", "translation": "Hello Sofia! My name is Alex"},
                {"label": "John 🙋‍♂️", "text": "¡Buenas! Soy John, mucho gusto ✨", "translation": "Hi! I'm John, nice to meet you"},
                {"label": "Ask back 💬", "text": "Me llamo Alex, ¿cómo estás?", "translation": "My name is Alex, how are you?"},
            ]
        if "italian" in lang or persona.get("name") == "Marco":
            return [
                {"label": "Alex 🙋‍♂️", "text": "Ciao Marco! Mi chiamo Alex 😊", "translation": "Hi Marco! My name is Alex"},
                {"label": "John 🙋‍♂️", "text": "Piacere! Sono John ✨", "translation": "Nice to meet you! I'm John"},
                {"label": "Ask back 💬", "text": "Mi chiamo Alex, come stai?", "translation": "My name is Alex, how are you?"},
            ]
        if "german" in lang or persona.get("name") == "Lukas":
            return [
                {"label": "Alex 🙋‍♂️", "text": "Hallo Lukas! Ich heiße Alex 😊", "translation": "Hello Lukas! My name is Alex"},
                {"label": "John 🙋‍♂️", "text": "Hi! Ich bin John, freut mich ✨", "translation": "Hi! I'm John, nice to meet you"},
                {"label": "Ask back 💬", "text": "Ich heiße Alex, wie geht's dir?", "translation": "My name is Alex, how are you doing?"},
            ]
        if "japanese" in lang or persona.get("name") == "Kenji":
            return [
                {"label": "Alex 🙋‍♂️", "text": "こんにちは！アレックスです 😊", "translation": "Hello! I'm Alex"},
                {"label": "John 🙋‍♂️", "text": "ジョンと言います！よろしくね ✨", "translation": "My name is John! Nice to meet you"},
            ]
        return [
            {"label": "Alex 🙋‍♂️", "text": "Hey! I'm Alex, nice to meet you 😊", "translation": "Hey! I'm Alex, nice to meet you"},
            {"label": "John 🙋‍♂️", "text": "My name is John, great to meet you! ✨", "translation": "My name is John, great to meet you!"},
        ]

    # 2. Coffee, Tea, Drinks, Food
    if any(k in text for k in ["café", "cafe", "thé", "the", "coffee", "tea", "comer", "manger", "cenar", "dîner", "pizza", "food"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "Coffee ☕", "text": "Je préfère le café, sans hésiter ! ☕", "translation": "I prefer coffee, definitely!"},
                {"label": "Tea 🍵", "text": "J'aime beaucoup le thé vert 🍵 Et toi ?", "translation": "I really like green tea. And you?"},
                {"label": "Both! 😋", "text": "J'aime les deux ! Un bon café le matin, du thé après.", "translation": "I like both! Coffee in the morning, tea later."},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "Coffee ☕", "text": "¡Prefiero el café definitivamente! ☕", "translation": "I definitely prefer coffee!"},
                {"label": "Tea 🍵", "text": "Me gusta más el té 🍵 ¿Y a ti?", "translation": "I like tea more. And you?"},
                {"label": "Both! 😋", "text": "¡Me encantan los dos! Depende del momento.", "translation": "I love both! Depends on the moment."},
            ]
        if "italian" in lang or persona.get("name") == "Marco":
            return [
                {"label": "Espresso ☕", "text": "Un buon caffè espresso sempre! ☕", "translation": "A good espresso always!"},
                {"label": "Tea 🍵", "text": "Preferisco il tè o una tisana 🍵", "translation": "I prefer tea or herbal tea"},
                {"label": "Pizza 🍕", "text": "Adoro la pizza margherita! 😋", "translation": "I love margherita pizza!"},
            ]
        if "german" in lang or persona.get("name") == "Lukas":
            return [
                {"label": "Coffee ☕", "text": "Ich liebe Kaffee am Morgen! ☕", "translation": "I love coffee in the morning!"},
                {"label": "Tea 🍵", "text": "Ich trinke lieber Tee 🍵 Und du?", "translation": "I prefer drinking tea. And you?"},
            ]
        return [
            {"label": "Coffee ☕", "text": "Coffee 100%! Can't start my day without it ☕", "translation": "Coffee 100%! Can't start my day without it"},
            {"label": "Tea 🍵", "text": "Definitely team tea 🍵 How about you?", "translation": "Definitely team tea. How about you?"},
            {"label": "Both! 😋", "text": "I love both! Coffee in the morning, tea in the afternoon.", "translation": "I love both! Coffee in the morning, tea in the afternoon."},
        ]

    # 3. How are you / How was your day / Greetings
    if any(k in text for k in ["comment tu vas", "ça va", "tu vas bien", "journée", "s'est passée", "cómo estás", "como estas", "qué tal", "tu día", "wie geht", "wie war dein tag", "come stai", "com'è andata", "how are you", "how was your day"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "Great! 😊", "text": "Ça va très bien, merci ! Et toi ?", "translation": "Very well, thank you! And you?"},
                {"label": "Good day ✨", "text": "J'ai passé une super journée, tranquille !", "translation": "I had a great day, chill!"},
                {"label": "A bit tired 🥱", "text": "Un peu fatigué(e) aujourd'hui, mais ça va !", "translation": "A bit tired today, but doing okay!"},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "Great! 😊", "text": "¡Muy bien, gracias! ¿Y tú qué tal?", "translation": "Very well, thanks! And how about you?"},
                {"label": "Good day ✨", "text": "¡Tuve un día genial hoy! ¿Y tú?", "translation": "I had a great day today! And you?"},
                {"label": "A bit tired 🥱", "text": "Un poco cansado/a hoy, pero bien.", "translation": "A bit tired today, but good."},
            ]
        if "italian" in lang or persona.get("name") == "Marco":
            return [
                {"label": "Great! 😊", "text": "Molto bene, grazie! E tu?", "translation": "Very well, thanks! And you?"},
                {"label": "Good day ✨", "text": "Ho passato una bella giornata oggi!", "translation": "I had a great day today!"},
            ]
        if "german" in lang or persona.get("name") == "Lukas":
            return [
                {"label": "Great! 😊", "text": "Mir geht's super, danke! Und dir?", "translation": "I'm doing great, thanks! And you?"},
                {"label": "Good day ✨", "text": "Mein Tag war echt gut und entspannt.", "translation": "My day was really good and relaxed."},
            ]
        return [
            {"label": "Great! 😊", "text": "Doing great, thanks! How about you?", "translation": "Doing great, thanks! How about you?"},
            {"label": "Good day ✨", "text": "Had a really nice day today!", "translation": "Had a really nice day today!"},
            {"label": "A bit tired 🥱", "text": "A bit tired, but overall good!", "translation": "A bit tired, but overall good!"},
        ]

    # 4. Location / City / Where are you from
    if any(k in text for k in ["d'où", "de dónde", "de donde", "habites", "où habites", "ville", "país", "pais", "woher", "wohnst", "dove vivi", "di dove", "where are you from", "where do you live", "coin"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "City 🏙️", "text": "J'habite en ville ! Et toi, tu es d'où ? 🏙️", "translation": "I live in the city! And you, where are you from?"},
                {"label": "Quiet place 🌿", "text": "J'habite dans un endroit calme. C'est très sympa.", "translation": "I live in a quiet place. It's very nice."},
                {"label": "Ask Paris 🎨", "text": "Tu aimes vivre à Paris ? C'est une belle ville !", "translation": "Do you like living in Paris? It's a beautiful city!"},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "City 🏙️", "text": "Vivo en una ciudad grande, ¿y tú de dónde eres? 🏙️", "translation": "I live in a big city, and where are you from?"},
                {"label": "Quiet place 🌿", "text": "Vivo en un sitio tranquilo y me gusta mucho.", "translation": "I live in a quiet place and I really like it."},
                {"label": "Ask Barcelona 🏖️", "text": "¿Qué es lo que más te gusta de Barcelona?", "translation": "What do you like the most about Barcelona?"},
            ]
        return [
            {"label": "Big city 🏙️", "text": "I live in a big city! Where are you from? 🏙️", "translation": "I live in a big city! Where are you from?"},
            {"label": "Quiet town 🌿", "text": "I live in a nice quiet town. How about you?", "translation": "I live in a nice quiet town. How about you?"},
        ]

    # 5. Music / Songs / Artists
    if any(k in text for k in ["musique", "música", "music", "musik", "musica", "écouter", "chanson", "artistas"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "Pop & Indie 🎸", "text": "J'adore écouter de la pop et de l'indie ! 🎶", "translation": "I love listening to pop and indie!"},
                {"label": "Everything 🎧", "text": "J'écoute un peu de tout avec mon casque 🎧", "translation": "I listen to a bit of everything with headphones"},
                {"label": "Recommend? 🎵", "text": "Tu as des artistes français préférés à me conseiller ?", "translation": "Do you have favorite French artists to recommend to me?"},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "Pop & Rock 🎸", "text": "¡Me encanta el pop y el rock en español! 🎶", "translation": "I love pop and rock in Spanish!"},
                {"label": "Everything 🎧", "text": "Escucho de todo un poco con auriculares 🎧", "translation": "I listen to a bit of everything with headphones"},
                {"label": "Recommend? 🎵", "text": "¿Qué música me recomiendas escuchar?", "translation": "What music do you recommend I listen to?"},
            ]
        return [
            {"label": "Indie & Pop 🎸", "text": "I love indie and pop music! 🎶", "translation": "I love indie and pop music!"},
            {"label": "Everything 🎧", "text": "I listen to a bit of everything honestly 🎧", "translation": "I listen to a bit of everything honestly"},
        ]

    # 6. Pets / Animals
    if any(k in text for k in ["animaux", "animales", "mascotas", "pets", "haustiere", "cane", "gatto", "perro", "gato", "chien", "chat"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "Dog person 🐶", "text": "Oui ! J'adore les chiens 🐶", "translation": "Yes! I love dogs"},
                {"label": "Cat person 🐱", "text": "Je préfère les chats 🐱 Tu en as toi ?", "translation": "I prefer cats. Do you have one?"},
                {"label": "No pets 🐾", "text": "Pas d'animaux pour l'instant, mais j'aimerais bien !", "translation": "No pets for now, but I would like to!"},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "Dog person 🐶", "text": "¡Sí! Me encantan los perros 🐶", "translation": "Yes! I love dogs"},
                {"label": "Cat person 🐱", "text": "¡Soy del equipo gatos! 🐱 ¿Tú tienes?", "translation": "I'm team cat! Do you have any?"},
                {"label": "No pets 🐾", "text": "No tengo ahora mismo, pero me encantaría.", "translation": "I don't have pets right now, but I'd love to."},
            ]
        return [
            {"label": "Dog person 🐶", "text": "Definitely a dog person! 🐶", "translation": "Definitely a dog person!"},
            {"label": "Cat person 🐱", "text": "Team cat all the way! 🐱 Do you have pets?", "translation": "Team cat all the way! Do you have pets?"},
        ]

    # 7. Plans / Tonight / Weekend / Tomorrow
    if any(k in text for k in ["plans", "planes", "projets", "ce soir", "esta noche", "fines de semana", "week-end", "weekend", "demain", "mañana", "plus tard", "más tarde", "wochenende", "heute abend", "stasera"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "Chill at home 🛋️", "text": "Je vais me poser devant un film ce soir 🛋️", "translation": "I'm going to chill in front of a movie tonight"},
                {"label": "Go out 🍕", "text": "Je vais sortir avec des amis manger un morceau 🍕", "translation": "I'm going to go out with friends to grab a bite"},
                {"label": "No plans yet 🤷‍♂️", "text": "Pas encore de plans prévus ! Et toi ?", "translation": "No plans yet! And you?"},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "Chill at home 🛋️", "text": "Voy a descansar en casa viendo una película 🛋️", "translation": "I'm going to rest at home watching a movie"},
                {"label": "Go out 🍕", "text": "Voy a salir con amigos a cenar algo rico 🍕", "translation": "I'm going to go out with friends to have a nice dinner"},
                {"label": "No plans yet 🤷‍♂️", "text": "Todavía no tengo planes, ¿tú qué vas a hacer?", "translation": "I don't have plans yet, what are you going to do?"},
            ]
        return [
            {"label": "Chill at home 🛋️", "text": "Just gonna relax at home with a movie 🛋️", "translation": "Just gonna relax at home with a movie"},
            {"label": "Go out 🍕", "text": "Meeting up with some friends for dinner 🍕", "translation": "Meeting up with some friends for dinner"},
            {"label": "No plans yet 🤷‍♂️", "text": "No plans yet, what about you?", "translation": "No plans yet, what about you?"},
        ]

    # 8. Traveling / Trips
    if any(k in text for k in ["voyager", "voyage", "viajar", "viaje", "reisen", "viaggiare", "travel"]):
        if "french" in lang or persona.get("name") == "Camille":
            return [
                {"label": "Love traveling! ✈️", "text": "J'adore voyager et découvrir de nouveaux pays ! ✈️", "translation": "I love traveling and discovering new countries!"},
                {"label": "Dream trip 🗺️", "text": "J'aimerais beaucoup visiter le Japon un jour ! 🌸", "translation": "I'd really love to visit Japan one day!"},
            ]
        if "spanish" in lang or persona.get("name") == "Sofia":
            return [
                {"label": "Love traveling! ✈️", "text": "¡Me encanta viajar y conocer lugares nuevos! ✈️", "translation": "I love traveling and seeing new places!"},
                {"label": "Dream trip 🗺️", "text": "Me encantaría hacer un viaje pronto 🌴", "translation": "I'd love to take a trip soon"},
            ]

    # 9. Generic Fallback Conversational Reactions
    if "french" in lang or persona.get("name") == "Camille":
        return [
            {"label": "Tell me more! ✨", "text": "C'est trop bien ! Raconte-moi un peu plus 😊", "translation": "That's awesome! Tell me a bit more"},
            {"label": "Totally agree 🙌", "text": "Grave, je suis tellement d'accord avec toi ! 😂", "translation": "Totally, I agree with you so much!"},
            {"label": "Ask back 💬", "text": "Et toi, qu'est-ce que tu en penses ? ✨", "translation": "And you, what do you think about it?"},
        ]
    if "spanish" in lang or persona.get("name") == "Sofia":
        return [
            {"label": "Tell me more! ✨", "text": "¡Qué guay! Cuéntame más sobre eso 😊", "translation": "How cool! Tell me more about that"},
            {"label": "Totally agree 🙌", "text": "¡Totalmente de acuerdo contigo! 😂", "translation": "Totally agree with you!"},
            {"label": "Ask back 💬", "text": "¿Y tú qué opinas de eso? ✨", "translation": "And what do you think about that?"},
        ]
    if "italian" in lang or persona.get("name") == "Marco":
        return [
            {"label": "Tell me more! ✨", "text": "Che bello! Raccontami di più 😊", "translation": "How nice! Tell me more"},
            {"label": "Totally agree 🙌", "text": "Verissimo, sono d'accordissimo con te! 😂", "translation": "So true, I totally agree with you!"},
            {"label": "Ask back 💬", "text": "E tu cosa ne pensi? ✨", "translation": "And what do you think?"},
        ]
    if "german" in lang or persona.get("name") == "Lukas":
        return [
            {"label": "Tell me more! ✨", "text": "Das klingt mega! Erzähl mir mehr darüber 😊", "translation": "That sounds great! Tell me more about it"},
            {"label": "Totally agree 🙌", "text": "Vollkommen richtig, sehe ich genauso! 😂", "translation": "Totally right, I see it the same way!"},
            {"label": "Ask back 💬", "text": "Und was denkst du darüber? ✨", "translation": "And what do you think about that?"},
        ]
    return [
        {"label": "Tell me more! ✨", "text": "That sounds awesome! Tell me more about it 😊", "translation": "That sounds awesome! Tell me more about it"},
        {"label": "Totally agree 🙌", "text": "Haha totally agree with you on that! 😂", "translation": "Haha totally agree with you on that!"},
        {"label": "Ask back 💬", "text": "What about you? What do you think? ✨", "translation": "What about you? What do you think?"},
    ]


def build_dm_system_prompt(
    persona: Dict[str, Any],
    proficiency_level: str = "beginner",
    learning_goal: str = "casual",
    native_language_name: str = "English",
) -> str:
    level_guidance = {
        "starter": (
            "- ABSOLUTE BEGINNER (Learner only knows basic words):\n"
            "- Use ULTRA-SHORT, SIMPLE sentences (1 sentence, max 2 simple sentences).\n"
            "- Stick to essential everyday words: greetings, name, coffee, music, how they are feeling.\n"
            "- Ask only 1 very simple question at a time (e.g. 'Tu aimes le café ? ☕', 'Comment tu t'appelles ?').\n"
            "- Include friendly English translation hints in parentheses for new questions so they never get stuck!\n"
            "- Be super warm and encouraging!"
        ),
        "beginner": (
            "- Use short, clear, everyday sentences (1-2 sentences maximum).\n"
            "- Use simple vocabulary, avoid overly complex idioms.\n"
            "- If the user makes a clear beginner grammar mistake (e.g. wrong tense, agreement, or false cognate), "
            "provide a gentle, encouraging correction in the JSON output."
        ),
        "intermediate": (
            "- Use natural, conversational language with common expressions.\n"
            "- Keep replies punchy and engaging (1-3 sentences).\n"
            "- Only provide a correction if there is a noticeable grammar or phrasing mistake that hinders natural flow."
        ),
        "advanced": (
            "- Use native-speed conversational texting style, modern slang, and natural idioms.\n"
            "- Only provide a correction for subtle phrasing or unnatural word choice."
        ),
    }.get(proficiency_level.lower(), "- Keep replies short, natural, and conversational.")

    goal_guidance = {
        "casual": "Focus on everyday casual chit-chat, banter, and hobbies.",
        "natural": "Emphasize sounding like a real native speaker texting a friend.",
        "vocab": "Naturally introduce fresh, useful descriptive words in context.",
        "grammar": "Be slightly more attentive to helping refine sentence structure.",
        "confidence": "Be extra encouraging, positive, and supportive.",
        "work": "Keep conversations geared towards professional, collegiate, and networking situations.",
    }.get(learning_goal.lower(), "Focus on fun, casual texting.")

    return f"""You are {persona['name']}, a {persona['bio']}
You are texting the user via Direct Message to help them practice {persona['language_name']}.

Core Rules:
1. YOU ARE NOT AN AI OR TEACHER. Never introduce yourself as an AI assistant, language bot, or tutor. Text like a real 20-something texting a friend on Instagram or WhatsApp.
2. Reply ONLY in {persona['language_name']} in character.
3. Keep your reply concise (1-3 sentences), warm, casual, and conversational, using realistic texting style and emojis (😭, 😂, 🙌, ✨) when natural.
4. User Proficiency Level: {proficiency_level.upper()}
{level_guidance}
5. User Learning Goal: {goal_guidance}

CRITICAL: Output MUST be a valid JSON object with EXACTLY this structure:
{{
  "reply": "<your in-character message in {persona['language_name']}>",
  "correction": null OR {{
    "original": "<the specific part or sentence the user said with a mistake>",
    "better": "<the natural, correct way to say it>",
    "explanation": "<a friendly, 1-sentence explanation in {native_language_name} explaining why>"
  }},
  "suggested_replies": [
    {{
      "label": "<short 1-4 word label with emoji, e.g. 'Coffee ☕', 'Alex 🙋‍♂️', 'Super! ✨'>",
      "text": "<natural 1-tap reply in {persona['language_name']} directly answering or continuing from your reply>",
      "translation": "<brief English translation of the reply text>"
    }}
  ]
}}

Guidelines:
- In "suggested_replies", provide 2 to 4 diverse, natural 1-tap quick reply options that directly answer or react to whatever question or statement you just made in "reply". These give the learner immediate options to tap and continue the chat.
- DO NOT correct every single message! If the user's message is correct or natural, set "correction": null.
- Never lecture or sound like a strict teacher. Keep explanations warm and brief.
- If there is a correction, your "reply" must STILL respond naturally to the meaning of what the user said, as a friend would!
"""


def _mock_chat_response(
    persona: Dict[str, Any],
    user_message: str,
    proficiency_level: str = "beginner",
) -> Dict[str, Any]:
    """Rich, deterministic mock response engine for offline testing and zero-API-key usage."""
    lang = persona.get("language_name", "Spanish").lower()
    msg_lower = user_message.lower().strip()
    is_starter = (proficiency_level or "").lower() == "starter"

    # Spanish mock replies
    if "spanish" in lang or persona.get("name") == "Sofia":
        if is_starter:
            if any(w in msg_lower for w in ["alex", "john", "llamo", "soy"]):
                return {
                    "reply": "¡Mucho gusto! 😊 ¿Cómo estás hoy? (How are you today?)",
                    "correction": None,
                }
            if any(w in msg_lower for w in ["hola", "buenos", "buenas"]):
                return {
                    "reply": "¡Hola! 😊 ¿Te gusta el café o el té? ☕ (Do you like coffee or tea?)",
                    "correction": None,
                }
            if any(w in msg_lower for w in ["bien", "muy bien", "gracias", "si", "sí"]):
                return {
                    "reply": "¡Qué bien! ✨ ¿De qué país eres? (Where are you from?)",
                    "correction": None,
                }
            starter_replies = [
                "¡Qué genial! 😊 ¿Te gusta la música? 🎵 (Do you like music?)",
                "¡Qué bien! 🙌 ¿Tienes mascotas? 🐶 (Do you have pets?)",
                "¡Mucho gusto! ✨ ¿Qué planes tienes hoy? (What plans do you have today?)",
            ]
            return {"reply": random.choice(starter_replies), "correction": None}

        # Check for common beginner mistakes
        if "soy hambriento" in msg_lower or "yo soy hambre" in msg_lower:
            return {
                "reply": "¡Jajaja ay no! 🍕 ¡Ve a comer algo ya! ¿Qué se te antoja cenar?",
                "correction": {
                    "original": user_message,
                    "better": "Tengo hambre",
                    "explanation": "In Spanish we say 'tener hambre' (to have hunger) rather than using 'ser' (to be)!",
                },
            }
        if "ayer yo comer" in msg_lower or "ayer comer" in msg_lower:
            return {
                "reply": "¿En serio? ¿Y qué comiste de rico? 😋 A mí me encanta probar sitios nuevos.",
                "correction": {
                    "original": user_message,
                    "better": "Ayer comí",
                    "explanation": "For past events ('yesterday'), use the preterite tense 'comí' instead of the infinitive 'comer'!",
                },
            }
        if "me llamo es" in msg_lower:
            return {
                "reply": "¡Qué bonito nombre! Encantada de conocerte ✨ ¿De dónde eres?",
                "correction": {
                    "original": user_message,
                    "better": "Me llamo...",
                    "explanation": "Say 'Me llamo [Name]' or 'Mi nombre es [Name]', without mixing both!",
                },
            }

        replies = [
            "¡Qué bien! Me alegro mucho 😊 ¿Y qué planes tienes para más tarde?",
            "Jajaja ¡totalmente de acuerdo! 🙌 A mí me pasa exactamente lo mismo.",
            "¡No me digas! 😮 ¿Y cómo terminó eso? Cuéntame más.",
            "¡Qué guay! Me encanta eso ✨ Por cierto, ¿qué tipo de música sueles escuchar?",
            "Uff, te entiendo perfectamente 😭 A veces los días se hacen eternos. ¿Pudiste descansar?",
        ]
        return {"reply": random.choice(replies), "correction": None}

    # French mock replies
    if "french" in lang or persona.get("name") == "Camille":
        if is_starter:
            if any(w in msg_lower for w in ["alex", "john", "m'appelle", "moi c'est", "je suis"]):
                return {
                    "reply": "Enchantée ! 😊 Tu vas bien aujourd'hui ? (Are you doing well today?)",
                    "correction": None,
                }
            if any(w in msg_lower for w in ["bonjour", "salut", "coucou", "hello", "hi"]):
                return {
                    "reply": "Coucou ! 😊 Tu aimes le café ou le thé ? ☕ (Do you like coffee or tea?)",
                    "correction": None,
                }
            if any(w in msg_lower for w in ["bien", "ca va", "ça va", "super", "oui", "merci"]):
                return {
                    "reply": "Super ! ✨ Tu habites dans quelle ville ? (What city do you live in?)",
                    "correction": None,
                }
            if any(w in msg_lower for w in ["café", "cafe", "thé", "the"]):
                return {
                    "reply": "Moi aussi j'adore ça ! ☕ Et tu aimes la musique ? 🎵 (Do you like music?)",
                    "correction": None,
                }
            starter_replies = [
                "C'est très sympa ! 😊 Et toi, tu as passé une bonne journée ? ✨",
                "Trop bien ! 🙌 Tu aimes voyager ? ✈️ (Do you like traveling?)",
                "Super ! 😊 Tu as des animaux de compagnie ? 🐶 (Do you have pets?)",
            ]
            return {"reply": random.choice(starter_replies), "correction": None}

        if "je suis fini" in msg_lower:
            return {
                "reply": "Super ! Tu vas pouvoir te poser un peu maintenant ☕ Tu as des projets pour ce soir ?",
                "correction": {
                    "original": user_message,
                    "better": "J'ai fini",
                    "explanation": "In French, to say 'I have finished', use 'avoir' (J'ai fini), because 'je suis fini' means 'I am ruined/dead' 😂!",
                },
            }
        replies = [
            "Trop bien ! Ça fait plaisir à entendre 😊 Et sinon, tu as prévu quoi pour ce soir ?",
            "Ah oui, carrément ! ☕ Je suis tellement d'accord avec toi.",
            "C'est vrai ?? Raconte, je veux tout savoir ! ✨",
            "Trop cool ! J'adore ça aussi. Tu habites dans quel coin d'ailleurs ?",
        ]
        return {"reply": random.choice(replies), "correction": None}

    # English mock replies
    if "english" in lang or persona.get("name") == "Emma":
        if "i go to the store yesterday" in msg_lower or "yesterday i go" in msg_lower:
            return {
                "reply": "Oh nice! Did you pick up anything good? I love shopping trips 😂",
                "correction": {
                    "original": user_message,
                    "better": "Yesterday I went...",
                    "explanation": "Use past tense 'went' instead of 'go' when talking about yesterday!",
                },
            }
        replies = [
            "That sounds amazing! 😊 Tell me more, what else did you get up to today?",
            "Haha totally agree! 😭 I feel like that always happens. What's next on your to-do list?",
            "No way, really?! That's so cool 🙌 How long have you been doing that?",
        ]
        return {"reply": random.choice(replies), "correction": None}

    # Generic language fallback
    generic_replies = [
        f"That's so nice! 😊 How was the rest of your day?",
        f"Haha totally! 🙌 Tell me more about what you did today.",
        f"That sounds great! ✨ What are your plans for tomorrow?",
    ]
    return {"reply": random.choice(generic_replies), "correction": None}


def get_ai_chat_response(
    persona: Dict[str, Any],
    history: List[Dict[str, str]],
    user_message: str,
    proficiency_level: str = "beginner",
    learning_goal: str = "casual",
    native_language_name: str = "English",
) -> Dict[str, Any]:
    """
    Main entry point for generating conversational AI replies with structured corrections and contextual suggested replies.
    Returns: {"reply": str, "correction": Optional[Dict[str, str]], "suggested_replies": List[Dict[str, str]]}
    """
    provider = settings.llm_provider
    res = None

    if provider == "openai" and settings.openai_api_key:
        try:
            res = _call_openai_chat(
                persona, history, user_message, proficiency_level, learning_goal, native_language_name
            )
        except Exception:
            # Fall back to mock on API error
            pass

    if not res and provider == "anthropic" and settings.anthropic_api_key:
        try:
            res = _call_anthropic_chat(
                persona, history, user_message, proficiency_level, learning_goal, native_language_name
            )
        except Exception:
            # Fall back to mock on API error
            pass

    if not res:
        res = _mock_chat_response(persona, user_message, proficiency_level)

    # Ensure dynamic suggested replies are always populated
    if not res.get("suggested_replies"):
        res["suggested_replies"] = generate_suggested_replies(
            persona,
            res.get("reply", ""),
            proficiency_level,
        )

    return res


def _call_openai_chat(
    persona: Dict[str, Any],
    history: List[Dict[str, str]],
    user_message: str,
    proficiency_level: str,
    learning_goal: str,
    native_language_name: str,
) -> Dict[str, Any]:
    system_prompt = build_dm_system_prompt(persona, proficiency_level, learning_goal, native_language_name)
    messages = [{"role": "system", "content": system_prompt}] + history + [
        {"role": "user", "content": user_message}
    ]

    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "content-type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.75,
            "max_tokens": 400,
        },
        timeout=25,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(raw)
    return {
        "reply": data.get("reply", "..."),
        "correction": data.get("correction"),
        "suggested_replies": data.get("suggested_replies") or [],
    }


def _call_anthropic_chat(
    persona: Dict[str, Any],
    history: List[Dict[str, str]],
    user_message: str,
    proficiency_level: str,
    learning_goal: str,
    native_language_name: str,
) -> Dict[str, Any]:
    system_prompt = build_dm_system_prompt(persona, proficiency_level, learning_goal, native_language_name)
    messages = history + [{"role": "user", "content": user_message}]

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.anthropic_model,
            "max_tokens": 400,
            "system": system_prompt,
            "messages": messages,
        },
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    text = "".join(parts).strip()

    # Try parsing JSON from Anthropic output
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return {
                "reply": parsed.get("reply", text),
                "correction": parsed.get("correction"),
                "suggested_replies": parsed.get("suggested_replies") or [],
            }
        except Exception:
            pass

    return {"reply": text, "correction": None, "suggested_replies": []}


# Backward compatibility for legacy lesson loop
def build_system_prompt(*args, **kwargs) -> str:
    return "You are a helpful language chat partner."


def get_ai_reply(system_prompt: str, history: List[Dict[str, str]], user_message: str, new_words: List[str]) -> str:
    persona = PERSONAS["fr"]
    res = get_ai_chat_response(persona, history, user_message)
    return res["reply"]


# ==============================================================================
# Translation Engine
# ==============================================================================

KNOWN_TRANSLATIONS = {
    # Full greetings
    "Coucou ! 👋 Moi c'est Camille. Je vais t'aider à pratiquer le français, mais t'inquiète — ça va pas ressembler à un cours d'école 😂\n\nComment s'est passée ta journée ? Raconte-moi un truc sympa !":
        "Hey! 👋 I'm Camille. I'm going to help you practice French, but don't worry — it's not going to feel like a school class 😂\n\nHow was your day? Tell me something fun!",
    "¡Holaaa! 👋 Soy Sofia. Te voy a ayudar a practicar español, pero tranqui — no te voy a hacer sentir como en el cole 😂\n\n¿Qué tal tu día hoy? Cuéntame algo divertido.":
        "Heyyy! 👋 I'm Sofia. I'm going to help you practice Spanish, but don't worry — I'm not going to make you feel like you're in school 😂\n\nHow was your day? Tell me something fun.",
    "Ciao! 👋 Sono Marco. Ti aiuterò a praticare l'italiano, ma non preoccuparti — niente lezioni noiose come a scuola 😂\n\nCom'è andata la tua giornata? Raccontami qualcosa!":
        "Hi! 👋 I'm Marco. I'll help you practice Italian, but don't worry — no boring lessons like in school 😂\n\nHow did your day go? Tell me something!",
    "Hey! 👋 Ich bin Lukas. Ich helfe dir dabei, dein Deutsch zu üben — und keine Sorge, das fühlt sich nicht wie Schule an 😂\n\nWie war dein Tag heute? Erzähl mal was Spannendes!":
        "Hey! 👋 I'm Lukas. I'll help you practice your German — and don't worry, it doesn't feel like school 😂\n\nHow was your day today? Tell me something exciting!",
    "ヤッホー！👋 ケンジだよ。日本語の練習、気軽に付き合うから安心してね！学校の授業みたいにはしないからさ 😂\n\n今日はどんな一日だった？何か面白いことあった？":
        "Yoo! 👋 I'm Kenji. Feel free to practice Japanese with me, don't worry! I won't make it like school classes 😂\n\nHow was your day? Anything interesting happen?",
    # Starter greetings
    "Bonjour ! 👋 Moi c'est Camille.\n\nComment tu t'appelles ? (What is your name?)":
        "Hello! 👋 I'm Camille.\n\nWhat is your name?",
    "¡Hola! 👋 Soy Sofia.\n\n¿Cómo te llamas? (What is your name?)":
        "Hello! 👋 I'm Sofia.\n\nWhat is your name?",
    "Ciao! 👋 Sono Marco.\n\nCome ti chiami? (What is your name?)":
        "Hi! 👋 I'm Marco.\n\nWhat is your name?",
    "Hallo! 👋 Ich bin Lukas.\n\nWie heißt du? (What is your name?)":
        "Hello! 👋 I'm Lukas.\n\nWhat is your name?",
    "こんにちは！👋 ケンジだよ。\n\nお名前は何ですか？ (What is your name?)":
        "Hello! 👋 I'm Kenji.\n\nWhat is your name?",
    "Hello! 👋 I'm Emma.\n\nWhat is your name?":
        "Hello! 👋 I'm Emma.\n\nWhat is your name?",
}

SENTENCE_TRANSLATIONS = {
    # French sentences
    "comment s'est passée ta journée ?": "how was your day?",
    "raconte-moi un truc sympa !": "tell me something fun / nice!",
    "raconte-moi un truc sympa": "tell me something nice",
    "qu'est-ce que tu racontes de beau aujourd'hui ?": "what nice things are you up to today?",
    "qu'est-ce que tu racontes de beau aujourd'hui": "what nice things are you up to today",
    "tu as prévu quoi pour ce soir ?": "what do you have planned for tonight?",
    "tu as prévu quoi pour ce soir": "what do you have planned for tonight",
    "comment ça va ?": "how is it going?",
    "comment ça va": "how is it going",
    "salut ! comment ça va aujourd’hui ?": "hi! how are you doing today?",
    "j'ai bu un super café ce matin": "I had a great coffee this morning",
    "tu fais quoi de beau à paris en ce moment ?": "what fun things are you doing in Paris right now?",
    "ça fait plaisir à entendre": "that's really nice to hear",
    "je suis tellement d'accord avec toi": "I completely agree with you",
    "raconte, je veux tout savoir !": "tell me, I want to know everything!",
    "tu habites dans quel coin d'ailleurs ?": "by the way, what area do you live in?",
    # Spanish sentences
    "¿qué tal tu día hoy?": "how was your day today?",
    "cuéntame algo divertido": "tell me something fun",
    "¡hola! ¿cómo estás hoy?": "hello! how are you today?",
    "hoy me tomé un café delicioso": "today I had a delicious coffee",
    "¿te gusta el café?": "do you like coffee?",
    "¿qué música estás escuchando últimamente?": "what music have you been listening to lately?",
    # English to French / Spanish common phrases
    "hello": "bonjour / salut",
    "how are you?": "comment vas-tu ? / comment ça va ?",
    "how are you": "comment ça va ?",
    "i had a good day": "j'ai passé une bonne journée",
    "what are you doing?": "tu fais quoi ?",
    "see you later": "à plus tard / à bientôt",
    "good night": "bonne nuit",
    "thank you very much": "merci beaucoup",
}

WORD_DICTIONARY = {
    # French words
    "bonjour": "hello / good morning",
    "salut": "hi / bye",
    "coucou": "hey / hi there",
    "moi": "me / myself",
    "c'est": "it is / that is",
    "je": "I",
    "tu": "you",
    "vais": "am going",
    "aider": "to help",
    "pratiquer": "to practice",
    "français": "French",
    "mais": "but",
    "t'inquiète": "don't worry",
    "ressembler": "to look like / resemble",
    "cours": "class / lesson",
    "école": "school",
    "comment": "how",
    "passée": "passed / went",
    "journée": "day",
    "raconte": "tell / narrate",
    "raconte-moi": "tell me",
    "racontes": "you tell / what you're chatting about",
    "truc": "thing / stuff",
    "sympa": "nice / cool / pleasant",
    "beau": "beautiful / handsome / nice",
    "aujourd'hui": "today",
    "soir": "evening / tonight",
    "demain": "tomorrow",
    "matin": "morning",
    "café": "coffee",
    "super": "great / awesome",
    "trop": "too much / super (slang)",
    "d'accord": "in agreement / okay",
    "merci": "thank you",
    "oui": "yes",
    "non": "no",
    "plaisir": "pleasure",
    "entendre": "to hear",
    "habites": "you live",
    "coin": "corner / neighborhood",
    "d'ailleurs": "by the way",
    # Spanish words
    "hola": "hello",
    "holaaa": "heyyy",
    "amigo": "friend",
    "amiga": "friend (female)",
    "gracias": "thank you",
    "tranqui": "chill / don't worry",
    "cole": "school",
    "día": "day",
    "hoy": "today",
    "divertido": "fun / entertaining",
    "música": "music",
    "tarde": "afternoon / late",
    "planes": "plans",
    "bueno": "good",
    "bien": "well",
    "café": "coffee",
    "delicioso": "delicious",
    "escuchando": "listening",
    # German words
    "hallo": "hello",
    "danke": "thank you",
    "bitte": "please",
    "schule": "school",
    "tag": "day",
    "heute": "today",
    "spannend": "exciting",
    # Italian words
    "ciao": "hello / goodbye",
    "grazie": "thank you",
    "scuola": "school",
    "giornata": "day",
    "qualcosa": "something",
}


def _mock_translation(text: str, target_lang_name: str) -> str:
    cleaned = text.strip()
    if cleaned in KNOWN_TRANSLATIONS:
        return KNOWN_TRANSLATIONS[cleaned]
    for k, v in KNOWN_TRANSLATIONS.items():
        if cleaned.startswith(k[:30]):
            return v

    lower_cleaned = cleaned.lower().strip(".,!?:;\"'«»—()[]")

    # Sentence-level exact match
    if lower_cleaned in SENTENCE_TRANSLATIONS:
        return SENTENCE_TRANSLATIONS[lower_cleaned]

    # Single word lookup
    if lower_cleaned in WORD_DICTIONARY:
        return WORD_DICTIONARY[lower_cleaned]

    # Clean stripped words in sentence
    words = lower_cleaned.split()
    if len(words) == 1 and words[0] in WORD_DICTIONARY:
        return WORD_DICTIONARY[words[0]]

    # If it's 2-3 words, try individual lookups
    if 1 < len(words) <= 3:
        translated_parts = [WORD_DICTIONARY.get(w, w) for w in words]
        if any(w in WORD_DICTIONARY for w in words):
            return " ".join(translated_parts)

    # Dynamic fallback showing the clean translated label
    return f"{text} ({target_lang_name})"



def _call_openai_translation(text: str, target_lang_name: str) -> str:
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "content-type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a professional translator. Translate the given text accurately and naturally into {target_lang_name}. Output ONLY the translated text, with no explanations, notes, or quote marks.",
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip().strip('"')


def _call_anthropic_translation(text: str, target_lang_name: str) -> str:
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.anthropic_model,
            "max_tokens": 300,
            "system": f"You are a professional translator. Translate the given text accurately and naturally into {target_lang_name}. Output ONLY the translated text, with no explanations, notes, or quote marks.",
            "messages": [{"role": "user", "content": text}],
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return "".join(parts).strip().strip('"')


def get_translation(text: str, target_lang_name: str = "English") -> str:
    """Translate text into the specified language."""
    provider = settings.llm_provider
    if provider == "openai" and settings.openai_api_key:
        try:
            return _call_openai_translation(text, target_lang_name)
        except Exception:
            pass

    if provider == "anthropic" and settings.anthropic_api_key:
        try:
            return _call_anthropic_translation(text, target_lang_name)
        except Exception:
            pass

    return _mock_translation(text, target_lang_name)
