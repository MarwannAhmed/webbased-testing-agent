# Web-Based Testing Agent

An AI-powered QA assistant built with Streamlit that acts as a "Human-in-the-Loop" partner for QA Engineers, solving real-world testing challenges through exploration, test design, and implementation.

## 📋 Project Vision

This project creates a capable testing partner that:
- **Explores** web pages to understand their structure, logic, and interactivity
- **Designs** test cases collaboratively with human oversight
- **Implements** executable, clean, and maintainable test code (Playwright + Python)
- **Verifies** that tests pass and provides evidence to build trust

The system emphasizes transparency and observability, allowing users to see the agent's work in real-time through a controlled browser instance and detailed metrics.

## 🎯 Key Features

### Exploration & Knowledge Acquisition
- Deep understanding of page structure through DOM analysis, screenshots, or hybrid approaches
- Intelligent navigation and element discovery
- Structured representation of pages capturing element candidates and locators

### Collaborative Test Design
- AI-proposed test case generation with coverage visualization
- Interactive review and refinement process
- Human-in-the-loop validation for quality assurance

### Implementation (Code Generation)
- Executable test code generation using Playwright + Python
- Intelligent locator strategy selection (ID, CSS, XPath, Semantic)
- Self-correction mechanisms during code generation

### Verification & Trust Building
- Evidence-based test validation with screenshots or video
- Step-by-step execution logs
- Iterative refinement based on user critique

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd webbased-testing-agent
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```
   Optional: Install additional browsers
   ```bash
   playwright install firefox
   playwright install webkit
   ```

6. **Get Gemini API Key**

   Obtain a free API key from Google AI Studio:
   - Visit https://aistudio.google.com/app/apikey
   - Click "Create API Key"
   - Copy the key and add it to your `.env` file as `GEMINI_API_KEY`

7. **Configure environment variables**

   Create a `.env` file in the root directory:
   ```bash
   DEBUG_MODE=false
   BROWSER_TYPE=chromium
   HEADLESS=false
   BROWSER_TIMEOUT=30000
   WAIT_UNTIL=networkidle
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   GEMINI_TEMPERATURE=0.2
   GEMINI_MAX_TOKENS=8192
   ```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

## 📁 Project Structure

```
webbased-testing-agent/
├── app.py              # Main Streamlit application
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not tracked)
├── .gitignore         # Git ignore rules
├── README.md          # Project documentation
├── agents/            # Agent implementations
│   └── __init__.py
│   └── exploration_agent.py  # Phase 1: Exploration & Knowledge Acquisition
├── components/        # UI components
│   └── __init__.py
└── utils/             # Utility functions
    ├── __init__.py
    ├── browser_controller.py  # Browser automation controller
    └── gemini_client.py       # LLM client for AI integration
```

## 🛠️ Development

### Branch Naming Convention

Follow these guidelines when creating new branches:

**Format:**
```
<type>/<short-description>
```

**Types:**
- `feature/` - New features or enhancements
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests
- `chore/` - Maintenance tasks

**Examples:**
- `feature/add-user-authentication`
- `fix/fix-login-error`
- `docs/update-api-documentation`
- `refactor/optimize-database-queries`
- `test/add-unit-tests`

**Rules:**
- Use lowercase letters
- Use hyphens to separate words
- Keep descriptions concise and descriptive
- Avoid special characters

### Commit Guidelines

**Format:**
```
<type>: <subject>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Rules:**
- Use imperative mood ("add" not "added" or "adds")
- Keep subject short and descriptive (50 characters or less)
- Don't capitalize first letter
- No period at the end

**Examples:**
```
feat: add user login functionality
fix: resolve timeout issue in data fetching
docs: update API documentation
refactor: optimize database queries
test: add unit tests for authentication
chore: update dependencies
```
