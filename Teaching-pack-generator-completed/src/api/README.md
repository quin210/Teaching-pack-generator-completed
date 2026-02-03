# API Module

FastAPI REST API for the Teaching Pack Generator system.

## Structure

```
src/api/
  __init__.py
  main.py
```

## Running the Server

From the project root:

```bash
# Option 1: Using run_server.py (recommended)
python run_server.py

# Option 2: Using uvicorn directly
cd src && uvicorn api.main:app --reload --port 8000
```

## API Documentation

Once the server is running, access:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Core Endpoints

- GET / - API information
- GET /health - Health check
- GET /docs - Interactive API documentation

### Lesson Processing

- POST /api/lesson/parse - Parse lesson file
- POST /api/skills/map - Map skills from lesson
- POST /api/diagnostic/build - Build diagnostic test

### Teaching Pack Generation

- POST /api/packs/generate - Generate complete teaching packs (full workflow)
- GET /api/jobs/{job_id} - Check job status

### Output Management

- GET /api/outputs - List output files
- GET /api/outputs/{filename} - Download output file

## Development

The API uses:

- FastAPI
- Pydantic
- Background tasks
- CORS

## Adding New Endpoints

1. Define the endpoint in main.py
2. Add request and response models if needed
3. Update this README with endpoint details
4. Test with /docs or test_api.py
