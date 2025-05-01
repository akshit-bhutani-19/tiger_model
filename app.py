from flask import Flask, request, jsonify
import boto3
import shutil
import os
import subprocess
import uuid
from datetime import datetime

app = Flask(__name__)
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

@app.route("/", methods=["GET"])
def home():
    return "🐅 Tiger Detection API is running!", 200

@app.route("/predict", methods=["POST"])
def predict():
    try:
        print("Received request")
        data = request.get_json()
        input_bucket = data.get("bucket")
        key = data.get("key")
        print(f"Input bucket: {input_bucket}, key: {key}")
    except Exception as e:
        return jsonify({"error": "Invalid JSON format"}), 400

    if not input_bucket or not key:
        return jsonify({"error": "Missing bucket or key"}), 400

    tmp_id = uuid.uuid4().hex
    input_path = f"/tmp/{tmp_id}_{os.path.basename(key)}"
    output_dir = f"runs/detect/tiger_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Temporary input path: {input_path}, output dir: {output_dir}")

    try:
        # Download image from S3
        s3.download_file(input_bucket, key, input_path)
        print(f"Downloaded {key} from {input_bucket} to {input_path}")

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

        print(f"YOLOv5 inference completed, results saved to {output_dir}")

        # Upload results to S3
        full_out_dir = os.path.join("runs/detect", os.path.basename(output_dir))
        uploaded_files = []
        detection_found = False

        for f in os.listdir(full_out_dir):
            if f.endswith(".txt"):
                txt_path = os.path.join(full_out_dir, f)
                if os.path.getsize(txt_path) > 0:
                    detection_found = True
                    break  # no need to check more

        if detection_found:
            print("Detection found ✅ Uploading results to S3.")
            for f in os.listdir(full_out_dir):
                if f.endswith((".jpg", ".txt")):
                    local_file = os.path.join(full_out_dir, f)
                    s3_key = f"tiger/{f}"
                    s3.upload_file(local_file, OUTPUT_BUCKET, s3_key)
                    uploaded_files.append(f"s3://{OUTPUT_BUCKET}/{s3_key}")
        else:
            print("No detections found ❌ Skipping upload.")

        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(full_out_dir):
            shutil.rmtree(full_out_dir)

        return jsonify({
            "message": "Inference complete ✅",
            "results": uploaded_files
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)