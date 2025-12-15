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

5. **Configure environment variables** (optional)
   
   Create a `.env` file in the root directory:
   ```bash
   DEBUG_MODE=false
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
├── components/        # UI components
│   └── __init__.py
└── utils/             # Utility functions
    └── __init__.py
```

## 🔧 Configuration

Configuration is managed through environment variables in the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_MODE` | `false` | Enable debug logging |

Additional configuration variables will be added as the implementation progresses.

## 🛠️ Development

### Branch Naming Convention

Follow these guidelines when creating new branches:

**Format:**
```
<type>/<short-description>
```

**Types:**
- `feature/` - New features or enhancements
- `bugfix/` - Bug fixes
- `hotfix/` - Urgent fixes for production
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests
- `chore/` - Maintenance tasks

**Examples:**
- `feature/add-user-authentication`
- `bugfix/fix-login-error`
- `hotfix/security-patch`
- `docs/update-api-documentation`
- `refactor/optimize-database-queries`
- `test/add-unit-tests`

**Rules:**
- Use lowercase letters
- Use hyphens to separate words
- Keep descriptions concise and descriptive
- Avoid special characters

### Commit Description Convention

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
