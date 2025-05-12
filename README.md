# AWS Lambda Handling MCP Client and Server vis Bedrock  

This project demonstrates how to create an MCP client and server hosted in an AWS lambda accessed via API Gateway 
that interacts with AWS Bedrock as the model.

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [Node.js](https://nodejs.org/) (for AWS CDK)
- [AWS CDK](https://aws.amazon.com/cdk/) installed (`npm install -g aws-cdk`)
- [Python 3.11](https://www.python.org/downloads/)

## Project Structure

```
hello-lambda/
├── README.md
├── cdk/
│   ├── cdk.json           # CDK configuration
│   └── mcp_stack.py       # CDK stack deployment script
├── lambda/
│   ├── mcp_handler.py      # Lambda handler entry point
│   ├── mcp_client.py       # MCP client that interacts with MCP server & Bedrock
│   ├── mcp_server.py       # MCP server contains all the exposed tools
│   ├── test_mcp_handler.py # Local test script for the handler
│   └── requirements.txt    # Lambda dependencies
└── tests/                  # Tests directory
```

## Setup

1. Create and activate a virtual environment:

```bash
pyenv install 3.12
pyenv virtualenv 3.12 venv
pyenv activate venv
```

2. Install dependencies:

There are separate requirements.txt for the lambda and CDK to support a separate bundling process.
To test locally you should install the requirements.txt file in the lambda directory.

```bash
pip install -r cdk/requirements.txt
pip install -r lambda/requirements.txt
```

## Local Testing

Before deploying to AWS you can test the Lambda function locally. this test should test the weather tool:

```bash
cd lambda
python test_mcp_handler.py"
```

## Deployment

1. Bootstrap your AWS environment (if not already done):

```bash
cd cdk
cdk bootstrap
```

2. Deploy the MCP stack which includes an API Gateway and Lambda function:

```bash
cdk deploy
```

3. Note the configuration output parameters:

```
BedrockMcpStack.ApiUrl = https://<APP_ID>.execute-api.us-west-2.amazonaws.com/prod/
BedrockMcpStack.FunctionName = BedrockMcpStack-BedrockMcpFunction<FUNCTION_ID>
```

## Testing the Lambda

After deployment, you can test your Lambda function via the API gateway using curl:

```bash
curl -G "https://<BedrockMcpStack.ApiUrl>" --data-urlencode "query=What's the temperature in New York City"
```


Note that the API gateway has a strict 1-minute timeout so for queries that take longer
try running the following command directly against the AWS Lambda function:

```bash
aws lambda invoke  --function-name <BedrockMcpStack.FunctionName>  --payload '{"queryStringParameters": {"query": "Summaries key points from the website - https://en.wikipedia.org/wiki/Black_hole"}}'  --cli-binary-format raw-in-base64-out output.json
cat output.json
```

## Cleanup

To avoid incurring charges, delete the resources when you're done:

```bash
cdk destroy
```