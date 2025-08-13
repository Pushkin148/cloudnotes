from flask import Flask, request, render_template_string, redirect, url_for
import boto3
import uuid
import os
from datetime import datetime

app = Flask(__name__)

# AWS configuration
S3_BUCKET = "cloudnotes-bucket-pushkin"
DYNAMO_TABLE = "CloudNotesMetaData"
AWS_REGION = "us-east-1"

s3 = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMO_TABLE)

# Upload page template
UPLOAD_PAGE = """
<!doctype html>
<title>Upload File</title>
<h2>Upload File</h2>
<form method=post enctype=multipart/form-data>
  Student Name: <input type=text name=student_name required><br><br>
  Class: <input type=text name=class_name required><br><br>
  Teacher Name: <input type=text name=teacher_name required><br><br>
  <input type=file name=file required><br><br>
  <input type=submit value=Upload>
</form>
"""

# Teacher dashboard template
TEACHER_PAGE = """
<!doctype html>
<title>Teacher Dashboard</title>
<h2>Teacher Dashboard</h2>
<form method="get">
  Search: <input type="text" name="q" value="{{ q|default('') }}">
  <input type="submit" value="Search">
</form>
<br>
<table border="1" cellpadding="5">
  <tr>
    <th>Student Name</th>
    <th>Class</th>
    <th>Teacher Name</th>
    <th>File Name</th>
    <th>Upload Time</th>
    <th>Size (KB)</th>
    <th>Download</th>
  </tr>
  {% for it in items %}
  <tr>
    <td>{{ it.get('StudentName','') }}</td>
    <td>{{ it.get('ClassName','') }}</td>
    <td>{{ it.get('TeacherName','') }}</td>
    <td>{{ it.get('FileName','') }}</td>
    <td>{{ it.get('UploadTime','') }}</td>
    <td>{{ ('%.2f' % it['SizeKB']) }}</td>
    <td><a href="{{ it.get('FileURL','#') }}" target="_blank">Download</a></td>
  </tr>
  {% endfor %}
</table>
"""

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        student_name = request.form["student_name"]
        class_name = request.form["class_name"]
        teacher_name = request.form["teacher_name"]
        file = request.files["file"]

        if file:
            # ✅ Get actual file size before upload
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            file_key = f"{uuid.uuid4()}_{file.filename}"
            s3.upload_fileobj(file, S3_BUCKET, file_key)

            file_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
            upload_time = datetime.utcnow().isoformat()

            # ✅ Only insert into DynamoDB if all fields are provided
            if student_name and class_name and teacher_name:
                table.put_item(Item={
                    "ID": str(uuid.uuid4()),
                    "StudentName": student_name,
                    "ClassName": class_name,
                    "TeacherName": teacher_name,
                    "FileName": file.filename,
                    "FileKey": file_key,
                    "FileURL": file_url,
                    "Size": file_size,
                    "UploadTime": upload_time
                })

            return "File uploaded successfully!"
    return UPLOAD_PAGE


@app.route("/teacher")
def teacher_dashboard():
    q = request.args.get("q", "").strip().lower()
    resp = table.scan()
    items = resp.get("Items", [])

    # Convert Decimal to float for Size
    for it in items:
        try:
            it["SizeKB"] = float(it.get("Size", 0) or 0) / 1024.0
        except:
            it["SizeKB"] = 0.0

        # ✅ Generate presigned download link (forces browser download)
        if it.get("FileKey"):
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET,
                    'Key': it["FileKey"],
                    'ResponseContentDisposition': f'attachment; filename="{it.get("FileName", "file")}"'
                },
                ExpiresIn=3600  # 1 hour validity
            )
            it["FileURL"] = presigned_url

    if q:
        items = [
            it for it in items
            if q in str(it.get("StudentName", "")).lower()
            or q in str(it.get("ClassName", "")).lower()
            or q in str(it.get("TeacherName", "")).lower()
        ]

    return render_template_string(TEACHER_PAGE, items=items, q=q)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
