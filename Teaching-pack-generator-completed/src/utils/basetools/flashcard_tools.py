import os
import json
from typing import List, Dict, Any

def generate_flashcards_html(title: str, flashcards: List[Dict[str, Any]]) -> str:
    """
    Generates a standalone HTML file for flashcards.
    
    Args:
        title: The title of the flashcard set (e.g., "Beginner Group Flashcards")
        flashcards: List of dicts with 'front', 'back', 'type', 'difficulty'
    """
    
    cards_html = ""
    for idx, card in enumerate(flashcards):
        front = card.get('front', '')
        back = card.get('back', '')
        card_type = card.get('type', 'Term')
        difficulty = card.get('difficulty', '')
        
        cards_html += f"""
        <div class="flashcard-container">
            <div class="flashcard" onclick="this.classList.toggle('flipped')">
                <div class="front">
                    <span class="card-type">{card_type}</span>
                    <div class="content">{front}</div>
                    <div class="hint">Click to flip</div>
                </div>
                <div class="back">
                    <span class="card-label">Explanation</span>
                    <div class="content">{back}</div>
                    {'<div class="difficulty">Difficulty: ' + str(difficulty) + '</div>' if difficulty else ''}
                </div>
            </div>
        </div>
        """

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{
            color: #333;
            margin-bottom: 30px;
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            width: 100%;
            max-width: 1200px;
        }}
        .flashcard-container {{
            perspective: 1000px;
            height: 250px;
            cursor: pointer;
        }}
        .flashcard {{
            position: relative;
            width: 100%;
            height: 100%;
            transition: transform 0.6s;
            transform-style: preserve-3d;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-radius: 15px;
        }}
        .flashcard.flipped {{
            transform: rotateY(180deg);
        }}
        .front, .back {{
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            border-radius: 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            box-sizing: border-box;
            text-align: center;
        }}
        .front {{
            background-color: white;
            color: #333;
        }}
        .back {{
            background-color: #6366f1;
            color: white;
            transform: rotateY(180deg);
        }}
        .card-type {{
            position: absolute;
            top: 15px;
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #6366f1;
            background: #eef2ff;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 700;
        }}
        .back .card-label {{
            position: absolute;
            top: 15px;
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.8);
        }}
        .content {{
            font-size: 1.2em;
            line-height: 1.5;
            overflow-y: auto;
            max-height: 160px;
            width: 100%;
        }}
        .hint {{
            position: absolute;
            bottom: 15px;
            font-size: 0.8em;
            color: #999;
        }}
        .difficulty {{
            position: absolute;
            bottom: 15px;
            font-size: 0.8em;
            background: rgba(0,0,0,0.2);
            padding: 2px 8px;
            border-radius: 4px;
        }}
        /* Print styles */
        @media print {{
            .flashcard-container {{
                page-break-inside: avoid;
                height: auto;
                margin-bottom: 20px;
                border: 1px solid #ccc;
            }}
            .flashcard {{
                transform: none !important;
                box-shadow: none;
                display: block;
            }}
            .front, .back {{
                position: relative;
                height: auto;
                backface-visibility: visible;
                transform: none;
                border-bottom: 1px dashed #ccc;
            }}
            .back {{
                background-color: white;
                color: black;
            }}
            .hint {{ display: none; }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="cards-grid">
        {cards_html}
    </div>
    <script>
        // No JS needed for individual flip, handling via inline onclick
    </script>
</body>
</html>
    """
    return html_template
