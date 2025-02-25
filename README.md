# AWS Unused Resource Detector (Lambda)

## 📌 Overview
This AWS Lambda function **automatically detects unused AWS resources** to help optimize cloud costs. It scans for unused:
- **EC2 Instances** (Stopped for X days)
- **EBS Volumes** (Unattached for X days)
- **Elastic IPs** (Not associated with any instance)
- **Load Balancers** (No active connections)
- **RDS Instances** (Stopped)
- **S3 Buckets** (No read/write activity)
- **DynamoDB Tables** (No recent access)
- **CloudFront Distributions** (Disabled)
- **Lambda Functions** (No invocations for X days)

The function **sends an email summary via SNS** and **stores a detailed CSV report in S3** for historical tracking.

---

## 🚀 **Deployment Steps**
Follow these steps to deploy the Lambda function.

### **1️⃣ Create an S3 Bucket**
This bucket will store the CSV reports of unused resources.
1. Go to **AWS Console → S3**  
2. Click **"Create bucket"**  
3. Set a **unique bucket name** (e.g., `unused-resources-reports`)  
4. Select a **region**  
5. Click **"Create bucket"**

---

### **2️⃣ Create an SNS Topic for Email Alerts**
1. Go to **AWS Console → SNS**  
2. Click **"Create topic"**  
3. Select **"Standard"**  
4. Name it (e.g., `UnusedResourceAlerts`) 
5. Click **"Create topic"**  
6. Copy the **SNS Topic ARN** (you’ll need it later)  
7. Click **"Create subscription"**
   - **Protocol:** Email  
   - **Endpoint:** Your email address  
8. **Check your email** and confirm the subscription.

---

### **3️⃣ Create the IAM Role for Lambda**
1. Go to **AWS Console → IAM → Roles**  
2. Click **"Create role"**  
3. **Choose a trusted entity:** Select **Lambda**  
4. Click **"Next"**  
5. **Attach permissions:** Click **"Create inline policy"**  
6. **Select "JSON" tab** and **paste** the code from iam-permissions.json file in this repository.
7. Click **"Next" → "Review"**  
8. Name the policy: **`UnusedResourceReadAccess`**  
9. Click **"Create policy"**  
10. Go back to **IAM Role Creation**, attach this policy, and **create the role**  
11. Copy the **IAM Role ARN** for the next step.

---

### **4️⃣ Deploy the Lambda Function**
1. Go to **AWS Console → Lambda**
2. Click **"Create function"**  
3. **Choose "Author from scratch"**  
4. **Function name:** `Automated-Cloud-Resource-Detector-Lambda`
5. **Runtime:** Python 3.x  
6. **Execution role:** Choose **"Use an existing role"**  
7. **Select the IAM Role** created earlier  
8. Click **"Create function"**  
9. Copy & Paste the `lambda_function.py` code into the editor  
10. Click **"Deploy"**

---

### **5️⃣ Set Environment Variables**
1. Go to **Lambda → Your Function → Configuration → Environment Variables**  
2. Click **"Edit" → "Add Environment Variable"**  
3. Add the following variables:
   - `EC2_UNUSED_DAYS` = `7` *(Modify if needed)*
   - `EBS_UNUSED_DAYS` = `7` *(Modify if needed)*
   - `S3_BUCKET_NAME` = `unused-resources-reports` *(Use the bucket you created)*
   - `SNS_TOPIC_ARN` = *(Paste your SNS Topic ARN)*
4. Click **"Save"**

---

### **6️⃣ Set Up an EventBridge Trigger (Automated Execution)**
1. Go to **AWS Console → EventBridge → Rules**
2. Click **"Create Rule"**
3. **Rule Name:** `UnusedResourceScheduler`
4. **Define pattern:** Select **"Schedule"**
5. **Cron expression:**  
   ```
   cron(0 7 * * ? *)  # Runs every day at 2 AM ET (7 AM UTC)
   ```
6. **Select Target:** Lambda function  
7. Choose your function: `Automated-Cloud-Resource-Detector-Lambda`
8. Click **"Create Rule"**

---

## ✅ **Testing the Lambda Function**
### **🔹 Test Manually**
1. Go to **AWS Lambda → Your Function**
2. Click **"Test"**
3. **Event Name:** `ManualTest`
4. **Event JSON:**
```
{
    "manual": true
}
```
5. Click **"Test"**
6. ✅ If successful, you will:
   - Receive an **SNS email** with the report summary
   - Find the CSV report in **S3**

---

## 📂 **Expected Output**
### **🔹 SNS Email Example**
```
🔍 AWS Unused Resources Report

📂 Report Saved To S3: s3://unused-resources-reports/unused-resources-report-2024-02-25.csv

Summary of Unused Resources:
• EC2 Instance: i-0123abcd (Region: us-east-1)
• S3 Bucket: old-bucket-name (Region: us-west-2)
• RDS Instance: db-unused-123 (Region: us-east-1)

Total Unused Resources: 3
```

---

## 🛠 **Customization Guide**
| **Setting**       | **Environment Variable** | **Default Value** | **How to Modify** |
|-------------------|------------------------|-------------------|-------------------|
| Unused EC2 Days  | `EC2_UNUSED_DAYS`       | `7`               | Change in Lambda Env Vars |
| Unused EBS Days  | `EBS_UNUSED_DAYS`       | `7`               | Change in Lambda Env Vars |
| S3 Bucket Name   | `S3_BUCKET_NAME`        | `unused-resources-reports` | Change in Lambda Env Vars |
| SNS Topic ARN    | `SNS_TOPIC_ARN`         | (Your ARN)        | Change in Lambda Env Vars |

---

## 📌 **License**
This project is licensed under the MIT License.

---

🚀 **Congratulations! Your AWS Unused Resource Detector is now fully set up and automated!** 
