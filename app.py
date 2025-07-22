#!/usr/bin/env python3
import os
from aws_cdk import App, Environment
from dotenv import load_dotenv
from infrastructure.web_crawler_stack import WebCrawlerStack

# Load environment variables
load_dotenv()

app = App()

# Get AWS configuration from environment
account = app.node.try_get_context("account") or os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("AWS_REGION", "us-east-1")

WebCrawlerStack(
    app,
    "WebCrawlerAgentStack",
    env=Environment(account=account, region=region),
    stack_name="web-crawler-agent"
)

app.synth()
