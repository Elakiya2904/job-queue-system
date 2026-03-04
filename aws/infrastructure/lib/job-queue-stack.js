"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.JobQueueStack = void 0;
const cdk = __importStar(require("aws-cdk-lib"));
const lambda = __importStar(require("aws-cdk-lib/aws-lambda"));
const sqs = __importStar(require("aws-cdk-lib/aws-sqs"));
const rds = __importStar(require("aws-cdk-lib/aws-rds"));
const ec2 = __importStar(require("aws-cdk-lib/aws-ec2"));
const iam = __importStar(require("aws-cdk-lib/aws-iam"));
const apigateway = __importStar(require("aws-cdk-lib/aws-apigateway"));
const logs = __importStar(require("aws-cdk-lib/aws-logs"));
const events = __importStar(require("aws-cdk-lib/aws-lambda-event-sources"));
class JobQueueStack extends cdk.Stack {
    constructor(scope, id, props) {
        super(scope, id, props);
        const environment = process.env.ENVIRONMENT || 'staging';
        // VPC for RDS and Lambda
        const vpc = new ec2.Vpc(this, 'JobQueueVPC', {
            maxAzs: 2,
            cidr: '10.0.0.0/16',
            subnetConfiguration: [
                {
                    cidrMask: 24,
                    name: 'Public',
                    subnetType: ec2.SubnetType.PUBLIC,
                },
                {
                    cidrMask: 24,
                    name: 'Private',
                    subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
                },
                {
                    cidrMask: 24,
                    name: 'Database',
                    subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
                },
            ],
        });
        // Security Groups
        const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
            vpc,
            description: 'Security group for Lambda functions',
            allowAllOutbound: true,
        });
        const rdsSecurityGroup = new ec2.SecurityGroup(this, 'RdsSecurityGroup', {
            vpc,
            description: 'Security group for RDS instance',
            allowAllOutbound: false,
        });
        // Allow Lambda to connect to RDS
        rdsSecurityGroup.addIngressRule(ec2.Peer.securityGroupId(lambdaSecurityGroup.securityGroupId), ec2.Port.tcp(5432), 'Allow Lambda access to PostgreSQL');
        // Dead Letter Queue
        const deadLetterQueue = new sqs.Queue(this, 'JobQueueDeadLetterQueue', {
            queueName: `job-queue-dlq-${environment}`,
            retentionPeriod: cdk.Duration.days(14),
        });
        // Main Task Queue
        const taskQueue = new sqs.Queue(this, 'JobQueueTaskQueue', {
            queueName: `job-queue-tasks-${environment}`,
            visibilityTimeout: cdk.Duration.minutes(15), // 15 minutes for long-running tasks
            deadLetterQueue: {
                queue: deadLetterQueue,
                maxReceiveCount: 3,
            },
            receiveMessageWaitTime: cdk.Duration.seconds(20), // Long polling
        });
        // RDS Aurora Serverless v2 PostgreSQL
        const dbCluster = new rds.DatabaseCluster(this, 'JobQueueDatabase', {
            engine: rds.DatabaseClusterEngine.auroraPostgres({
                version: rds.AuroraPostgresEngineVersion.VER_15_4,
            }),
            credentials: rds.Credentials.fromGeneratedSecret('jobqueue_admin', {
                secretName: `job-queue-db-credentials-${environment}`,
            }),
            serverlessV2MinCapacity: 0.5,
            serverlessV2MaxCapacity: 4,
            writer: rds.ClusterInstance.serverlessV2('writer'),
            vpc,
            vpcSubnets: {
                subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
            },
            securityGroups: [rdsSecurityGroup],
            defaultDatabaseName: 'jobqueue',
            deletionProtection: environment === 'production',
            backup: {
                retention: environment === 'production'
                    ? cdk.Duration.days(7)
                    : cdk.Duration.days(1),
            },
        });
        // Lambda Execution Role
        const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
            assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
            ],
        });
        // Allow Lambda to access SQS
        taskQueue.grantConsumeMessages(lambdaRole);
        deadLetterQueue.grantConsumeMessages(lambdaRole);
        // Allow Lambda to access RDS
        dbCluster.secret?.grantRead(lambdaRole);
        // API Lambda Function
        const apiLambda = new lambda.Function(this, 'JobQueueApiLambda', {
            functionName: `job-queue-api-${environment}`,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'lambda_handler.lambda_handler',
            code: lambda.Code.fromAsset('../backend'), // Will be replaced in CI/CD
            vpc,
            vpcSubnets: {
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
            },
            securityGroups: [lambdaSecurityGroup],
            role: lambdaRole,
            timeout: cdk.Duration.seconds(30),
            memorySize: 512,
            environment: {
                DATABASE_URL: `postgresql://jobqueue_admin:password@${dbCluster.clusterEndpoint.hostname}:5432/jobqueue`,
                SQS_QUEUE_URL: taskQueue.queueUrl,
                SQS_DLQ_URL: deadLetterQueue.queueUrl,
                AWS_REGION: this.region,
                ENVIRONMENT: environment,
            },
            logRetention: logs.RetentionDays.ONE_WEEK,
        });
        // Worker Lambda Function
        const workerLambda = new lambda.Function(this, 'JobQueueWorkerLambda', {
            functionName: `job-queue-worker-${environment}`,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'lambda_handler.lambda_handler',
            code: lambda.Code.fromAsset('../worker'), // Will be replaced in CI/CD
            vpc,
            vpcSubnets: {
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
            },
            securityGroups: [lambdaSecurityGroup],
            role: lambdaRole,
            timeout: cdk.Duration.minutes(15), // Long timeout for task processing
            memorySize: 1024,
            environment: {
                DATABASE_URL: `postgresql://jobqueue_admin:password@${dbCluster.clusterEndpoint.hostname}:5432/jobqueue`,
                AWS_REGION: this.region,
                ENVIRONMENT: environment,
            },
            logRetention: logs.RetentionDays.ONE_WEEK,
        });
        // SQS Event Source for Worker Lambda
        workerLambda.addEventSource(new events.SqsEventSource(taskQueue, {
            batchSize: 5, // Process up to 5 messages at once
            maxBatchingWindow: cdk.Duration.seconds(10),
            reportBatchItemFailures: true,
        }));
        // API Gateway
        const api = new apigateway.LambdaRestApi(this, 'JobQueueApi', {
            handler: apiLambda,
            restApiName: `job-queue-api-${environment}`,
            description: `Job Queue System API - ${environment}`,
            deployOptions: {
                stageName: environment,
                loggingLevel: apigateway.MethodLoggingLevel.INFO,
                dataTraceEnabled: true,
            },
            defaultCorsPreflightOptions: {
                allowOrigins: apigateway.Cors.ALL_ORIGINS,
                allowMethods: apigateway.Cors.ALL_METHODS,
                allowHeaders: [
                    'Content-Type',
                    'X-Amz-Date',
                    'Authorization',
                    'X-Api-Key',
                    'X-Amz-Security-Token',
                ],
            },
        });
        // Outputs
        new cdk.CfnOutput(this, 'ApiGatewayUrl', {
            value: api.url,
            description: 'API Gateway URL',
        });
        new cdk.CfnOutput(this, 'TaskQueueUrl', {
            value: taskQueue.queueUrl,
            description: 'SQS Task Queue URL',
        });
        new cdk.CfnOutput(this, 'DeadLetterQueueUrl', {
            value: deadLetterQueue.queueUrl,
            description: 'SQS Dead Letter Queue URL',
        });
        new cdk.CfnOutput(this, 'DatabaseEndpoint', {
            value: dbCluster.clusterEndpoint.hostname,
            description: 'RDS Cluster Endpoint',
        });
        new cdk.CfnOutput(this, 'DatabaseSecretArn', {
            value: dbCluster.secret?.secretArn || 'Not available',
            description: 'Database credentials secret ARN',
        });
    }
}
exports.JobQueueStack = JobQueueStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiam9iLXF1ZXVlLXN0YWNrLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiam9iLXF1ZXVlLXN0YWNrLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7OztBQUFBLGlEQUFtQztBQUNuQywrREFBaUQ7QUFDakQseURBQTJDO0FBQzNDLHlEQUEyQztBQUMzQyx5REFBMkM7QUFDM0MseURBQTJDO0FBQzNDLHVFQUF5RDtBQUN6RCwyREFBNkM7QUFDN0MsNkVBQStEO0FBRy9ELE1BQWEsYUFBYyxTQUFRLEdBQUcsQ0FBQyxLQUFLO0lBQzFDLFlBQVksS0FBZ0IsRUFBRSxFQUFVLEVBQUUsS0FBc0I7UUFDOUQsS0FBSyxDQUFDLEtBQUssRUFBRSxFQUFFLEVBQUUsS0FBSyxDQUFDLENBQUM7UUFFeEIsTUFBTSxXQUFXLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxXQUFXLElBQUksU0FBUyxDQUFDO1FBRXpELHlCQUF5QjtRQUN6QixNQUFNLEdBQUcsR0FBRyxJQUFJLEdBQUcsQ0FBQyxHQUFHLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRTtZQUMzQyxNQUFNLEVBQUUsQ0FBQztZQUNULElBQUksRUFBRSxhQUFhO1lBQ25CLG1CQUFtQixFQUFFO2dCQUNuQjtvQkFDRSxRQUFRLEVBQUUsRUFBRTtvQkFDWixJQUFJLEVBQUUsUUFBUTtvQkFDZCxVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxNQUFNO2lCQUNsQztnQkFDRDtvQkFDRSxRQUFRLEVBQUUsRUFBRTtvQkFDWixJQUFJLEVBQUUsU0FBUztvQkFDZixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxtQkFBbUI7aUJBQy9DO2dCQUNEO29CQUNFLFFBQVEsRUFBRSxFQUFFO29CQUNaLElBQUksRUFBRSxVQUFVO29CQUNoQixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxnQkFBZ0I7aUJBQzVDO2FBQ0Y7U0FDRixDQUFDLENBQUM7UUFFSCxrQkFBa0I7UUFDbEIsTUFBTSxtQkFBbUIsR0FBRyxJQUFJLEdBQUcsQ0FBQyxhQUFhLENBQUMsSUFBSSxFQUFFLHFCQUFxQixFQUFFO1lBQzdFLEdBQUc7WUFDSCxXQUFXLEVBQUUscUNBQXFDO1lBQ2xELGdCQUFnQixFQUFFLElBQUk7U0FDdkIsQ0FBQyxDQUFDO1FBRUgsTUFBTSxnQkFBZ0IsR0FBRyxJQUFJLEdBQUcsQ0FBQyxhQUFhLENBQUMsSUFBSSxFQUFFLGtCQUFrQixFQUFFO1lBQ3ZFLEdBQUc7WUFDSCxXQUFXLEVBQUUsaUNBQWlDO1lBQzlDLGdCQUFnQixFQUFFLEtBQUs7U0FDeEIsQ0FBQyxDQUFDO1FBRUgsaUNBQWlDO1FBQ2pDLGdCQUFnQixDQUFDLGNBQWMsQ0FDN0IsR0FBRyxDQUFDLElBQUksQ0FBQyxlQUFlLENBQUMsbUJBQW1CLENBQUMsZUFBZSxDQUFDLEVBQzdELEdBQUcsQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxFQUNsQixtQ0FBbUMsQ0FDcEMsQ0FBQztRQUVGLG9CQUFvQjtRQUNwQixNQUFNLGVBQWUsR0FBRyxJQUFJLEdBQUcsQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLHlCQUF5QixFQUFFO1lBQ3JFLFNBQVMsRUFBRSxpQkFBaUIsV0FBVyxFQUFFO1lBQ3pDLGVBQWUsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUM7U0FDdkMsQ0FBQyxDQUFDO1FBRUgsa0JBQWtCO1FBQ2xCLE1BQU0sU0FBUyxHQUFHLElBQUksR0FBRyxDQUFDLEtBQUssQ0FBQyxJQUFJLEVBQUUsbUJBQW1CLEVBQUU7WUFDekQsU0FBUyxFQUFFLG1CQUFtQixXQUFXLEVBQUU7WUFDM0MsaUJBQWlCLEVBQUUsR0FBRyxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLEVBQUUsb0NBQW9DO1lBQ2pGLGVBQWUsRUFBRTtnQkFDZixLQUFLLEVBQUUsZUFBZTtnQkFDdEIsZUFBZSxFQUFFLENBQUM7YUFDbkI7WUFDRCxzQkFBc0IsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUMsRUFBRSxlQUFlO1NBQ2xFLENBQUMsQ0FBQztRQUVILHNDQUFzQztRQUN0QyxNQUFNLFNBQVMsR0FBRyxJQUFJLEdBQUcsQ0FBQyxlQUFlLENBQUMsSUFBSSxFQUFFLGtCQUFrQixFQUFFO1lBQ2xFLE1BQU0sRUFBRSxHQUFHLENBQUMscUJBQXFCLENBQUMsY0FBYyxDQUFDO2dCQUMvQyxPQUFPLEVBQUUsR0FBRyxDQUFDLDJCQUEyQixDQUFDLFFBQVE7YUFDbEQsQ0FBQztZQUNGLFdBQVcsRUFBRSxHQUFHLENBQUMsV0FBVyxDQUFDLG1CQUFtQixDQUFDLGdCQUFnQixFQUFFO2dCQUNqRSxVQUFVLEVBQUUsNEJBQTRCLFdBQVcsRUFBRTthQUN0RCxDQUFDO1lBQ0YsdUJBQXVCLEVBQUUsR0FBRztZQUM1Qix1QkFBdUIsRUFBRSxDQUFDO1lBQzFCLE1BQU0sRUFBRSxHQUFHLENBQUMsZUFBZSxDQUFDLFlBQVksQ0FBQyxRQUFRLENBQUM7WUFDbEQsR0FBRztZQUNILFVBQVUsRUFBRTtnQkFDVixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxnQkFBZ0I7YUFDNUM7WUFDRCxjQUFjLEVBQUUsQ0FBQyxnQkFBZ0IsQ0FBQztZQUNsQyxtQkFBbUIsRUFBRSxVQUFVO1lBQy9CLGtCQUFrQixFQUFFLFdBQVcsS0FBSyxZQUFZO1lBQ2hELE1BQU0sRUFBRTtnQkFDTixTQUFTLEVBQUUsV0FBVyxLQUFLLFlBQVk7b0JBQ3JDLENBQUMsQ0FBQyxHQUFHLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7b0JBQ3RCLENBQUMsQ0FBQyxHQUFHLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7YUFDekI7U0FDRixDQUFDLENBQUM7UUFFSCx3QkFBd0I7UUFDeEIsTUFBTSxVQUFVLEdBQUcsSUFBSSxHQUFHLENBQUMsSUFBSSxDQUFDLElBQUksRUFBRSxxQkFBcUIsRUFBRTtZQUMzRCxTQUFTLEVBQUUsSUFBSSxHQUFHLENBQUMsZ0JBQWdCLENBQUMsc0JBQXNCLENBQUM7WUFDM0QsZUFBZSxFQUFFO2dCQUNmLEdBQUcsQ0FBQyxhQUFhLENBQUMsd0JBQXdCLENBQUMsMENBQTBDLENBQUM7Z0JBQ3RGLEdBQUcsQ0FBQyxhQUFhLENBQUMsd0JBQXdCLENBQUMsOENBQThDLENBQUM7YUFDM0Y7U0FDRixDQUFDLENBQUM7UUFFSCw2QkFBNkI7UUFDN0IsU0FBUyxDQUFDLG9CQUFvQixDQUFDLFVBQVUsQ0FBQyxDQUFDO1FBQzNDLGVBQWUsQ0FBQyxvQkFBb0IsQ0FBQyxVQUFVLENBQUMsQ0FBQztRQUVqRCw2QkFBNkI7UUFDN0IsU0FBUyxDQUFDLE1BQU0sRUFBRSxTQUFTLENBQUMsVUFBVSxDQUFDLENBQUM7UUFFeEMsc0JBQXNCO1FBQ3RCLE1BQU0sU0FBUyxHQUFHLElBQUksTUFBTSxDQUFDLFFBQVEsQ0FBQyxJQUFJLEVBQUUsbUJBQW1CLEVBQUU7WUFDL0QsWUFBWSxFQUFFLGlCQUFpQixXQUFXLEVBQUU7WUFDNUMsT0FBTyxFQUFFLE1BQU0sQ0FBQyxPQUFPLENBQUMsV0FBVztZQUNuQyxPQUFPLEVBQUUsK0JBQStCO1lBQ3hDLElBQUksRUFBRSxNQUFNLENBQUMsSUFBSSxDQUFDLFNBQVMsQ0FBQyxZQUFZLENBQUMsRUFBRSw0QkFBNEI7WUFDdkUsR0FBRztZQUNILFVBQVUsRUFBRTtnQkFDVixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxtQkFBbUI7YUFDL0M7WUFDRCxjQUFjLEVBQUUsQ0FBQyxtQkFBbUIsQ0FBQztZQUNyQyxJQUFJLEVBQUUsVUFBVTtZQUNoQixPQUFPLEVBQUUsR0FBRyxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDO1lBQ2pDLFVBQVUsRUFBRSxHQUFHO1lBQ2YsV0FBVyxFQUFFO2dCQUNYLFlBQVksRUFBRSx3Q0FBd0MsU0FBUyxDQUFDLGVBQWUsQ0FBQyxRQUFRLGdCQUFnQjtnQkFDeEcsYUFBYSxFQUFFLFNBQVMsQ0FBQyxRQUFRO2dCQUNqQyxXQUFXLEVBQUUsZUFBZSxDQUFDLFFBQVE7Z0JBQ3JDLFVBQVUsRUFBRSxJQUFJLENBQUMsTUFBTTtnQkFDdkIsV0FBVyxFQUFFLFdBQVc7YUFDekI7WUFDRCxZQUFZLEVBQUUsSUFBSSxDQUFDLGFBQWEsQ0FBQyxRQUFRO1NBQzFDLENBQUMsQ0FBQztRQUVILHlCQUF5QjtRQUN6QixNQUFNLFlBQVksR0FBRyxJQUFJLE1BQU0sQ0FBQyxRQUFRLENBQUMsSUFBSSxFQUFFLHNCQUFzQixFQUFFO1lBQ3JFLFlBQVksRUFBRSxvQkFBb0IsV0FBVyxFQUFFO1lBQy9DLE9BQU8sRUFBRSxNQUFNLENBQUMsT0FBTyxDQUFDLFdBQVc7WUFDbkMsT0FBTyxFQUFFLCtCQUErQjtZQUN4QyxJQUFJLEVBQUUsTUFBTSxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsV0FBVyxDQUFDLEVBQUUsNEJBQTRCO1lBQ3RFLEdBQUc7WUFDSCxVQUFVLEVBQUU7Z0JBQ1YsVUFBVSxFQUFFLEdBQUcsQ0FBQyxVQUFVLENBQUMsbUJBQW1CO2FBQy9DO1lBQ0QsY0FBYyxFQUFFLENBQUMsbUJBQW1CLENBQUM7WUFDckMsSUFBSSxFQUFFLFVBQVU7WUFDaEIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxRQUFRLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQyxFQUFFLG1DQUFtQztZQUN0RSxVQUFVLEVBQUUsSUFBSTtZQUNoQixXQUFXLEVBQUU7Z0JBQ1gsWUFBWSxFQUFFLHdDQUF3QyxTQUFTLENBQUMsZUFBZSxDQUFDLFFBQVEsZ0JBQWdCO2dCQUN4RyxVQUFVLEVBQUUsSUFBSSxDQUFDLE1BQU07Z0JBQ3ZCLFdBQVcsRUFBRSxXQUFXO2FBQ3pCO1lBQ0QsWUFBWSxFQUFFLElBQUksQ0FBQyxhQUFhLENBQUMsUUFBUTtTQUMxQyxDQUFDLENBQUM7UUFFSCxxQ0FBcUM7UUFDckMsWUFBWSxDQUFDLGNBQWMsQ0FDekIsSUFBSSxNQUFNLENBQUMsY0FBYyxDQUFDLFNBQVMsRUFBRTtZQUNuQyxTQUFTLEVBQUUsQ0FBQyxFQUFFLG1DQUFtQztZQUNqRCxpQkFBaUIsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUM7WUFDM0MsdUJBQXVCLEVBQUUsSUFBSTtTQUM5QixDQUFDLENBQ0gsQ0FBQztRQUVGLGNBQWM7UUFDZCxNQUFNLEdBQUcsR0FBRyxJQUFJLFVBQVUsQ0FBQyxhQUFhLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRTtZQUM1RCxPQUFPLEVBQUUsU0FBUztZQUNsQixXQUFXLEVBQUUsaUJBQWlCLFdBQVcsRUFBRTtZQUMzQyxXQUFXLEVBQUUsMEJBQTBCLFdBQVcsRUFBRTtZQUNwRCxhQUFhLEVBQUU7Z0JBQ2IsU0FBUyxFQUFFLFdBQVc7Z0JBQ3RCLFlBQVksRUFBRSxVQUFVLENBQUMsa0JBQWtCLENBQUMsSUFBSTtnQkFDaEQsZ0JBQWdCLEVBQUUsSUFBSTthQUN2QjtZQUNELDJCQUEyQixFQUFFO2dCQUMzQixZQUFZLEVBQUUsVUFBVSxDQUFDLElBQUksQ0FBQyxXQUFXO2dCQUN6QyxZQUFZLEVBQUUsVUFBVSxDQUFDLElBQUksQ0FBQyxXQUFXO2dCQUN6QyxZQUFZLEVBQUU7b0JBQ1osY0FBYztvQkFDZCxZQUFZO29CQUNaLGVBQWU7b0JBQ2YsV0FBVztvQkFDWCxzQkFBc0I7aUJBQ3ZCO2FBQ0Y7U0FDRixDQUFDLENBQUM7UUFFSCxVQUFVO1FBQ1YsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxlQUFlLEVBQUU7WUFDdkMsS0FBSyxFQUFFLEdBQUcsQ0FBQyxHQUFHO1lBQ2QsV0FBVyxFQUFFLGlCQUFpQjtTQUMvQixDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGNBQWMsRUFBRTtZQUN0QyxLQUFLLEVBQUUsU0FBUyxDQUFDLFFBQVE7WUFDekIsV0FBVyxFQUFFLG9CQUFvQjtTQUNsQyxDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLG9CQUFvQixFQUFFO1lBQzVDLEtBQUssRUFBRSxlQUFlLENBQUMsUUFBUTtZQUMvQixXQUFXLEVBQUUsMkJBQTJCO1NBQ3pDLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsa0JBQWtCLEVBQUU7WUFDMUMsS0FBSyxFQUFFLFNBQVMsQ0FBQyxlQUFlLENBQUMsUUFBUTtZQUN6QyxXQUFXLEVBQUUsc0JBQXNCO1NBQ3BDLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsbUJBQW1CLEVBQUU7WUFDM0MsS0FBSyxFQUFFLFNBQVMsQ0FBQyxNQUFNLEVBQUUsU0FBUyxJQUFJLGVBQWU7WUFDckQsV0FBVyxFQUFFLGlDQUFpQztTQUMvQyxDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUFuTkQsc0NBbU5DIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcclxuaW1wb3J0ICogYXMgbGFtYmRhIGZyb20gJ2F3cy1jZGstbGliL2F3cy1sYW1iZGEnO1xyXG5pbXBvcnQgKiBhcyBzcXMgZnJvbSAnYXdzLWNkay1saWIvYXdzLXNxcyc7XHJcbmltcG9ydCAqIGFzIHJkcyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtcmRzJztcclxuaW1wb3J0ICogYXMgZWMyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1lYzInO1xyXG5pbXBvcnQgKiBhcyBpYW0gZnJvbSAnYXdzLWNkay1saWIvYXdzLWlhbSc7XHJcbmltcG9ydCAqIGFzIGFwaWdhdGV3YXkgZnJvbSAnYXdzLWNkay1saWIvYXdzLWFwaWdhdGV3YXknO1xyXG5pbXBvcnQgKiBhcyBsb2dzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1sb2dzJztcclxuaW1wb3J0ICogYXMgZXZlbnRzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1sYW1iZGEtZXZlbnQtc291cmNlcyc7XHJcbmltcG9ydCB7IENvbnN0cnVjdCB9IGZyb20gJ2NvbnN0cnVjdHMnO1xyXG5cclxuZXhwb3J0IGNsYXNzIEpvYlF1ZXVlU3RhY2sgZXh0ZW5kcyBjZGsuU3RhY2sge1xyXG4gIGNvbnN0cnVjdG9yKHNjb3BlOiBDb25zdHJ1Y3QsIGlkOiBzdHJpbmcsIHByb3BzPzogY2RrLlN0YWNrUHJvcHMpIHtcclxuICAgIHN1cGVyKHNjb3BlLCBpZCwgcHJvcHMpO1xyXG5cclxuICAgIGNvbnN0IGVudmlyb25tZW50ID0gcHJvY2Vzcy5lbnYuRU5WSVJPTk1FTlQgfHwgJ3N0YWdpbmcnO1xyXG5cclxuICAgIC8vIFZQQyBmb3IgUkRTIGFuZCBMYW1iZGFcclxuICAgIGNvbnN0IHZwYyA9IG5ldyBlYzIuVnBjKHRoaXMsICdKb2JRdWV1ZVZQQycsIHtcclxuICAgICAgbWF4QXpzOiAyLFxyXG4gICAgICBjaWRyOiAnMTAuMC4wLjAvMTYnLFxyXG4gICAgICBzdWJuZXRDb25maWd1cmF0aW9uOiBbXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgY2lkck1hc2s6IDI0LFxyXG4gICAgICAgICAgbmFtZTogJ1B1YmxpYycsXHJcbiAgICAgICAgICBzdWJuZXRUeXBlOiBlYzIuU3VibmV0VHlwZS5QVUJMSUMsXHJcbiAgICAgICAgfSxcclxuICAgICAgICB7XHJcbiAgICAgICAgICBjaWRyTWFzazogMjQsXHJcbiAgICAgICAgICBuYW1lOiAnUHJpdmF0ZScsXHJcbiAgICAgICAgICBzdWJuZXRUeXBlOiBlYzIuU3VibmV0VHlwZS5QUklWQVRFX1dJVEhfRUdSRVNTLFxyXG4gICAgICAgIH0sXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgY2lkck1hc2s6IDI0LFxyXG4gICAgICAgICAgbmFtZTogJ0RhdGFiYXNlJyxcclxuICAgICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfSVNPTEFURUQsXHJcbiAgICAgICAgfSxcclxuICAgICAgXSxcclxuICAgIH0pO1xyXG5cclxuICAgIC8vIFNlY3VyaXR5IEdyb3Vwc1xyXG4gICAgY29uc3QgbGFtYmRhU2VjdXJpdHlHcm91cCA9IG5ldyBlYzIuU2VjdXJpdHlHcm91cCh0aGlzLCAnTGFtYmRhU2VjdXJpdHlHcm91cCcsIHtcclxuICAgICAgdnBjLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ1NlY3VyaXR5IGdyb3VwIGZvciBMYW1iZGEgZnVuY3Rpb25zJyxcclxuICAgICAgYWxsb3dBbGxPdXRib3VuZDogdHJ1ZSxcclxuICAgIH0pO1xyXG5cclxuICAgIGNvbnN0IHJkc1NlY3VyaXR5R3JvdXAgPSBuZXcgZWMyLlNlY3VyaXR5R3JvdXAodGhpcywgJ1Jkc1NlY3VyaXR5R3JvdXAnLCB7XHJcbiAgICAgIHZwYyxcclxuICAgICAgZGVzY3JpcHRpb246ICdTZWN1cml0eSBncm91cCBmb3IgUkRTIGluc3RhbmNlJyxcclxuICAgICAgYWxsb3dBbGxPdXRib3VuZDogZmFsc2UsXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBBbGxvdyBMYW1iZGEgdG8gY29ubmVjdCB0byBSRFNcclxuICAgIHJkc1NlY3VyaXR5R3JvdXAuYWRkSW5ncmVzc1J1bGUoXHJcbiAgICAgIGVjMi5QZWVyLnNlY3VyaXR5R3JvdXBJZChsYW1iZGFTZWN1cml0eUdyb3VwLnNlY3VyaXR5R3JvdXBJZCksXHJcbiAgICAgIGVjMi5Qb3J0LnRjcCg1NDMyKSxcclxuICAgICAgJ0FsbG93IExhbWJkYSBhY2Nlc3MgdG8gUG9zdGdyZVNRTCdcclxuICAgICk7XHJcblxyXG4gICAgLy8gRGVhZCBMZXR0ZXIgUXVldWVcclxuICAgIGNvbnN0IGRlYWRMZXR0ZXJRdWV1ZSA9IG5ldyBzcXMuUXVldWUodGhpcywgJ0pvYlF1ZXVlRGVhZExldHRlclF1ZXVlJywge1xyXG4gICAgICBxdWV1ZU5hbWU6IGBqb2ItcXVldWUtZGxxLSR7ZW52aXJvbm1lbnR9YCxcclxuICAgICAgcmV0ZW50aW9uUGVyaW9kOiBjZGsuRHVyYXRpb24uZGF5cygxNCksXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBNYWluIFRhc2sgUXVldWVcclxuICAgIGNvbnN0IHRhc2tRdWV1ZSA9IG5ldyBzcXMuUXVldWUodGhpcywgJ0pvYlF1ZXVlVGFza1F1ZXVlJywge1xyXG4gICAgICBxdWV1ZU5hbWU6IGBqb2ItcXVldWUtdGFza3MtJHtlbnZpcm9ubWVudH1gLFxyXG4gICAgICB2aXNpYmlsaXR5VGltZW91dDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoMTUpLCAvLyAxNSBtaW51dGVzIGZvciBsb25nLXJ1bm5pbmcgdGFza3NcclxuICAgICAgZGVhZExldHRlclF1ZXVlOiB7XHJcbiAgICAgICAgcXVldWU6IGRlYWRMZXR0ZXJRdWV1ZSxcclxuICAgICAgICBtYXhSZWNlaXZlQ291bnQ6IDMsXHJcbiAgICAgIH0sXHJcbiAgICAgIHJlY2VpdmVNZXNzYWdlV2FpdFRpbWU6IGNkay5EdXJhdGlvbi5zZWNvbmRzKDIwKSwgLy8gTG9uZyBwb2xsaW5nXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBSRFMgQXVyb3JhIFNlcnZlcmxlc3MgdjIgUG9zdGdyZVNRTFxyXG4gICAgY29uc3QgZGJDbHVzdGVyID0gbmV3IHJkcy5EYXRhYmFzZUNsdXN0ZXIodGhpcywgJ0pvYlF1ZXVlRGF0YWJhc2UnLCB7XHJcbiAgICAgIGVuZ2luZTogcmRzLkRhdGFiYXNlQ2x1c3RlckVuZ2luZS5hdXJvcmFQb3N0Z3Jlcyh7XHJcbiAgICAgICAgdmVyc2lvbjogcmRzLkF1cm9yYVBvc3RncmVzRW5naW5lVmVyc2lvbi5WRVJfMTVfNCxcclxuICAgICAgfSksXHJcbiAgICAgIGNyZWRlbnRpYWxzOiByZHMuQ3JlZGVudGlhbHMuZnJvbUdlbmVyYXRlZFNlY3JldCgnam9icXVldWVfYWRtaW4nLCB7XHJcbiAgICAgICAgc2VjcmV0TmFtZTogYGpvYi1xdWV1ZS1kYi1jcmVkZW50aWFscy0ke2Vudmlyb25tZW50fWAsXHJcbiAgICAgIH0pLFxyXG4gICAgICBzZXJ2ZXJsZXNzVjJNaW5DYXBhY2l0eTogMC41LFxyXG4gICAgICBzZXJ2ZXJsZXNzVjJNYXhDYXBhY2l0eTogNCxcclxuICAgICAgd3JpdGVyOiByZHMuQ2x1c3Rlckluc3RhbmNlLnNlcnZlcmxlc3NWMignd3JpdGVyJyksXHJcbiAgICAgIHZwYyxcclxuICAgICAgdnBjU3VibmV0czoge1xyXG4gICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfSVNPTEFURUQsXHJcbiAgICAgIH0sXHJcbiAgICAgIHNlY3VyaXR5R3JvdXBzOiBbcmRzU2VjdXJpdHlHcm91cF0sXHJcbiAgICAgIGRlZmF1bHREYXRhYmFzZU5hbWU6ICdqb2JxdWV1ZScsXHJcbiAgICAgIGRlbGV0aW9uUHJvdGVjdGlvbjogZW52aXJvbm1lbnQgPT09ICdwcm9kdWN0aW9uJyxcclxuICAgICAgYmFja3VwOiB7XHJcbiAgICAgICAgcmV0ZW50aW9uOiBlbnZpcm9ubWVudCA9PT0gJ3Byb2R1Y3Rpb24nIFxyXG4gICAgICAgICAgPyBjZGsuRHVyYXRpb24uZGF5cyg3KSBcclxuICAgICAgICAgIDogY2RrLkR1cmF0aW9uLmRheXMoMSksXHJcbiAgICAgIH0sXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBMYW1iZGEgRXhlY3V0aW9uIFJvbGVcclxuICAgIGNvbnN0IGxhbWJkYVJvbGUgPSBuZXcgaWFtLlJvbGUodGhpcywgJ0xhbWJkYUV4ZWN1dGlvblJvbGUnLCB7XHJcbiAgICAgIGFzc3VtZWRCeTogbmV3IGlhbS5TZXJ2aWNlUHJpbmNpcGFsKCdsYW1iZGEuYW1hem9uYXdzLmNvbScpLFxyXG4gICAgICBtYW5hZ2VkUG9saWNpZXM6IFtcclxuICAgICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ3NlcnZpY2Utcm9sZS9BV1NMYW1iZGFCYXNpY0V4ZWN1dGlvblJvbGUnKSxcclxuICAgICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ3NlcnZpY2Utcm9sZS9BV1NMYW1iZGFWUENBY2Nlc3NFeGVjdXRpb25Sb2xlJyksXHJcbiAgICAgIF0sXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBBbGxvdyBMYW1iZGEgdG8gYWNjZXNzIFNRU1xyXG4gICAgdGFza1F1ZXVlLmdyYW50Q29uc3VtZU1lc3NhZ2VzKGxhbWJkYVJvbGUpO1xyXG4gICAgZGVhZExldHRlclF1ZXVlLmdyYW50Q29uc3VtZU1lc3NhZ2VzKGxhbWJkYVJvbGUpO1xyXG5cclxuICAgIC8vIEFsbG93IExhbWJkYSB0byBhY2Nlc3MgUkRTXHJcbiAgICBkYkNsdXN0ZXIuc2VjcmV0Py5ncmFudFJlYWQobGFtYmRhUm9sZSk7XHJcblxyXG4gICAgLy8gQVBJIExhbWJkYSBGdW5jdGlvblxyXG4gICAgY29uc3QgYXBpTGFtYmRhID0gbmV3IGxhbWJkYS5GdW5jdGlvbih0aGlzLCAnSm9iUXVldWVBcGlMYW1iZGEnLCB7XHJcbiAgICAgIGZ1bmN0aW9uTmFtZTogYGpvYi1xdWV1ZS1hcGktJHtlbnZpcm9ubWVudH1gLFxyXG4gICAgICBydW50aW1lOiBsYW1iZGEuUnVudGltZS5QWVRIT05fM18xMSxcclxuICAgICAgaGFuZGxlcjogJ2xhbWJkYV9oYW5kbGVyLmxhbWJkYV9oYW5kbGVyJyxcclxuICAgICAgY29kZTogbGFtYmRhLkNvZGUuZnJvbUFzc2V0KCcuLi9iYWNrZW5kJyksIC8vIFdpbGwgYmUgcmVwbGFjZWQgaW4gQ0kvQ0RcclxuICAgICAgdnBjLFxyXG4gICAgICB2cGNTdWJuZXRzOiB7XHJcbiAgICAgICAgc3VibmV0VHlwZTogZWMyLlN1Ym5ldFR5cGUuUFJJVkFURV9XSVRIX0VHUkVTUyxcclxuICAgICAgfSxcclxuICAgICAgc2VjdXJpdHlHcm91cHM6IFtsYW1iZGFTZWN1cml0eUdyb3VwXSxcclxuICAgICAgcm9sZTogbGFtYmRhUm9sZSxcclxuICAgICAgdGltZW91dDogY2RrLkR1cmF0aW9uLnNlY29uZHMoMzApLFxyXG4gICAgICBtZW1vcnlTaXplOiA1MTIsXHJcbiAgICAgIGVudmlyb25tZW50OiB7XHJcbiAgICAgICAgREFUQUJBU0VfVVJMOiBgcG9zdGdyZXNxbDovL2pvYnF1ZXVlX2FkbWluOnBhc3N3b3JkQCR7ZGJDbHVzdGVyLmNsdXN0ZXJFbmRwb2ludC5ob3N0bmFtZX06NTQzMi9qb2JxdWV1ZWAsXHJcbiAgICAgICAgU1FTX1FVRVVFX1VSTDogdGFza1F1ZXVlLnF1ZXVlVXJsLFxyXG4gICAgICAgIFNRU19ETFFfVVJMOiBkZWFkTGV0dGVyUXVldWUucXVldWVVcmwsXHJcbiAgICAgICAgQVdTX1JFR0lPTjogdGhpcy5yZWdpb24sXHJcbiAgICAgICAgRU5WSVJPTk1FTlQ6IGVudmlyb25tZW50LFxyXG4gICAgICB9LFxyXG4gICAgICBsb2dSZXRlbnRpb246IGxvZ3MuUmV0ZW50aW9uRGF5cy5PTkVfV0VFSyxcclxuICAgIH0pO1xyXG5cclxuICAgIC8vIFdvcmtlciBMYW1iZGEgRnVuY3Rpb25cclxuICAgIGNvbnN0IHdvcmtlckxhbWJkYSA9IG5ldyBsYW1iZGEuRnVuY3Rpb24odGhpcywgJ0pvYlF1ZXVlV29ya2VyTGFtYmRhJywge1xyXG4gICAgICBmdW5jdGlvbk5hbWU6IGBqb2ItcXVldWUtd29ya2VyLSR7ZW52aXJvbm1lbnR9YCxcclxuICAgICAgcnVudGltZTogbGFtYmRhLlJ1bnRpbWUuUFlUSE9OXzNfMTEsXHJcbiAgICAgIGhhbmRsZXI6ICdsYW1iZGFfaGFuZGxlci5sYW1iZGFfaGFuZGxlcicsXHJcbiAgICAgIGNvZGU6IGxhbWJkYS5Db2RlLmZyb21Bc3NldCgnLi4vd29ya2VyJyksIC8vIFdpbGwgYmUgcmVwbGFjZWQgaW4gQ0kvQ0RcclxuICAgICAgdnBjLFxyXG4gICAgICB2cGNTdWJuZXRzOiB7XHJcbiAgICAgICAgc3VibmV0VHlwZTogZWMyLlN1Ym5ldFR5cGUuUFJJVkFURV9XSVRIX0VHUkVTUyxcclxuICAgICAgfSxcclxuICAgICAgc2VjdXJpdHlHcm91cHM6IFtsYW1iZGFTZWN1cml0eUdyb3VwXSxcclxuICAgICAgcm9sZTogbGFtYmRhUm9sZSxcclxuICAgICAgdGltZW91dDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoMTUpLCAvLyBMb25nIHRpbWVvdXQgZm9yIHRhc2sgcHJvY2Vzc2luZ1xyXG4gICAgICBtZW1vcnlTaXplOiAxMDI0LFxyXG4gICAgICBlbnZpcm9ubWVudDoge1xyXG4gICAgICAgIERBVEFCQVNFX1VSTDogYHBvc3RncmVzcWw6Ly9qb2JxdWV1ZV9hZG1pbjpwYXNzd29yZEAke2RiQ2x1c3Rlci5jbHVzdGVyRW5kcG9pbnQuaG9zdG5hbWV9OjU0MzIvam9icXVldWVgLFxyXG4gICAgICAgIEFXU19SRUdJT046IHRoaXMucmVnaW9uLFxyXG4gICAgICAgIEVOVklST05NRU5UOiBlbnZpcm9ubWVudCxcclxuICAgICAgfSxcclxuICAgICAgbG9nUmV0ZW50aW9uOiBsb2dzLlJldGVudGlvbkRheXMuT05FX1dFRUssXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBTUVMgRXZlbnQgU291cmNlIGZvciBXb3JrZXIgTGFtYmRhXHJcbiAgICB3b3JrZXJMYW1iZGEuYWRkRXZlbnRTb3VyY2UoXHJcbiAgICAgIG5ldyBldmVudHMuU3FzRXZlbnRTb3VyY2UodGFza1F1ZXVlLCB7XHJcbiAgICAgICAgYmF0Y2hTaXplOiA1LCAvLyBQcm9jZXNzIHVwIHRvIDUgbWVzc2FnZXMgYXQgb25jZVxyXG4gICAgICAgIG1heEJhdGNoaW5nV2luZG93OiBjZGsuRHVyYXRpb24uc2Vjb25kcygxMCksXHJcbiAgICAgICAgcmVwb3J0QmF0Y2hJdGVtRmFpbHVyZXM6IHRydWUsXHJcbiAgICAgIH0pXHJcbiAgICApO1xyXG5cclxuICAgIC8vIEFQSSBHYXRld2F5XHJcbiAgICBjb25zdCBhcGkgPSBuZXcgYXBpZ2F0ZXdheS5MYW1iZGFSZXN0QXBpKHRoaXMsICdKb2JRdWV1ZUFwaScsIHtcclxuICAgICAgaGFuZGxlcjogYXBpTGFtYmRhLFxyXG4gICAgICByZXN0QXBpTmFtZTogYGpvYi1xdWV1ZS1hcGktJHtlbnZpcm9ubWVudH1gLFxyXG4gICAgICBkZXNjcmlwdGlvbjogYEpvYiBRdWV1ZSBTeXN0ZW0gQVBJIC0gJHtlbnZpcm9ubWVudH1gLFxyXG4gICAgICBkZXBsb3lPcHRpb25zOiB7XHJcbiAgICAgICAgc3RhZ2VOYW1lOiBlbnZpcm9ubWVudCxcclxuICAgICAgICBsb2dnaW5nTGV2ZWw6IGFwaWdhdGV3YXkuTWV0aG9kTG9nZ2luZ0xldmVsLklORk8sXHJcbiAgICAgICAgZGF0YVRyYWNlRW5hYmxlZDogdHJ1ZSxcclxuICAgICAgfSxcclxuICAgICAgZGVmYXVsdENvcnNQcmVmbGlnaHRPcHRpb25zOiB7XHJcbiAgICAgICAgYWxsb3dPcmlnaW5zOiBhcGlnYXRld2F5LkNvcnMuQUxMX09SSUdJTlMsXHJcbiAgICAgICAgYWxsb3dNZXRob2RzOiBhcGlnYXRld2F5LkNvcnMuQUxMX01FVEhPRFMsXHJcbiAgICAgICAgYWxsb3dIZWFkZXJzOiBbXHJcbiAgICAgICAgICAnQ29udGVudC1UeXBlJyxcclxuICAgICAgICAgICdYLUFtei1EYXRlJyxcclxuICAgICAgICAgICdBdXRob3JpemF0aW9uJyxcclxuICAgICAgICAgICdYLUFwaS1LZXknLFxyXG4gICAgICAgICAgJ1gtQW16LVNlY3VyaXR5LVRva2VuJyxcclxuICAgICAgICBdLFxyXG4gICAgICB9LFxyXG4gICAgfSk7XHJcblxyXG4gICAgLy8gT3V0cHV0c1xyXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0FwaUdhdGV3YXlVcmwnLCB7XHJcbiAgICAgIHZhbHVlOiBhcGkudXJsLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ0FQSSBHYXRld2F5IFVSTCcsXHJcbiAgICB9KTtcclxuXHJcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnVGFza1F1ZXVlVXJsJywge1xyXG4gICAgICB2YWx1ZTogdGFza1F1ZXVlLnF1ZXVlVXJsLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ1NRUyBUYXNrIFF1ZXVlIFVSTCcsXHJcbiAgICB9KTtcclxuXHJcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnRGVhZExldHRlclF1ZXVlVXJsJywge1xyXG4gICAgICB2YWx1ZTogZGVhZExldHRlclF1ZXVlLnF1ZXVlVXJsLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ1NRUyBEZWFkIExldHRlciBRdWV1ZSBVUkwnLFxyXG4gICAgfSk7XHJcblxyXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0RhdGFiYXNlRW5kcG9pbnQnLCB7XHJcbiAgICAgIHZhbHVlOiBkYkNsdXN0ZXIuY2x1c3RlckVuZHBvaW50Lmhvc3RuYW1lLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ1JEUyBDbHVzdGVyIEVuZHBvaW50JyxcclxuICAgIH0pO1xyXG5cclxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdEYXRhYmFzZVNlY3JldEFybicsIHtcclxuICAgICAgdmFsdWU6IGRiQ2x1c3Rlci5zZWNyZXQ/LnNlY3JldEFybiB8fCAnTm90IGF2YWlsYWJsZScsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnRGF0YWJhc2UgY3JlZGVudGlhbHMgc2VjcmV0IEFSTicsXHJcbiAgICB9KTtcclxuICB9XHJcbn0iXX0=