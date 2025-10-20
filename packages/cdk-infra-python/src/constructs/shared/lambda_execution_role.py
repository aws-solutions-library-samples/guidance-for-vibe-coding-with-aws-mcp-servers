"""
Shared Lambda Execution Role Construct

This construct creates a custom Lambda execution role that replaces the AWS managed
AWSLambdaBasicExecutionRole to satisfy CDK Nag security requirements.
"""

from aws_cdk import Stack, aws_iam as iam
from cdk_nag import NagSuppressions
from constructs import Construct


class LambdaExecutionRoleConstruct(Construct):
    """
    Shared construct for creating a custom Lambda execution role.

    This role provides the same permissions as AWSLambdaBasicExecutionRole
    but as a custom managed policy to satisfy CDK Nag requirements.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create custom policy with same permissions as AWSLambdaBasicExecutionRole
        self.lambda_execution_policy = iam.ManagedPolicy(
            self,
            "CustomLambdaExecutionPolicy",
            managed_policy_name="CustomLambdaBasicExecutionRole",
            description="Custom Lambda execution policy replacing AWS managed AWSLambdaBasicExecutionRole",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                    resources=[f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:*"],
                )
            ],
        )

        # Create the Lambda execution role
        self.lambda_execution_role = iam.Role(
            self,
            "CustomLambdaExecutionRole",
            role_name="CustomLambdaExecutionRole",
            description="Custom Lambda execution role for CDK Nag compliance",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[self.lambda_execution_policy],
        )

        # Suppress CloudWatch Logs wildcard permission - required for Lambda log group creation
        NagSuppressions.add_resource_suppressions(
            self.lambda_execution_policy.node.default_child,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Lambda functions require wildcard permissions for CloudWatch Logs to dynamically create log groups and streams at runtime. This is a standard pattern for Lambda execution roles and is necessary for proper logging functionality.",
                    "appliesTo": ["Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:*"],
                }
            ],
        )

    @property
    def role(self) -> iam.Role:
        """Return the custom Lambda execution role."""
        return self.lambda_execution_role
