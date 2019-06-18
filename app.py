from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost", user="root", password="cyx19980413", db="Fins", charset="utf8mb4",
                             port=3306, cursorclass=pymysql.cursors.DictCursor, autocommit=True)


def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return dec


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/back2CFG")
@login_required
def back2CFG():
    return redirect(url_for("closeFG"))


@app.route("/home")
@login_required
def home():
    with connection.cursor() as cursor:
        query = "select avatar, bio from Person where username = %s"
        cursor.execute(query, session["username"])
        data = cursor.fetchone()

    return render_template("home.html", username=session["username"], avatar=data['avatar'], bio=data['bio'])


@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")


@app.route("/closeFG", methods=["GET"])
@login_required
def closeFG():
    return render_template("closeFG.html")


@app.route("/createFG", methods=["GET"])
@login_required
def createFG():
    return render_template("createFG.html")


@app.route("/images", methods=["GET"])
@login_required
def images():
    # query = "SELECT photoID, filePath, timestamp, photoOwner, caption, lname, fname FROM (SELECT photoID, filePath, timestamp, photoOwner, caption from Photo natural join Share natural join Belong where belong.username = %s) as t1 left join(select lname, fname, photoID from Person natural join Tag where acceptedTag = true) as t2 using(photoID) order by timestamp desc"
    query = "SELECT distinct photoID, filePath, timestamp, photoOwner, caption FROM " \
            "((SELECT distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Share natural join Belong where belong.username = %s)" \
            " union distinct " \
            "(select distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Follow where follow.followerUsername = %s and follow.followeeUsername = Photo.photoOwner and acceptedfollow = true and photo.allFollowers = true)" \
            "union distinct (select distinct photoID, filePath, timestamp, photoOwner, caption from Photo where photoOwner = %s)) as t" \
            " order by timestamp desc"
    with connection.cursor() as cursor:
        cursor.execute(query, (session['username'], session["username"], session["username"]))
    data = cursor.fetchall()

    return render_template("images.html", data=data)


@app.route("/chooseTag", methods=['POST'])
@login_required
def chooseTag():
    choice = request.form.get('tagbtn')
    with connection.cursor() as cursor:
        query = "select lname, fname, photoID from Person natural join Tag where acceptedTag = true and photoID = %s"
        cursor.execute(query, choice)
        data = cursor.fetchall()
    return render_template("showTag.html", data=data)




# @app.route("/showTag")
# @login_required
# def showTag():
#
#     return render_template("showTag.html")


@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]

        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")


@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        cap = request.form.get("captionInput")
        if request.form.get("allFollowerFlag"):
            allFollowerFlag = True
            query = "INSERT INTO photo (timestamp, filePath, photoOwner, caption, allFollowers) VALUES (%s, %s, %s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(query, (
                    time.strftime('%Y-%m-%d %H:%M:%S'), image_name, session['username'], cap, allFollowerFlag))

            # with connection.cursor() as cursor:
            #     query = "SELECT groupName, groupOwner FROM Belong WHERE username = %s"
            #     cursor.execute(query, session["username"])
            #     data = cursor.fetchall()
            #
            # with connection.cursor() as cursor:
            #     query = "select MAX(photoID) as ID from Photo"
            #     cursor.execute(query)
            #     ID = cursor.fetchall()
            #
            # for line in data:
            #     with connection.cursor() as cursor:
            #         query = "INSERT INTO Share VALUES (%s, %s, %s)"
            #         cursor.execute(query, (line['groupName'], line['groupOwner'], ID[0]['ID']))

            message = "Image has been successfully uploaded."
            return render_template("upload.html", message=message)
        else:
            allFollowerFlag = False
            query = "INSERT INTO photo (timestamp, filePath, photoOwner, caption, allFollowers) VALUES (%s, %s, %s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(query, (
                    time.strftime('%Y-%m-%d %H:%M:%S'), image_name, session['username'], cap, allFollowerFlag))

            with connection.cursor() as cursor:
                query = "SELECT groupName, groupOwner, ROW_NUMBER() OVER (ORDER BY groupName) AS No FROM Belong WHERE username = %s"
                cursor.execute(query, session["username"])
            data = cursor.fetchall()
            return render_template("shareCFG.html", data=data)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)


@app.route("/createfg", methods=["POST"])
@login_required
def createfg():
    FGname = request.form.get("groupName")
    try:
        with connection.cursor() as cursor:
            query1 = "INSERT INTO CloseFriendGroup (groupName, groupOwner) VALUES (%s, %s)"
            cursor.execute(query1, (FGname, session["username"]))
            query2 = "INSERT INTO Belong (groupName, groupOwner, username) VALUES (%s, %s, %s)"
            cursor.execute(query2, (FGname, session["username"], session["username"]))
            message = "Group Created Successfully."
    except:
        message = "Group already exits."
    return render_template("createFG.html", message=message)


@app.route("/addFriend")
@login_required
def addFriend():
    return render_template("addFriend.html")


@app.route("/addF", methods=["POST"])
@login_required
def addF():
    Fname = request.form.get("FriendName")
    Gname = request.form.get("GroupName")
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO Belong (groupName, groupOwner, username) VALUES (%s, %s, %s)"
            cursor.execute(query, (Gname, session["username"], Fname))
            message = "Add Successfully."
    except:
        message = "Failed. Please check group name and username or maybe user is already in the group."
    return render_template("addFriend.html", message=message)


@app.route("/myCFG")
@login_required
def myCFG():
    with connection.cursor() as cursor:
        query = "SELECT groupName, username FROM Belong WHERE groupOwner = %s"
        cursor.execute(query, (session["username"]))
        data = cursor.fetchall()
    return render_template("myCFG.html", data=data)


@app.route("/followSystem")
@login_required
def followSys():
    return render_template("followSystem.html")


@app.route("/followOther")
@login_required
def followOther():
    return render_template("followOther.html")


@app.route("/followReq")
@login_required
def followReq():
    with connection.cursor() as cursor:
        query = "SELECT followerUsername FROM Follow WHERE followeeUsername = %s AND acceptedfollow = False"
        cursor.execute(query, session["username"])
    data = cursor.fetchall()

    return render_template("followReq.html", data=data)


@app.route("/followerAccept", methods=['POST'])
@login_required
def folloerAccept():
    with connection.cursor() as cursor:
        query = "SELECT followerUsername FROM Follow WHERE followeeUsername = %s AND acceptedfollow = False"
        cursor.execute(query, session["username"])
        data = cursor.fetchall()
    accept = request.form.getlist('accept')
    decline = request.form.getlist('decline')

    for item in accept:
        with connection.cursor() as cursor:
            query = "update Follow set acceptedfollow = true where followerUsername = %s and followeeUsername = %s"
            cursor.execute(query, (item, session["username"]))

    for item in decline:
        with connection.cursor() as cursor:
            query = "delete from Follow where followerUsername = %s and followeeUsername = %s"
            cursor.execute(query, (item, session["username"]))

    return render_template("followSystem.html")


@app.route("/Fother", methods=["POST"])
@login_required
def Fother():
    F_user = request.form.get("Fusername")
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO Follow (followerUsername, followeeUsername, acceptedfollow) VALUES (%s, %s, %s)"
            cursor.execute(query, (session["username"], F_user, False))
            message = "Request sent."
    except pymysql.err.IntegrityError:
        message = "Failed. Please check the username you entered. Maybe you have already posted that request"
    return render_template("followOther.html", message=message)


@app.route("/shareCFG")
@login_required
def shareCFG():
    return render_template("shareCFG.html")


@app.route("/chooseCFG", methods=["POST"])
@login_required
def chooseCFG():
    with connection.cursor() as cursor:
        query = "SELECT groupName, groupOwner, ROW_NUMBER() OVER (ORDER BY groupName) AS No FROM Belong WHERE username = %s"
        cursor.execute(query, session["username"])
    data = cursor.fetchall()
    chosen = request.form.getlist('chosen')
    with connection.cursor() as cursor:
        query = "select MAX(photoID) as ID from Photo"
        cursor.execute(query)
        ID = cursor.fetchall()
    for CFG in chosen:
        with connection.cursor() as cursor:
            query = "INSERT INTO Share VALUES (%s, %s, %s)"
            cursor.execute(query, (data[int(CFG) - 1]['groupName'], data[int(CFG) - 1]['groupOwner'], ID[0]['ID']))
    message = 'Image has been successfully uploaded.'
    return render_template("upload.html", message=message)


@app.route("/tagSystem")
@login_required
def tagSystem():
    return render_template("tagSystem.html")


@app.route("/sendTag")
@login_required
def sendTag():
    with connection.cursor() as cursor:
        query = "SELECT distinct photoID, filePath, timestamp, photoOwner, caption FROM " \
            "((SELECT distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Share natural join Belong where belong.username = %s)" \
            " union distinct " \
            "(select distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Follow where follow.followerUsername = %s and follow.followeeUsername = Photo.photoOwner and acceptedfollow = true and photo.allFollowers = true)" \
            "union distinct (select distinct photoID, filePath, timestamp, photoOwner, caption from Photo where photoOwner = %s)) as t" \
            " order by timestamp desc"
        cursor.execute(query, (session["username"], session["username"], session["username"]))
        data = cursor.fetchall()
    return render_template("sendTag.html", data=data)


@app.route("/tagOther", methods=['POST'])
@login_required
def tagOther():
    photo = request.form.get("selection")
    user = request.form.get("tagUsername")
    with connection.cursor() as cursor:
        query = "SELECT distinct photoID, filePath, timestamp, photoOwner, caption FROM " \
            "((SELECT distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Share natural join Belong where belong.username = %s)" \
            " union distinct " \
            "(select distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Follow where follow.followerUsername = %s and follow.followeeUsername = Photo.photoOwner and acceptedfollow = true and photo.allFollowers = true)" \
            "union distinct (select distinct photoID, filePath, timestamp, photoOwner, caption from Photo where photoOwner = %s)) as t" \
            " order by timestamp desc"
        cursor.execute(query, (session["username"], session["username"], session["username"]))
        data = cursor.fetchall()
    try:
        with connection.cursor() as cursor:
            query = "SELECT distinct photoID, filePath, timestamp, photoOwner, caption FROM " \
            "((SELECT distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Share natural join Belong where belong.username = %s)" \
            " union distinct " \
            "(select distinct photoID, filePath, timestamp, photoOwner, caption from Photo natural join Follow where follow.followerUsername = %s and follow.followeeUsername = Photo.photoOwner and acceptedfollow = true and photo.allFollowers = true)" \
            "union distinct (select distinct photoID, filePath, timestamp, photoOwner, caption from Photo where photoOwner = %s)) as t" \
            " where photoID = %s"
            cursor.execute(query, (user, user, user, photo))
            temp = cursor.fetchall()
            print(temp)
            if temp:
                if user == session["username"]:
                    with connection.cursor() as cursor:
                        query = "insert into Tag values(%s, %s, true)"
                        cursor.execute(query, (user, int(photo)))
                else:
                    with connection.cursor() as cursor:
                        query = "insert into Tag values(%s, %s, false)"
                        cursor.execute(query, (user, int(photo)))
                message = "Send successfully."
            else:
                message = "This photo is not visible to the user."
    except:
        message = "Maybe you have already sent it or the user has already tagged it."
    return render_template("sendTag.html", message=message, data=data)


@app.route("/tagReq")
@login_required
def tagReq():
    with connection.cursor() as cursor:
        query = "select distinct filePath, photoID from Tag natural join Photo where Tag.username = %s and acceptedTag = false"
        cursor.execute(query, session["username"])
        data = cursor.fetchall()
    return render_template("tagReq.html", data=data)


@app.route("/tagAccept", methods=['POST'])
@login_required
def tagAccept():
    accept = request.form.getlist('accept')
    decline = request.form.getlist('decline')

    for item in accept:
        with connection.cursor() as cursor:
            query = "update Tag set acceptedTag = true where photoID = %s"
            cursor.execute(query, item)

    for item in decline:
        with connection.cursor() as cursor:
            query = "delete from Tag where photoID = %s and username = %s"
            cursor.execute(query, (item, session["username"]))

    with connection.cursor() as cursor:
        query = "select distinct filePath, photoID from Tag natural join Photo where Tag.username = %s and acceptedTag = false"
        cursor.execute(query, session["username"])
        data = cursor.fetchall()

    return render_template("/tagReq.html", data=data)


@app.route("/personFile")
@login_required
def personFile():
    return render_template("personFile.html")


@app.route("/profile", methods=["POST"])
@login_required
def profile():
    if request.files:
        image_file = request.files.get("avatar", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        bio = request.form.get("bio")
        with connection.cursor() as cursor:
            query = "update Person set bio = %s, avatar = %s where username = %s"
            cursor.execute(query, (bio, image_name, session["username"]))
            message = 'Successfully Saved.'

    else:
        message = "Fail to save."
    return render_template("personFile.html", message=message)



if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
