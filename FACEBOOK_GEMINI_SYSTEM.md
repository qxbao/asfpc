# Facebook Profile Scraping and Gemini Analysis System

This document describes the newly implemented Facebook Profile Scraping and Gemini Analysis System that efficiently scrapes Facebook user profiles and analyzes their financial status using Google Gemini AI while minimizing API token usage.

## 🎯 System Overview

The system provides comprehensive functionality for:
- **Profile Data Collection**: Scrape Facebook profiles using browser automation
- **Financial Analysis**: Analyze profiles using Google Gemini AI for financial status assessment
- **N8N Integration**: API endpoints designed for N8N workflow automation
- **Optimization**: Caching, batching, and rate limiting for efficient operation

## 📊 Database Schema

### New Tables

#### `user_profile`
Stores scraped Facebook profile data:
- `facebook_id` (unique): Facebook user identifier
- `name`: Display name
- `bio`: Profile bio/about section
- `location`: User location
- `work`: Work/employment information
- `education`: Education details
- `profile_url`: Facebook profile URL
- `posts_sample`: Sample of recent posts
- `last_scraped`: Timestamp of last scraping
- `scraped_by_account_id`: Reference to scraping account

#### `financial_analysis`
Stores Gemini AI analysis results:
- `financial_status`: "low", "medium", or "high"
- `confidence_score`: 0.0 to 1.0 confidence level
- `analysis_summary`: Text summary of analysis
- `indicators`: JSON object with specific indicators found
- `gemini_model_used`: Model version used
- `token_usage`: Prompt, completion, and total tokens used
- `user_profile_id`: Reference to analyzed profile

## 🚀 API Endpoints

### Profile Scraping

#### `POST /analysis/scrape-profile`
Scrape a single Facebook profile.

**Request:**
```json
{
  "profile_url": "https://facebook.com/username",
  "account_id": 1,
  "force_refresh": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Profile scraped successfully",
  "profile": {
    "id": 1,
    "facebook_id": "username",
    "name": "John Doe",
    "bio": "Software Engineer at TechCorp",
    // ... other profile fields
  }
}
```

#### `POST /analysis/scrape-profiles/bulk`
Scrape multiple profiles with rate limiting (background processing).

**Request:**
```json
{
  "profile_urls": [
    "https://facebook.com/user1",
    "https://facebook.com/user2"
  ],
  "account_id": 1,
  "delay_seconds": 5
}
```

### Financial Analysis

#### `POST /analysis/analyze-profile`
Analyze a single profile for financial status.

**Request:**
```json
{
  "profile_id": 1,
  "force_reanalysis": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Profile analyzed successfully",
  "analysis": {
    "id": 1,
    "financial_status": "medium",
    "confidence_score": 0.85,
    "analysis_summary": "Middle-class lifestyle with stable employment...",
    "indicators": {
      "job_indicators": ["Software Engineer", "TechCorp"],
      "lifestyle_indicators": ["Travel posts", "Restaurant visits"],
      "education_indicators": ["University degree"],
      "location_indicators": ["Urban area"]
    }
  }
}
```

#### `POST /analysis/analyze-profiles/batch`
Batch analyze multiple profiles (optimized for token usage).

**Request:**
```json
{
  "profile_ids": [1, 2, 3, 4, 5],
  "force_reanalysis": false
}
```

**Response:**
```json
{
  "success": true,
  "results": [/* analysis results */],
  "errors": [],
  "total_tokens_used": 2500,
  "profiles_processed": 5,
  "profiles_failed": 0
}
```

### Data Retrieval

#### `GET /analysis/profiles`
Get recent profiles with optional filtering.

Query Parameters:
- `limit`: Number of profiles (default: 50, max: 200)
- `account_id`: Filter by scraping account (optional)

#### `GET /analysis/profiles/{profile_id}`
Get detailed information about a specific profile.

#### `GET /analysis/profiles/{profile_id}/analyses`
Get all financial analyses for a specific profile.

#### `GET /analysis/analyses/recent`
Get recent financial analyses across all profiles.

#### `GET /analysis/analyses/stats`
Get analysis statistics including distribution by financial status.

#### `GET /analysis/profiles/needing-analysis`
Get profiles that haven't been analyzed or need re-analysis.

## ⚙️ Configuration

### Environment Variables

```bash
# Database Configuration
PG_HOST=localhost
PG_PORT=5432
PG_USER=your_username
PG_PASSWORD=your_password
PG_DATABASE=your_database_name

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key

# N8N Integration
N8N_URL=your_n8n_url
```

### Database Setup

1. Run Alembic migration:
```bash
alembic upgrade head
```

2. Add Facebook accounts for scraping:
```bash
POST /account/add
{
  "username": "your_fb_username",
  "email": "your_fb_email@example.com",
  "password": "your_fb_password"
}
```

3. Login accounts to get session cookies:
```bash
POST /account/login/{account_id}
```

## 🔧 Optimization Features

### Caching
- Profiles are cached to avoid re-scraping within 24 hours (configurable)
- Use `force_refresh=true` to override caching

### Batching
- Gemini API calls are batched to reduce token costs
- Batch size configurable (default: 5 profiles per API call)
- Automatic retry logic for failed analyses

### Rate Limiting
- Configurable delays between profile scrapes (default: 5 seconds)
- Background processing for bulk operations to avoid timeouts

### Token Optimization
- Batch processing reduces API calls by up to 80%
- Detailed token usage tracking per analysis
- Confidence-based re-analysis scheduling

## 🔍 Financial Analysis

### Status Categories
- **Low**: Students, unemployed, entry-level jobs, financial struggles
- **Medium**: Standard employment, middle-class lifestyle, moderate spending
- **High**: Executive positions, luxury indicators, high-end education/locations

### Analysis Indicators
The system looks for:
- **Job Indicators**: Titles, companies, industry
- **Lifestyle Indicators**: Travel, dining, purchases, activities
- **Education Indicators**: Schools, degrees, certifications
- **Location Indicators**: Expensive areas, neighborhoods

### Confidence Scoring
- 0.0-0.3: Low confidence (limited data)
- 0.4-0.7: Medium confidence (some indicators)
- 0.8-1.0: High confidence (strong indicators)

## 🚦 Usage Workflow

### Typical N8N Workflow

1. **Profile Discovery**: Input Facebook profile URLs
2. **Account Selection**: Choose available Facebook account for scraping
3. **Scraping**: Call `/analysis/scrape-profile` or bulk endpoint
4. **Analysis**: Call `/analysis/analyze-profile` or batch endpoint
5. **Results**: Retrieve analysis via `/analysis/profiles/{id}/analyses`
6. **Statistics**: Monitor performance via `/analysis/analyses/stats`

### Example N8N Nodes

```
1. HTTP Request → POST /analysis/scrape-profile
2. Wait 30 seconds (allow scraping to complete)
3. HTTP Request → POST /analysis/analyze-profile
4. Process Results → Filter by confidence_score > 0.7
5. Store Results → Save to external system
```

## 🛡️ Error Handling

The system includes comprehensive error handling:
- Invalid profile URLs
- Blocked Facebook accounts
- Rate limiting responses
- Gemini API failures
- Database connection issues
- Network timeouts

All endpoints return structured error responses with appropriate HTTP status codes.

## 📈 Monitoring

### Available Metrics
- Profiles scraped per account
- Analysis success/failure rates
- Token usage statistics
- Financial status distribution
- Average confidence scores

### Health Check
Use `GET /health` to verify system status.

## 🔒 Security Considerations

- Facebook credentials stored encrypted in database
- API keys managed through environment variables
- Rate limiting prevents abuse
- Session management for Facebook authentication
- Input validation on all endpoints

## 📝 Next Steps

To extend the system:
1. Add more social media platforms (Instagram, LinkedIn)
2. Implement webhook notifications for completed analyses
3. Add machine learning models for improved accuracy
4. Create dashboard for monitoring and management
5. Add support for different analysis types (interests, demographics)

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Errors**: Check connection settings and run migrations
3. **Scraping Failures**: Verify Facebook account status and cookies
4. **Analysis Failures**: Check Gemini API key and quota

### Debug Mode
Start the application with `--debug` flag for detailed logging:
```bash
python app.py --debug
```