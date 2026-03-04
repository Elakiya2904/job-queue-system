import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as events from 'aws-cdk-lib/aws-lambda-event-sources';
import { Construct } from 'constructs';
import { IpAddresses } from 'aws-cdk-lib/aws-ec2';
import * as path from 'path';

export class JobQueueStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const environment = process.env.ENVIRONMENT || 'staging';

    // VPC for RDS and Lambda
    const vpc = new ec2.Vpc(this, 'JobQueueVPC', {
      ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
      maxAzs: 2,
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
    rdsSecurityGroup.addIngressRule(
      ec2.Peer.securityGroupId(lambdaSecurityGroup.securityGroupId),
      ec2.Port.tcp(5432),
      'Allow Lambda access to PostgreSQL'
    );

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
    const logGroup = new logs.LogGroup(this, 'JobQueueApiLambdaLogGroup', {
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const apiLambda = new lambda.Function(this, 'JobQueueApiLambda', {
      functionName: `job-queue-api-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'backend')),
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
      logGroup: logGroup,
    });

    // Worker Lambda Function
    const workerLambda = new lambda.Function(this, 'JobQueueWorkerLambda', {
      functionName: `job-queue-worker-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'worker')),
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
    workerLambda.addEventSource(
      new events.SqsEventSource(taskQueue, {
        batchSize: 5, // Process up to 5 messages at once
        maxBatchingWindow: cdk.Duration.seconds(10),
        reportBatchItemFailures: true,
      })
    );

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