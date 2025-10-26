# Country Currency & Exchange API

A RESTful API that fetches country data from external APIs, stores it in a database, and provides CRUD operations.

## Features

- Fetch and cache country data from external APIs
- CRUD operations for country records
- Filter countries by region and currency
- Sort countries by GDP
- Generate and serve summary images
- MySQL database for persistence
- Environment variables support
- CORS support

## Requirements

- Python 3.12+
- MySQL 8.0+
- System dependencies:
  - python3-dev
  - default-libmysqlclient-dev
  - build-essential
  - pkg-config

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv env
   source env/bin/activate  # Linux/macOS
   # or
   env\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create MySQL database:
   ```bash
   mysql -u root -e "CREATE DATABASE IF NOT EXISTS hng3_countries;"
   ```

5. Configure environment variables in `.env`:
   ```
   DB_NAME=hng3_countries
   DB_USER=root
   DB_PASSWORD=
   DB_HOST=localhost
   DB_PORT=3306
   ```

6. Apply database migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

- `POST /countries/refresh` - Fetch all countries and exchange rates
- `GET /countries` - Get all countries (supports filters and sorting)
  - Query parameters:
    - `region=Africa` - Filter by region
    - `currency=NGN` - Filter by currency code
    - `sort=gdp_desc` - Sort by GDP (descending)
- `GET /countries/{name}` - Get one country by name
- `DELETE /countries/{name}` - Delete a country record
- `GET /status` - Show total countries and last refresh timestamp
- `GET /countries/image` - Serve summary image

## Sample Responses

### GET /countries?region=Africa
```json
[
  {
    "id": 1,
    "name": "Nigeria",
    "capital": "Abuja",
    "region": "Africa",
    "population": 206139589,
    "currency_code": "NGN",
    "exchange_rate": 1600.23,
    "estimated_gdp": 25767448125.2,
    "flag_url": "https://flagcdn.com/ng.svg",
    "last_refreshed_at": "2025-10-22T18:00:00Z"
  }
]
```

### GET /status
```json
{
  "total_countries": 250,
  "last_refreshed_at": "2025-10-22T18:00:00Z"
}
```

## Error Handling

The API returns consistent JSON error responses:
- 404 - `{"error": "Country not found"}`
- 400 - `{"error": "Validation failed"}`
- 500 - `{"error": "Internal server error"}`
- 503 - `{"error": "External data source unavailable"}`

## Development

1. Install development dependencies:
   ```bash
   pip install black isort pylint
   ```

2. Format code:
   ```bash
   black .
   isort .
   ```

3. Run tests:
   ```bash
   python manage.py test
   ```

## Deployment

This project can be deployed on any platform that supports Python/Django applications. Some popular options:
- Railway
- Heroku
- AWS
- PXXL App

For deployment instructions specific to your chosen platform, please refer to their documentation.

## License

This project is licensed under the MIT License - see the LICENSE file for details.# HNG_TASK4
