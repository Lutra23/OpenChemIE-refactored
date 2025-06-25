# OpenChemIE Refactored

This is the refactored version of the OpenChemIE project, designed with a modular monorepo structure.

## Overview

OpenChemIE is a tool for extracting chemical information from scientific documents. This refactored version provides a modern architecture with a FastAPI backend and a Vue.js frontend.

## Project Structure

- `app/api/`: The backend FastAPI application.
- `app/web/`: The frontend Vue.js application.
- `app/core/`: The core chemical extraction logic (as a Python package).
- `models/`: Directory for storing AI model files.
- `infra/`: Docker and docker-compose configurations.

## Getting Started

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Lutra23/OpenChemIE-refactored.git
    cd OpenChemIE-refactored
    ```

2.  **Download Models:**
    Download the required models and place them in the `models/` directory. (Further instructions on specific models to be added).

3.  **Run with Docker:**
    ```bash
    docker-compose up --build
    ```

4.  Access the services:
    -   API: `http://localhost:8000`
    -   Web App: `http://localhost:5173` 