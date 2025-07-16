# Pokemon Deck Builder API

A FastAPI-based conversational AI system for building Pokemon Trading Card Game decks. Features intelligent deck building guidance, card search, and phase-based progression through the deck construction process.

## Features

- 🤖 **Conversational AI Deck Building** - Claude AI provides expert Pokemon TCG guidance
- 🔍 **Smart Card Search** - Dynamic queries with type, HP, and name filtering
- 📊 **Phase-Based Progression** - Strategy → Core Pokemon → Support → Energy → Complete
- 🎯 **Intent Analysis** - Understands user messages and provides contextual responses
- 📚 **TCG Rules Enforcement** - 60-card decks, max 4 copies, evolution chains
- 🗃️ **Supabase Integration** - Real-time card database with standard format filtering

## Quick Start

### Prerequisites

- Python 3.9+
- Supabase account and database
- Claude API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd pokemon-deck-builder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

4. **Start the server**
   ```bash
   python main.py
   ```

5. **Test the API**
   ```bash
   python test_client.py
   ```

## Environment Variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
CLAUDE_API_KEY=your-claude-api-key
```

## API Endpoints

### Main Conversation
- `POST /decks/pokemon-chat` - Conversational deck building interface

### Card Management
- `GET/POST /cards/search` - Search Pokemon cards with filters
- `GET /cards/filters` - Get available filter options
- `GET /cards/{card_id}` - Get specific card details

### Deck Management  
- `POST /decks/add-card` - Add specific cards to deck
- `GET /decks/summary/{user_id}` - Get current deck state

### System
- `GET /health` - Health check with service status
- `GET /docs` - Interactive API documentation

## Usage Examples

### Start a Conversation
```bash
curl -X POST "http://localhost:8000/decks/pokemon-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "trainer123",
    "message": "I want to build an aggressive fire deck"
  }'
```

### Search for Cards
```bash
curl "http://localhost:8000/cards/search?name=Charizard&card_types=Pokémon&limit=5"
```

### Add Card to Deck
```bash
curl -X POST "http://localhost:8000/decks/add-card" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "trainer123",
    "card_id": "base1-4",
    "quantity": 2
  }'
```

## Architecture

### Core Components

- **Conversation Service** - Manages deck building state and phase progression
- **Intent Analyzer** - Parses user messages to understand intent and extract card information
- **Claude Client** - Provides expert Pokemon TCG guidance and recommendations
- **Card Queries** - Dynamic Supabase queries with standard format filtering
- **Deck Building Service** - Main orchestrator that coordinates all components

### Database Schema

The system expects a Supabase table named `pokemon_cards` with columns:
- `id` - Unique card identifier
- `name` - Card name
- `card_type` - Pokemon, Trainer, or Energy
- `pokemon_types` - Array of Pokemon types (Fire, Water, etc.)
- `hp` - Hit points for Pokemon cards
- `subtypes` - Array of card subtypes (Basic, Stage 1, Supporter, etc.)
- `standard_legal` - Boolean for tournament legality

### Phase Progression

1. **Strategy Phase** - Define deck archetype and strategy
2. **Core Pokemon Phase** - Select main attackers (8-12 cards)
3. **Support Phase** - Add Trainer cards for consistency (20-35 cards)
4. **Energy Phase** - Add Energy cards to power attacks (8-15 cards)
5. **Complete Phase** - Finalize and optimize the 60-card deck

## Development

### Project Structure
```
pokemon-deck-builder/
├── app/
│   ├── database/           # Supabase integration
│   ├── routers/           # FastAPI route handlers
│   ├── schemas/           # Pydantic models
│   ├── services/          # Business logic
│   └── utils/             # Utilities (Claude client, intent analyzer)
├── main.py               # FastAPI application
├── test_client.py        # Test suite
└── requirements.txt      # Dependencies
```

### Running Tests
```bash
# Start the server first
python main.py

# Run the test suite
python test_client.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [Claude AI](https://www.anthropic.com/claude)
- Database by [Supabase](https://supabase.com/)
- Pokemon TCG data structure follows official tournament standards