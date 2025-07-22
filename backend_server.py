from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
import json
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client(
    'bedrock-agent-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Configuration from environment variables
AGENT_ID = os.getenv('BEDROCK_AGENT_ID')
AGENT_ALIAS_ID = os.getenv('BEDROCK_AGENT_ALIAS_ID', 'TSTALIASID')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests from the frontend."""
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400

        user_message = data['message']
        session_id = data.get('sessionId', f'session-{os.urandom(8).hex()}')

        logger.info(f"Received message: {user_message}")
        logger.info(f"Session ID: {session_id}")

        if not AGENT_ID:
            return jsonify({
                'error': 'Bedrock Agent not configured. Please set BEDROCK_AGENT_ID environment variable.'
            }), 500

        # Invoke Bedrock Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=user_message
        )

        # Process the response stream
        agent_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    agent_response += chunk['bytes'].decode('utf-8')

        logger.info(f"Agent response: {agent_response}")

        return jsonify({
            'response': agent_response,
            'sessionId': session_id,
            'metadata': {
                'agentId': AGENT_ID,
                'aliasId': AGENT_ALIAS_ID
            }
        })

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': f'Failed to process request: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'agent_configured': bool(AGENT_ID),
        'region': os.getenv('AWS_REGION', 'us-east-1')
    })

@app.route('/api/config', methods=['GET'])
def config():
    """Get configuration information."""
    return jsonify({
        'agent_id': AGENT_ID,
        'agent_alias_id': AGENT_ALIAS_ID,
        'region': os.getenv('AWS_REGION', 'us-east-1'),
        'configured': bool(AGENT_ID)
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3001))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Agent ID: {AGENT_ID}")
    logger.info(f"Agent Alias ID: {AGENT_ALIAS_ID}")

    # Bind to localhost only for security - not accessible from other devices
    app.run(host='127.0.0.1', port=port, debug=debug)
