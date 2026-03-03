#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { JobQueueStack } from './lib/job-queue-stack';

const app = new cdk.App();

const environment = process.env.ENVIRONMENT || 'staging';
const account = process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID;
const region = process.env.CDK_DEFAULT_REGION || process.env.AWS_DEFAULT_REGION || 'us-east-1';

if (!account) {
  throw new Error('AWS Account ID is required. Set CDK_DEFAULT_ACCOUNT or AWS_ACCOUNT_ID environment variable.');
}

new JobQueueStack(app, `JobQueueStack-${environment}`, {
  env: {
    account: account,
    region: region,
  },
  tags: {
    Environment: environment,
    Project: 'JobQueueSystem',
  },
});