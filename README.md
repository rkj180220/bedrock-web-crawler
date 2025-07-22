# Web Crawler Agent - AWS Bedrock & Lambda

A comprehensive web-crawler agent built with AWS Bedrock, Lambda, CDK, and React that can scrape websites and answer questions about their content.

## 🏗️ Architecture

- **Frontend**: React application with modern UI
- **Backend**: Flask API server for Bedrock Agent communication
- **Scraper**: AWS Lambda function with web scraping capabilities
- **Agent**: AWS Bedrock Agent with registered scraping tool
- **Infrastructure**: AWS CDK for deployment

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with your credentials
- Node.js (v16 or higher)
- Python 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### 1. Environment Setup

Create a `.env` file in the root directory:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token
CDK_DEFAULT_ACCOUNT=your_account_id

# These will be populated after deployment
BEDROCK_AGENT_ID=
BEDROCK_AGENT_ALIAS_ID=
LAMBDA_FUNCTION_ARN=
BEDROCK_AGENT_ROLE_ARN=
```

### 2. Deploy Infrastructure

```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### 3. Update Environment Variables

After deployment, update your `.env` file with the output values from the Bedrock Agent setup.

### 4. Start the Application

Terminal 1 - Backend API:
```bash
python backend_server.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm start
```

## 📱 Usage

1. Open your browser to `http://localhost:3000`
2. Type messages like:
   - "Crawl https://example.com and summarize the content"
   - "What is the main topic of https://news.website.com?"
   - "Extract all links from https://github.com/user/repo"

## 🔧 Configuration

### Lambda Function Environment Variables

- `MAX_CONTENT_SIZE`: Maximum HTML content size (default: 1MB)
- `REQUEST_TIMEOUT`: HTTP request timeout (default: 30 seconds)

### Security

- API Gateway is configured for your use only
- Lambda function has minimal required permissions
- CORS is configured for local development

## 🛠️ Development

### Project Structure

```
├── app.py                 # CDK app entry point
├── lambda_function.py     # Web scraper Lambda function
├── backend_server.py      # Flask API server
├── setup_bedrock_agent.py # Bedrock Agent configuration
├── infrastructure/        # CDK infrastructure code
├── frontend/             # React application
└── deploy.sh            # Deployment script
```

### Manual Deployment Steps

If you prefer manual deployment:

1. Deploy CDK stack:
   ```bash
   pip install -r requirements.txt
   cdk bootstrap
   cdk deploy
   ```

2. Setup Bedrock Agent:
   ```bash
   # Set environment variables from CDK outputs
   python setup_bedrock_agent.py
   ```

3. Start services:
   ```bash
   # Backend
   python backend_server.py
   
   # Frontend
   cd frontend && npm install && npm start
   ```

## 🔍 Features

- **Smart Web Scraping**: Handles gzip compression, redirects, and size limits
- **Clean Text Extraction**: Removes scripts, styles, and navigation elements
- **Real-time Chat Interface**: Modern React UI with loading states
- **Error Handling**: Comprehensive error handling and user feedback
- **Configurable Limits**: Adjustable content size and timeout limits
- **AWS Integration**: Full AWS Bedrock Agent integration

## 🚨 Troubleshooting

### Common Issues

1. **"Bedrock Agent not configured"**
   - Ensure BEDROCK_AGENT_ID is set in .env
   - Run the setup_bedrock_agent.py script

2. **"Lambda function timeout"**
   - Increase timeout in web_crawler_stack.py
   - Redeploy with `cdk deploy`

3. **"CORS errors"**
   - Check backend_server.py is running on port 3001
   - Verify proxy setting in frontend/package.json

### Logs

- **Lambda logs**: Check CloudWatch Logs
- **Backend logs**: Console output from backend_server.py
- **Frontend logs**: Browser developer console

## 📄 License

This project is for educational and development purposes.
