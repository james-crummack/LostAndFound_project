from flask import Flask, render_template, request, send_file, session, redirect, url_for
import mysql.connector
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import csv
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey123'

# --- MySQL Config ---
mysql_config = {
    'user': 'james',
    'password': 'groupq',
    'host': '34.147.246.76',
    'database': 'LostAndFound',
    'port': 3306
}

# --- MongoDB Config ---
mongo_uri = "mongodb+srv://james:groupq@lostandfoundcluster.wabnl2o.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
mongo_db = mongo_client["LostAndFound"]

sql_export = []
sql_export_headers = []
mongo_export = []
mongo_export_headers = []

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        try:
            conn = mysql.connector.connect(**mysql_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Users WHERE Email = %s AND Password_Hash = %s", (email, password))
            user = cursor.fetchone()

            if user:
                session["user_id"] = user["User_ID"]
                session["role"] = user["Role"]
                session["name"] = user["Name"]
                return redirect(url_for("index"))
            else:
                error = "Invalid credentials."
        except Exception as e:
            error = str(e)

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    global sql_export, sql_export_headers, mongo_export, mongo_export_headers
    sql_result = ""
    mongo_result = ""
    sql_tables = []
    mongo_collections = mongo_db.list_collection_names()

    # Get MySQL tables
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        sql_tables = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        sql_tables = [f"❌ Error: {e}"]
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

    if request.method == "POST" and "sql_query" in request.form:
        sql_query_raw = request.form["sql_query"]
        sql_query = sql_query_raw.strip().lower()
        user_role = session.get("role")
        allow_sql = False

        if user_role == "Admin":
            allow_sql = True
        elif user_role == "Employee":
            allowed_tables = ["claims", "lost_items"]
            is_allowed_table = any(
                f"from {t}" in sql_query or
                f"into {t}" in sql_query or
                f"update {t}" in sql_query or
                f"delete from {t}" in sql_query
                for t in allowed_tables
            )
            allow_sql = is_allowed_table

        if allow_sql:
            try:
                conn = mysql.connector.connect(**mysql_config)
                cursor = conn.cursor()
                cursor.execute(sql_query_raw)
                # 👇 Place this inside the SELECT query handler in the `/index` route:
                if sql_query.startswith("select"):
                    rows = cursor.fetchall()
                    sql_export_headers = [desc[0] for desc in cursor.description]

                    # Table match flags
                    is_claims_query = "from claims" in sql_query
                    is_items_query = "from lost_items" in sql_query
                    is_logs_query = "from item_logs" in sql_query
                    is_users_query = "from users" in sql_query

                    mongo_fields = []
                    mongo_collection = None
                    mongo_key = None
                    use_mongo = False

                    # Determine MongoDB mapping
                    if is_claims_query or is_items_query or is_logs_query:
                        mongo_fields = ["Image_URL", "Additional_Notes", "Tags"]
                        mongo_collection = "Lost_Items_Metadata"
                        mongo_key = "Item_ID"
                        use_mongo = True

                    elif is_users_query:
                        mongo_fields = ["Last_Action", "Last_Activity", "Recent_Message"]
                        mongo_collection = "User_Metadata_Combined"
                        mongo_key = "User_ID"
                        use_mongo = True

                        def build_user_metadata(uid):
                            activity = mongo_db["User_Activity_Logs"].find_one({"User_ID": uid}, sort=[("Timestamp", -1)])
                            notif = mongo_db["Notifications"].find_one({"User_ID": uid}, sort=[("Timestamp", -1)])
                            return {
                                "Last_Action": activity.get("Action") if activity else "",
                                "Last_Activity": activity.get("Timestamp") if activity else "",
                                "Recent_Message": notif.get("Message") if notif else ""
                            }

                    # Prepare headers
                    if use_mongo:
                        sql_export_headers += mongo_fields

                    # Merge SQL + MongoDB
                    merged_rows = []
                    for row in rows:
                        row_dict = dict(zip(sql_export_headers[:len(row)], row))  # slice only original headers

                        if use_mongo:
                            lookup_id = row_dict.get(mongo_key)
                            mongo_doc = {}

                            if is_users_query:
                                mongo_doc = build_user_metadata(lookup_id)
                            else:
                                mongo_doc = mongo_db[mongo_collection].find_one({mongo_key: lookup_id}) or {}

                            for field in mongo_fields:
                                row_dict[field] = mongo_doc.get(field, "")

                        merged_rows.append([row_dict.get(col, "") for col in sql_export_headers])

                    sql_export = merged_rows

                    # Render HTML Table
                    sql_result = f"<table class='table table-striped'><thead><tr>{''.join(f'<th>{col}</th>' for col in sql_export_headers)}</tr></thead><tbody>"
                    for row in sql_export:
                        sql_result += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
                    sql_result += "</tbody></table>"


                else:
                    conn.commit()
                    sql_result = "✅ SQL query executed successfully."
            except Exception as e:
                sql_result = f"❌ SQL Error: {e}"
            finally:
                if 'conn' in locals() and conn.is_connected():
                    conn.close()
        else:
            sql_result = "❌ You do not have permission to run this SQL query."

    if request.method == "POST" and "collection" in request.form and "mongo_query" in request.form:
        try:
            collection = request.form["collection"]
            mode = request.form.get("mode")
            raw_input = request.form["mongo_query"]
            parsed_input = eval(raw_input)

            user_role = session.get("role")
            user_id = session.get("user_id")

            if user_role == "User":
                if collection == "Notifications" or collection == "Lost_Items_Metadata":
                    parsed_input["User_ID"] = user_id
                else:
                    mongo_result = "❌ Access denied to this collection."
                    return render_template("index.html",
                                           sql_result=sql_result,
                                           mongo_result=mongo_result,
                                           sql_tables=sql_tables,
                                           mongo_collections=mongo_collections)

            if mode == "insert" and user_role in ["Admin", "Employee"]:
                mongo_db[collection].insert_one(parsed_input)
                mongo_result = "✅ Document inserted successfully."

            elif mode == "update" and user_role == "Admin":
                filter_query = parsed_input.get("filter", {})
                update_values = parsed_input.get("update", {})
                result = mongo_db[collection].update_many(filter_query, {'$set': update_values})
                mongo_result = f"✅ Updated {result.modified_count} document(s)."

            elif mode == "delete" and user_role == "Admin":
                result = mongo_db[collection].delete_many(parsed_input)
                mongo_result = f"✅ Deleted {result.deleted_count} document(s)."

            elif mode == "find":
                results = list(mongo_db[collection].find(parsed_input))
                mongo_export = results
                mongo_result = "<table class='table table-striped'><thead><tr>"
                if results:
                    mongo_export_headers = list(results[0].keys())
                    for col in mongo_export_headers:
                        mongo_result += f"<th>{col}</th>"
                    mongo_result += "</tr></thead><tbody>"
                    for doc in results:
                        mongo_result += "<tr>"
                        for col in mongo_export_headers:
                            mongo_result += f"<td>{doc.get(col, '')}</td>"
                        mongo_result += "</tr>"
                    mongo_result += "</tbody></table>"
                else:
                    mongo_result = "No matching documents found."

            else:
                mongo_result = "❌ You do not have permission to perform this MongoDB operation."

        except Exception as e:
            mongo_result = f"❌ MongoDB Error: {e}"

    return render_template("index.html",
                           sql_result=sql_result,
                           mongo_result=mongo_result,
                           sql_tables=sql_tables,
                           mongo_collections=mongo_collections)

@app.route("/download-csv")
def download_csv():
    global sql_export, sql_export_headers
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(sql_export_headers)
    cw.writerows(sql_export)
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output,
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='sql_query_results.csv')

@app.route("/download-mongo-csv")
def download_mongo_csv():
    global mongo_export, mongo_export_headers
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(mongo_export_headers)
    for doc in mongo_export:
        row = [doc.get(key, '') for key in mongo_export_headers]
        cw.writerow(row)
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output,
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='mongo_query_results.csv')

if __name__ == "__main__":
    app.run(debug=True)

