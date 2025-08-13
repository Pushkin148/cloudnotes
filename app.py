import boto3
from flask import Flask, request, render_template_string
from datetime import datetime

app = Flask(__name__)

AWS_REGION = "us-east-1"  # Your AWS region

# Initialize AWS clients with region
s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

S3_BUCKET = "cloudnotes-bucket-pushkin"
DYNAMODB_TABLE = "CloudNotesMetaData"

table = dynamodb.Table(DYNAMODB_TABLE)

# ---------------- Student Upload Page ----------------
@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            # Upload file to S3
            s3.upload_fileobj(file, S3_BUCKET, file.filename)

            # Save metadata to DynamoDB
            metadata = {
                "FileName": file.filename,
                "Bucket": S3_BUCKET,
                "ClassID": request.form.get("class_id", "unknown"),
                "Size": len(file.read()),
                "StudentID": request.form.get("student_id", "unknown"),
                "StudentName": request.form.get("student_name", "unknown"),
                "TeacherName": request.form.get("teacher_name", "unknown"),
                "UploadTime": datetime.utcnow().isoformat()
            }

            table.put_item(Item=metadata)

            return f"✅ Uploaded {file.filename} successfully."

    return '''
        <h2>Student Assignment Upload</h2>
        <form method="POST" enctype="multipart/form-data">
            Student Name: <input type="text" name="student_name"><br>
            Student ID: <input type="text" name="student_id"><br>
            Class ID: <input type="text" name="class_id"><br>
            Teacher Name: <input type="text" name="teacher_name"><br>
            File: <input type="file" name="file"><br><br>
            <input type="submit" value="Upload">
        </form>
    '''

# ---------------- Teacher View Page ----------------
@app.route("/teacher")
def teacher_view():
    response = table.scan()
    items = response.get("Items", [])

    html = "<h2>Uploaded Assignments</h2><table border='1'>"
    html += "<tr><th>File Name</th><th>Student Name</th><th>Student ID</th><th>Class ID</th><th>Teacher Name</th><th>Upload Time</th><th>Bucket</th></tr>"
    
    for item in items:
        html += f"<tr><td>{item.get('FileName')}</td><td>{item.get('StudentName')}</td><td>{item.get('StudentID')}</td><td>{item.get('ClassID')}</td><td>{item.get('TeacherName')}</td><td>{item.get('UploadTime')}</td><td>{item.get('Bucket')}</td></tr>"

    html += "</table>"
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
