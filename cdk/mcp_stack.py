#!/usr/bin/env python3
from platform import system

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigw,
)
from constructs import Construct
import os


class BedrockMcpStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a Lambda Layer with dependencies
        layer = self.create_dependencies_layer(
            "DependenciesLayer",
            "../lambda/requirements.txt",
            _lambda.Runtime.PYTHON_3_11
        )

        # Define the Lambda function with increased memory and timeout
        mcp_lambda = _lambda.Function(
            self, "BedrockMcpFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../lambda"),
            handler="mcp_handler.handler",
            memory_size=1024,
            # Increased memory for MCP processing
            timeout=cdk.Duration.seconds(120),
            # Increased timeout for API calls
            layers=[layer],
            # Add the dependencies layer
        )

        # Output the API URL
        cdk.CfnOutput(
            self, "FunctionName",
            value=mcp_lambda.function_name,
            description="Lambda function name"
        )

        # Add Bedrock permissions
        mcp_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Converse"
                ],
                resources=["*"]
                # You may want to restrict this in production
            )
        )

        # Create an API Gateway to expose the Lambda
        api = apigw.LambdaRestApi(
            self, "BedrockMcpApi",
            handler=mcp_lambda,
            proxy=True,
            deploy_options=apigw.StageOptions(
                stage_name="prod"
            )
        )

        # Output the API URL
        cdk.CfnOutput(
            self, "ApiUrl",
            value=api.url,
            description="URL for the API Gateway"
        )

    def create_dependencies_layer(self, layer_id, requirements_path, runtime):
        """Create a Lambda Layer with dependencies."""
        # Create a temporary directory for the layer
        layer_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lambda_layer")
        python_dir = os.path.join(layer_dir, "python")
        os.makedirs(python_dir, exist_ok=True)

        # Install dependencies with platform-specific flags for Lambda compatibility
        os.system(
            f"pip install --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: --target {python_dir} -r {requirements_path}")

        # Create the layer
        return _lambda.LayerVersion(
            self, layer_id,
            code=_lambda.Code.from_asset(layer_dir),
            compatible_runtimes=[runtime],
            description=f'Dependencies for MCP Lambda'
        )


app = cdk.App()
BedrockMcpStack(app, "BedrockMcpStack")
app.synth()
