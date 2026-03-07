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
                version: rds.AuroraPostgresEngineVersion.VER_14_7,
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
        // Allow Lambda to access RDS credentials from Secrets Manager
        dbCluster.secret?.grantRead(lambdaRole);
        // API Lambda Function
        const logGroup = new logs.LogGroup(this, 'JobQueueApiLambdaLogGroup', {
            retention: logs.RetentionDays.ONE_WEEK,
        });
        const apiLambda = new lambda.Function(this, 'JobQueueApiLambda', {
            functionName: `job-queue-api-${environment}`,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'lambda_handler.lambda_handler',
            code: lambda.Code.fromAsset('../../backend'), // Backend application code
            vpc,
            vpcSubnets: {
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
            },
            securityGroups: [lambdaSecurityGroup],
            role: lambdaRole,
            timeout: cdk.Duration.seconds(30),
            memorySize: 512,
            environment: {
                DB_HOST: dbCluster.clusterEndpoint.hostname,
                DB_PORT: '5432',
                DB_NAME: 'jobqueue',
                DB_USER: 'jobqueue_admin',
                DB_SECRET_ARN: dbCluster.secret?.secretArn || '',
                SQS_QUEUE_URL: taskQueue.queueUrl,
                SQS_DLQ_URL: deadLetterQueue.queueUrl,
                ENVIRONMENT: environment,
            },
            logGroup: logGroup,
        });
        // Worker Lambda Function
        const workerLambda = new lambda.Function(this, 'JobQueueWorkerLambda', {
            functionName: `job-queue-worker-${environment}`,
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'lambda_handler.lambda_handler',
            code: lambda.Code.fromAsset('../../worker'), // Worker application code
            vpc,
            vpcSubnets: {
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
            },
            securityGroups: [lambdaSecurityGroup],
            role: lambdaRole,
            timeout: cdk.Duration.minutes(15), // Long timeout for task processing
            memorySize: 1024,
            environment: {
                DB_HOST: dbCluster.clusterEndpoint.hostname,
                DB_PORT: '5432',
                DB_NAME: 'jobqueue',
                DB_USER: 'jobqueue_admin',
                DB_SECRET_ARN: dbCluster.secret?.secretArn || '',
                SQS_QUEUE_URL: taskQueue.queueUrl,
                SQS_DLQ_URL: deadLetterQueue.queueUrl,
                ENVIRONMENT: environment,
            },
            logGroup: logGroup,
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiam9iLXF1ZXVlLXN0YWNrLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiam9iLXF1ZXVlLXN0YWNrLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7OztBQUFBLGlEQUFtQztBQUNuQywrREFBaUQ7QUFDakQseURBQTJDO0FBQzNDLHlEQUEyQztBQUMzQyx5REFBMkM7QUFDM0MseURBQTJDO0FBQzNDLHVFQUF5RDtBQUN6RCwyREFBNkM7QUFDN0MsNkVBQStEO0FBRy9ELE1BQWEsYUFBYyxTQUFRLEdBQUcsQ0FBQyxLQUFLO0lBQzFDLFlBQVksS0FBZ0IsRUFBRSxFQUFVLEVBQUUsS0FBc0I7UUFDOUQsS0FBSyxDQUFDLEtBQUssRUFBRSxFQUFFLEVBQUUsS0FBSyxDQUFDLENBQUM7UUFFeEIsTUFBTSxXQUFXLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxXQUFXLElBQUksU0FBUyxDQUFDO1FBRXpELHlCQUF5QjtRQUN6QixNQUFNLEdBQUcsR0FBRyxJQUFJLEdBQUcsQ0FBQyxHQUFHLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRTtZQUMzQyxNQUFNLEVBQUUsQ0FBQztZQUNULElBQUksRUFBRSxhQUFhO1lBQ25CLG1CQUFtQixFQUFFO2dCQUNuQjtvQkFDRSxRQUFRLEVBQUUsRUFBRTtvQkFDWixJQUFJLEVBQUUsUUFBUTtvQkFDZCxVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxNQUFNO2lCQUNsQztnQkFDRDtvQkFDRSxRQUFRLEVBQUUsRUFBRTtvQkFDWixJQUFJLEVBQUUsU0FBUztvQkFDZixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxtQkFBbUI7aUJBQy9DO2dCQUNEO29CQUNFLFFBQVEsRUFBRSxFQUFFO29CQUNaLElBQUksRUFBRSxVQUFVO29CQUNoQixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxnQkFBZ0I7aUJBQzVDO2FBQ0Y7U0FDRixDQUFDLENBQUM7UUFFSCxrQkFBa0I7UUFDbEIsTUFBTSxtQkFBbUIsR0FBRyxJQUFJLEdBQUcsQ0FBQyxhQUFhLENBQUMsSUFBSSxFQUFFLHFCQUFxQixFQUFFO1lBQzdFLEdBQUc7WUFDSCxXQUFXLEVBQUUscUNBQXFDO1lBQ2xELGdCQUFnQixFQUFFLElBQUk7U0FDdkIsQ0FBQyxDQUFDO1FBRUgsTUFBTSxnQkFBZ0IsR0FBRyxJQUFJLEdBQUcsQ0FBQyxhQUFhLENBQUMsSUFBSSxFQUFFLGtCQUFrQixFQUFFO1lBQ3ZFLEdBQUc7WUFDSCxXQUFXLEVBQUUsaUNBQWlDO1lBQzlDLGdCQUFnQixFQUFFLEtBQUs7U0FDeEIsQ0FBQyxDQUFDO1FBRUgsaUNBQWlDO1FBQ2pDLGdCQUFnQixDQUFDLGNBQWMsQ0FDN0IsR0FBRyxDQUFDLElBQUksQ0FBQyxlQUFlLENBQUMsbUJBQW1CLENBQUMsZUFBZSxDQUFDLEVBQzdELEdBQUcsQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxFQUNsQixtQ0FBbUMsQ0FDcEMsQ0FBQztRQUVGLG9CQUFvQjtRQUNwQixNQUFNLGVBQWUsR0FBRyxJQUFJLEdBQUcsQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLHlCQUF5QixFQUFFO1lBQ3JFLFNBQVMsRUFBRSxpQkFBaUIsV0FBVyxFQUFFO1lBQ3pDLGVBQWUsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUM7U0FDdkMsQ0FBQyxDQUFDO1FBRUgsa0JBQWtCO1FBQ2xCLE1BQU0sU0FBUyxHQUFHLElBQUksR0FBRyxDQUFDLEtBQUssQ0FBQyxJQUFJLEVBQUUsbUJBQW1CLEVBQUU7WUFDekQsU0FBUyxFQUFFLG1CQUFtQixXQUFXLEVBQUU7WUFDM0MsaUJBQWlCLEVBQUUsR0FBRyxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLEVBQUUsb0NBQW9DO1lBQ2pGLGVBQWUsRUFBRTtnQkFDZixLQUFLLEVBQUUsZUFBZTtnQkFDdEIsZUFBZSxFQUFFLENBQUM7YUFDbkI7WUFDRCxzQkFBc0IsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUMsRUFBRSxlQUFlO1NBQ2xFLENBQUMsQ0FBQztRQUVILHNDQUFzQztRQUN0QyxNQUFNLFNBQVMsR0FBRyxJQUFJLEdBQUcsQ0FBQyxlQUFlLENBQUMsSUFBSSxFQUFFLGtCQUFrQixFQUFFO1lBQ2xFLE1BQU0sRUFBRSxHQUFHLENBQUMscUJBQXFCLENBQUMsY0FBYyxDQUFDO2dCQUMvQyxPQUFPLEVBQUUsR0FBRyxDQUFDLDJCQUEyQixDQUFDLFFBQVE7YUFDbEQsQ0FBQztZQUNGLFdBQVcsRUFBRSxHQUFHLENBQUMsV0FBVyxDQUFDLG1CQUFtQixDQUFDLGdCQUFnQixFQUFFO2dCQUNqRSxVQUFVLEVBQUUsNEJBQTRCLFdBQVcsRUFBRTthQUN0RCxDQUFDO1lBQ0YsdUJBQXVCLEVBQUUsR0FBRztZQUM1Qix1QkFBdUIsRUFBRSxDQUFDO1lBQzFCLE1BQU0sRUFBRSxHQUFHLENBQUMsZUFBZSxDQUFDLFlBQVksQ0FBQyxRQUFRLENBQUM7WUFDbEQsR0FBRztZQUNILFVBQVUsRUFBRTtnQkFDVixVQUFVLEVBQUUsR0FBRyxDQUFDLFVBQVUsQ0FBQyxnQkFBZ0I7YUFDNUM7WUFDRCxjQUFjLEVBQUUsQ0FBQyxnQkFBZ0IsQ0FBQztZQUNsQyxtQkFBbUIsRUFBRSxVQUFVO1lBQy9CLGtCQUFrQixFQUFFLFdBQVcsS0FBSyxZQUFZO1lBQ2hELE1BQU0sRUFBRTtnQkFDTixTQUFTLEVBQUUsV0FBVyxLQUFLLFlBQVk7b0JBQ3JDLENBQUMsQ0FBQyxHQUFHLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7b0JBQ3RCLENBQUMsQ0FBQyxHQUFHLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7YUFDekI7U0FDRixDQUFDLENBQUM7UUFFSCx3QkFBd0I7UUFDeEIsTUFBTSxVQUFVLEdBQUcsSUFBSSxHQUFHLENBQUMsSUFBSSxDQUFDLElBQUksRUFBRSxxQkFBcUIsRUFBRTtZQUMzRCxTQUFTLEVBQUUsSUFBSSxHQUFHLENBQUMsZ0JBQWdCLENBQUMsc0JBQXNCLENBQUM7WUFDM0QsZUFBZSxFQUFFO2dCQUNmLEdBQUcsQ0FBQyxhQUFhLENBQUMsd0JBQXdCLENBQUMsMENBQTBDLENBQUM7Z0JBQ3RGLEdBQUcsQ0FBQyxhQUFhLENBQUMsd0JBQXdCLENBQUMsOENBQThDLENBQUM7YUFDM0Y7U0FDRixDQUFDLENBQUM7UUFFSCw2QkFBNkI7UUFDN0IsU0FBUyxDQUFDLG9CQUFvQixDQUFDLFVBQVUsQ0FBQyxDQUFDO1FBQzNDLGVBQWUsQ0FBQyxvQkFBb0IsQ0FBQyxVQUFVLENBQUMsQ0FBQztRQUVqRCw4REFBOEQ7UUFDOUQsU0FBUyxDQUFDLE1BQU0sRUFBRSxTQUFTLENBQUMsVUFBVSxDQUFDLENBQUM7UUFFeEMsc0JBQXNCO1FBQ3RCLE1BQU0sUUFBUSxHQUFHLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxJQUFJLEVBQUUsMkJBQTJCLEVBQUU7WUFDcEUsU0FBUyxFQUFFLElBQUksQ0FBQyxhQUFhLENBQUMsUUFBUTtTQUN2QyxDQUFDLENBQUM7UUFFSCxNQUFNLFNBQVMsR0FBRyxJQUFJLE1BQU0sQ0FBQyxRQUFRLENBQUMsSUFBSSxFQUFFLG1CQUFtQixFQUFFO1lBQy9ELFlBQVksRUFBRSxpQkFBaUIsV0FBVyxFQUFFO1lBQzVDLE9BQU8sRUFBRSxNQUFNLENBQUMsT0FBTyxDQUFDLFdBQVc7WUFDbkMsT0FBTyxFQUFFLCtCQUErQjtZQUN4QyxJQUFJLEVBQUUsTUFBTSxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsZUFBZSxDQUFDLEVBQUUsMkJBQTJCO1lBQ3pFLEdBQUc7WUFDSCxVQUFVLEVBQUU7Z0JBQ1YsVUFBVSxFQUFFLEdBQUcsQ0FBQyxVQUFVLENBQUMsbUJBQW1CO2FBQy9DO1lBQ0QsY0FBYyxFQUFFLENBQUMsbUJBQW1CLENBQUM7WUFDckMsSUFBSSxFQUFFLFVBQVU7WUFDaEIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxRQUFRLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQztZQUNqQyxVQUFVLEVBQUUsR0FBRztZQUNmLFdBQVcsRUFBRTtnQkFDWCxPQUFPLEVBQUUsU0FBUyxDQUFDLGVBQWUsQ0FBQyxRQUFRO2dCQUMzQyxPQUFPLEVBQUUsTUFBTTtnQkFDZixPQUFPLEVBQUUsVUFBVTtnQkFDbkIsT0FBTyxFQUFFLGdCQUFnQjtnQkFDekIsYUFBYSxFQUFFLFNBQVMsQ0FBQyxNQUFNLEVBQUUsU0FBUyxJQUFJLEVBQUU7Z0JBQ2hELGFBQWEsRUFBRSxTQUFTLENBQUMsUUFBUTtnQkFDakMsV0FBVyxFQUFFLGVBQWUsQ0FBQyxRQUFRO2dCQUNyQyxXQUFXLEVBQUUsV0FBVzthQUN6QjtZQUNELFFBQVEsRUFBRSxRQUFRO1NBQ25CLENBQUMsQ0FBQztRQUVILHlCQUF5QjtRQUN6QixNQUFNLFlBQVksR0FBRyxJQUFJLE1BQU0sQ0FBQyxRQUFRLENBQUMsSUFBSSxFQUFFLHNCQUFzQixFQUFFO1lBQ3JFLFlBQVksRUFBRSxvQkFBb0IsV0FBVyxFQUFFO1lBQy9DLE9BQU8sRUFBRSxNQUFNLENBQUMsT0FBTyxDQUFDLFdBQVc7WUFDbkMsT0FBTyxFQUFFLCtCQUErQjtZQUN4QyxJQUFJLEVBQUUsTUFBTSxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsY0FBYyxDQUFDLEVBQUUsMEJBQTBCO1lBQ3ZFLEdBQUc7WUFDSCxVQUFVLEVBQUU7Z0JBQ1YsVUFBVSxFQUFFLEdBQUcsQ0FBQyxVQUFVLENBQUMsbUJBQW1CO2FBQy9DO1lBQ0QsY0FBYyxFQUFFLENBQUMsbUJBQW1CLENBQUM7WUFDckMsSUFBSSxFQUFFLFVBQVU7WUFDaEIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxRQUFRLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQyxFQUFFLG1DQUFtQztZQUN0RSxVQUFVLEVBQUUsSUFBSTtZQUNoQixXQUFXLEVBQUU7Z0JBQ1gsT0FBTyxFQUFFLFNBQVMsQ0FBQyxlQUFlLENBQUMsUUFBUTtnQkFDM0MsT0FBTyxFQUFFLE1BQU07Z0JBQ2YsT0FBTyxFQUFFLFVBQVU7Z0JBQ25CLE9BQU8sRUFBRSxnQkFBZ0I7Z0JBQ3pCLGFBQWEsRUFBRSxTQUFTLENBQUMsTUFBTSxFQUFFLFNBQVMsSUFBSSxFQUFFO2dCQUNoRCxhQUFhLEVBQUUsU0FBUyxDQUFDLFFBQVE7Z0JBQ2pDLFdBQVcsRUFBRSxlQUFlLENBQUMsUUFBUTtnQkFDckMsV0FBVyxFQUFFLFdBQVc7YUFDekI7WUFDRCxRQUFRLEVBQUUsUUFBUTtTQUNuQixDQUFDLENBQUM7UUFFSCxxQ0FBcUM7UUFDckMsWUFBWSxDQUFDLGNBQWMsQ0FDekIsSUFBSSxNQUFNLENBQUMsY0FBYyxDQUFDLFNBQVMsRUFBRTtZQUNuQyxTQUFTLEVBQUUsQ0FBQyxFQUFFLG1DQUFtQztZQUNqRCxpQkFBaUIsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUM7WUFDM0MsdUJBQXVCLEVBQUUsSUFBSTtTQUM5QixDQUFDLENBQ0gsQ0FBQztRQUVGLGNBQWM7UUFDZCxNQUFNLEdBQUcsR0FBRyxJQUFJLFVBQVUsQ0FBQyxhQUFhLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRTtZQUM1RCxPQUFPLEVBQUUsU0FBUztZQUNsQixXQUFXLEVBQUUsaUJBQWlCLFdBQVcsRUFBRTtZQUMzQyxXQUFXLEVBQUUsMEJBQTBCLFdBQVcsRUFBRTtZQUNwRCxhQUFhLEVBQUU7Z0JBQ2IsU0FBUyxFQUFFLFdBQVc7Z0JBQ3RCLFlBQVksRUFBRSxVQUFVLENBQUMsa0JBQWtCLENBQUMsSUFBSTtnQkFDaEQsZ0JBQWdCLEVBQUUsSUFBSTthQUN2QjtZQUNELDJCQUEyQixFQUFFO2dCQUMzQixZQUFZLEVBQUUsVUFBVSxDQUFDLElBQUksQ0FBQyxXQUFXO2dCQUN6QyxZQUFZLEVBQUUsVUFBVSxDQUFDLElBQUksQ0FBQyxXQUFXO2dCQUN6QyxZQUFZLEVBQUU7b0JBQ1osY0FBYztvQkFDZCxZQUFZO29CQUNaLGVBQWU7b0JBQ2YsV0FBVztvQkFDWCxzQkFBc0I7aUJBQ3ZCO2FBQ0Y7U0FDRixDQUFDLENBQUM7UUFFSCxVQUFVO1FBQ1YsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxlQUFlLEVBQUU7WUFDdkMsS0FBSyxFQUFFLEdBQUcsQ0FBQyxHQUFHO1lBQ2QsV0FBVyxFQUFFLGlCQUFpQjtTQUMvQixDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGNBQWMsRUFBRTtZQUN0QyxLQUFLLEVBQUUsU0FBUyxDQUFDLFFBQVE7WUFDekIsV0FBVyxFQUFFLG9CQUFvQjtTQUNsQyxDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLG9CQUFvQixFQUFFO1lBQzVDLEtBQUssRUFBRSxlQUFlLENBQUMsUUFBUTtZQUMvQixXQUFXLEVBQUUsMkJBQTJCO1NBQ3pDLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsa0JBQWtCLEVBQUU7WUFDMUMsS0FBSyxFQUFFLFNBQVMsQ0FBQyxlQUFlLENBQUMsUUFBUTtZQUN6QyxXQUFXLEVBQUUsc0JBQXNCO1NBQ3BDLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsbUJBQW1CLEVBQUU7WUFDM0MsS0FBSyxFQUFFLFNBQVMsQ0FBQyxNQUFNLEVBQUUsU0FBUyxJQUFJLGVBQWU7WUFDckQsV0FBVyxFQUFFLGlDQUFpQztTQUMvQyxDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUEvTkQsc0NBK05DIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcclxuaW1wb3J0ICogYXMgbGFtYmRhIGZyb20gJ2F3cy1jZGstbGliL2F3cy1sYW1iZGEnO1xyXG5pbXBvcnQgKiBhcyBzcXMgZnJvbSAnYXdzLWNkay1saWIvYXdzLXNxcyc7XHJcbmltcG9ydCAqIGFzIHJkcyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtcmRzJztcclxuaW1wb3J0ICogYXMgZWMyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1lYzInO1xyXG5pbXBvcnQgKiBhcyBpYW0gZnJvbSAnYXdzLWNkay1saWIvYXdzLWlhbSc7XHJcbmltcG9ydCAqIGFzIGFwaWdhdGV3YXkgZnJvbSAnYXdzLWNkay1saWIvYXdzLWFwaWdhdGV3YXknO1xyXG5pbXBvcnQgKiBhcyBsb2dzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1sb2dzJztcclxuaW1wb3J0ICogYXMgZXZlbnRzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1sYW1iZGEtZXZlbnQtc291cmNlcyc7XHJcbmltcG9ydCB7IENvbnN0cnVjdCB9IGZyb20gJ2NvbnN0cnVjdHMnO1xyXG5cclxuZXhwb3J0IGNsYXNzIEpvYlF1ZXVlU3RhY2sgZXh0ZW5kcyBjZGsuU3RhY2sge1xyXG4gIGNvbnN0cnVjdG9yKHNjb3BlOiBDb25zdHJ1Y3QsIGlkOiBzdHJpbmcsIHByb3BzPzogY2RrLlN0YWNrUHJvcHMpIHtcclxuICAgIHN1cGVyKHNjb3BlLCBpZCwgcHJvcHMpO1xyXG5cclxuICAgIGNvbnN0IGVudmlyb25tZW50ID0gcHJvY2Vzcy5lbnYuRU5WSVJPTk1FTlQgfHwgJ3N0YWdpbmcnO1xyXG5cclxuICAgIC8vIFZQQyBmb3IgUkRTIGFuZCBMYW1iZGFcclxuICAgIGNvbnN0IHZwYyA9IG5ldyBlYzIuVnBjKHRoaXMsICdKb2JRdWV1ZVZQQycsIHtcclxuICAgICAgbWF4QXpzOiAyLFxyXG4gICAgICBjaWRyOiAnMTAuMC4wLjAvMTYnLFxyXG4gICAgICBzdWJuZXRDb25maWd1cmF0aW9uOiBbXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgY2lkck1hc2s6IDI0LFxyXG4gICAgICAgICAgbmFtZTogJ1B1YmxpYycsXHJcbiAgICAgICAgICBzdWJuZXRUeXBlOiBlYzIuU3VibmV0VHlwZS5QVUJMSUMsXHJcbiAgICAgICAgfSxcclxuICAgICAgICB7XHJcbiAgICAgICAgICBjaWRyTWFzazogMjQsXHJcbiAgICAgICAgICBuYW1lOiAnUHJpdmF0ZScsXHJcbiAgICAgICAgICBzdWJuZXRUeXBlOiBlYzIuU3VibmV0VHlwZS5QUklWQVRFX1dJVEhfRUdSRVNTLFxyXG4gICAgICAgIH0sXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgY2lkck1hc2s6IDI0LFxyXG4gICAgICAgICAgbmFtZTogJ0RhdGFiYXNlJyxcclxuICAgICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfSVNPTEFURUQsXHJcbiAgICAgICAgfSxcclxuICAgICAgXSxcclxuICAgIH0pO1xyXG5cclxuICAgIC8vIFNlY3VyaXR5IEdyb3Vwc1xyXG4gICAgY29uc3QgbGFtYmRhU2VjdXJpdHlHcm91cCA9IG5ldyBlYzIuU2VjdXJpdHlHcm91cCh0aGlzLCAnTGFtYmRhU2VjdXJpdHlHcm91cCcsIHtcclxuICAgICAgdnBjLFxyXG4gICAgICBkZXNjcmlwdGlvbjogJ1NlY3VyaXR5IGdyb3VwIGZvciBMYW1iZGEgZnVuY3Rpb25zJyxcclxuICAgICAgYWxsb3dBbGxPdXRib3VuZDogdHJ1ZSxcclxuICAgIH0pO1xyXG5cclxuICAgIGNvbnN0IHJkc1NlY3VyaXR5R3JvdXAgPSBuZXcgZWMyLlNlY3VyaXR5R3JvdXAodGhpcywgJ1Jkc1NlY3VyaXR5R3JvdXAnLCB7XHJcbiAgICAgIHZwYyxcclxuICAgICAgZGVzY3JpcHRpb246ICdTZWN1cml0eSBncm91cCBmb3IgUkRTIGluc3RhbmNlJyxcclxuICAgICAgYWxsb3dBbGxPdXRib3VuZDogZmFsc2UsXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBBbGxvdyBMYW1iZGEgdG8gY29ubmVjdCB0byBSRFNcclxuICAgIHJkc1NlY3VyaXR5R3JvdXAuYWRkSW5ncmVzc1J1bGUoXHJcbiAgICAgIGVjMi5QZWVyLnNlY3VyaXR5R3JvdXBJZChsYW1iZGFTZWN1cml0eUdyb3VwLnNlY3VyaXR5R3JvdXBJZCksXHJcbiAgICAgIGVjMi5Qb3J0LnRjcCg1NDMyKSxcclxuICAgICAgJ0FsbG93IExhbWJkYSBhY2Nlc3MgdG8gUG9zdGdyZVNRTCdcclxuICAgICk7XHJcblxyXG4gICAgLy8gRGVhZCBMZXR0ZXIgUXVldWVcclxuICAgIGNvbnN0IGRlYWRMZXR0ZXJRdWV1ZSA9IG5ldyBzcXMuUXVldWUodGhpcywgJ0pvYlF1ZXVlRGVhZExldHRlclF1ZXVlJywge1xyXG4gICAgICBxdWV1ZU5hbWU6IGBqb2ItcXVldWUtZGxxLSR7ZW52aXJvbm1lbnR9YCxcclxuICAgICAgcmV0ZW50aW9uUGVyaW9kOiBjZGsuRHVyYXRpb24uZGF5cygxNCksXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBNYWluIFRhc2sgUXVldWVcclxuICAgIGNvbnN0IHRhc2tRdWV1ZSA9IG5ldyBzcXMuUXVldWUodGhpcywgJ0pvYlF1ZXVlVGFza1F1ZXVlJywge1xyXG4gICAgICBxdWV1ZU5hbWU6IGBqb2ItcXVldWUtdGFza3MtJHtlbnZpcm9ubWVudH1gLFxyXG4gICAgICB2aXNpYmlsaXR5VGltZW91dDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoMTUpLCAvLyAxNSBtaW51dGVzIGZvciBsb25nLXJ1bm5pbmcgdGFza3NcclxuICAgICAgZGVhZExldHRlclF1ZXVlOiB7XHJcbiAgICAgICAgcXVldWU6IGRlYWRMZXR0ZXJRdWV1ZSxcclxuICAgICAgICBtYXhSZWNlaXZlQ291bnQ6IDMsXHJcbiAgICAgIH0sXHJcbiAgICAgIHJlY2VpdmVNZXNzYWdlV2FpdFRpbWU6IGNkay5EdXJhdGlvbi5zZWNvbmRzKDIwKSwgLy8gTG9uZyBwb2xsaW5nXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBSRFMgQXVyb3JhIFNlcnZlcmxlc3MgdjIgUG9zdGdyZVNRTFxyXG4gICAgY29uc3QgZGJDbHVzdGVyID0gbmV3IHJkcy5EYXRhYmFzZUNsdXN0ZXIodGhpcywgJ0pvYlF1ZXVlRGF0YWJhc2UnLCB7XHJcbiAgICAgIGVuZ2luZTogcmRzLkRhdGFiYXNlQ2x1c3RlckVuZ2luZS5hdXJvcmFQb3N0Z3Jlcyh7XHJcbiAgICAgICAgdmVyc2lvbjogcmRzLkF1cm9yYVBvc3RncmVzRW5naW5lVmVyc2lvbi5WRVJfMTRfNyxcclxuICAgICAgfSksXHJcbiAgICAgIGNyZWRlbnRpYWxzOiByZHMuQ3JlZGVudGlhbHMuZnJvbUdlbmVyYXRlZFNlY3JldCgnam9icXVldWVfYWRtaW4nLCB7XHJcbiAgICAgICAgc2VjcmV0TmFtZTogYGpvYi1xdWV1ZS1kYi1jcmVkZW50aWFscy0ke2Vudmlyb25tZW50fWAsXHJcbiAgICAgIH0pLFxyXG4gICAgICBzZXJ2ZXJsZXNzVjJNaW5DYXBhY2l0eTogMC41LFxyXG4gICAgICBzZXJ2ZXJsZXNzVjJNYXhDYXBhY2l0eTogNCxcclxuICAgICAgd3JpdGVyOiByZHMuQ2x1c3Rlckluc3RhbmNlLnNlcnZlcmxlc3NWMignd3JpdGVyJyksXHJcbiAgICAgIHZwYyxcclxuICAgICAgdnBjU3VibmV0czoge1xyXG4gICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfSVNPTEFURUQsXHJcbiAgICAgIH0sXHJcbiAgICAgIHNlY3VyaXR5R3JvdXBzOiBbcmRzU2VjdXJpdHlHcm91cF0sXHJcbiAgICAgIGRlZmF1bHREYXRhYmFzZU5hbWU6ICdqb2JxdWV1ZScsXHJcbiAgICAgIGRlbGV0aW9uUHJvdGVjdGlvbjogZW52aXJvbm1lbnQgPT09ICdwcm9kdWN0aW9uJyxcclxuICAgICAgYmFja3VwOiB7XHJcbiAgICAgICAgcmV0ZW50aW9uOiBlbnZpcm9ubWVudCA9PT0gJ3Byb2R1Y3Rpb24nIFxyXG4gICAgICAgICAgPyBjZGsuRHVyYXRpb24uZGF5cyg3KSBcclxuICAgICAgICAgIDogY2RrLkR1cmF0aW9uLmRheXMoMSksXHJcbiAgICAgIH0sXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBMYW1iZGEgRXhlY3V0aW9uIFJvbGVcclxuICAgIGNvbnN0IGxhbWJkYVJvbGUgPSBuZXcgaWFtLlJvbGUodGhpcywgJ0xhbWJkYUV4ZWN1dGlvblJvbGUnLCB7XHJcbiAgICAgIGFzc3VtZWRCeTogbmV3IGlhbS5TZXJ2aWNlUHJpbmNpcGFsKCdsYW1iZGEuYW1hem9uYXdzLmNvbScpLFxyXG4gICAgICBtYW5hZ2VkUG9saWNpZXM6IFtcclxuICAgICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ3NlcnZpY2Utcm9sZS9BV1NMYW1iZGFCYXNpY0V4ZWN1dGlvblJvbGUnKSxcclxuICAgICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ3NlcnZpY2Utcm9sZS9BV1NMYW1iZGFWUENBY2Nlc3NFeGVjdXRpb25Sb2xlJyksXHJcbiAgICAgIF0sXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBBbGxvdyBMYW1iZGEgdG8gYWNjZXNzIFNRU1xyXG4gICAgdGFza1F1ZXVlLmdyYW50Q29uc3VtZU1lc3NhZ2VzKGxhbWJkYVJvbGUpO1xyXG4gICAgZGVhZExldHRlclF1ZXVlLmdyYW50Q29uc3VtZU1lc3NhZ2VzKGxhbWJkYVJvbGUpO1xyXG5cclxuICAgIC8vIEFsbG93IExhbWJkYSB0byBhY2Nlc3MgUkRTIGNyZWRlbnRpYWxzIGZyb20gU2VjcmV0cyBNYW5hZ2VyXHJcbiAgICBkYkNsdXN0ZXIuc2VjcmV0Py5ncmFudFJlYWQobGFtYmRhUm9sZSk7XHJcblxyXG4gICAgLy8gQVBJIExhbWJkYSBGdW5jdGlvblxyXG4gICAgY29uc3QgbG9nR3JvdXAgPSBuZXcgbG9ncy5Mb2dHcm91cCh0aGlzLCAnSm9iUXVldWVBcGlMYW1iZGFMb2dHcm91cCcsIHtcclxuICAgICAgcmV0ZW50aW9uOiBsb2dzLlJldGVudGlvbkRheXMuT05FX1dFRUssXHJcbiAgICB9KTtcclxuXHJcbiAgICBjb25zdCBhcGlMYW1iZGEgPSBuZXcgbGFtYmRhLkZ1bmN0aW9uKHRoaXMsICdKb2JRdWV1ZUFwaUxhbWJkYScsIHtcclxuICAgICAgZnVuY3Rpb25OYW1lOiBgam9iLXF1ZXVlLWFwaS0ke2Vudmlyb25tZW50fWAsXHJcbiAgICAgIHJ1bnRpbWU6IGxhbWJkYS5SdW50aW1lLlBZVEhPTl8zXzExLFxyXG4gICAgICBoYW5kbGVyOiAnbGFtYmRhX2hhbmRsZXIubGFtYmRhX2hhbmRsZXInLFxyXG4gICAgICBjb2RlOiBsYW1iZGEuQ29kZS5mcm9tQXNzZXQoJy4uLy4uL2JhY2tlbmQnKSwgLy8gQmFja2VuZCBhcHBsaWNhdGlvbiBjb2RlXHJcbiAgICAgIHZwYyxcclxuICAgICAgdnBjU3VibmV0czoge1xyXG4gICAgICAgIHN1Ym5ldFR5cGU6IGVjMi5TdWJuZXRUeXBlLlBSSVZBVEVfV0lUSF9FR1JFU1MsXHJcbiAgICAgIH0sXHJcbiAgICAgIHNlY3VyaXR5R3JvdXBzOiBbbGFtYmRhU2VjdXJpdHlHcm91cF0sXHJcbiAgICAgIHJvbGU6IGxhbWJkYVJvbGUsXHJcbiAgICAgIHRpbWVvdXQ6IGNkay5EdXJhdGlvbi5zZWNvbmRzKDMwKSxcclxuICAgICAgbWVtb3J5U2l6ZTogNTEyLFxyXG4gICAgICBlbnZpcm9ubWVudDoge1xyXG4gICAgICAgIERCX0hPU1Q6IGRiQ2x1c3Rlci5jbHVzdGVyRW5kcG9pbnQuaG9zdG5hbWUsXHJcbiAgICAgICAgREJfUE9SVDogJzU0MzInLFxyXG4gICAgICAgIERCX05BTUU6ICdqb2JxdWV1ZScsXHJcbiAgICAgICAgREJfVVNFUjogJ2pvYnF1ZXVlX2FkbWluJyxcclxuICAgICAgICBEQl9TRUNSRVRfQVJOOiBkYkNsdXN0ZXIuc2VjcmV0Py5zZWNyZXRBcm4gfHwgJycsXHJcbiAgICAgICAgU1FTX1FVRVVFX1VSTDogdGFza1F1ZXVlLnF1ZXVlVXJsLFxyXG4gICAgICAgIFNRU19ETFFfVVJMOiBkZWFkTGV0dGVyUXVldWUucXVldWVVcmwsXHJcbiAgICAgICAgRU5WSVJPTk1FTlQ6IGVudmlyb25tZW50LFxyXG4gICAgICB9LFxyXG4gICAgICBsb2dHcm91cDogbG9nR3JvdXAsXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBXb3JrZXIgTGFtYmRhIEZ1bmN0aW9uXHJcbiAgICBjb25zdCB3b3JrZXJMYW1iZGEgPSBuZXcgbGFtYmRhLkZ1bmN0aW9uKHRoaXMsICdKb2JRdWV1ZVdvcmtlckxhbWJkYScsIHtcclxuICAgICAgZnVuY3Rpb25OYW1lOiBgam9iLXF1ZXVlLXdvcmtlci0ke2Vudmlyb25tZW50fWAsXHJcbiAgICAgIHJ1bnRpbWU6IGxhbWJkYS5SdW50aW1lLlBZVEhPTl8zXzExLFxyXG4gICAgICBoYW5kbGVyOiAnbGFtYmRhX2hhbmRsZXIubGFtYmRhX2hhbmRsZXInLFxyXG4gICAgICBjb2RlOiBsYW1iZGEuQ29kZS5mcm9tQXNzZXQoJy4uLy4uL3dvcmtlcicpLCAvLyBXb3JrZXIgYXBwbGljYXRpb24gY29kZVxyXG4gICAgICB2cGMsXHJcbiAgICAgIHZwY1N1Ym5ldHM6IHtcclxuICAgICAgICBzdWJuZXRUeXBlOiBlYzIuU3VibmV0VHlwZS5QUklWQVRFX1dJVEhfRUdSRVNTLFxyXG4gICAgICB9LFxyXG4gICAgICBzZWN1cml0eUdyb3VwczogW2xhbWJkYVNlY3VyaXR5R3JvdXBdLFxyXG4gICAgICByb2xlOiBsYW1iZGFSb2xlLFxyXG4gICAgICB0aW1lb3V0OiBjZGsuRHVyYXRpb24ubWludXRlcygxNSksIC8vIExvbmcgdGltZW91dCBmb3IgdGFzayBwcm9jZXNzaW5nXHJcbiAgICAgIG1lbW9yeVNpemU6IDEwMjQsXHJcbiAgICAgIGVudmlyb25tZW50OiB7XHJcbiAgICAgICAgREJfSE9TVDogZGJDbHVzdGVyLmNsdXN0ZXJFbmRwb2ludC5ob3N0bmFtZSxcclxuICAgICAgICBEQl9QT1JUOiAnNTQzMicsXHJcbiAgICAgICAgREJfTkFNRTogJ2pvYnF1ZXVlJyxcclxuICAgICAgICBEQl9VU0VSOiAnam9icXVldWVfYWRtaW4nLFxyXG4gICAgICAgIERCX1NFQ1JFVF9BUk46IGRiQ2x1c3Rlci5zZWNyZXQ/LnNlY3JldEFybiB8fCAnJyxcclxuICAgICAgICBTUVNfUVVFVUVfVVJMOiB0YXNrUXVldWUucXVldWVVcmwsXHJcbiAgICAgICAgU1FTX0RMUV9VUkw6IGRlYWRMZXR0ZXJRdWV1ZS5xdWV1ZVVybCxcclxuICAgICAgICBFTlZJUk9OTUVOVDogZW52aXJvbm1lbnQsXHJcbiAgICAgIH0sXHJcbiAgICAgIGxvZ0dyb3VwOiBsb2dHcm91cCxcclxuICAgIH0pO1xyXG5cclxuICAgIC8vIFNRUyBFdmVudCBTb3VyY2UgZm9yIFdvcmtlciBMYW1iZGFcclxuICAgIHdvcmtlckxhbWJkYS5hZGRFdmVudFNvdXJjZShcclxuICAgICAgbmV3IGV2ZW50cy5TcXNFdmVudFNvdXJjZSh0YXNrUXVldWUsIHtcclxuICAgICAgICBiYXRjaFNpemU6IDUsIC8vIFByb2Nlc3MgdXAgdG8gNSBtZXNzYWdlcyBhdCBvbmNlXHJcbiAgICAgICAgbWF4QmF0Y2hpbmdXaW5kb3c6IGNkay5EdXJhdGlvbi5zZWNvbmRzKDEwKSxcclxuICAgICAgICByZXBvcnRCYXRjaEl0ZW1GYWlsdXJlczogdHJ1ZSxcclxuICAgICAgfSlcclxuICAgICk7XHJcblxyXG4gICAgLy8gQVBJIEdhdGV3YXlcclxuICAgIGNvbnN0IGFwaSA9IG5ldyBhcGlnYXRld2F5LkxhbWJkYVJlc3RBcGkodGhpcywgJ0pvYlF1ZXVlQXBpJywge1xyXG4gICAgICBoYW5kbGVyOiBhcGlMYW1iZGEsXHJcbiAgICAgIHJlc3RBcGlOYW1lOiBgam9iLXF1ZXVlLWFwaS0ke2Vudmlyb25tZW50fWAsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiBgSm9iIFF1ZXVlIFN5c3RlbSBBUEkgLSAke2Vudmlyb25tZW50fWAsXHJcbiAgICAgIGRlcGxveU9wdGlvbnM6IHtcclxuICAgICAgICBzdGFnZU5hbWU6IGVudmlyb25tZW50LFxyXG4gICAgICAgIGxvZ2dpbmdMZXZlbDogYXBpZ2F0ZXdheS5NZXRob2RMb2dnaW5nTGV2ZWwuSU5GTyxcclxuICAgICAgICBkYXRhVHJhY2VFbmFibGVkOiB0cnVlLFxyXG4gICAgICB9LFxyXG4gICAgICBkZWZhdWx0Q29yc1ByZWZsaWdodE9wdGlvbnM6IHtcclxuICAgICAgICBhbGxvd09yaWdpbnM6IGFwaWdhdGV3YXkuQ29ycy5BTExfT1JJR0lOUyxcclxuICAgICAgICBhbGxvd01ldGhvZHM6IGFwaWdhdGV3YXkuQ29ycy5BTExfTUVUSE9EUyxcclxuICAgICAgICBhbGxvd0hlYWRlcnM6IFtcclxuICAgICAgICAgICdDb250ZW50LVR5cGUnLFxyXG4gICAgICAgICAgJ1gtQW16LURhdGUnLFxyXG4gICAgICAgICAgJ0F1dGhvcml6YXRpb24nLFxyXG4gICAgICAgICAgJ1gtQXBpLUtleScsXHJcbiAgICAgICAgICAnWC1BbXotU2VjdXJpdHktVG9rZW4nLFxyXG4gICAgICAgIF0sXHJcbiAgICAgIH0sXHJcbiAgICB9KTtcclxuXHJcbiAgICAvLyBPdXRwdXRzXHJcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnQXBpR2F0ZXdheVVybCcsIHtcclxuICAgICAgdmFsdWU6IGFwaS51cmwsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnQVBJIEdhdGV3YXkgVVJMJyxcclxuICAgIH0pO1xyXG5cclxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdUYXNrUXVldWVVcmwnLCB7XHJcbiAgICAgIHZhbHVlOiB0YXNrUXVldWUucXVldWVVcmwsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnU1FTIFRhc2sgUXVldWUgVVJMJyxcclxuICAgIH0pO1xyXG5cclxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdEZWFkTGV0dGVyUXVldWVVcmwnLCB7XHJcbiAgICAgIHZhbHVlOiBkZWFkTGV0dGVyUXVldWUucXVldWVVcmwsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnU1FTIERlYWQgTGV0dGVyIFF1ZXVlIFVSTCcsXHJcbiAgICB9KTtcclxuXHJcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnRGF0YWJhc2VFbmRwb2ludCcsIHtcclxuICAgICAgdmFsdWU6IGRiQ2x1c3Rlci5jbHVzdGVyRW5kcG9pbnQuaG9zdG5hbWUsXHJcbiAgICAgIGRlc2NyaXB0aW9uOiAnUkRTIENsdXN0ZXIgRW5kcG9pbnQnLFxyXG4gICAgfSk7XHJcblxyXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0RhdGFiYXNlU2VjcmV0QXJuJywge1xyXG4gICAgICB2YWx1ZTogZGJDbHVzdGVyLnNlY3JldD8uc2VjcmV0QXJuIHx8ICdOb3QgYXZhaWxhYmxlJyxcclxuICAgICAgZGVzY3JpcHRpb246ICdEYXRhYmFzZSBjcmVkZW50aWFscyBzZWNyZXQgQVJOJyxcclxuICAgIH0pO1xyXG4gIH1cclxufSJdfQ==