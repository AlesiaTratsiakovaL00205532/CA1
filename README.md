# CloudFormation Lab

## Overview

This project uses AWS CloudFormation to provision:
1. A public-facing Apache website on EC2, with static content stored in S3.
2. A separate three-tier architecture (planned).

## Static Website Architecture

Browser → EC2 / Apache → local copy of website content
Private S3 bucket → EC2 downloads index.html using an instance role

The template configures a systemd timer to download index.html approximately every minute. A successful download replaces the served page.

## Environment Constraints

The AWS Academy sandbox prohibits creating IAM roles.
The template therefore uses the pre-provisioned LabInstanceProfile.
Its permissions are controlled by the lab, rather than scoped by this template.

The current template requires a default VPC and internet connectivity.
The website currently uses HTTP, not HTTPS.

## Progress and Evidence

The initial website was deployed and displayed the required header after a manual download from S3.

Automatic content download has been added to the template.
End-to-end verification of this version is pending.

## References

- AWS — Creating your first stack:
  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.walkthrough.html
  Starting point for the EC2, security group, and Apache configuration.

- AWS — Amazon S3 template snippets:
  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/quickref-s3.html
  Starting point for the S3 bucket definition.

- AWS — IAM role resource:
  https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-iam-role.html

- AWS — IAM instance profile resource:
  https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-iam-instanceprofile.html

## AI Assistance Disclosure

GitHub Copilot CLI was used for guided explanations and code suggestions.
The systemd download service and timer were AI-assisted adaptations,
not copied from the cited AWS templates.
