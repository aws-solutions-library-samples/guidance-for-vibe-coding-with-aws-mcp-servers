# Guidance for Vibe Coding AI Agents with AWS MCP Servers

## Table of Contents

1. [Overview](#overview)
   - [Architecture](#architecture)
   - [Cost](#cost)
2. [Deployment Options](#deployment-options)
3. [Repository Structure](#repository-structure)
4. [Prerequisites](#prerequisites)
   - [Operating System](#operating-system)
   - [Third-party Tools](#third-party-tools)
   - [AWS Account Requirements](#aws-account-requirements)
   - [Supported Regions](#supported-regions)
5. [Deployment Steps](#deployment-steps)
6. [Deployment Validation](#deployment-validation)
7. [Running the Guidance](#running-the-guidance)
8. [Next Steps](#next-steps)
9. [Cleanup](#cleanup)
10. [FAQ and Known Issues](#faq-and-known-issues)
11. [Notices](#notices)
12. [Authors](#authors)

## Overview

This Guidance demonstrates how to build AI-powered development workflows using Amazon Bedrock AgentCore and the Model Context Protocol (MCP). It provides a complete, deployable hotel booking agent system that showcases "vibe coding" techniques - an AI-assisted development approach that accelerates software development through intelligent code generation, discovery, and problem-solving.

The Guidance is designed as an interactive workshop where participants learn to:

- Use AI tools to understand and navigate complex codebases quickly
- Generate, enhance, and debug code efficiently with AI assistance
- Leverage AI for architecture analysis, optimization, and testing
- Rapidly prototype and iterate on ideas using AI-powered development tools

Participants deploy a realistic hotel booking agent using Amazon Bedrock AgentCore and gain hands-on experience with AI development tools including Kiro, Amazon Q, and AWS MCP Servers. The skills learned can be immediately applied to production projects and shared across development teams.

### Architecture

The solution implements a multi-tier architecture combining Amazon Bedrock AgentCore with serverless AWS services:

![Architecture Diagram - Overview](assets/images/guidance-vibe-coding-aws-mcp-1.png)

![Architecture Diagram - Detailed Components](assets/images/guidance-vibe-coding-aws-mcp-2.png)

**Architecture Flow:**

- **User Interaction** - Users interact with the AgentCore agent through natural language conversations
- **Agent Orchestration** - Amazon Bedrock AgentCore processes requests and determines required actions
- **MCP Server Bridge** - Model Context Protocol server translates agent actions into API calls
- **Backend Services** - Three specialized APIs handle hotel search, reservations, and content moderation
- **Data Storage** - Amazon DynamoDB stores hotel and reservation data

**Key Components:**

- **Amazon Bedrock AgentCore** - Intelligent conversational agent with natural language understanding
- **MCP Server** (AWS Lambda) - Protocol bridge connecting agent to backend APIs
- **Property Resolution API** (AWS Lambda + API Gateway) - Hotel search powered by Amazon Location Service
- **Reservations API** (AWS Lambda + API Gateway) - Booking management and CRUD operations
- **Toxicity Detection API** (AWS Lambda + API Gateway) - Content moderation using Amazon Comprehend
- **Amazon DynamoDB** - NoSQL database for hotels and reservations

### Cost

You are responsible for the cost of the AWS services used while running this Guidance. As of October 2025, the cost for running this Guidance with the default settings in the US West (Oregon) Region is estimated at approximately $XX.XX per month for processing XXXXX requests.

**Note:** Cost estimation is pending completion. This section will be updated with detailed pricing breakdown from AWS Pricing Calculator.

We recommend creating a [Budget](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) through [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) to help manage costs. Prices are subject to change. For full details, refer to the pricing webpage for each AWS service used in this Guidance.

### Sample Cost Table

The following table provides a sample cost breakdown for deploying this Guidance with the default parameters in the US West (Oregon) Region for 3 hours of usage.

| AWS Service              | Purpose                            | Cost [USD] | Note               |
| ------------------------ | ---------------------------------- | ---------- | ------------------ |
| Amazon Bedrock           | Agent model invocation             | $0.18      |                    |
| Amazon Bedrock AgentCore | Hotel booking agent and MCP Server | $0.65      | 0.5 vCPU, 1 GB     |
| Amazon Comprehend        | Toxicity detection API             | $0.03      | Optional challenge |
| AWS DynamoDB             | Mock APIs                          | $0.003     |                    |
| AWS Lambda               | Mock APIs                          | $0.0001    |                    |
| Amazon ECR               | AgentCore image                    | $0.004     |                    |
| Amazon CloudWatch        | Monitoring and logs                | $0.50      |                    |
| Amazon Location Service  | Property resolution API            | $0.01      |                    |
| **Total**                |                                    | **$1.38**  |                    |

## Deployment Options

This Guidance can be deployed in two ways:

### Option 1: AWS Workshop Studio (Recommended for Workshop Participants)

If you're participating in an AWS-hosted workshop event, use Workshop Studio for a pre-configured environment with all prerequisites and infrastructure already set up:

**Access Workshop Studio:** Visit [https://studio.us-east-1.prod.workshops.aws/workshops/public/33b9f640-2cab-47f0-bfdd-d3aab3c38eee](https://studio.us-east-1.prod.workshops.aws/workshops/public/33b9f640-2cab-47f0-bfdd-d3aab3c38eee)

The Workshop Studio environment includes:

- Pre-installed development tools and prerequisites
- Pre-deployed AWS infrastructure (APIs, Agent, MCP Server)
- Ready-to-use development environment

Simply follow the on-screen instructions in Workshop Studio to access your temporary AWS account and begin the workshop activities.

### Option 2: Self-Deployment in Your Own AWS Account

If you want to deploy this Guidance in your own AWS account, continue with the sections below:

- [Prerequisites](#prerequisites) - Install required tools
- [Deployment Steps](#deployment-steps) - Deploy the infrastructure
- [Deployment Validation](#deployment-validation) - Verify your deployment

## Repository Structure

This repository contains a complete Amazon Bedrock AgentCore hotel booking system with workshop materials:

```text
├── packages/                   # Core application packages
│   ├── agentcore-agents/       # Amazon Bedrock AgentCore agents
│   │   └── hotel-booking-agent/    # Intelligent hotel booking assistant
│   ├── agentcore-mcp-servers/  # Model Context Protocol servers
│   │   └── hotel-booking/      # Hotel booking MCP server
│   ├── agentcore-tools/        # AgentCore deployment utilities
│   │   ├── deploy.sh          # Agent/MCP server deployment script
│   │   └── destroy.sh         # Cleanup and removal script
│   └── cdk-infra-python/      # AWS CDK infrastructure
│       ├── src/stacks/        # CDK stack definitions
│       └── app.py             # CDK application entry point
├── docs/                      # Workshop documentation
│   ├── astro-docs/            # Participant documentation site
```

### System Components

- **AgentCore Agent** - Intelligent conversational agent that understands natural language and orchestrates hotel booking operations
- **MCP Server** - Protocol server that bridges the agent with hotel booking APIs (Property Resolution, Reservations, Toxicity Detection)
- **Mock APIs** - Three production-like services for hotel search, booking management, and content moderation
- **CDK Infrastructure** - Complete AWS deployment including Lambda functions, API Gateway, DynamoDB, and IAM resources

## Prerequisites

### Operating System

These deployment instructions are optimized to work on **macOS, Linux, and Windows** operating systems. Deployment on other operating systems may require additional steps.

### Third-party Tools

The following tools must be installed before deploying this Guidance:

- **Node.js** (v20.18.1 or later) - JavaScript runtime

  ```bash
  node --version
  ```

- **Python** (v3.12 or later) - Required for AWS CDK infrastructure

  ```bash
  python --version
  ```

- **pnpm** - Fast, disk space efficient package manager

  ```bash
  npm install -g pnpm
  pnpm --version
  ```

- **uv** - Fast Python package installer and resolver

  ```bash
  # Install uv (macOS/Linux)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv --version
  ```

- **Docker Desktop or Rancher Desktop** - Container runtime for local development

  ```bash
  docker --version
  ```

- **Graphviz** - Graph visualization software (required for CDK diagrams)

  - Visit [graphviz.org/download](https://graphviz.org/download/) for installation instructions

- **AWS CLI** (v2) - Command line interface for AWS services

  ```bash
  aws --version
  aws configure list
  ```

- **AWS CDK CLI** - Infrastructure as Code toolkit

  ```bash
  pnpm add -g aws-cdk
  cdk --version
  ```

- **Bruno CLI** - API testing tool for validating deployments
  ```bash
  npm install -g @usebruno/cli
  bru --version
  ```

### AWS Account Requirements

This Guidance requires an AWS account with the following:

- **AWS CDK Bootstrap** - If using AWS CDK for the first time in your account/region, you must bootstrap your environment:

  ```bash
  cdk bootstrap aws://ACCOUNT-NUMBER/REGION
  ```

- **IAM Permissions** - Your AWS credentials must have permissions to create and manage:
  - AWS Lambda functions
  - Amazon API Gateway REST APIs
  - Amazon DynamoDB tables
  - Amazon Cognito user pools
  - IAM roles and policies
  - Amazon Bedrock AgentCore agents
  - Amazon Location Service resources
  - Amazon Comprehend API access

### Supported Regions

This Guidance has been tested and validated in the following AWS Regions:

- **us-west-2** (US West - Oregon)
- **us-east-1** (US East - N. Virginia)

While the solution may work in other regions, these two regions are officially supported and recommended for deployment.

## Deployment Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/aws-samples/agentcore-tech-summit-2025.git
cd agentcore-tech-summit-2025
```

### Step 2: Install Dependencies and Start Workshop Documentation

Install project dependencies and start the workshop documentation locally:

```bash
# Install all dependencies
pnpm install

# Build and serve documentation locally (opens on localhost)
pnpm docs:init
```

The documentation will be available at `http://localhost:4321`. **Open this URL and follow the detailed setup instructions** in the participant guide for prerequisites installation and environment configuration.

**Important:** After starting the documentation server, navigate to:

1. **"Setup your own development environment"** - Follow the complete deployment instructions
2. **"Setup up your IDE Extensions"** - Configure your AI development tools

These sections provide comprehensive guidance for deploying the infrastructure and configuring your development environment. Once complete, you'll be ready to begin the workshop activities.

## Deployment Validation

Verify your deployment was successful:

1. **Check CloudFormation Stacks**

   ```bash
   # List all deployed stacks
   aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
   ```

   You should see these stacks:

   - `AgentCoreTechSummitMockApis`
   - `AgentCoreTechSummitBookingAgent`
   - `AgentCoreTechSummitMcpServer`

2. **Verify API Endpoints**

   ```bash
   # Get stack outputs (API URLs and keys)
   aws cloudformation describe-stacks \
     --stack-name AgentCoreTechSummitMockApis \
     --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
     --output table
   ```

3. **Test APIs with Bruno CLI**

   ```bash
   # Run API tests
   pnpm test:apis:reservations
   pnpm test:apis:toxicity
   ```

   All tests should pass, confirming the APIs are functioning correctly.

4. **Verify AgentCore Deployments**

   Check the AWS Console to confirm the Agent and MCP Server are listed in Amazon Bedrock AgentCore.

## Running the Guidance

Once deployed, follow the workshop documentation for detailed activities:

1. **Access Workshop Documentation**

   If you closed the documentation server, restart it with:

   ```bash
   pnpm docs:init
   ```

   Then open `http://localhost:4321` in your browser.

2. **Configure Your AI Development Tool**

   Follow the workshop documentation to configure your preferred AI tool (Kiro, Amazon Q Developer, VS Code + Cline, etc.) to connect to the deployed MCP server.

3. **Workshop Phases**

   The workshop is organized into three phases:

   - **Phase 1:** Understanding the codebase and architecture
   - **Phase 2:** Enhancing the agent with new capabilities
   - **Phase 3:** Testing, debugging, and optimization

4. **Interact with the Agent**

   Use your configured AI tool to interact with the hotel booking agent through natural language conversations. The agent can:

   - Search for hotels by location
   - Create and manage reservations
   - Moderate user-generated content
   - Maintain conversation context

## Next Steps

After completing the workshop, consider these enhancements:

- **Add New APIs** - Integrate additional services (payment processing, loyalty programs, reviews)
- **Enhance Agent Capabilities** - Add multi-language support, price comparison, or recommendation features
- **Implement Production Features** - Add monitoring, logging, error handling, and rate limiting
- **Explore Other MCP Servers** - Integrate AWS MCP Servers for documentation access and best practices
- **Scale the Solution** - Implement caching, optimize Lambda functions, add CDN for static assets
- **Security Hardening** - Implement WAF rules, enhance IAM policies, add encryption at rest

## Cleanup

To avoid ongoing charges, delete all deployed resources:

1. **Destroy AgentCore Deployments**

   ```bash
   # Remove Agent and MCP Server from AgentCore
   ./packages/agentcore-tools/destroy.sh hotel_booking_agent
   ./packages/agentcore-tools/destroy.sh hotel_booking_mcp
   ```

2. **Delete CDK Stacks**

   ```bash
   # Delete all stacks in reverse order
   pnpm cdk destroy AgentCoreTechSummitMcpServer
   pnpm cdk destroy AgentCoreTechSummitBookingAgent
   pnpm cdk destroy AgentCoreTechSummitMockApis
   ```

3. **Manual Cleanup (if needed)**

   Some resources may require manual deletion:

   - **S3 Buckets** - Empty and delete any S3 buckets created by the stacks
   - **CloudWatch Logs** - Delete log groups if you want to remove all traces
   - **DynamoDB Tables** - Verify tables are deleted (should be automatic with stack deletion)

   Check for remaining resources:

   ```bash
   # List S3 buckets
   aws s3 ls | grep -i "agentcore\|workshop"

   # List CloudWatch log groups
   aws logs describe-log-groups --query 'logGroups[?contains(logGroupName, `agentcore`) || contains(logGroupName, `workshop`)].logGroupName'
   ```

## FAQ and Known Issues

**Q: Which AWS regions are supported?**

A: This Guidance has been tested in us-west-2 (Oregon) and us-east-1 (N. Virginia). Other regions may work but are not officially supported.

**Q: What are the estimated costs?**

A: Cost estimates are pending. See the [Cost](#cost) section for details. Most workshop activities can be completed within AWS Free Tier limits.

**Q: Can I use this in production?**

A: This Guidance is designed as a workshop and learning tool. Not intended for production use.

**Known Issues:**

1. **Python Interpreter Permission Errors**

   - **Problem:** `Permission denied` error when running CDK commands
   - **Solution:** Recreate the uv virtual environment:
     ```bash
     cd packages/cdk-infra-python
     rm -rf .venv
     uv sync
     cd ../..
     ```

2. **Stack Does Not Exist Error**

   - **Problem:** Getting "Stack does not exist" when running CloudFormation commands
   - **Solution:** Verify you're using the correct AWS profile:
     ```bash
     aws configure list
     export AWS_PROFILE=YOUR_PROFILE_NAME
     ```

3. **MCP Server Connection Issues**

   - **Problem:** `spawn uvx ENOENT` error when MCP servers try to start
   - **Solution:** Use the full path to uvx in your MCP configuration. Find it with `which uvx` and update your MCP settings file.

4. **API Tests Timeout**

   - **Problem:** Bruno API tests timeout on first run
   - **Solution:** Wait a few seconds for Lambda cold start and retry the tests.

5. **CDK Bootstrap Stack**
   - **Note:** Keep the CDK bootstrap stack if you plan to use CDK for other projects. Only delete if you're certain you won't use CDK in this AWS account/region again.

## Notices

_Customers are responsible for making their own independent assessment of the information in this Guidance. This Guidance: (a) is for informational purposes only, (b) represents AWS current product offerings and practices, which are subject to change without notice, and (c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided "as is" without warranties, representations, or conditions of any kind, whether express or implied. AWS responsibilities and liabilities to its customers are controlled by AWS agreements, and this Guidance is not part of, nor does it modify, any agreement between AWS and its customers._

## Authors

- AWS Prototyping and Cloud Engineering Team
