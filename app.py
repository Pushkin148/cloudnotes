from flask import Flask, request, render_template_string, redirect, url_for
import boto3
import os

app = Flask(__name__)

S3_BUCKET = "cloudnotes-bucket-pushkin"
s3_client = boto3.client("s3")

# HTML template
UPLOAD_FORM = """
<!doctype html>
<title>CloudNotes</title>
<h1>Upload a File to CloudNotes</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <input type=submit value=Upload>
</form>
<p>{{ message }}</p>

<h2>Files in CloudNotes</h2>
<ul>
{% for file in files %}
  <li>
    {{ file }}
    - <a href="{{ url_for('download_file', filename=file) }}">Download</a>
  </li>
{% endfor %}
</ul>
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

    # Fetch file list from S3
    files = []
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        if "Contents" in response:
            files = [obj["Key"] for obj in response["Contents"]]
    except Exception as e:
        message += f" (Error listing files: {e})"

    return render_template_string(UPLOAD_FORM, message=message, files=files)

@app.route("/download/<filename>")
def download_file(filename):
    try:
        # Generate a pre-signed URL for downloading with forced attachment
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': filename,
                'ResponseContentDisposition': f'attachment; filename="{filename}"'
            },
            ExpiresIn=60  # URL valid for 60 seconds
        )
        return redirect(url)
    except Exception as e:
        return f"❌ Download failed: {e}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)


