# OpenChemIE - Refactored

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.68%2B-green.svg)
![Vue.js](https://img.shields.io/badge/Vue.js-3.x-brightgreen.svg)

**OpenChemIE** is an advanced chemical information extraction tool that leverages state-of-the-art AI models to extract chemical entities, reactions, and relationships from scientific literature PDFs.

## 🚀 Features

- **Multi-Modal Extraction**: Extract chemical structures, reactions, and text from PDF documents
- **AI-Powered Recognition**: Utilize specialized models for molecular detection, reaction parsing, and NER
- **Modern Architecture**: Clean separation between API, web interface, and core extraction logic
- **Docker Support**: Easy deployment with containerization
- **RESTful API**: Well-documented FastAPI backend
- **Interactive Web Interface**: Modern Vue.js frontend for easy interaction

## 🏗️ Architecture

```
OpenChemIE-refactored/
├── app/
│   ├── api/          # FastAPI backend
│   ├── web/          # Vue.js frontend  
│   └── core/         # Core extraction logic
├── models/           # AI model files (not included in repo)
├── infra/            # Docker configurations
├── docs/             # Documentation and examples
├── scripts/          # Utility scripts
└── tests/            # Test suites
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Node.js 14+ (for frontend development)
- Docker & Docker Compose (for containerized deployment)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Lutra23/OpenChemIE-refactored.git
   cd OpenChemIE-refactored
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Download model files** (Required)
   ```bash
   # Download model files to models/ directory
   # Model files are available separately due to size constraints
   # Contact repository maintainer for model access
   ```

4. **Install frontend dependencies**
   ```bash
   cd app/web
   npm install
   ```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f infra/docker-compose.yml up --build
```

## 🚀 Usage

### API Server

```bash
# Start the FastAPI server
cd app/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API documentation will be available at `http://localhost:8000/docs`

### Web Interface

```bash
# Start the Vue.js development server
cd app/web
npm run dev
```

Web interface will be available at `http://localhost:3000`

### Core Extraction (Python API)

```python
from app.core.extractor import OpenChemIEExtractor

# Initialize extractor
extractor = OpenChemIEExtractor()

# Extract from PDF
results = extractor.extract_from_pdf('path/to/paper.pdf')
print(results)
```

## 📚 API Documentation

### Main Endpoints

- `POST /extract/pdf` - Extract information from uploaded PDF
- `POST /extract/text` - Extract from text input
- `GET /health` - Health check endpoint
- `GET /models/status` - Check model loading status

For detailed API documentation, visit `/docs` endpoint when running the server.

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

If you encounter any issues or have questions:

1. Check the [documentation](docs/)
2. Search existing [issues](https://github.com/Lutra23/OpenChemIE-refactored/issues)
3. Create a new issue with detailed information

## 🔬 Research & Citation

If you use OpenChemIE in your research, please cite:

```bibtex
@software{openchemie2024,
  title={OpenChemIE: AI-Powered Chemical Information Extraction},
  author={Your Name},
  year={2024},
  url={https://github.com/Lutra23/OpenChemIE-refactored}
}
```

---

**Built with ❤️ for the chemistry research community**