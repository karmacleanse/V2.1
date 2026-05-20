"""
Sketch generator using fal.ai Flux Schnell.
Generates ultra-minimal monochrome line-art sketches as watermarks for paid certificates.
~$0.003 per image, <1 second generation.
"""
import os
import logging
import re
from pathlib import Path
from dotenv import load_dotenv
import fal_client

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

# Set FAL_KEY env so fal_client picks it up
if os.environ.get('FAL_KEY'):
    fal_client.api_key = os.environ['FAL_KEY']

# Symbolic keyword mapping by severity (for consistent style across same severity)
SEVERITY_SYMBOLS = {
    'Low': [
        'paper crane',
        'closed envelope',
        'broken pencil',
        'single fallen leaf',
        'smoke trail',
    ],
    'Moderate': [
        'two intertwined circles',
        'tangled thread spool',
        'half-open padlock',
        'cracked porcelain cup',
        'fading handprint',
    ],
    'High': [
        'broken bridge with missing planks',
        'chain with one broken link',
        'torn page',
        'empty wooden chair',
        'fractured mirror',
    ],
    'Critical': [
        'shattered hourglass with falling sand',
        'labyrinth with closed exits',
        'broken compass',
        'empty bird cage with open door',
        'torn black flag',
    ],
}

# Keywords extracted from confession to add symbolic detail
KEYWORD_SYMBOLS = {
    'ghost': 'faceless silhouette walking away',
    'lie': 'crossed fingers',
    'cheat': 'two diverging paths',
    'forgot': 'empty calendar page',
    'late': 'broken clock with falling hands',
    'message': 'sealed letter envelope',
    'meeting': 'empty conference chair',
    'friend': 'two empty cups facing each other',
    'birthday': 'unlit candle with smoke',
    'apology': 'outstretched open hand',
}

BASE_STYLE = (
    "black ink line art illustration, "
    "bold clean outlines, simple iconic drawing, "
    "centered composition on white background, "
    "vintage engraving style, woodcut inspired, "
    "bureaucratic stamp aesthetic"
)

NEGATIVE_PROMPT = (
    "blank, empty, white space only, "
    "photorealistic, anime, manga, 3d render, "
    "colorful, vibrant, painted, shaded, "
    "text, words, letters, signature, watermark, logo, "
    "busy composition, cluttered, multiple subjects"
)


def build_sketch_prompt(severity_class: str, confession: str) -> str:
    """Build prompt with consistent style + symbolic subject"""
    import random
    
    # Pick a symbol — primarily by severity, supplemented by keyword
    text = confession.lower()
    matched_keyword = None
    for keyword, symbol in KEYWORD_SYMBOLS.items():
        if keyword in text:
            matched_keyword = symbol
            break
    
    # Base symbol by severity
    symbols = SEVERITY_SYMBOLS.get(severity_class, SEVERITY_SYMBOLS['Moderate'])
    # Use deterministic pick by confession length so same confession -> same sketch
    symbol_idx = (len(confession) + (ord(severity_class[0]) if severity_class else 0)) % len(symbols)
    base_symbol = symbols[symbol_idx]
    
    subject = matched_keyword if matched_keyword else base_symbol
    
    return f"{subject}, {BASE_STYLE}"


async def generate_sketch(severity_class: str, confession: str) -> dict:
    """
    Generate a minimalist sketch image for a paid certificate.
    Returns: {'url': str, 'prompt': str} or {'error': str}
    """
    if not os.environ.get('FAL_KEY'):
        return {'error': 'FAL_KEY not configured'}
    
    prompt = build_sketch_prompt(severity_class, confession)
    logger.info(f"Generating sketch with prompt: {prompt[:100]}...")
    
    try:
        # Deterministic seed by severity for consistency
        seed = hash(severity_class + str(len(confession))) % 100000
        
        handler = await fal_client.submit_async(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "square_hd",  # 1024x1024
                "num_inference_steps": 4,  # Flux schnell is super fast at 4 steps
                "num_images": 1,
                "enable_safety_checker": True,
                "seed": seed,
            },
        )
        
        result = await handler.get()
        
        if not result.get('images'):
            logger.error(f"No images returned: {result}")
            return {'error': 'No image generated'}
        
        image_url = result['images'][0]['url']
        logger.info(f"Sketch generated: {image_url}")
        
        return {
            'url': image_url,
            'prompt': prompt,
            'seed': seed,
        }
        
    except Exception as e:
        logger.error(f"Sketch generation failed: {e}")
        return {'error': str(e)}
