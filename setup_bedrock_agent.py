import boto3
import json
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

class BedrockAgentSetup:
    def __init__(self):
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        self.lambda_client = boto3.client('lambda', region_name=os.getenv('AWS_REGION', 'us-east-1'))

    def wait_for_agent_ready(self, agent_id: str, max_wait_time: int = 300):
        """Wait for the agent to be in a ready state."""
        print(f"Waiting for agent {agent_id} to be ready...")
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                response = self.bedrock_agent.get_agent(agentId=agent_id)
                agent_status = response['agent']['agentStatus']
                print(f"Agent status: {agent_status}")

                if agent_status in ['NOT_PREPARED', 'PREPARED', 'FAILED']:
                    if agent_status == 'FAILED':
                        raise Exception(f"Agent creation failed: {response.get('failureReasons', [])}")
                    print(f"✅ Agent is ready with status: {agent_status}")
                    return True
                elif agent_status in ['CREATING', 'UPDATING', 'PREPARING']:
                    print(f"Agent still {agent_status.lower()}... waiting 10 seconds")
                    time.sleep(10)
                else:
                    print(f"Unknown agent status: {agent_status}")
                    time.sleep(10)

            except Exception as e:
                print(f"Error checking agent status: {e}")
                time.sleep(10)

        raise Exception(f"Agent did not become ready within {max_wait_time} seconds")

    def create_or_update_agent(self, lambda_function_arn: str, agent_role_arn: str):
        """Create or update the Bedrock Agent with web scraping capabilities."""

        agent_name = "web-crawler-agent"

        # Check if agent already exists
        try:
            existing_agents = self.bedrock_agent.list_agents()
            existing_agent = None
            print(f"Found {len(existing_agents.get('agentSummaries', []))} existing agents")

            for agent in existing_agents.get('agentSummaries', []):
                print(f"Checking agent: {agent.get('agentName')} (ID: {agent.get('agentId')})")
                if agent['agentName'] == agent_name:
                    existing_agent = agent
                    print(f"✅ Found existing agent: {agent['agentId']}")
                    break

            # Also check if we have a specific agent ID we know about
            if not existing_agent:
                # Try to get the agent directly if we know it exists
                try:
                    test_response = self.bedrock_agent.get_agent(agentId="CCZNEDALHD")
                    if test_response['agent']['agentName'] == agent_name:
                        existing_agent = {
                            'agentId': 'CCZNEDALHD',
                            'agentName': agent_name
                        }
                        print(f"✅ Found existing agent by direct lookup: CCZNEDALHD")
                except Exception as e:
                    print(f"Direct agent lookup failed: {e}")

        except Exception as e:
            print(f"Error checking existing agents: {e}")
            existing_agents = {'agentSummaries': []}
            existing_agent = None

        agent_instruction = """
        You are a web scraping assistant. Your primary function is to help users scrape and analyze web content.
        
        When a user asks you to scrape a website or provides a URL, use the web_scrape tool to fetch the content.
        
        You can:
        1. Scrape web pages and extract clean text content
        2. Handle various web formats and encodings
        3. Provide summaries of scraped content
        4. Answer questions about the scraped content
        
        Always be helpful and provide clear responses about the scraped content.
        """

        if existing_agent:
            # Update existing agent
            agent_id = existing_agent['agentId']
            print(f"Updating existing agent: {agent_id}")

            try:
                response = self.bedrock_agent.update_agent(
                    agentId=agent_id,
                    agentName=agent_name,
                    instruction=agent_instruction,
                    agentResourceRoleArn=agent_role_arn,
                    foundationModel="anthropic.claude-3-sonnet-20240229-v1:0"
                )

                # Wait for update to complete
                self.wait_for_agent_ready(agent_id)
            except Exception as e:
                print(f"Error updating agent: {e}")
                print("Proceeding with existing agent...")
        else:
            # Create new agent
            print("Creating new Bedrock Agent...")

            response = self.bedrock_agent.create_agent(
                agentName=agent_name,
                instruction=agent_instruction,
                agentResourceRoleArn=agent_role_arn,
                foundationModel="anthropic.claude-3-sonnet-20240229-v1:0"
            )
            agent_id = response['agent']['agentId']

            # Wait for creation to complete
            self.wait_for_agent_ready(agent_id)

        print(f"Agent ID: {agent_id}")

        # Create or update action group (now that agent is ready)
        self.create_or_update_action_group(agent_id, lambda_function_arn)

        # Prepare the agent
        print("Preparing agent...")
        self.bedrock_agent.prepare_agent(agentId=agent_id)

        # Wait for preparation to complete
        self.wait_for_agent_ready(agent_id)

        # Create or update agent alias
        alias_id = self.create_or_update_alias(agent_id)

        return agent_id, alias_id

    def create_or_update_action_group(self, agent_id: str, lambda_function_arn: str):
        """Create or update the action group for web scraping."""

        action_group_name = "web-scrape-action-group"

        # Define the API schema for the web scraping tool
        api_schema = {
            "openapi": "3.0.0",
            "info": {
                "title": "Web Scraping API",
                "version": "1.0.0",
                "description": "API for web scraping functionality"
            },
            "paths": {
                "/scrape": {
                    "post": {
                        "summary": "Scrape a website",
                        "description": "Scrape content from a given URL and return clean text",
                        "operationId": "scrape_website",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "url": {
                                                "type": "string",
                                                "description": "The URL to scrape"
                                            }
                                        },
                                        "required": ["url"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {
                                                    "type": "boolean"
                                                },
                                                "content": {
                                                    "type": "string"
                                                },
                                                "title": {
                                                    "type": "string"
                                                },
                                                "url": {
                                                    "type": "string"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        # Check if action group exists - now properly including agentVersion
        try:
            existing_action_groups = self.bedrock_agent.list_agent_action_groups(
                agentId=agent_id,
                agentVersion="DRAFT"
            )
            existing_action_group = None
            for ag in existing_action_groups.get('actionGroupSummaries', []):
                if ag['actionGroupName'] == action_group_name:
                    existing_action_group = ag
                    break
        except Exception as e:
            print(f"Error checking existing action groups: {e}")
            existing_action_group = None

        if existing_action_group:
            # Update existing action group
            print(f"Updating existing action group: {existing_action_group['actionGroupId']}")

            self.bedrock_agent.update_agent_action_group(
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupId=existing_action_group['actionGroupId'],
                actionGroupName=action_group_name,
                description="Action group for web scraping functionality",
                actionGroupExecutor={
                    'lambda': lambda_function_arn
                },
                apiSchema={
                    'payload': json.dumps(api_schema)
                }
            )
        else:
            # Create new action group
            print("Creating action group...")

            self.bedrock_agent.create_agent_action_group(
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupName=action_group_name,
                description="Action group for web scraping functionality",
                actionGroupExecutor={
                    'lambda': lambda_function_arn
                },
                apiSchema={
                    'payload': json.dumps(api_schema)
                }
            )

    def create_or_update_alias(self, agent_id: str) -> str:
        """Create or update agent alias."""

        alias_name = "web-crawler-live"

        # Check if alias exists
        try:
            existing_aliases = self.bedrock_agent.list_agent_aliases(agentId=agent_id)
            existing_alias = None
            for alias in existing_aliases.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == alias_name:
                    existing_alias = alias
                    break
        except Exception as e:
            print(f"Error checking existing aliases: {e}")
            existing_alias = None

        if existing_alias:
            # Update existing alias
            print(f"Updating existing alias: {existing_alias['agentAliasId']}")

            response = self.bedrock_agent.update_agent_alias(
                agentId=agent_id,
                agentAliasId=existing_alias['agentAliasId'],
                agentAliasName=alias_name,
                description="Live alias for web crawler agent"
            )
            alias_id = existing_alias['agentAliasId']
        else:
            # Create new alias
            print("Creating agent alias...")

            response = self.bedrock_agent.create_agent_alias(
                agentId=agent_id,
                agentAliasName=alias_name,
                description="Live alias for web crawler agent"
            )
            alias_id = response['agentAlias']['agentAliasId']

        return alias_id

def main():
    """Main function to set up the Bedrock Agent."""

    # Get Lambda function ARN and Bedrock role ARN from CDK outputs
    # These would typically be passed as parameters or environment variables
    lambda_function_arn = os.getenv('LAMBDA_FUNCTION_ARN')
    agent_role_arn = os.getenv('BEDROCK_AGENT_ROLE_ARN')

    if not lambda_function_arn or not agent_role_arn:
        print("Error: Missing required environment variables:")
        print("- LAMBDA_FUNCTION_ARN")
        print("- BEDROCK_AGENT_ROLE_ARN")
        print("\nPlease deploy the CDK stack first and set these environment variables.")
        return

    setup = BedrockAgentSetup()
    agent_id, alias_id = setup.create_or_update_agent(lambda_function_arn, agent_role_arn)

    print(f"\n✅ Bedrock Agent setup complete!")
    print(f"Agent ID: {agent_id}")
    print(f"Alias ID: {alias_id}")
    print(f"\nYou can now use this agent in your React frontend.")

if __name__ == "__main__":
    main()
