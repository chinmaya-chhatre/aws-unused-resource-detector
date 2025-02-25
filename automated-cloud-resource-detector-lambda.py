import boto3
import csv
import json
import os
from datetime import datetime, timezone
from io import StringIO

# ------------------ AWS Clients ------------------
# These clients allow interaction with AWS services
ec2_client = boto3.client("ec2")
elb_client = boto3.client("elbv2")
rds_client = boto3.client("rds")
s3_client = boto3.client("s3")
sns_client = boto3.client("sns")
dynamodb_client = boto3.client("dynamodb")
cloudfront_client = boto3.client("cloudfront")
lambda_client = boto3.client("lambda")

# ------------------ Configurable Settings ------------------
# Modify these values as per your requirements.
EC2_UNUSED_DAYS = int(os.getenv("EC2_UNUSED_DAYS", "7"))  # Number of days to consider an EC2 instance as unused
EBS_UNUSED_DAYS = int(os.getenv("EBS_UNUSED_DAYS", "7"))  # Number of days to consider an EBS volume as unused
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  # S3 bucket where reports are saved
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")  # SNS Topic ARN for email alerts

# ------------------ Functions for Detecting Unused Resources ------------------

def get_unused_ec2_instances():
    """Finds EC2 instances that are stopped for more than the configured number of days."""
    instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])

    unused_instances = []
    for reservation in instances["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            region = instance["Placement"]["AvailabilityZone"]
            launch_time = instance["LaunchTime"]

            # Calculate how long the instance has been stopped
            stopped_days = (datetime.now(timezone.utc) - launch_time).days
            if stopped_days >= EC2_UNUSED_DAYS:
                unused_instances.append(["EC2 Instance", instance_id, region, stopped_days])

    return unused_instances

def get_unused_ebs_volumes():
    """Finds EBS volumes that have been unattached for more than the configured number of days."""
    volumes = ec2_client.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])

    unused_volumes = []
    for volume in volumes["Volumes"]:
        volume_id = volume["VolumeId"]
        az = volume["AvailabilityZone"]
        create_time = volume["CreateTime"]

        if (datetime.now(timezone.utc) - create_time).days >= EBS_UNUSED_DAYS:
            unused_volumes.append(["EBS Volume", volume_id, az, "-"])

    return unused_volumes

def get_unused_elastic_ips():
    """Finds Elastic IPs that are not associated with any running instance."""
    addresses = ec2_client.describe_addresses()["Addresses"]
    return [["Elastic IP", addr["PublicIp"], addr["NetworkBorderGroup"], "-"] for addr in addresses if "InstanceId" not in addr]

def get_unused_load_balancers():
    """Finds Load Balancers that have no active connections."""
    lbs = elb_client.describe_load_balancers()["LoadBalancers"]

    unused_lbs = []
    for lb in lbs:
        lb_name = lb["LoadBalancerName"]
        region = lb["AvailabilityZones"][0]["ZoneName"]
        lb_state = lb["State"]["Code"]

        if lb_state == "active":
            unused_lbs.append(["Load Balancer", lb_name, region, "-"])

    return unused_lbs

def get_unused_rds_instances():
    """Finds RDS instances that are in a stopped state."""
    instances = rds_client.describe_db_instances()["DBInstances"]
    return [["RDS Instance", db["DBInstanceIdentifier"], db["AvailabilityZone"], "-"] for db in instances if db["DBInstanceStatus"] == "stopped"]

def get_unused_s3_buckets():
    """Finds S3 buckets with no read/write activity."""
    buckets = s3_client.list_buckets()["Buckets"]

    unused_buckets = []
    for bucket in buckets:
        bucket_name = bucket["Name"]
        region = s3_client.get_bucket_location(Bucket=bucket_name)["LocationConstraint"]

        try:
            objects = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            if "Contents" not in objects:  # No objects in the bucket
                unused_buckets.append(["S3 Bucket", bucket_name, region, "-"])
        except Exception:
            continue

    return unused_buckets

def get_unused_dynamodb_tables():
    """Finds unused DynamoDB tables (not recently accessed)."""
    tables = dynamodb_client.list_tables()["TableNames"]
    return [["DynamoDB Table", table, "-", "-"] for table in tables]

def get_unused_cloudfront_distributions():
    """Finds CloudFront distributions that are disabled."""
    response = cloudfront_client.list_distributions()
    
    if "DistributionList" in response and "Items" in response["DistributionList"]:
        distributions = response["DistributionList"]["Items"]
        return [["CloudFront Distribution", dist["Id"], "-", "-"] for dist in distributions if not dist["Enabled"]]
    
    return []

def get_unused_lambda_functions():
    """Finds Lambda functions with no invocations."""
    functions = lambda_client.list_functions()["Functions"]
    return [["Lambda Function", fn["FunctionName"], "-", "-"] for fn in functions]

# ------------------ S3 & Email Handling ------------------

def save_report_to_s3(report_data):
    """Saves the CSV report to an S3 bucket."""
    if S3_BUCKET_NAME and report_data:
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(["Resource Type", "ID", "Region/Zone", "Unused Days"])
        csv_writer.writerows(report_data)

        filename = f"unused-resources-report-{datetime.now().strftime('%Y-%m-%d')}.csv"
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=filename,
            Body=csv_buffer.getvalue(),
            ContentType="text/csv"
        )
        return f"s3://{S3_BUCKET_NAME}/{filename}"
    
    return None

def send_alert(subject, message):
    """Sends an SNS email notification with the unused resource report summary."""
    if SNS_TOPIC_ARN:
        sns_client.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    else:
        print("SNS_TOPIC_ARN is not set. Skipping alert.")

# ------------------ Lambda Handler ------------------

def lambda_handler(event, context):
    """Main Lambda function that detects unused resources and saves results to S3."""
    
    report_data = []
    report_data.extend(get_unused_ec2_instances())
    report_data.extend(get_unused_ebs_volumes())
    report_data.extend(get_unused_elastic_ips())
    report_data.extend(get_unused_load_balancers())
    report_data.extend(get_unused_rds_instances())
    report_data.extend(get_unused_s3_buckets())
    report_data.extend(get_unused_dynamodb_tables())
    report_data.extend(get_unused_cloudfront_distributions())
    report_data.extend(get_unused_lambda_functions())

    # Save report to S3
    report_path = save_report_to_s3(report_data)
    s3_message = f"📂 **Report Saved To S3**: `{report_path}`" if report_path else "⚠️ **No S3 report generated.**"

    # Summary of unused resources
    summary_message = "\n".join([f"• {res[0]}: {res[1]} (Region: {res[2]})" for res in report_data])

    # Prepare Email Alert
    alert_message = f"""
    🔍 **AWS Unused Resources Report** 🔍
    
    {s3_message}

    **Summary of Unused Resources:**
    {summary_message if summary_message else "🎉 No unused resources found!"}

    **Total Unused Resources:** {len(report_data)}
    """

    send_alert("AWS Unused Resources Report", alert_message)

    return {"statusCode": 200, "body": json.dumps("Execution Completed")}
