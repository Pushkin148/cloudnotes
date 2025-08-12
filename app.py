from flask import Flask, request, render_template_string
import boto3
import os

app = Flask(__name__)


S3_BUCKET = "cloudnotes-bucket-pushkin"

# Initialize boto3 S3 client (will use EC2 IAM Role)
s3_client = boto3.client("s3")

# HTML 
UPLOAD_FORM = """
<!doctype html>
<title>Upload to CloudNotes</title>
<h1>Upload a File to CloudNotes</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <input type=submit value=Upload>
</form>
<p>{{ message }}</p>
"""

@app.route("/", methods=["GET", "POST"])
def upload_file():
    message = ""
    if request.method == "POST":
        if "file" not in request.files:
            message = "No file part"
        else:
            file = request.files["file"]
            if file.filename == "":
                message = "No file selected"
            else:
                try:
                    s3_client.upload_fileobj(file, S3_BUCKET, file.filename)
                    message = f"✅ Uploaded {file.filename} to S3 bucket {S3_BUCKET}"
                except Exception as e:
                    message = f"❌ Upload failed: {e}"
    return render_template_string(UPLOAD_FORM, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)

