import boto3
import shutil
import os
import subprocess
import uuid
from datetime import datetime

access_key=""
secret_access_key=""
s3 = boto3.client(
    's3',
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_access_key,
    region_name='ap-south-1'
)

# Update these
OUTPUT_BUCKET = "wilidlife-watch-output-bucket"

input_bucket = "wildlife-watch-input-bucket"
key = "tiger-camera-trap.jpg"

if not input_bucket or not key:
    print("Missing bucket or key")

tmp_id = uuid.uuid4().hex
input_path = f"/tmp/{tmp_id}_{os.path.basename(key)}"
output_dir = f"runs/detect/tiger_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

try:
    # Download image from S3
    s3.download_file(input_bucket, key, input_path)
    print("image downloaded")

    # Run YOLOv5 inference
    subprocess.run([
        "python", "detect.py",
        "--weights", "best.pt",
        "--img", "640",
        "--conf", "0.25",
        "--source", input_path,
        "--project", "runs/detect",
        "--name", os.path.basename(output_dir),
        "--exist-ok",
        "--save-txt",
        "--save-conf"
    ], check=True)

    # Upload results to S3
    full_out_dir = os.path.join("runs/detect", os.path.basename(output_dir))
    uploaded_files = []

    for f in os.listdir(full_out_dir):
        if f.endswith((".jpg", ".txt")):
            local_file = os.path.join(full_out_dir, f)
            s3_key = f"{os.path.splitext(key)[0]}_output/{f}"
            s3.upload_file(local_file, OUTPUT_BUCKET, s3_key)
            uploaded_files.append(f"s3://{OUTPUT_BUCKET}/{s3_key}")

    print("file uploaded")


    # Clean up
    if os.path.exists(input_path):
        os.remove(input_path)
    if os.path.exists(full_out_dir):
        shutil.rmtree(full_out_dir)

    print("local files cleaned up")

except Exception as e:
    print("error", str(e))