#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { JobQueueStack } from './lib/job-queue-stack';

const app = new cdk.App();

const environment = process.env.ENVIRONMENT || 'staging';
const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

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