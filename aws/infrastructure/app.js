#!/usr/bin/env node
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
const cdk = __importStar(require("aws-cdk-lib"));
const job_queue_stack_1 = require("./lib/job-queue-stack");
const app = new cdk.App();
const environment = process.env.ENVIRONMENT || 'staging';
const account = process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID;
const region = process.env.CDK_DEFAULT_REGION || process.env.AWS_DEFAULT_REGION || 'us-east-1';
if (!account) {
    throw new Error('AWS Account ID is required. Set CDK_DEFAULT_ACCOUNT or AWS_ACCOUNT_ID environment variable.');
}
new job_queue_stack_1.JobQueueStack(app, `JobQueueStack-${environment}`, {
    env: {
        account: account,
        region: region,
    },
    tags: {
        Environment: environment,
        Project: 'JobQueueSystem',
    },
});
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYXBwLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiYXBwLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7OztBQUNBLGlEQUFtQztBQUNuQywyREFBc0Q7QUFFdEQsTUFBTSxHQUFHLEdBQUcsSUFBSSxHQUFHLENBQUMsR0FBRyxFQUFFLENBQUM7QUFFMUIsTUFBTSxXQUFXLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxXQUFXLElBQUksU0FBUyxDQUFDO0FBQ3pELE1BQU0sT0FBTyxHQUFHLE9BQU8sQ0FBQyxHQUFHLENBQUMsbUJBQW1CLElBQUksT0FBTyxDQUFDLEdBQUcsQ0FBQyxjQUFjLENBQUM7QUFDOUUsTUFBTSxNQUFNLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxrQkFBa0IsSUFBSSxPQUFPLENBQUMsR0FBRyxDQUFDLGtCQUFrQixJQUFJLFdBQVcsQ0FBQztBQUUvRixJQUFJLENBQUMsT0FBTyxFQUFFLENBQUM7SUFDYixNQUFNLElBQUksS0FBSyxDQUFDLDZGQUE2RixDQUFDLENBQUM7QUFDakgsQ0FBQztBQUVELElBQUksK0JBQWEsQ0FBQyxHQUFHLEVBQUUsaUJBQWlCLFdBQVcsRUFBRSxFQUFFO0lBQ3JELEdBQUcsRUFBRTtRQUNILE9BQU8sRUFBRSxPQUFPO1FBQ2hCLE1BQU0sRUFBRSxNQUFNO0tBQ2Y7SUFDRCxJQUFJLEVBQUU7UUFDSixXQUFXLEVBQUUsV0FBVztRQUN4QixPQUFPLEVBQUUsZ0JBQWdCO0tBQzFCO0NBQ0YsQ0FBQyxDQUFDIiwic291cmNlc0NvbnRlbnQiOlsiIyEvdXNyL2Jpbi9lbnYgbm9kZVxyXG5pbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xyXG5pbXBvcnQgeyBKb2JRdWV1ZVN0YWNrIH0gZnJvbSAnLi9saWIvam9iLXF1ZXVlLXN0YWNrJztcclxuXHJcbmNvbnN0IGFwcCA9IG5ldyBjZGsuQXBwKCk7XHJcblxyXG5jb25zdCBlbnZpcm9ubWVudCA9IHByb2Nlc3MuZW52LkVOVklST05NRU5UIHx8ICdzdGFnaW5nJztcclxuY29uc3QgYWNjb3VudCA9IHByb2Nlc3MuZW52LkNES19ERUZBVUxUX0FDQ09VTlQgfHwgcHJvY2Vzcy5lbnYuQVdTX0FDQ09VTlRfSUQ7XHJcbmNvbnN0IHJlZ2lvbiA9IHByb2Nlc3MuZW52LkNES19ERUZBVUxUX1JFR0lPTiB8fCBwcm9jZXNzLmVudi5BV1NfREVGQVVMVF9SRUdJT04gfHwgJ3VzLWVhc3QtMSc7XHJcblxyXG5pZiAoIWFjY291bnQpIHtcclxuICB0aHJvdyBuZXcgRXJyb3IoJ0FXUyBBY2NvdW50IElEIGlzIHJlcXVpcmVkLiBTZXQgQ0RLX0RFRkFVTFRfQUNDT1VOVCBvciBBV1NfQUNDT1VOVF9JRCBlbnZpcm9ubWVudCB2YXJpYWJsZS4nKTtcclxufVxyXG5cclxubmV3IEpvYlF1ZXVlU3RhY2soYXBwLCBgSm9iUXVldWVTdGFjay0ke2Vudmlyb25tZW50fWAsIHtcclxuICBlbnY6IHtcclxuICAgIGFjY291bnQ6IGFjY291bnQsXHJcbiAgICByZWdpb246IHJlZ2lvbixcclxuICB9LFxyXG4gIHRhZ3M6IHtcclxuICAgIEVudmlyb25tZW50OiBlbnZpcm9ubWVudCxcclxuICAgIFByb2plY3Q6ICdKb2JRdWV1ZVN5c3RlbScsXHJcbiAgfSxcclxufSk7Il19