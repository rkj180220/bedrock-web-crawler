#!/bin/bash

# Web Crawler Agent Deployment Script
set -e

echo "🚀 Starting Web Crawler Agent Deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create one with your AWS credentials."
    exit 1
fi

# Load environment variables (filtering out comments and empty lines)
set -a
source <(grep -v '^#' .env | grep -v '^$' | grep '=')
set +a

echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

echo "🔧 Checking CDK installation..."
if ! command -v cdk &> /dev/null; then
    echo "📥 CDK CLI not found. Installing AWS CDK CLI..."
    npm install -g aws-cdk
    echo "✅ CDK CLI installed successfully"
else
    echo "✅ CDK CLI already installed"
fi

echo "🔍 Verifying CDK version..."
cdk --version

echo "🏗️  Deploying CDK Stack..."
cdk bootstrap
cdk deploy --require-approval never

echo "📋 Getting CDK outputs..."
LAMBDA_ARN=$(aws cloudformation describe-stacks --stack-name web-crawler-agent --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' --output text)
BEDROCK_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name web-crawler-agent --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentRoleArn`].OutputValue' --output text)
API_URL=$(aws cloudformation describe-stacks --stack-name web-crawler-agent --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' --output text)

echo "🤖 Setting up Bedrock Agent..."
export LAMBDA_FUNCTION_ARN=$LAMBDA_ARN
export BEDROCK_AGENT_ROLE_ARN=$BEDROCK_ROLE_ARN

python setup_bedrock_agent.py

echo "📱 Installing frontend dependencies..."
cd frontend
npm install

echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "  - Lambda Function ARN: $LAMBDA_ARN"
echo "  - API Gateway URL: $API_URL"
echo "  - Bedrock Agent Role: $BEDROCK_ROLE_ARN"
echo ""
echo "🎯 Next Steps:"
echo "  1. Update your .env file with the Bedrock Agent ID and Alias ID"
echo "  2. Run 'npm start' in the frontend directory to start the React app"
echo "  3. Run 'python backend_server.py' to start the backend API server"
echo ""
echo "🔗 Your web crawler agent is ready to use!"
