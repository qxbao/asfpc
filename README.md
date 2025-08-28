# ASFPC
**A**utomated **S**ystem for **F**inding **P**otential **C**ustomers

This project aims to create an automated system that can efficiently identify and target potential customers for a business. By leveraging data analysis and machine learning techniques, the system will analyze customer behavior, preferences, and demographics to generate leads and improve marketing strategies.

## Contents
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup)
- [Docker](#docker)

## Requirements
- Python 3.8 or higher
- PostgreSQL Server
- N8N Server

## Installation
1. Clone the repository:
```bash
  git clone https://github.com/qxbao/asfpc.git
  cd asfpc
```
2. Create virtual environment & activate:
```bash
  python -m venv .venv
  .venv/Scripts/activate  # Powershell
  "./.venv/Scripts/activate" # Command Prompt
```
3. Install requirement dependencies:
```bash
  pip install -r requirements.txt
```

## Setup
This section will guide you through the setup process for the project.

### Environment Variables
Create a `.env` file in the root directory and add the following environment variables:
```bash
PG_HOST=localhost
PG_PORT=5432
PG_USER=your_username
PG_PASSWORD=your_password
PG_DATABASE=your_database_name
N8N_URL=n8n_url
```

### Database
  1. Install PostgreSQL Server.
  2. Create a new database for the project.
  3. Update the database connection settings in the `.env` file.

### N8N
If you want to connect to an external N8N server, go directly to step 3:

  1. Install N8N.
  2. Create a new workflow for the project.
  3. Update the N8N URL in the `.env` file.

## Docker
This project includes a Docker Compose file for easy setup and deployment. To get started with Docker:

1. Make sure you have Docker and Docker Compose installed.
2. Run the following command to start the services:
```bash
docker-compose up -d
```
3. Access the application at `http://localhost:8000` and the database at port `5433`.